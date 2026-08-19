import re
from dataclasses import dataclass, field
from pathlib import Path


MODULE_RE = re.compile(r"^(?:Address\s+)?(?P<address>[0-9A-F]{2})[:\-]\s*(?P<name>[^\r\n]+)", re.I)
MODULE_ALT_RE = re.compile(r"^Address\s+(?P<address>[0-9A-F]{2})\s*:\s*(?P<name>.+)$", re.I)
DTC_P_RE = re.compile(r"\b([PBCU][0-9A-F]{4})\b", re.I)
DTC_VAG_RE = re.compile(r"^\s*(\d{5})\s*-\s*(.+)$")
FAULT_COUNT_RE = re.compile(r"^\s*(\d+)\s+Faults?\s+Found", re.I)
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


@dataclass
class ScanResult:
    source_path: str
    vin: str = ""
    modules: list = field(default_factory=list)
    faults: list = field(default_factory=list)
    raw_text: str = ""


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
        # Prefer the first non-metadata line as title.
        title = lines[0].strip()
    else:
        # UDS reports may put a code after "Fault Code:".
        mf = re.search(r"Fault Code:\s*([PBCU][0-9A-F]{4}|\d{5,6})", joined, re.I)
        if not mf:
            return None
        if mf.group(1)[0].isalpha():
            p = mf
        else:
            vag = mf.group(1)
        title = lines[0].strip()
    code = p.group(1).upper() if p else ""
    # Trim common VCDS suffix from first-line title.
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
        # Fault blocks usually begin with 5-digit VAG number or a P/B/C/U code line.
        starts = []
        for i, line in enumerate(current_lines):
            if DTC_VAG_RE.match(line) or DTC_P_RE.search(line) or re.search(r"Fault Code:\s*([PBCU][0-9A-F]{4}|\d{5,6})", line, re.I):
                if any(x in line for x in ("Part No", "Coding", "Shop #")):
                    continue
                starts.append(i)
        # Remove nested duplicate starts: keep a new block only after some separation.
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
            # VCDS summary starts after full controller details; stop at Scan/End lines only if next module not found.
            current_lines.append(line)
    finish_module()
    result.modules = modules

    # Fallback for a Fault Codes screen / PDF that has no Address headers.
    if not result.faults:
        chunks = re.split(r"\n\s*\n", text)
        for chunk in chunks:
            if DTC_P_RE.search(chunk) or DTC_VAG_RE.match(chunk.strip()):
                f = _fault_from_block(chunk, "", "Necunoscut")
                if f and f.key not in {x.key for x in result.faults}:
                    result.faults.append(f)
    return result


def parse_autoscan_file(path):
    return parse_autoscan_text(read_scan_file(path), path)


def normalize_code(code):
    if not code:
        return ""
    code = code.strip().upper()
    m = DTC_P_RE.search(code)
    if m:
        return m.group(1).upper()
    d = re.search(r"\b\d{5,6}\b", code)
    return d.group(0) if d else code


def lookup_dtc(con, fault):
    candidates = []
    for x in (fault.code, fault.vag_code):
        x = normalize_code(x)
        if x and x not in candidates:
            candidates.append(x)
    for code in candidates:
        row = con.execute("SELECT * FROM dtcs WHERE UPPER(code)=?", (code.upper(),)).fetchone()
        if row:
            return row
    # Search aliases inside title/description, useful for 16683/P0299/000665 style entries.
    for code in candidates:
        row = con.execute("SELECT * FROM dtcs WHERE UPPER(title) LIKE ? OR UPPER(description) LIKE ? LIMIT 1", (f"%{code}%", f"%{code}%")).fetchone()
        if row:
            return row
    return None


def diagnostic_plan(con, fault, generation_id=None, engine_id=None):
    row = lookup_dtc(con, fault)
    base = {
        "found": bool(row),
        "code": fault.code or fault.vag_code,
        "module": f"{fault.module_address} {fault.module_name}".strip(),
        "scan_title": fault.title,
        "status": fault.status or "Nespecificat în raport",
        "freeze_frame": fault.freeze_frame or fault.raw_block,
    }
    if row:
        keys = set(row.keys())
        def g(key, default=""):
            return row[key] if key in keys and row[key] else default
        base.update({
            "title": g("title", fault.title),
            "description": g("description", ""),
            "symptoms": g("symptoms", ""),
            "causes": g("causes", ""),
            "component": g("component", "Confirmă piesa după cod motor și controller."),
            "location": g("component_location", "Locația exactă diferă după model/motor; confirmă după cod motor."),
            "parameters": g("vcds_parameters", "Folosește Advanced Measuring Values și caută parametrul aferent sistemului."),
            "expected": g("expected_values", "Compară valoarea actuală cu specified/target și cu limitele controllerului."),
            "test_path": g("test_path", "Intră în modulul indicat de Auto-Scan și verifică Fault Codes + Advanced Measuring Values."),
            "diagnosis": g("diagnosis", ""),
            "repair": g("repair", ""),
            "replacement": g("replacement_steps", "După confirmarea defectului, urmează manualul de reparație pentru demontare/montare."),
            "severity": g("severity", "Mediu"),
            "verified": bool(g("verified", 0)),
        })
    else:
        base.update({
            "title": fault.title or "DTC neindexat încă",
            "description": "Codul a fost extras corect din Auto-Scan, dar nu are încă o fișă completă în baza locală.",
            "symptoms": "Folosește simptomele mașinii și statusul/Freeze Frame din raport.",
            "causes": "Nu schimba o piesă doar pe baza codului. Verifică alimentare, masă, siguranțe, cablaj, conectori și valorile live ale sistemului înainte de înlocuire.",
            "component": "De stabilit după textul exact al DTC-ului, modul și codul motor.",
            "location": "De confirmat după model/generație/motor.",
            "parameters": "În modulul care a raportat eroarea: Advanced Measuring Values / Measuring Blocks; caută numele senzorului/actuatorului din DTC și valorile specified/actual.",
            "expected": "Nu există o valoare universală. Folosește limitele controllerului și comparația specified vs actual.",
            "test_path": f"[{fault.module_address or 'modul'} - {fault.module_name}] > [Fault Codes] > [Advanced Measuring Values] / [Output Tests] / [Basic Settings] numai dacă sunt relevante.",
            "diagnosis": "1) Salvează Auto-Scan-ul. 2) Notează dacă eroarea este statică sau intermitentă și Freeze Frame. 3) Verifică tensiunea bateriei. 4) Inspectează cablajul/conectorii. 5) Verifică valorile live. 6) Folosește Output Tests/Basic Settings doar dacă procedura controllerului o cere. 7) Repară cauza, șterge DTC și repetă Auto-Scan.",
            "repair": "Fișa exactă trebuie adăugată în baza KID Diagnostic înainte de a recomanda înlocuirea unei piese.",
            "replacement": "Nu se recomandă înlocuirea automată a unei piese pentru un DTC neindexat.",
            "severity": "De evaluat",
            "verified": False,
        })
    return base


def compare_results(before, after):
    b = {f.key: f for f in before.faults}
    a = {f.key: f for f in after.faults}
    resolved = [b[k] for k in b.keys() - a.keys()]
    remaining = [a[k] for k in b.keys() & a.keys()]
    new = [a[k] for k in a.keys() - b.keys()]
    return resolved, remaining, new
