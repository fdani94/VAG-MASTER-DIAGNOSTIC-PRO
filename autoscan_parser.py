import re
from dataclasses import dataclass, field
from pathlib import Path


# Module headers may be written as ``Address 01: Engine`` or as the compact
# Auto-Scan summary form ``01-Engine -- Status: ...``.  K-Line fault details
# also contain lines such as ``07-10 - Signal too Low`` / ``49-10 - No
# Communications``; the negative look-ahead prevents those sub-status bytes
# from being misclassified as controller addresses.
MODULE_RE = re.compile(r"^(?:Address\s+)?(?P<address>[0-9A-F]{2})[:\-]\s*(?!\d{1,3}\s*-)(?P<name>[^\r\n]+)", re.I)
MODULE_ALT_RE = re.compile(r"^Address\s+(?P<address>[0-9A-F]{2})\s*:\s*(?P<name>.+)$", re.I)
DTC_P_RE = re.compile(r"\b([PBCU][0-9A-F]{4})\b", re.I)
DTC_VAG_RE = re.compile(r"^\s*(\d{5})\s*-\s*(.+)$")
FAULT_COUNT_RE = re.compile(r"^\s*(\d+)\s+Faults?\s+Found\b", re.I | re.M)
NO_FAULT_RE = re.compile(r"No\s+fault\s+code\s+found", re.I)
VIN_RE = re.compile(r"\bVIN:\s*([A-HJ-NPR-Z0-9]{17})\b", re.I)
MILEAGE_RE = re.compile(r"(?:Mileage|Kilometerstand|Kilometrage):\s*([^\r\n]+)", re.I)
STATUS_WORDS = ("Intermittent", "Sporadic", "Static", "Confirmed", "Pending", "MIL ON", "No Signal", "Implausible", "Not Confirmed")


@dataclass
class ScanFault:
    module_address: str = ""
    module_name: str = ""
    code: str = ""
    vag_code: str = ""
    title: str = ""
    status: str = ""
    raw_block: str = ""
    freeze_frame: str = ""
    frequency: str = ""
    mileage: str = ""

    @property
    def key(self):
        return f"{self.module_address}:{self.code or self.vag_code}:{self.title}".lower()


@dataclass
class ScanModule:
    address: str
    name: str
    part_no: str = ""
    component: str = ""
    coding: str = ""
    faults: list = field(default_factory=list)
    declared_fault_count: int | None = None


@dataclass
class ScanResult:
    source_path: str
    vin: str = ""
    modules: list = field(default_factory=list)
    faults: list = field(default_factory=list)
    raw_text: str = ""
    declared_fault_count: int | None = None
    parsed_fault_count: int = 0
    validation_ok: bool | None = None
    validation_message: str = ""
    validation_details: list = field(default_factory=list)


def read_scan_file(path):
    path = Path(path)
    ext = path.suffix.lower()
    if ext in (".txt", ".log", ".csv"):
        for enc in ("utf-8-sig", "cp1252", "latin-1"):
            try:
                return path.read_text(encoding=enc, errors="strict")
            except UnicodeDecodeError:
                continue
        return path.read_text(encoding="utf-8", errors="replace")
    if ext == ".pdf":
        try:
            from pypdf import PdfReader
        except Exception as exc:
            raise RuntimeError("Suportul PDF necesită pachetul pypdf. Folosește TXT sau instalează pypdf.") from exc
        reader = PdfReader(str(path))
        pages = []
        for page in reader.pages:
            try:
                pages.append(page.extract_text(extraction_mode="layout") or "")
            except TypeError:
                pages.append(page.extract_text() or "")
        text = "\n".join(pages)
        if not text.strip():
            raise ValueError("PDF-ul nu conține text extractibil. Exportă Auto-Scan-ul ca TXT din VCDS.")
        return text
    raise ValueError("Format nesuportat. Încarcă Auto-Scan VCDS .TXT, .LOG sau PDF cu text.")


def _clean_module_name(name):
    name = re.sub(r"\s+Labels:.*$", "", name, flags=re.I)
    name = re.sub(r"\s+Control Module.*$", "", name, flags=re.I)
    return name.strip(" :-")


def _extract_status(block):
    hits = []
    low = block.lower()
    for word in STATUS_WORDS:
        if word.lower() in low:
            hits.append(word)
    return ", ".join(dict.fromkeys(hits))


