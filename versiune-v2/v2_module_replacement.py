from __future__ import annotations

from dataclasses import dataclass, field
import re

MODULE_REPLACEMENT_VERSION = "2.3.0"

ROSS_TECH = {
    "01042": ("Ross-Tech 01042 — Control Module; Not Coded", "https://wiki.ross-tech.com/wiki/index.php/01042"),
    "U1013": ("Ross-Tech U1013 — Control Module Not Coded", "https://wiki.ross-tech.com/wiki/index.php/29709/U1013/053267"),
    "01044": ("Ross-Tech 01044 — Control Module Incorrectly Coded", "https://wiki.ross-tech.com/wiki/index.php/01044"),
    "02095": ("Ross-Tech 02095 — Component Protection Active", "https://wiki.ross-tech.com/wiki/index.php/02095"),
    "U1101": ("Ross-Tech U1101 — Component Protection Active", "https://wiki.ross-tech.com/wiki/index.php/29797/U1101/053505"),
    "02084": ("Ross-Tech 02084 — Component Protection", "https://wiki.ross-tech.com/wiki/index.php/02084"),
    "U1100": ("Ross-Tech U1100 — Component Protection: No Basic Setting", "https://wiki.ross-tech.com/wiki/index.php/29796/U1100/053504"),
}

NOT_CODED_CODES = {"01042", "U1013", "29709", "053267"}
INCORRECT_CODES = {"01044"}
CP_CODES = {"02095", "U1101", "29797", "053505", "02084", "U1100", "29796", "053504"}


@dataclass
class CodingFinding:
    severity: str
    kind: str
    address: str
    module_name: str
    dtc_code: str = ""
    dtc_title: str = ""
    coding: str = ""
    part_no_sw: str = ""
    part_no_hw: str = ""
    component: str = ""
    asam_dataset: str = ""
    shop_code: str = ""
    confidence: int = 0
    requires_online: bool = False
    evidence: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    source_title: str = ""
    source_url: str = ""

    @property
    def label(self):
        return {
            "NOT_CODED": "MODUL NECODAT",
            "INCORRECT_CODING": "CODARE GREȘITĂ",
            "COMPONENT_PROTECTION": "COMPONENT PROTECTION",
            "BASIC_SETTING": "BASIC SETTINGS / ADAPTARE",
        }.get(self.kind, self.kind.replace("_", " "))


@dataclass
class CodingRecoveryAnalysis:
    findings: list[CodingFinding] = field(default_factory=list)
    modules_without_coding_line: list[str] = field(default_factory=list)
    scanned_module_count: int = 0

    @property
    def blocking_count(self):
        return sum(1 for item in self.findings if item.requires_online)

    @property
    def coding_fault_count(self):
        return sum(1 for item in self.findings if item.kind in {"NOT_CODED", "INCORRECT_CODING"})

    @property
    def basic_setting_count(self):
        return sum(1 for item in self.findings if item.kind == "BASIC_SETTING")

    def summary(self):
        if not self.findings:
            return "CODING CHECK: fără DTC explicit de modul necodat, codare greșită sau Component Protection."
        parts = [f"{len(self.findings)} constatări"]
        if self.coding_fault_count:
            parts.append(f"{self.coding_fault_count} coding")
        if self.blocking_count:
            parts.append(f"{self.blocking_count} blocaj online")
        if self.basic_setting_count:
            parts.append(f"{self.basic_setting_count} basic setting")
        return "CODING CHECK: " + " • ".join(parts)


def _norm_addr(value):
    text = str(value or "").strip().upper()
    match = re.search(r"\b([0-9A-F]{2})\b", text)
    return match.group(1) if match else text[:2]


def _module_blocks(raw_text):
    text = str(raw_text or "").replace("\r\n", "\n").replace("\r", "\n")
    matches = list(re.finditer(
        r"(?im)^(?:Address\s+)?(?P<address>[0-9A-F]{2})\s*[:\-]\s*(?!\d{1,3}\s*-).*$",
        text,
    ))
    blocks = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        blocks[_norm_addr(match.group("address"))] = text[match.start():end].strip()
    return blocks


def _field(block, label):
    match = re.search(rf"(?im)^\s*{re.escape(label)}\s*:\s*([^\r\n]+)", block or "")
    return match.group(1).strip() if match else ""


