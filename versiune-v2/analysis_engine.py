from __future__ import annotations

from dataclasses import dataclass

from data import DTCInfo, ScanFault, ScanResult, dtc_info


@dataclass(frozen=True)
class CommonFinding:
    title: str
    evidence: str
    first_action: str
    confidence: str


@dataclass(frozen=True)
class PrioritizedFault:
    fault: ScanFault
    info: DTCInfo
    score: int
    level: str
    secondary_reason: str = ""


@dataclass(frozen=True)
class ScanAnalysis:
    prioritized: tuple[PrioritizedFault, ...]
    common_findings: tuple[CommonFinding, ...]
    confirmed_count: int
    intermittent_count: int
    verified_count: int
    network_count: int
    power_count: int


SECONDARY_MODULES = {
    "P1649": "03",
    "P1653": "03",
    "P1847": "03",
    "P1853": "03",
    "01316": "03",
    "01314": "01",
    "01315": "02",
}

POWER_CODES = {
    "00446",
    "00668",
    "03041",
    "P0560",
    "P0561",
    "P0562",
    "P0563",
    "P068A",
}
NETWORK_NUMERIC = {"01312", "01329", "01336", "02071"}


def _code(fault: ScanFault) -> str:
    return fault.display_code.upper().strip()


def _status_score(status: str) -> int:
    low = (status or "").casefold()
    score = 12
    confirmed = "confirmat" in low and "neconfirmat" not in low
    if confirmed or any(term in low for term in ("static", "permanent")):
        score += 22
    if "martor mil aprins" in low or "mil on" in low:
        score += 15
    if any(term in low for term in ("intermitent", "sporadic")):
        score -= 5
    if "neconfirmat" in low:
        score -= 8
    return score


def _priority_score(value: str) -> int:
    try:
        priority = int(value.strip())
    except (AttributeError, ValueError):
        return 0
    if priority <= 2:
        return 35
    if priority <= 4:
        return 22
    if priority <= 6:
        return 9
    return 2


def _severity_score(value: str) -> int:
    low = (value or "").casefold()
    if any(term in low for term in ("critic", "urgent")):
        return 35
    if any(term in low for term in ("ridicat", "high")):
        return 24
    if any(term in low for term in ("mediu", "medium")):
        return 12
    return 3


def _level(score: int) -> str:
    if score >= 100:
        return "Prioritate imediată"
    if score >= 70:
        return "Prioritate ridicată"
    if score >= 40:
        return "Prioritate medie"
    return "De programat și confirmat"


