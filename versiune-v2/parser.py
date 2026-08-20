from __future__ import annotations

import re
from pathlib import Path

from data import ModuleResult, ScanResult, Vehicle

VIN_RE = re.compile(r"\bVIN:\s*([A-HJ-NPR-Z0-9]{17})\b", re.IGNORECASE)
MILEAGE_RE = re.compile(r"Mileage:\s*(\d+)\s*km", re.IGNORECASE)
MODULE_STATUS_RE = re.compile(
    r"^\s*([0-9A-F]{2})-([^\r\n-]+?)\s*--\s*Status:\s*([^\r\n]+)$",
    re.IGNORECASE | re.MULTILINE,
)
ADDRESS_RE = re.compile(
    r"^\s*Address\s+([0-9A-F]{2}):\s*([^\r\n(]+)",
    re.IGNORECASE | re.MULTILINE,
)
OBD_DTC_RE = re.compile(r"\b([PBCU][0-9A-F]{4})\b", re.IGNORECASE)
VAG_DTC_RE = re.compile(r"^\s*(\d{5})\s+-\s+[^\r\n]+", re.MULTILINE)
CHASSIS_RE = re.compile(r"Chassis Type:\s*([^\r\n]+)", re.IGNORECASE)


def _clean_module_name(value: str) -> str:
    return " ".join(value.replace("Elect.", "Electronică").split())


def _status_from_vcds(raw: str) -> tuple[str, int]:
    lowered = raw.casefold()
    if "malfunction" in lowered or "defect" in lowered:
        return "Eroare", 1
    if "cannot be reached" in lowered or "no communication" in lowered:
        return "Fără comunicare", 1
    if "ok" in lowered:
        return "OK", 0
    return raw.strip(), 0


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        value = value.upper()
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def parse_autoscan_text(text: str, source_name: str = "Auto-Scan importat") -> ScanResult:
    if not text.strip():
        raise ValueError("Fișierul Auto-Scan este gol.")

    vin_match = VIN_RE.search(text)
    mileage_match = MILEAGE_RE.search(text)
    chassis_match = CHASSIS_RE.search(text)

    modules: list[ModuleResult] = []
    for address, name, status_raw in MODULE_STATUS_RE.findall(text):
        status, dtc_count = _status_from_vcds(status_raw)
        modules.append(
            ModuleResult(address.upper(), _clean_module_name(name), status, dtc_count)
        )

    if not modules:
        seen_addresses: set[str] = set()
        for address, name in ADDRESS_RE.findall(text):
            address = address.upper()
            if address in seen_addresses:
                continue
            seen_addresses.add(address)
            modules.append(ModuleResult(address, _clean_module_name(name), "Citit", 0))

    dtc_codes = _dedupe(OBD_DTC_RE.findall(text) + VAG_DTC_RE.findall(text))
    malfunction_slots = [index for index, module in enumerate(modules) if module.dtc_count]
    if dtc_codes and modules and not malfunction_slots:
        first = modules[0]
        modules[0] = ModuleResult(first.address, first.name, f"{len(dtc_codes)} erori", len(dtc_codes))

    vehicle = Vehicle(
        brand="VAG",
        model=(chassis_match.group(1).strip() if chassis_match else "Vehicul detectat"),
        year=0,
        engine="Identificare din Auto-Scan",
        vin=(vin_match.group(1).upper() if vin_match else "VIN nedetectat"),
        mileage_km=(int(mileage_match.group(1)) if mileage_match else 0),
        modules=len(modules),
    )
    return ScanResult(
        vehicle=vehicle,
        modules=modules,
        dtc_codes=dtc_codes,
        source_name=source_name,
        raw_text=text,
    )


def parse_autoscan_file(path: str | Path) -> ScanResult:
    file_path = Path(path)
    try:
        text = file_path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        text = file_path.read_text(encoding="cp1252", errors="replace")
    return parse_autoscan_text(text, file_path.name)
