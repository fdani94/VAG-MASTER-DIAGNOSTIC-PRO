from __future__ import annotations

import re
from pathlib import Path

from data import ModuleResult, ScanFault, ScanResult, Vehicle
from localization import romanianize, status_in_romanian


VIN_RE = re.compile(r"\bVIN:\s*([A-HJ-NPR-Z0-9]{17})\b", re.IGNORECASE)
LICENSE_RE = re.compile(r"\bLicense Plate:\s*([^\r\n]+)", re.IGNORECASE)
MILEAGE_RE = re.compile(
    r"(?:Mileage|Kilometerstand|Kilometrage):\s*([0-9][0-9 .]*)\s*km",
    re.IGNORECASE,
)
CHASSIS_RE = re.compile(r"Chassis Type:\s*([^\r\n]+)", re.IGNORECASE)
SUMMARY_RE = re.compile(
    r"^\s*([0-9A-F]{2})-([^\r\n]+?)\s*--\s*Status:\s*([^\r\n]+)$",
    re.IGNORECASE | re.MULTILINE,
)
ADDRESS_RE = re.compile(
    r"^\s*Address\s+([0-9A-F]{2})\s*:\s*([^\r\n]+)$",
    re.IGNORECASE,
)
FAULT_COUNT_RE = re.compile(r"^\s*(\d+)\s+Faults?\s+Found\b", re.IGNORECASE | re.MULTILINE)
NO_FAULT_RE = re.compile(r"No\s+fault\s+code\s+found", re.IGNORECASE)
SAE_RE = re.compile(r"\b([PBCU][0-9A-F]{4})(?:[0-9A-F]{2})?\b", re.IGNORECASE)
SAE_START_RE = re.compile(r"^\s*([PBCU][0-9A-F]{4})(?:[0-9A-F]{2})?\b(.*)$", re.IGNORECASE)
VAG_START_RE = re.compile(r"^\s*(\d{4,6})\s+-\s+(.+)$")
FAULT_CODE_RE = re.compile(
    r"^\s*Fault Code:\s*([PBCU][0-9A-F]{4})(?:[0-9A-F]{2})?|\bFault Code:\s*(\d{4,6})",
    re.IGNORECASE,
)
VBATT_RE = re.compile(
    r"VBatt\s+start/end:\s*([0-9.]+)V\s*/\s*([0-9.]+)V",
    re.IGNORECASE,
)
STATUS_TERMS = (
    "Intermittent",
    "Sporadic",
    "Static",
    "Not Confirmed",
    "Confirmed",
    "Pending",
    "MIL ON",
    "No Signal",
    "Implausible",
    "Permanent",
)

