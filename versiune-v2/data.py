from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from functools import lru_cache

from localization import romanianize


@dataclass(frozen=True)
class Vehicle:
    brand: str = ""
    model: str = ""
    year: int = 0
    engine: str = ""
    engine_code: str = ""
    chassis: str = ""
    platform: str = ""
    vin: str = ""
    license_plate: str = ""
    mileage_km: int = 0
    modules: int = 0

    @property
    def display_name(self) -> str:
        if self.brand or self.model:
            return " ".join(x for x in (self.brand, self.model) if x).strip()
        return "Niciun vehicul încărcat"

    @property
    def subtitle(self) -> str:
        values = [str(self.year) if self.year else "", self.engine, self.chassis]
        return " • ".join(value for value in values if value) or "Importați un Auto-Scan VCDS"


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
    priority: str = ""

    @property
    def display_code(self) -> str:
        return self.code or self.vag_code or "DTC"

    @property
    def key(self) -> str:
        return f"{self.module_address}:{self.display_code}:{self.title}".casefold()


@dataclass
class ModuleResult:
    address: str
    name: str
    status: str = "Necitit"
    dtc_count: int = 0
    part_no: str = ""
    component: str = ""
    coding: str = ""
    faults: list[ScanFault] = field(default_factory=list)
    declared_fault_count: int | None = None


@dataclass(frozen=True)
class DTCInfo:
    code: str
    title: str
    severity: str
    system: str
    summary: str
    causes: tuple[str, ...]
    checks: tuple[str, ...]
    repairs: tuple[str, ...]
    location: str
    warning: str
    symptoms: tuple[str, ...] = ()
    component: str = ""
    parameters: str = ""
    expected: str = ""
    test_path: str = ""
    replacement: tuple[str, ...] = ()
    original_title: str = ""
    verified: bool = False
    source_title: str = ""
    source_url: str = ""


@dataclass(frozen=True)
class DTCSearchHit:
    code: str
    title: str
    summary: str
    verified: bool


@dataclass(frozen=True)
class GuidedProcedure:
    title: str
    category: str
    module: str
    platform: str
    duration: str
    description: str
    prerequisites: tuple[str, ...]
    steps: tuple[str, ...]
    verification: tuple[str, ...]
    safety: str
    vcds_path: str = ""
    source_title: str = ""
    source_url: str = ""
    verified: bool = False


@dataclass
class ScanResult:
    vehicle: Vehicle = field(default_factory=Vehicle)
    modules: list[ModuleResult] = field(default_factory=list)
    faults: list[ScanFault] = field(default_factory=list)
    source_name: str = "Niciun Auto-Scan încărcat"
    source_path: str = ""
    raw_text: str = ""
    declared_fault_count: int | None = None
    parsed_fault_count: int = 0
    validation_ok: bool | None = None
    validation_message: str = "Importați un fișier Auto-Scan VCDS TXT, LOG sau PDF."
    validation_details: list[str] = field(default_factory=list)
    voltage_start: float | None = None
    voltage_end: float | None = None

    @property
    def dtc_codes(self) -> list[str]:
        return [fault.display_code for fault in self.faults]

    @property
    def fault_modules(self) -> int:
        return sum(1 for module in self.modules if module.dtc_count > 0)

    @property
    def total_dtc(self) -> int:
        return len(self.faults)


def empty_scan() -> ScanResult:
    return ScanResult()


def default_scan() -> ScanResult:
    """Compatibilitate API: starea implicită este goală și nu conține date artificiale."""
    return empty_scan()


def _lines(value: str, fallback: tuple[str, ...]) -> tuple[str, ...]:
    import re

    text = (value or "").strip()
    if not text:
        return fallback
    text = re.sub(r"(?<!^)(?=\d+[.)]\s+)", "\n", text)
    values = []
    for item in re.split(r"\r?\n|\s*;\s*", text):
        cleaned = re.sub(r"^\s*\d+[.)]\s*", "", item).strip(" -")
        if cleaned:
            values.append(cleaned)
    return tuple(romanianize(item) for item in values) or fallback


def _system_for(code: str, module_address: str = "", module_name: str = "") -> str:
    if module_address or module_name:
        return " • ".join(x for x in (module_address, romanianize(module_name)) if x)
    return {
        "P": "Grup motopropulsor",
        "B": "Caroserie și confort",
        "C": "Șasiu",
        "U": "Comunicație și rețea",
    }.get(code[:1], "Sistem VAG specific")