def _module_data(module, block):
    return {
        "coding": str(getattr(module, "coding", "") or "").strip() or _field(block, "Coding"),
        "part_no_sw": str(getattr(module, "part_no_sw", "") or "").strip() or _field(block, "Part No SW") or str(getattr(module, "part_no", "") or "").strip(),
        "part_no_hw": str(getattr(module, "part_no_hw", "") or "").strip() or _field(block, "Part No HW"),
        "component": str(getattr(module, "component", "") or "").strip() or _field(block, "Component"),
        "asam_dataset": str(getattr(module, "asam_dataset", "") or "").strip() or _field(block, "ASAM Dataset"),
        "shop_code": str(getattr(module, "shop_code", "") or "").strip() or _field(block, "Shop #"),
    }


def _fault_text(fault):
    return " ".join(str(value or "") for value in (
        getattr(fault, "code", ""), getattr(fault, "vag_code", ""),
        getattr(fault, "title", ""), getattr(fault, "raw_block", ""),
    )).upper()


def _fault_codes(fault):
    values = {
        str(getattr(fault, "code", "") or "").strip().upper(),
        str(getattr(fault, "vag_code", "") or "").strip().upper(),
    }
    values.update(re.findall(r"\b(?:[PBCU][0-9A-F]{4}|\d{5,6})\b", _fault_text(fault)))
    return {value for value in values if value}


def _kind(fault):
    text = _fault_text(fault)
    codes = _fault_codes(fault)
    if codes & CP_CODES or "COMPONENT PROTECTION" in text:
        return "COMPONENT_PROTECTION"
    if codes & NOT_CODED_CODES or "CONTROL MODULE NOT CODED" in text or "CONTROL MODULE; NOT CODED" in text:
        return "NOT_CODED"
    if codes & INCORRECT_CODES or "INCORRECTLY CODED" in text or "INCORRECT CODING" in text:
        return "INCORRECT_CODING"
    if "NO OR INCORRECT BASIC SETTING" in text or "NO BASIC SETTING" in text or "BASIC SETTING / ADAPTATION" in text:
        return "BASIC_SETTING"
    return ""


def _source(kind, codes):
    preferred = {
        "NOT_CODED": ("U1013", "01042"),
        "INCORRECT_CODING": ("01044",),
        "COMPONENT_PROTECTION": ("U1101", "U1100", "02084", "02095"),
    }.get(kind, ())
    for code in preferred:
        if code in codes:
            return ROSS_TECH[code]
    if kind == "NOT_CODED":
        return ROSS_TECH["01042"]
    if kind == "INCORRECT_CODING":
        return ROSS_TECH["01044"]
    if kind == "COMPONENT_PROTECTION":
        return ROSS_TECH["02095"]
    return ("Auto-Scan VCDS — text DTC", "")


def _actions(kind):
    if kind == "NOT_CODED":
        return [
            "Salvează Auto-Scan-ul și identificarea controllerului înainte de orice modificare.",
            "Verifică Part No/SW/HW și compatibilitatea cu chassis-ul, anul, motorul și echiparea mașinii.",
            "Dacă ai Auto-Scan înainte de înlocuire, compară Coding ORIGINAL; nu copia coding de la altă mașină.",
            "În VCDS folosește Coding-07 / Long Coding Helper numai cu valori documentate pentru controllerul exact.",
            "Dacă documentația controllerului cere WSC/importer/device valide, verifică valorile respective.",
            "Șterge DTC-urile, execută ciclul de contact cerut și repetă Auto-Scan-ul; 01042/U1013 trebuie să dispară.",
        ]
    if kind == "INCORRECT_CODING":
        return [
            "Păstrează coding-ul actual ca probă, dar nu îl considera automat corect.",
            "Verifică Part No/SW/HW și dacă modulul instalat este potrivit configurației mașinii.",
            "Verifică Installation List în 19-CAN Gateway și modulele dependente relevante.",
            "Compară cu Auto-Scan/Coding ORIGINAL anterior și folosește numai procedura documentată pentru controllerul exact.",
            "După recodare șterge erorile și repetă Auto-Scan-ul; 01044 trebuie să dispară fără alte DTC-uri de configurare.",
        ]
    if kind == "COMPONENT_PROTECTION":
        return [
            "Nu încerca recodări repetate pentru eliminarea Component Protection.",
            "Confirmă compatibilitatea modulului și păstrează Auto-Scan-ul/identificarea lui.",
            "Pentru DTC-urile de Component Protection folosește procedura de fabrică cu acces online unde este cerută.",
            "După autorizare/provizionare execută coding/adaptation/basic settings numai dacă documentația controllerului le cere.",
            "Repetă Auto-Scan-ul și confirmă dispariția DTC-ului și a limitărilor de funcție.",
        ]
    return [
        "Verifică mai întâi dacă există și un DTC de coding; coding-ul corect are prioritate.",
        "Respectă exact condițiile de Basic Settings/Adaptation ale controllerului.",
        "Rulează numai grupul/canalul documentat; KID nu inventează valori sau Security Access.",
        "Șterge DTC-ul și repetă Auto-Scan-ul pentru confirmare.",
    ]