VIN_YEAR_CODES = "123456789ABCDEFGHJKLMNPRSTVWXY"
CHASSIS_MAP: tuple[tuple[str, str, str, str], ...] = (
    ("8K", "Audi", "A4 B8 (8K)", "MLB"),
    ("8T", "Audi", "A5 (8T)", "MLB"),
    ("8R", "Audi", "Q5 (8R)", "MLB"),
    ("4F", "Audi", "A6 C6 (4F)", "PL47"),
    ("4G", "Audi", "A6/A7 C7 (4G)", "MLB"),
    ("4K", "Audi", "A6/A7 C8 (4K)", "MLB Evo"),
    ("8V", "Audi", "A3 (8V)", "MQB"),
    ("8Y", "Audi", "A3 (8Y)", "MQB Evo"),
    ("8P", "Audi", "A3 (8P)", "PQ35"),
    ("4L", "Audi", "Q7 (4L)", "PL71"),
    ("4M", "Audi", "Q7 (4M)", "MLB Evo"),
    ("1J", "Volkswagen", "Golf IV / Bora (1J)", "PQ34"),
    ("1K", "Volkswagen", "Golf V / Jetta (1K)", "PQ35"),
    ("5K", "Volkswagen", "Golf VI (5K)", "PQ35"),
    ("5G", "Volkswagen", "Golf VII (5G)", "MQB"),
    ("CD", "Volkswagen", "Golf VIII (CD)", "MQB Evo"),
    ("3B", "Volkswagen", "Passat B5 (3B)", "PL45"),
    ("3C", "Volkswagen", "Passat B6 (3C)", "PQ46"),
    ("36", "Volkswagen", "Passat B7 (36)", "PQ46"),
    ("3G", "Volkswagen", "Passat B8 (3G)", "MQB"),
    ("6R", "Volkswagen", "Polo (6R)", "PQ25"),
    ("6C", "Volkswagen", "Polo (6C)", "PQ25"),
    ("AW", "Volkswagen", "Polo (AW)", "MQB A0"),
    ("5N", "Volkswagen", "Tiguan (5N)", "PQ35"),
    ("AD", "Volkswagen", "Tiguan (AD)", "MQB"),
    ("1Z", "Škoda", "Octavia II (1Z)", "PQ35"),
    ("5E", "Škoda", "Octavia III (5E)", "MQB"),
    ("NX", "Škoda", "Octavia IV (NX)", "MQB Evo"),
    ("3T", "Škoda", "Superb II (3T)", "PQ46"),
    ("3V", "Škoda", "Superb III (3V)", "MQB"),
    ("5J", "Škoda", "Fabia II (5J)", "PQ25"),
    ("6V", "Škoda", "Fabia III (6V)", "PQ26"),
    ("1P", "SEAT / Cupra", "Leon II (1P)", "PQ35"),
    ("5F", "SEAT / Cupra", "Leon III (5F)", "MQB"),
    ("KL", "SEAT / Cupra", "Leon IV (KL)", "MQB Evo"),
    ("6J", "SEAT / Cupra", "Ibiza IV (6J)", "PQ25"),
    ("KJ", "SEAT / Cupra", "Ibiza V (KJ)", "MQB A0"),
)


def read_scan_file(path: str | Path) -> str:
    file_path = Path(path)
    extension = file_path.suffix.casefold()
    if extension in (".txt", ".log", ".csv"):
        for encoding in ("utf-8-sig", "cp1252", "latin-1"):
            try:
                return file_path.read_text(encoding=encoding, errors="strict")
            except UnicodeDecodeError:
                continue
        return file_path.read_text(encoding="utf-8", errors="replace")
    if extension == ".pdf":
        try:
            from pypdf import PdfReader
        except Exception as exc:
            raise RuntimeError(
                "Citirea PDF necesită pachetul pypdf. Reinstalați aplicația din pachetul complet."
            ) from exc
        reader = PdfReader(str(file_path))
        pages: list[str] = []
        for page in reader.pages:
            try:
                text = page.extract_text(extraction_mode="layout") or ""
            except TypeError:
                text = page.extract_text() or ""
            pages.append(text)
        result = "\n".join(pages)
        if not result.strip():
            raise ValueError(
                "PDF-ul nu conține text extractibil. Exportați Auto-Scan-ul direct din VCDS ca PDF sau TXT; PDF-urile scanate ca imagine necesită OCR."
            )
        return result
    raise ValueError("Format nesuportat. Selectați Auto-Scan VCDS .TXT, .LOG, .CSV sau .PDF.")


def _field(block: str, label: str) -> str:
    match = re.search(rf"{re.escape(label)}:\s*([^\r\n]+)", block, re.IGNORECASE)
    return match.group(1).strip() if match else ""