def _extract_field(block, label):
    m = re.search(rf"{re.escape(label)}:\s*([^\r\n]+)", block, re.I)
    return m.group(1).strip() if m else ""


def _fault_from_block(block, module_address, module_name):
    lines = [x.rstrip() for x in block.splitlines() if x.strip()]
    if not lines:
        return None
    joined = "\n".join(lines)
    p = DTC_P_RE.search(joined)
    vag = ""
    title = ""
    m = DTC_VAG_RE.match(lines[0])
    if m:
        vag = m.group(1)
        title = m.group(2).strip()
    elif p:
        title = lines[0].strip()
    else:
        mf = re.search(r"Fault Code:\s*([PBCU][0-9A-F]{4}|\d{5,6})", joined, re.I)
        if not mf:
            return None
        if mf.group(1)[0].isalpha():
            p = mf
        else:
            vag = mf.group(1)
        title = lines[0].strip()
    code = p.group(1).upper() if p else ""
    if code and code in title.upper():
        title = re.sub(rf"\s*-?\s*{re.escape(code)}.*$", "", title, flags=re.I).strip(" -") or title
    freeze_lines = []
    in_freeze = False
    for line in lines:
        if "Freeze Frame" in line or "Fault Priority" in line or "Fault Frequency" in line:
            in_freeze = True
        if in_freeze:
            freeze_lines.append(line)
    return ScanFault(
        module_address=module_address,
        module_name=module_name,
        code=code,
        vag_code=vag,
        title=title,
        status=_extract_status(joined),
        raw_block=joined,
        freeze_frame="\n".join(freeze_lines),
        frequency=_extract_field(joined, "Fault Frequency"),
        mileage=_extract_field(joined, "Mileage") or _extract_field(joined, "Kilometerstand"),
    )


def _validate_result(result):
    """Cross-check VCDS-declared per-module fault totals against parsed DTCs."""
    details = []
    declared_total = 0
    modules_with_declaration = 0
    for module in result.modules:
        if module.declared_fault_count is None:
            continue
        modules_with_declaration += 1
        declared_total += module.declared_fault_count
        parsed = len(module.faults)
        if parsed != module.declared_fault_count:
            details.append(
                f"{module.address} {module.name}: VCDS declară {module.declared_fault_count}, parserul a extras {parsed}."
            )

    result.parsed_fault_count = len(result.faults)
    if modules_with_declaration:
        result.declared_fault_count = declared_total
        result.validation_ok = not details and declared_total == result.parsed_fault_count
        if result.validation_ok:
            result.validation_message = (
                f"VALIDARE OK: VCDS declară {declared_total} erori, iar aplicația a extras {result.parsed_fault_count}."
            )
        else:
            missing = max(0, declared_total - result.parsed_fault_count)
            extra = max(0, result.parsed_fault_count - declared_total)
            if missing:
                result.validation_message = (
                    f"ATENȚIE: {missing} erori declarate de VCDS nu au fost parsate. "
                    f"Declarate: {declared_total} • Extrase: {result.parsed_fault_count}."
                )
            elif extra:
                result.validation_message = (
                    f"ATENȚIE: parserul a extras {extra} intrări în plus față de totalul declarat de VCDS. "
                    f"Declarate: {declared_total} • Extrase: {result.parsed_fault_count}."
                )
            else:
                result.validation_message = "ATENȚIE: există neconcordanțe pe module, chiar dacă totalul general coincide."
    else:
        # A Fault Codes screen may not contain per-module "X Faults Found" declarations.
        result.declared_fault_count = None
        result.validation_ok = None
        result.validation_message = (
            "VALIDARE LIMITATĂ: raportul nu conține totaluri VCDS «X Faults Found» pe module; "
            f"au fost extrase {result.parsed_fault_count} erori."
        )
    result.validation_details = details
    return result