def analyze_scan(scan: ScanResult) -> ScanAnalysis:
    rows: list[tuple[ScanFault, DTCInfo]] = [
        (fault, dtc_info(fault.display_code, fault)) for fault in scan.faults
    ]
    codes = [_code(fault) for fault, _ in rows]
    code_set = set(codes)
    addresses = {fault.module_address for fault, _ in rows}

    network_count = sum(
        1 for code in codes if code.startswith(("U0", "U1")) or code in NETWORK_NUMERIC
    )
    power_count = sum(
        1
        for fault, info in rows
        if _code(fault) in POWER_CODES
        or any(
            term in f"{fault.title} {info.title}".casefold()
            for term in ("subtensiune", "undervoltage", "tensiune alimentare", "energy management")
        )
    )

    findings: list[CommonFinding] = []
    low_voltage = (
        scan.voltage_start is not None and scan.voltage_start < 12.0
    ) or (scan.voltage_end is not None and scan.voltage_end < 12.0)
    if low_voltage or "03041" in code_set or power_count >= 2:
        voltage_text = (
            f"VCDS a înregistrat {scan.voltage_start:.1f} V la început și "
            f"{scan.voltage_end:.1f} V la final. "
            if scan.voltage_start is not None and scan.voltage_end is not None
            else "Raportul conține indicii de management energetic sau alimentare. "
        )
        findings.append(
            CommonFinding(
                "Alimentare și stare baterie",
                voltage_text + "O tensiune joasă poate produce erori secundare în mai multe module.",
                "Testați bateria în repaus și la pornire, încărcarea alternatorului, bornele și masele; apoi rescanați înainte de a condamna module.",
                "Ridicată" if low_voltage and "03041" in code_set else "Medie",
            )
        )

    glow_codes = sorted(code for code in code_set if code.startswith("P067") and code[-1:].isdigit())
    if len(glow_codes) >= 2:
        findings.append(
            CommonFinding(
                "Defecțiuni grupate în sistemul de preîncălzire",
                f"Sunt prezente {len(glow_codes)} circuite de bujii incandescente: {', '.join(glow_codes)}.",
                "Verificați mai întâi alimentarea comună, modulul/releul de preîncălzire și cablajul, apoi comparați electric fiecare bujie.",
                "Ridicată",
            )
        )

    if {"02615", "02616"}.issubset(code_set):
        findings.append(
            CommonFinding(
                "Blocare și deblocare clapetă rezervor",
                "Codurile 02615 și 02616 apar împreună în același sistem de confort.",
                "Verificați actuatorul clapetei, mufa și cablajul comun înainte de înlocuirea oricărei unități de comandă.",
                "Ridicată",
            )
        )

    if codes.count("02115") >= 2:
        findings.append(
            CommonFinding(
                "Închidere centralizată pe mai multe uși",
                "Același cod 02115 este memorat în cel puțin două module de ușă.",
                "Comparați alimentarea, cablajul din burdufuri și starea broaștelor; confirmați separat fiecare ușă prin valori și teste de actuatori.",
                "Medie",
            )
        )

    if network_count >= 3:
        findings.append(
            CommonFinding(
                "Comunicație CAN/LIN afectată în mai multe puncte",
                f"Au fost identificate {network_count} coduri de comunicație.",
                "Verificați alimentarea comună, lista de instalare Gateway și integritatea magistralei înainte de înlocuirea modulelor raportate offline.",
                "Medie",
            )
        )

    if "02095" in code_set:
        findings.append(
            CommonFinding(
                "Protecție componente activă",
                "Un modul raportează că protecția componentelor este activă.",
                "Confirmați istoricul și compatibilitatea numărului de piesă; eliminarea protecției necesită procedura autorizată corespunzătoare vehiculului.",
                "Ridicată",
            )
        )

    prioritized: list[PrioritizedFault] = []
    for fault, info in rows:
        code = _code(fault)
        score = _status_score(fault.status)
        score += _priority_score(fault.priority)
        score += _severity_score(info.severity)
        score += {"15": 28, "03": 24, "01": 20, "02": 18}.get(fault.module_address, 4)
        if code in POWER_CODES:
            score += 18
        if info.verified:
            score += 3

        secondary_reason = ""
        target = SECONDARY_MODULES.get(code)
        if target and target in addresses and fault.module_address != target:
            score -= 28
            secondary_reason = (
                f"Poate fi efect secundar; verificați mai întâi erorile primare din modulul {target}."
            )
        prioritized.append(
            PrioritizedFault(
                fault=fault,
                info=info,
                score=score,
                level=_level(score),
                secondary_reason=secondary_reason,
            )
        )

    prioritized.sort(
        key=lambda item: (
            -item.score,
            item.fault.module_address,
            item.fault.display_code,
        )
    )
    confirmed_count = sum(
        1
        for fault, _ in rows
        if "confirmat" in fault.status.casefold() and "neconfirmat" not in fault.status.casefold()
    )
    intermittent_count = sum(
        1 for fault, _ in rows if "intermitent" in fault.status.casefold()
    )
    verified_count = sum(1 for _, info in rows if info.verified)
    return ScanAnalysis(
        prioritized=tuple(prioritized),
        common_findings=tuple(findings),
        confirmed_count=confirmed_count,
        intermittent_count=intermittent_count,
        verified_count=verified_count,
        network_count=network_count,
        power_count=power_count,
    )