def _module_name(value: str) -> str:
    value = re.sub(r"\s+Labels:.*$", "", value, flags=re.IGNORECASE)
    value = value.strip(" :-")
    translations = (
        ("Door Elect, Driver", "Electronică ușă șofer"),
        ("Door Elect, Pass.", "Electronică ușă pasager"),
        ("Door, Rear Left", "Ușă spate stânga"),
        ("Door, Rear Right", "Ușă spate dreapta"),
        ("Park/Steer Assist", "Asistență parcare/direcție"),
        ("Acc/Start Auth.", "Autorizare acces/pornire"),
        ("Steering Angle", "Unghi volan"),
        ("Steering wheel", "Volan și coloană direcție"),
        ("Central Conv.", "Confort centralizat"),
        ("Cent. Elect.", "Electronică centrală"),
        ("Auto HVAC", "Climatizare automată"),
        ("ABS Brakes", "Frâne ABS/ESP"),
        ("CAN Gateway", "Gateway CAN"),
        ("Parking Brake", "Frână de parcare"),
        ("Instruments", "Panou instrumente"),
        ("Telephone", "Telefon"),
        ("Airbags", "Airbag"),
        ("Engine", "Motor"),
    )
    for source, target in translations:
        value = re.sub(re.escape(source), target, value, flags=re.IGNORECASE)
    return romanianize(value)


def _fault_status(block: str) -> str:
    low = block.casefold()
    found = []
    for term in STATUS_TERMS:
        if term.casefold() not in low:
            continue
        if term == "Confirmed" and "not confirmed" in low:
            continue
        found.append(status_in_romanian(term))
    return ", ".join(dict.fromkeys(found))


def _normalize_vag_code(value: str) -> str:
    digits = value.strip()
    if len(digits) == 6 and digits.startswith("0"):
        return digits[1:]
    if len(digits) == 4:
        return digits.zfill(5)
    return digits


def _fault_from_block(block: str, address: str, module_name: str) -> ScanFault | None:
    lines = [line.rstrip() for line in block.splitlines() if line.strip()]
    if not lines:
        return None
    joined = "\n".join(lines)
    sae = SAE_RE.search(joined)
    vag_match = VAG_START_RE.match(lines[0])
    vag_code = _normalize_vag_code(vag_match.group(1)) if vag_match else ""
    title = vag_match.group(2).strip() if vag_match else ""

    if not title and lines:
        fault_code = FAULT_CODE_RE.search(lines[0])
        if fault_code and len(lines) > 1:
            title = lines[1].strip()
        else:
            modern = SAE_START_RE.match(lines[0])
            if modern:
                suffix = modern.group(2).strip(" -")
                suffix = re.sub(r"^(?:[0-9A-F]{2}\s*-\s*)+", "", suffix, flags=re.IGNORECASE)
                title = suffix or lines[0].strip()
    if not sae and not vag_code:
        return None

    freeze_index = next(
        (
            index
            for index, line in enumerate(lines)
            if "freeze frame" in line.casefold() or "fault priority" in line.casefold()
        ),
        -1,
    )
    freeze = "\n".join(lines[freeze_index:]) if freeze_index >= 0 else ""
    return ScanFault(
        module_address=address,
        module_name=module_name,
        code=sae.group(1).upper() if sae else "",
        vag_code=vag_code,
        title=title or (sae.group(1).upper() if sae else vag_code),
        status=_fault_status(joined),
        raw_block=joined,
        freeze_frame=freeze,
        frequency=_field(joined, "Fault Frequency"),
        mileage=_field(joined, "Mileage") or _field(joined, "Kilometerstand"),
        priority=_field(joined, "Fault Priority"),
    )


def _fault_starts(lines: list[str]) -> list[int]:
    candidates: list[int] = []
    for index, line in enumerate(lines):
        if VAG_START_RE.match(line) or SAE_START_RE.match(line) or FAULT_CODE_RE.search(line):
            if any(token in line for token in ("Part No", "Coding", "Shop #", "ASAM", "ROD")):
                continue
            candidates.append(index)
    result: list[int] = []
    for index in candidates:
        if result and index - result[-1] <= 1:
            previous = lines[result[-1]]
            if VAG_START_RE.match(previous) and SAE_START_RE.match(lines[index]):
                continue
        result.append(index)
    return result