def parse_autoscan_text(text, source_path=""):
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    result = ScanResult(source_path=str(source_path), raw_text=text)
    vm = VIN_RE.search(text)
    if vm:
        result.vin = vm.group(1)

    lines = text.splitlines()
    current = None
    current_lines = []
    modules = []

    def finish_module():
        nonlocal current, current_lines
        if not current:
            return
        body = "\n".join(current_lines)
        current.part_no = _extract_field(body, "Part No SW") or _extract_field(body, "Part No")
        current.component = _extract_field(body, "Component")
        current.coding = _extract_field(body, "Coding")
        cm = FAULT_COUNT_RE.search(body)
        if cm:
            current.declared_fault_count = int(cm.group(1))
        elif NO_FAULT_RE.search(body):
            current.declared_fault_count = 0

        starts = []
        for i, line in enumerate(current_lines):
            if DTC_VAG_RE.match(line) or DTC_P_RE.search(line) or re.search(r"Fault Code:\s*([PBCU][0-9A-F]{4}|\d{5,6})", line, re.I):
                if any(x in line for x in ("Part No", "Coding", "Shop #")):
                    continue
                starts.append(i)
        dedup = []
        for pos in starts:
            if not dedup or pos - dedup[-1] > 1:
                dedup.append(pos)
        for n, start in enumerate(dedup):
            end = dedup[n + 1] if n + 1 < len(dedup) else len(current_lines)
            block = "\n".join(current_lines[start:end])
            fault = _fault_from_block(block, current.address, current.name)
            if fault and (fault.code or fault.vag_code):
                if fault.key not in {f.key for f in current.faults}:
                    current.faults.append(fault)
                    result.faults.append(fault)
        modules.append(current)
        current = None
        current_lines = []

    for line in lines:
        m = MODULE_ALT_RE.match(line.strip()) or MODULE_RE.match(line.strip())
        if m and m.group("address").upper() not in ("00",):
            finish_module()
            current = ScanModule(m.group("address").upper(), _clean_module_name(m.group("name")))
            current_lines = [line]
        elif current:
            current_lines.append(line)
    finish_module()
    result.modules = modules
    return _validate_result(result)


def parse_autoscan_file(path):
    return parse_autoscan_text(read_scan_file(path), str(path))


def _lookup_dtc(con, fault):
    candidates = []
    if fault.code:
        candidates.append(fault.code.upper())
    if fault.vag_code:
        candidates.append(fault.vag_code)
    for code in candidates:
        row = con.execute("SELECT * FROM dtcs WHERE upper(code)=upper(?) LIMIT 1", (code,)).fetchone()
        if row:
            return row
    return None


def diagnostic_plan(con, fault, generation_id=None, engine_id=None):
    row = _lookup_dtc(con, fault)
    if row:
        return {
            "found": True,
            "verified": bool(row["verified"]),
            "title": row["title"] or fault.title,
            "description": row["description"] or "",
            "symptoms": row["symptoms"] or "",
            "causes": row["causes"] or "",
            "component": row["component"] or "",
            "location": row["component_location"] or "",
            "parameters": row["vcds_parameters"] or "",
            "expected": row["expected_values"] or "",
            "test_path": row["test_path"] or "",
            "diagnosis": row["diagnosis"] or "",
            "repair": row["repair"] or "",
            "replacement": row["replacement_steps"] or "",
            "severity": row["severity"] or "",
            "status": fault.status,
            "freeze_frame": fault.freeze_frame,
        }
    return {
        "found": False,
        "verified": False,
        "title": fault.title or (fault.code or fault.vag_code),
        "description": "Cod identificat în Auto-Scan, dar fără fișă locală completă. Nu se inventează o procedură.",
        "symptoms": "",
        "causes": "Confirmă textul exact VCDS, controllerul, platforma și codul motor înainte de diagnostic.",
        "component": "De confirmat după documentația controllerului exact.",
        "location": "",
        "parameters": "Folosește Advanced Measuring Values / Measuring Blocks relevante sistemului raportor.",
        "expected": "Compară cu specificația de fabrică pentru platforma și motorul selectat.",
        "test_path": f"VCDS > Address {fault.module_address} > Fault Codes / Advanced Measuring Values",
        "diagnosis": "1) Salvează Auto-Scan complet. 2) Notează Freeze Frame. 3) Verifică alimentări, conectori și cablaj. 4) Măsoară parametrii live relevanți. 5) Repară cauza și repetă scanarea.",
        "repair": "Repară numai cauza confirmată prin măsurători/documentație.",
        "replacement": "După înlocuire: coding/adaptation/basic setting numai dacă procedura oficială pentru controllerul exact o cere; apoi test și Auto-Scan final.",
        "severity": "Nespecificat",
        "status": fault.status,
        "freeze_frame": fault.freeze_frame,
    }