def dtc_info(code: str, fault: ScanFault | None = None) -> DTCInfo:
    from database import get_database

    db = get_database()
    normalized = db.normalize_code(code)
    row = db.lookup_dtc(normalized)
    module_address = fault.module_address if fault else ""
    module_name = fault.module_name if fault else ""
    original_title = (fault.title if fault else "") or (str(row["title"]) if row else "")
    title = (
        str(row["title_ro"])
        if row and "title_ro" in row.keys() and row["title_ro"]
        else romanianize(str(row["title"]))
        if row
        else romanianize(original_title) or "Cod neindexat în baza locală"
    )
    keys = set(row.keys()) if row else set()

    def value(name: str, default=""):
        return row[name] if row and name in keys and row[name] not in (None, "") else default

    generic_causes = (
        "Alimentare, masă, siguranță, conector sau cablaj cu contact imperfect",
        "Senzorul, actuatorul ori unitatea indicată de textul exact al erorii",
        "Defect secundar produs de alt modul sau de o tensiune necorespunzătoare",
    )
    generic_checks = (
        "Salvați Auto-Scan-ul original și analizați statusul și valorile memorate la apariția erorii",
        "Verificați tensiunea bateriei, alimentările, masele, siguranțele și conectorii",
        "Comparați valorile solicitate cu cele reale în Valori de măsură avansate",
        "Folosiți testele de actuatori sau setările de bază numai dacă procedura unității le cere",
    )
    generic_repairs = (
        "Remediați numai cauza confirmată prin măsurători și inspecție",
        "Nu înlocuiți automat o componentă doar pe baza codului DTC",
        "După reparație ștergeți erorile, efectuați testul funcțional și repetați Auto-Scan-ul",
    )
    description = romanianize(str(value("description", "")))
    summary = description or (
        f"Codul {normalized} a fost identificat de VCDS. Textul raportat este: "
        f"{romanianize(original_title)}. Interpretarea exactă depinde de modul, "
        "software, motorizare și condițiile memorate la apariția erorii."
    )
    verified = bool(value("verified", 0))
    warning = (
        "Fișă VAG detaliată. Confirmați totuși cauza prin măsurători înainte de înlocuirea pieselor."
        if verified
        else "Definiție de catalog. Textul original VCDS și identificarea exactă a unității au prioritate; confirmați cauza prin măsurători."
    )
    return DTCInfo(
        code=normalized or code.strip().upper() or "DTC",
        title=title,
        severity=romanianize(str(value("severity", "De evaluat"))),
        system=_system_for(normalized, module_address, module_name),
        summary=summary,
        symptoms=_lines(
            str(value("symptoms", "")),
            ("Simptomele se confirmă pe vehicul și din condițiile memorate la apariția erorii.",),
        ),
        causes=_lines(str(value("causes", "")), generic_causes),
        checks=_lines(str(value("diagnosis", "")), generic_checks),
        repairs=_lines(str(value("repair", "")), generic_repairs),
        location=romanianize(
            str(
                value(
                    "component_location",
                    "Poziția exactă se stabilește după model, generație, cod motor și numărul piesei.",
                )
            )
        ),
        warning=warning,
        component=romanianize(
            str(value("component", "Componenta se identifică după textul DTC, modul și codul motor."))
        ),
        parameters=romanianize(
            str(
                value(
                    "vcds_parameters",
                    "Valori de măsură avansate: comparați valoarea solicitată cu valoarea reală.",
                )
            )
        ),
        expected=romanianize(
            str(
                value(
                    "expected_values",
                    "Folosiți limitele documentate de unitatea de comandă; nu există o valoare universală.",
                )
            )
        ),
        test_path=romanianize(
            str(
                value(
                    "test_path",
                    f"[{module_address or 'Modul'}] > Coduri de eroare > Valori de măsură avansate",
                )
            )
        ),
        replacement=_lines(
            str(value("replacement_steps", "")),
            ("Înlocuiți componenta numai după confirmarea electrică și mecanică a defectului.",),
        ),
        original_title=original_title,
        verified=verified,
        source_title=romanianize(
            str(value("source_title", "Catalog local KID Diagnostic"))
        ),
        source_url=str(value("source_url", "")),
    )


def search_dtc_infos(query: str, limit: int = 300) -> list[DTCSearchHit]:
    from database import get_database

    db = get_database()
    hits: list[DTCSearchHit] = []
    for row in db.search_dtcs(query, limit):
        verified = bool(row["verified"])
        hits.append(
            DTCSearchHit(
                code=str(row["code"]),
                title=str(row["title_ro"] or romanianize(str(row["title"]))),
                summary=(
                    "Fișă VAG detaliată - deschideți codul pentru diagnostic, măsurători și surse."
                    if verified
                    else "Definiție de catalog - confirmați textul exact VCDS și condițiile memorate."
                ),
                verified=verified,
            )
        )
    return hits


@lru_cache(maxsize=3)
def load_procedures(kind: str) -> tuple[GuidedProcedure, ...]:
    from database import get_database

    return tuple(get_database().guided_procedures(kind))


def find_procedures(items: Iterable[GuidedProcedure], query: str) -> list[GuidedProcedure]:
    needle = query.strip().casefold()
    if not needle:
        return list(items)
    return [
        item
        for item in items
        if needle
        in f"{item.title} {item.category} {item.module} {item.platform} {item.description} {item.vcds_path}".casefold()
    ]