def _parse_detail_sections(text: str) -> dict[str, ModuleResult]:
    lines = text.splitlines()
    sections: list[tuple[str, str, list[str]]] = []
    current_address = ""
    current_name = ""
    current_lines: list[str] = []

    def finish() -> None:
        nonlocal current_address, current_name, current_lines
        if current_address:
            sections.append((current_address, current_name, current_lines))
        current_address, current_name, current_lines = "", "", []

    for line in lines:
        match = ADDRESS_RE.match(line)
        if match:
            finish()
            current_address = match.group(1).upper()
            current_name = _module_name(match.group(2))
            current_lines = [line]
        elif current_address:
            current_lines.append(line)
    finish()

    modules: dict[str, ModuleResult] = {}
    for address, name, body_lines in sections:
        body = "\n".join(body_lines)
        count_match = FAULT_COUNT_RE.search(body)
        declared = int(count_match.group(1)) if count_match else (0 if NO_FAULT_RE.search(body) else None)
        faults: list[ScanFault] = []
        starts = _fault_starts(body_lines)
        for position, start in enumerate(starts):
            end = starts[position + 1] if position + 1 < len(starts) else len(body_lines)
            fault = _fault_from_block("\n".join(body_lines[start:end]), address, name)
            if fault and fault.key not in {item.key for item in faults}:
                faults.append(fault)
        modules[address] = ModuleResult(
            address=address,
            name=name,
            status=f"{len(faults)} erori" if faults else "OK",
            dtc_count=len(faults),
            part_no=(_field(body, "Part No SW") or _field(body, "Part No")).split(" HW:")[0].strip(),
            component=_field(body, "Component"),
            coding=_field(body, "Coding"),
            faults=faults,
            declared_fault_count=declared,
        )
    return modules


def _merge_modules(text: str, details: dict[str, ModuleResult]) -> list[ModuleResult]:
    order: list[str] = []
    summaries: dict[str, tuple[str, str]] = {}
    for address, name, raw_status in SUMMARY_RE.findall(text):
        address = address.upper()
        if address not in order:
            order.append(address)
        summaries[address] = (_module_name(name), status_in_romanian(raw_status))
    for address in details:
        if address not in order:
            order.append(address)

    result: list[ModuleResult] = []
    for address in order:
        detail = details.get(address)
        summary_name, summary_status = summaries.get(address, ("", "Necitit"))
        if detail:
            detail.name = detail.name or summary_name
            if detail.dtc_count:
                detail.status = f"{detail.dtc_count} erori"
            else:
                detail.status = summary_status if summary_status != "Eroare" else "OK"
            result.append(detail)
        else:
            result.append(
                ModuleResult(
                    address=address,
                    name=summary_name or f"Modul {address}",
                    status=summary_status,
                    dtc_count=1 if summary_status in ("Eroare", "Fără comunicare") else 0,
                )
            )
    return result


def _brand_from_vin(vin: str) -> str:
    prefix = vin[:3].upper()
    if prefix in {"WAU", "TRU"}:
        return "Audi"
    if prefix in {"TMB", "TMP"}:
        return "Škoda"
    if prefix in {"VSS"}:
        return "SEAT / Cupra"
    if prefix.startswith("WV"):
        return "Volkswagen"
    return "VAG"


def _year_from_vin(vin: str) -> int:
    if len(vin) != 17:
        return 0
    code = vin[9].upper()
    if code not in VIN_YEAR_CODES:
        return 0
    offset = VIN_YEAR_CODES.index(code)
    candidates = [2001 + offset, 2031 + offset]
    valid = [year for year in candidates if 1996 <= year <= 2027]
    return max(valid) if valid else 0


def _identity_from_chassis(chassis: str, brand: str) -> tuple[str, str, str]:
    prefix = re.split(r"[-/ ]", chassis.upper())[0]
    for code, mapped_brand, model, platform in CHASSIS_MAP:
        if prefix.startswith(code) and (brand in ("VAG", mapped_brand) or mapped_brand.startswith(brand)):
            return mapped_brand, model, platform
    return brand, f"Vehicul {prefix}" if prefix else "Vehicul identificat", "Platformă de confirmat"