def analyze_replacement_coding(scan):
    analysis = CodingRecoveryAnalysis()
    if scan is None:
        return analysis
    modules = {_norm_addr(getattr(m, "address", "")): m for m in list(getattr(scan, "modules", []) or [])}
    blocks = _module_blocks(getattr(scan, "raw_text", ""))
    analysis.scanned_module_count = len(modules)
    for address, module in modules.items():
        if not _module_data(module, blocks.get(address, ""))["coding"]:
            analysis.modules_without_coding_line.append(address)

    seen = set()
    for fault in list(getattr(scan, "faults", []) or []):
        kind = _kind(fault)
        if not kind:
            continue
        address = _norm_addr(getattr(fault, "module_address", ""))
        module = modules.get(address)
        data = _module_data(module, blocks.get(address, "")) if module else {key: "" for key in ("coding", "part_no_sw", "part_no_hw", "component", "asam_dataset", "shop_code")}
        codes = _fault_codes(fault)
        dtc_code = str(getattr(fault, "code", "") or getattr(fault, "vag_code", "") or "").strip().upper()
        key = (kind, address, dtc_code, str(getattr(fault, "title", "") or ""))
        if key in seen:
            continue
        seen.add(key)
        evidence = [
            f"DTC VCDS: {dtc_code or 'text explicit'} — {getattr(fault, 'title', '') or kind}",
            f"Controller: Address {address or '—'} {getattr(fault, 'module_name', '') or ''}".strip(),
        ]
        for label, field_name in (("Part No SW", "part_no_sw"), ("Part No HW", "part_no_hw"), ("Component", "component"), ("ASAM", "asam_dataset"), ("Shop/WSC", "shop_code")):
            if data[field_name]:
                evidence.append(f"{label}: {data[field_name]}")
        if data["coding"]:
            suffix = " (probă, NU valoare confirmată)" if kind == "INCORRECT_CODING" else ""
            evidence.append(f"Coding din Auto-Scan{suffix}: {data['coding']}")
        else:
            evidence.append("Lipsește linia Coding în export; aceasta singură NU dovedește că modulul este necodat.")
        source_title, source_url = _source(kind, codes)
        analysis.findings.append(CodingFinding(
            severity="BLOCAJ" if kind == "COMPONENT_PROTECTION" else ("CRITIC" if kind in {"NOT_CODED", "INCORRECT_CODING"} else "ATENȚIE"),
            kind=kind,
            address=address,
            module_name=str(getattr(fault, "module_name", "") or getattr(module, "name", "") or "Controller"),
            dtc_code=dtc_code,
            dtc_title=str(getattr(fault, "title", "") or ""),
            coding=data["coding"], part_no_sw=data["part_no_sw"], part_no_hw=data["part_no_hw"],
            component=data["component"], asam_dataset=data["asam_dataset"], shop_code=data["shop_code"],
            confidence=100 if kind != "BASIC_SETTING" else 90,
            requires_online=(kind == "COMPONENT_PROTECTION"),
            evidence=evidence, actions=_actions(kind), source_title=source_title, source_url=source_url,
        ))
    priority = {"BLOCAJ": 0, "CRITIC": 1, "ATENȚIE": 2}
    analysis.findings.sort(key=lambda item: (priority.get(item.severity, 9), item.address, item.dtc_code))
    return analysis


def render_recovery_text(analysis):
    lines = [
        "=== KID CODING RECOVERY V2.3.0 ===",
        analysis.summary(),
        f"Module scanate: {analysis.scanned_module_count}. Module fără linie Coding: {len(analysis.modules_without_coding_line)} (nu sunt declarate automat necodate).",
    ]
    for item in analysis.findings:
        lines += ["", f"[{item.severity}] Address {item.address} {item.module_name} — {item.label} — {item.dtc_code or item.dtc_title}"]
        lines += [f"  EVIDENȚĂ: {entry}" for entry in item.evidence]
        lines += [f"  PAS: {step}" for step in item.actions]
        if item.source_title:
            lines.append(f"  SURSĂ: {item.source_title} {item.source_url}".rstrip())
    lines.append("=== END KID CODING RECOVERY ===")
    return "\n".join(lines)


__all__ = ["MODULE_REPLACEMENT_VERSION", "CodingFinding", "CodingRecoveryAnalysis", "analyze_replacement_coding", "render_recovery_text"]