def _vehicle(
    text: str,
    modules: list[ModuleResult],
    vin: str,
    mileage: int,
    chassis: str,
    license_plate: str,
) -> Vehicle:
    brand = _brand_from_vin(vin)
    brand, model, platform = _identity_from_chassis(chassis, brand)
    engine_module = next((module for module in modules if module.address == "01"), None)
    engine_code = ""
    if engine_module:
        match = re.search(r"\((?:J\d+-)?([A-Z0-9]{3,5})\)", engine_module.name)
        if match:
            engine_code = match.group(1)
    engine = " - ".join(
        value for value in (engine_code, engine_module.component if engine_module else "") if value
    ) or "Motorizare de confirmat din raport"
    return Vehicle(
        brand=brand,
        model=model,
        year=_year_from_vin(vin),
        engine=engine,
        engine_code=engine_code,
        chassis=chassis,
        platform=platform,
        vin=vin or "VIN nedetectat",
        license_plate=license_plate,
        mileage_km=mileage,
        modules=len(modules),
    )


def _validate(scan: ScanResult) -> None:
    details: list[str] = []
    declared_total = 0
    declarations = 0
    for module in scan.modules:
        if module.declared_fault_count is None:
            continue
        declarations += 1
        declared_total += module.declared_fault_count
        if module.declared_fault_count != len(module.faults):
            details.append(
                f"{module.address} {module.name}: VCDS declară {module.declared_fault_count}, aplicația a extras {len(module.faults)}."
            )
    scan.parsed_fault_count = len(scan.faults)
    scan.declared_fault_count = declared_total if declarations else None
    if declarations:
        scan.validation_ok = not details and declared_total == scan.parsed_fault_count
        if scan.validation_ok:
            scan.validation_message = (
                f"VALIDARE COMPLETĂ: VCDS declară {declared_total} erori, iar aplicația a extras {scan.parsed_fault_count}."
            )
        else:
            scan.validation_message = (
                "ATENȚIE: numărul erorilor extrase nu corespunde complet raportului VCDS. "
                f"Declarate: {declared_total}; extrase: {scan.parsed_fault_count}."
            )
    else:
        scan.validation_ok = None
        scan.validation_message = (
            "VALIDARE PARȚIALĂ: raportul nu conține totaluri «X Faults Found» pe module; "
            f"au fost extrase {scan.parsed_fault_count} erori."
        )
    scan.validation_details = details


def parse_autoscan_text(text: str, source_name: str = "Auto-Scan importat") -> ScanResult:
    if not text.strip():
        raise ValueError("Fișierul Auto-Scan este gol.")
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    vin_match = VIN_RE.search(normalized)
    mileage_match = MILEAGE_RE.search(normalized)
    chassis_match = CHASSIS_RE.search(normalized)
    license_match = LICENSE_RE.search(normalized)
    vin = vin_match.group(1).upper() if vin_match else ""
    mileage = (
        int(re.sub(r"\D", "", mileage_match.group(1)))
        if mileage_match and re.sub(r"\D", "", mileage_match.group(1))
        else 0
    )
    chassis = chassis_match.group(1).strip() if chassis_match else ""
    license_plate = license_match.group(1).strip() if license_match else ""

    detail_modules = _parse_detail_sections(normalized)
    modules = _merge_modules(normalized, detail_modules)
    faults = [fault for module in modules for fault in module.faults]
    if not modules and not faults:
        raise ValueError(
            "Fișierul nu pare a fi un Auto-Scan VCDS: nu au fost găsite module sau coduri de eroare."
        )
    scan = ScanResult(
        vehicle=_vehicle(normalized, modules, vin, mileage, chassis, license_plate),
        modules=modules,
        faults=faults,
        source_name=source_name,
        source_path=source_name,
        raw_text=normalized,
    )
    voltage = VBATT_RE.search(normalized)
    if voltage:
        scan.voltage_start = float(voltage.group(1))
        scan.voltage_end = float(voltage.group(2))
    _validate(scan)
    return scan


def parse_autoscan_file(path: str | Path) -> ScanResult:
    file_path = Path(path)
    return parse_autoscan_text(read_scan_file(file_path), file_path.name)
