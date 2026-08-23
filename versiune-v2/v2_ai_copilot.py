from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import autoscan_parser as base_parser

COPILOT_VERSION = "2.1.0"
VCDS_SIGNATURE_RE = re.compile(r"\bVCDS\b|VAG-COM", re.IGNORECASE)
ADDRESS_RE = re.compile(r"^\s*Address\s+([0-9A-F]{2})\s*:\s*([^\r\n]+)$", re.IGNORECASE | re.MULTILINE)
NUMERIC_DTC_RE = re.compile(r"^\s*(\d{4,6})\s*-\s*(.+?)\s*$")
UDS_OBD_RE = re.compile(
    r"^\s*([PCBU][0-9A-F]{4})\s+([0-9A-F]{2})(?:\s+\[(\d+)\])?\s*-\s*(.+?)\s*$",
    re.IGNORECASE,
)
VCDS_VERSION_RE = re.compile(r"^\s*(VCDS(?: Version)?[^\r\n]*)$", re.IGNORECASE | re.MULTILINE)
DATA_VERSION_RE = re.compile(r"^\s*Data version:\s*([^\r\n]+)", re.IGNORECASE | re.MULTILINE)
CHASSIS_RE = re.compile(r"^\s*Chassis Type:\s*([^\r\n]+)", re.IGNORECASE | re.MULTILINE)
MILEAGE_RE = re.compile(r"(?:Mileage|Kilometerstand|Kilometrage):\s*([^\r\n]+)", re.IGNORECASE)

VCDS_FUNCTIONS = {
    "fault_codes": {
        "name": "Fault Codes - 02",
        "summary": "Citește DTC-urile memorate în controller și păstrează Auto-Scan-ul înainte de ștergere.",
        "steps": [
            "Selectează controllerul exact raportat de Auto-Scan.",
            "Citește și salvează Fault Codes + Freeze Frame înainte de Clear Codes.",
            "Rezolvă cauza, apoi șterge erorile și repetă Auto-Scan-ul pentru comparație.",
        ],
    },
    "measuring": {
        "name": "Measuring Blocks - 08 / Advanced Measuring Values",
        "summary": "Date live. Pe controlere UDS/ODX/ASAM se folosesc de regulă Advanced Measuring Values.",
        "steps": [
            "Confirmă controllerul și motorul/echiparea exactă.",
            "Selectează numai parametrii relevanți pentru simptom și DTC.",
            "Compară actual cu specified/target și cu documentația controllerului.",
        ],
    },
    "output_tests": {
        "name": "Output Tests - 03",
        "summary": "Comandă actuatori suportați de ECU; secvența și disponibilitatea sunt decise de controller.",
        "steps": [
            "Respectă condițiile din documentația de reparație; multe teste cer motor oprit.",
            "Nu rula Output Tests în mers.",
            "La sisteme de siguranță (de ex. ABS), nu continua fără procedura documentată pentru controllerul exact.",
        ],
    },
    "basic_settings": {
        "name": "Basic Settings - 04",
        "summary": "Inițializări/calibrări ghidate. Utilizarea greșită poate produce funcționare incorectă sau avarii.",
        "steps": [
            "Salvează Auto-Scan-ul și DTC-urile înainte de procedură.",
            "Folosește numai procedura documentată pentru ECU/controller și echiparea exactă.",
            "Pe UDS/ODX/ASAM folosește funcția denumită oferită de controller, nu ghici grupuri/canale.",
        ],
    },
    "coding": {
        "name": "Coding - 07 / Long Coding",
        "summary": "Modifică configurația controllerului numai pe baza identificării complete și a opțiunii documentate.",
        "steps": [
            "Salvează Coding ORIGINAL și Auto-Scan BEFORE.",
            "Confirmă Address, Part No SW/HW, Component, ASAM/ROD și echiparea reală.",
            "Schimbă o singură opțiune documentată; notează Before/After.",
            "Repornește/retestează dacă procedura o cere și rulează Auto-Scan AFTER.",
        ],
    },
    "adaptation": {
        "name": "Adaptation - 10",
        "summary": "Schimbă valori/canale de adaptare; nu există întotdeauna revenire simplă dacă valoarea originală nu a fost salvată.",
        "steps": [
            "Salvează valoarea originală și Auto-Scan-ul BEFORE.",
            "Confirmă canalul/funcția exactă din documentația controllerului.",
            "Aplică o singură schimbare și verifică rezultatul.",
        ],
    },
    "security_access": {
        "name": "Security Access - 16 / Login-Coding II - 11",
        "summary": "Deblochează unele funcții de coding/adaptation. Codul nu trebuie ghicit sau brute-force-uit.",
        "steps": [
            "Identifică exact controllerul și funcția dorită.",
            "Folosește numai un cod documentat pentru ECU/controllerul și funcția exactă.",
            "Nu încerca serii de coduri și nu repeta accesări la întâmplare.",
        ],
    },
    "readiness": {
        "name": "Readiness - 15",
        "summary": "Arată starea monitoarelor de emisii; Clear DTC poate reseta monitoarele testabile la incomplete.",
        "steps": [
            "Citește Readiness înainte de Clear Codes când diagnostichezi emisii.",
            "Nu interpreta un monitor incomplet ca piesă defectă fără condițiile de rulare/diagnostic relevante.",
        ],
    },
    "advanced_id": {
        "name": "Advanced ID - 1A",
        "summary": "Identificare suplimentară a controllerului; utilă pentru confirmarea software/hardware.",
        "steps": ["Păstrează identificarea în raport înainte de coding/adaptation."],
    },
    "autoscan": {
        "name": "Auto-Scan",
        "summary": "Snapshot de bază pentru module, DTC-uri și coding. Se recomandă BEFORE și AFTER.",
        "steps": [
            "Salvează scanarea originală înainte de intervenții.",
            "După intervenție repetă Auto-Scan-ul și compară module, DTC și coding.",
        ],
    },
    "sri": {
        "name": "SRI Reset",
        "summary": "Resetare service numai după operația de mentenanță și cu intervalul corect pentru vehicul.",
        "steps": ["Confirmă tipul de service și configurația vehiculului înainte de resetare."],
    },
}


def _confidence(score: int) -> str:
    if score >= 90:
        return "ridicată"
    if score >= 75:
        return "bună"
    if score >= 55:
        return "medie"
    return "scăzută"


def read_scan_file_audited(path: str | Path) -> tuple[str, list[str]]:
    path = Path(path)
    ext = path.suffix.lower()
    warnings: list[str] = []
    if ext in (".txt", ".log", ".csv"):
        payload = path.read_bytes()
        for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
            try:
                return payload.decode(enc), warnings
            except UnicodeDecodeError:
                continue
        return payload.decode("utf-8", errors="replace"), [
            "Encoding necunoscut; caracterele invalide au fost înlocuite."
        ]

    if ext == ".pdf":
        try:
            from pypdf import PdfReader
        except Exception as exc:
            raise RuntimeError("Suportul PDF necesită pachetul pypdf.") from exc
        reader = PdfReader(str(path))
        pages: list[str] = []
        for number, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text(extraction_mode="layout") or ""
            except TypeError:
                text = page.extract_text() or ""
            if text.strip():
                pages.append(text)
            else:
                warnings.append(f"Pagina {number} nu conține text extractibil.")
        if not pages:
            raise ValueError(
                "PDF-ul nu conține text extractibil. Exportă Auto-Scan-ul ca TXT din VCDS; OCR automat nu este folosit pentru a evita citiri false."
            )
        return "\n\n".join(pages), warnings

    raise ValueError("Format nesuportat. Încarcă Auto-Scan VCDS TXT, LOG, CSV sau PDF cu text.")


def _extract(line_block: str, label: str) -> str:
    match = re.search(rf"^\s*{re.escape(label)}\s*:\s*([^\r\n]+)", line_block, re.IGNORECASE | re.MULTILINE)
    return match.group(1).strip() if match else ""


def _module_chunks(text: str) -> list[tuple[str, str, str]]:
    matches = list(ADDRESS_RE.finditer(text))
    chunks: list[tuple[str, str, str]] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        chunks.append((match.group(1).upper(), match.group(2).strip(), text[start:end]))
    return chunks


def _fault_status(text: str) -> str:
    terms = []
    upper = text.upper()
    for label in ("INTERMITTENT", "SPORADIC", "STATIC", "PERMANENT", "MIL ON", "CONFIRMED", "PENDING"):
        if label in upper:
            terms.append(label.title())
    return ", ".join(dict.fromkeys(terms))


def _augment_modern_uds(result: Any) -> Any:
    text = str(getattr(result, "raw_text", "") or "")
    module_by_address = {str(getattr(m, "address", "")).upper(): m for m in getattr(result, "modules", [])}

    for address, raw_name, chunk in _module_chunks(text):
        module = module_by_address.get(address)
        if module is None:
            continue

        setattr(module, "raw_block", chunk)
        sw_line = _extract(chunk, "Part No SW")
        hw_match = re.search(r"\bHW:\s*([^\r\n]+)", sw_line, re.IGNORECASE)
        if hw_match:
            setattr(module, "part_no_hw", hw_match.group(1).strip())
            setattr(module, "part_no_sw", sw_line[: hw_match.start()].strip())
        else:
            setattr(module, "part_no_sw", sw_line or getattr(module, "part_no", ""))
            setattr(module, "part_no_hw", _extract(chunk, "Part No HW"))
        setattr(module, "asam_dataset", _extract(chunk, "ASAM Dataset"))
        setattr(module, "rod", _extract(chunk, "ROD"))
        setattr(module, "vcid", _extract(chunk, "VCID"))
        setattr(module, "shop", _extract(chunk, "Shop #"))
        setattr(module, "readiness", _extract(chunk, "Readiness"))

        pending_vag = ""
        pending_title = ""
        lines = chunk.splitlines()
        for i, raw in enumerate(lines):
            stripped = raw.strip()
            numeric = NUMERIC_DTC_RE.match(stripped)
            if numeric:
                pending_vag = numeric.group(1)
                pending_title = numeric.group(2).strip()
                continue

            uds = UDS_OBD_RE.match(stripped)
            if not uds:
                continue

            obd_code = uds.group(1).upper()
            status_byte = uds.group(2).upper()
            bracket = uds.group(3) or ""
            detail = uds.group(4).strip()

            fault = next(
                (f for f in getattr(module, "faults", []) if str(getattr(f, "code", "")).upper() == obd_code),
                None,
            )
            if fault is None and pending_vag:
                fault = next(
                    (f for f in getattr(module, "faults", []) if str(getattr(f, "vag_code", "")) == pending_vag),
                    None,
                )

            if fault is None:
                block_end = len(lines)
                for j in range(i + 1, len(lines)):
                    if NUMERIC_DTC_RE.match(lines[j].strip()) or UDS_OBD_RE.match(lines[j].strip()):
                        block_end = j
                        break
                raw_block = "\n".join(lines[i:block_end])
                fault = base_parser.ScanFault(
                    module_address=address,
                    module_name=getattr(module, "name", raw_name),
                    code=obd_code,
                    vag_code=pending_vag,
                    title=pending_title or detail,
                    status=_fault_status(raw_block or detail),
                    raw_block=raw_block,
                    freeze_frame=raw_block if "Freeze Frame" in raw_block else "",
                    frequency=_extract(raw_block, "Fault Frequency"),
                    mileage=_extract(raw_block, "Mileage") or _extract(raw_block, "Kilometerstand"),
                )
                module.faults.append(fault)
                result.faults.append(fault)
            else:
                fault.code = obd_code
                if pending_vag and not getattr(fault, "vag_code", ""):
                    fault.vag_code = pending_vag
                if pending_title and (
                    not getattr(fault, "title", "")
                    or str(getattr(fault, "title", "")).upper().startswith(obd_code)
                ):
                    fault.title = pending_title
                if not getattr(fault, "status", ""):
                    fault.status = _fault_status(detail)
                if stripped not in str(getattr(fault, "raw_block", "")):
                    fault.raw_block = (str(getattr(fault, "raw_block", "")).rstrip() + "\n" + stripped).strip()

            setattr(fault, "uds_status_byte", status_byte)
            setattr(fault, "uds_bracket", bracket)
            setattr(fault, "uds_detail", detail)
            pending_vag = ""
            pending_title = ""

    unique = []
    seen = set()
    for fault in getattr(result, "faults", []):
        key = (
            str(getattr(fault, "module_address", "")).upper(),
            str(getattr(fault, "code", "") or getattr(fault, "vag_code", "")).upper(),
            str(getattr(fault, "vag_code", "")).upper(),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(fault)
    result.faults = unique
    for module in getattr(result, "modules", []):
        module.faults = [f for f in unique if str(getattr(f, "module_address", "")).upper() == str(module.address).upper()]
    try:
        base_parser._validate_result(result)
    except Exception:
        result.parsed_fault_count = len(result.faults)
    return result


def parse_autoscan_file_audited(path: str | Path) -> Any:
    text, warnings = read_scan_file_audited(path)
    result = base_parser.parse_autoscan_text(text, str(path))
    _augment_modern_uds(result)
    result.extraction_warnings = list(warnings)
    version = VCDS_VERSION_RE.search(text)
    data = DATA_VERSION_RE.search(text)
    chassis = CHASSIS_RE.search(text)
    mileage = MILEAGE_RE.search(text)
    result.vcds_version = version.group(1).strip() if version else ""
    result.data_version = data.group(1).strip() if data else ""
    result.chassis_type = chassis.group(1).strip() if chassis else ""
    result.mileage_header = mileage.group(1).strip() if mileage else ""
    result.audit = audit_scan_result(result, warnings)
    return result


def audit_scan_result(result: Any, extraction_warnings: list[str] | None = None) -> dict[str, Any]:
    raw = str(getattr(result, "raw_text", "") or "")
    warnings = list(extraction_warnings if extraction_warnings is not None else getattr(result, "extraction_warnings", []) or [])
    score = 100
    issues: list[dict[str, str]] = []

    def issue(severity: str, message: str, penalty: int = 0) -> None:
        nonlocal score
        issues.append({"severity": severity, "message": message})
        score = max(0, score - penalty)

    if len(raw.strip()) < 120:
        issue("error", "Conținutul Auto-Scan este prea scurt pentru o verificare solidă.", 30)
    if not VCDS_SIGNATURE_RE.search(raw):
        issue("error", "Nu a fost identificată semnătura VCDS/VAG-COM în sursă.", 20)
    if not getattr(result, "vin", ""):
        issue("warning", "VIN-ul nu a fost găsit în raport; identificarea vehiculului trebuie confirmată manual.", 5)
    if not getattr(result, "modules", []):
        issue("error", "Nu au fost identificate blocuri Address/module.", 35)

    validation_ok = getattr(result, "validation_ok", None)
    if validation_ok is False:
        issue("error", getattr(result, "validation_message", "Numărul DTC declarat nu corespunde cu cel extras."), 30)
    elif validation_ok is None:
        issue("warning", "Raportul nu oferă suficiente totaluri «X Faults Found» pentru validare completă.", 5)

    duplicates = []
    seen = set()
    for fault in getattr(result, "faults", []):
        key = (
            str(getattr(fault, "module_address", "")).upper(),
            str(getattr(fault, "code", "") or getattr(fault, "vag_code", "")).upper(),
        )
        if key in seen:
            duplicates.append("/".join(key))
        seen.add(key)
    if duplicates:
        issue("warning", f"Au fost detectate DTC duplicate: {', '.join(duplicates[:5])}.", 5)

    if "\ufffd" in raw:
        issue("warning", "Textul conține caractere de înlocuire; encoding-ul sursei poate fi incomplet.", 10)

    for warning in dict.fromkeys(str(x).strip() for x in warnings if str(x).strip()):
        issue("warning", warning, 8)

    confidence = _confidence(score)
    has_error = any(x["severity"] == "error" for x in issues)
    verified = score >= 75 and not has_error and not warnings

    module_count = len(getattr(result, "modules", []) or [])
    fault_count = len(getattr(result, "faults", []) or [])
    coding_count = sum(1 for m in getattr(result, "modules", []) if str(getattr(m, "coding", "")).strip())
    evidence = [
        f"Module extrase: {module_count}",
        f"DTC extrase: {fault_count}",
        f"Module cu Coding ORIGINAL: {coding_count}",
    ]
    if getattr(result, "vin", ""):
        evidence.append(f"VIN extras: {result.vin}")
    declared = getattr(result, "declared_fault_count", None)
    if declared is not None:
        evidence.append(f"DTC declarate de VCDS: {declared}")

    if not issues:
        issues.append({"severity": "ok", "message": "Structura Auto-Scan este intern consistentă în verificările disponibile."})

    audit = {
        "score": score,
        "confidence": confidence,
        "verified": verified,
        "issues": issues,
        "evidence": evidence,
        "moduleCount": module_count,
        "faultCount": fault_count,
        "declaredFaultCount": declared,
    }
    result.audit = audit
    return audit


def _vehicle_text(selected_vehicle: str | None) -> str:
    return str(selected_vehicle or "").strip() or "Vehicul selectat în KID Diagnostic V2"


def _plan_for_fault(plans: list | None, fault: Any) -> dict[str, Any]:
    for item in plans or []:
        try:
            f, plan = item
        except Exception:
            continue
        if f is fault:
            return plan or {}
        if (
            str(getattr(f, "module_address", "")).upper() == str(getattr(fault, "module_address", "")).upper()
            and str(getattr(f, "code", "") or getattr(f, "vag_code", "")).upper()
            == str(getattr(fault, "code", "") or getattr(fault, "vag_code", "")).upper()
        ):
            return plan or {}
    return {}


def build_verified_report(
    result: Any,
    plans: list | None = None,
    selected_vehicle: str | None = None,
    audit: dict[str, Any] | None = None,
) -> str:
    audit = audit or getattr(result, "audit", None) or audit_scan_result(result)
    lines = [
        "KID DIAGNOSTIC V2 — RAPORT VCDS VERIFICAT AI",
        "=" * 64,
        "",
        "1. VEHICUL ȘI SURSĂ",
        f"Vehicul: {_vehicle_text(selected_vehicle)}",
        f"Fișier: {Path(str(getattr(result, 'source_path', '') or 'Auto-Scan')).name}",
        f"VIN: {getattr(result, 'vin', '') or 'neextras'}",
        f"VCDS: {getattr(result, 'vcds_version', '') or 'neextras'}",
        f"Data Version: {getattr(result, 'data_version', '') or 'neextras'}",
        f"Chassis Type: {getattr(result, 'chassis_type', '') or 'neextras'}",
        f"Kilometraj raport: {getattr(result, 'mileage_header', '') or 'neextras'}",
        "",
        "2. AUDITUL CITIRII AUTO-SCAN",
        f"Scor: {audit['score']}/100 • încredere {audit['confidence']} • {'VERIFICAT' if audit['verified'] else 'NECESITĂ ATENȚIE'}",
    ]
    for item in audit.get("issues", []):
        lines.append(f"- {str(item.get('severity', '')).upper()}: {item.get('message', '')}")

    lines += ["", "3. MODULE ȘI IDENTIFICARE"]
    for module in getattr(result, "modules", []) or []:
        address = getattr(module, "address", "")
        name = getattr(module, "name", "")
        lines.append(f"\nAddress {address}: {name}")
        lines.append(f"  Part No SW: {getattr(module, 'part_no_sw', '') or getattr(module, 'part_no', '') or '—'}")
        lines.append(f"  Part No HW: {getattr(module, 'part_no_hw', '') or '—'}")
        lines.append(f"  Component: {getattr(module, 'component', '') or '—'}")
        lines.append(f"  ASAM: {getattr(module, 'asam_dataset', '') or '—'}")
        lines.append(f"  ROD: {getattr(module, 'rod', '') or '—'}")
        lines.append(f"  Coding ORIGINAL: {getattr(module, 'coding', '') or 'neextras'}")
        readiness = getattr(module, "readiness", "")
        if readiness:
            lines.append(f"  Readiness: {readiness}")

    lines += ["", "4. DTC ȘI PLAN DE VERIFICARE"]
    if not getattr(result, "faults", []):
        lines.append("Nu au fost extrase DTC-uri din raport.")
    for index, fault in enumerate(getattr(result, "faults", []) or [], start=1):
        plan = _plan_for_fault(plans, fault)
        code = getattr(fault, "code", "") or getattr(fault, "vag_code", "") or "DTC"
        vag = getattr(fault, "vag_code", "")
        uds_meta = ""
        if getattr(fault, "uds_status_byte", ""):
            uds_meta = f" {fault.uds_status_byte}" + (f" [{fault.uds_bracket}]" if getattr(fault, "uds_bracket", "") else "")
        lines.append(f"\n{index}. Address {getattr(fault, 'module_address', '')} • {code}{uds_meta}" + (f" / VAG {vag}" if vag else ""))
        lines.append(f"   Text Auto-Scan: {getattr(fault, 'title', '') or getattr(fault, 'uds_detail', '') or '—'}")
        lines.append(f"   Stare: {getattr(fault, 'status', '') or 'nespecificată'}")
        if plan:
            lines.append(f"   Bază locală: {'fișă verificată' if plan.get('verified') else 'ghid local / de confirmat'}")
            if plan.get("component"):
                lines.append(f"   Piesă/sistem: {plan.get('component')}")
            if plan.get("parameters"):
                lines.append(f"   Verificare VCDS: {plan.get('parameters')}")
            if plan.get("expected"):
                lines.append(f"   Valori/comportament așteptat: {plan.get('expected')}")
            if plan.get("diagnosis"):
                lines.append(f"   Diagnostic: {plan.get('diagnosis')}")
        if getattr(fault, "freeze_frame", ""):
            lines.append("   Freeze Frame disponibil în sursă: DA")

    lines += ["", "5. SNAPSHOT CODING — BEFORE"]
    coded = False
    for module in getattr(result, "modules", []) or []:
        coding = str(getattr(module, "coding", "") or "").strip()
        if coding:
            coded = True
            lines.append(f"- Address {module.address} {module.name}: {coding}")
    if not coded:
        lines.append("Nu a fost extras Coding din sursă. Nu se recomandă scriere până când starea BEFORE nu este salvată.")

    lines += [
        "",
        "6. REGULI COPILOT PENTRU SCRIERI VCDS",
        "- Nu inventează Long Coding, Security Access, canale sau valori Adaptation.",
        "- Confirmă Address + Part No SW/HW + Component + ASAM/ROD + echiparea reală înainte de recomandare exactă.",
        "- Salvează Auto-Scan și Coding ORIGINAL BEFORE.",
        "- Modifică o singură opțiune documentată, notează Before/After și rulează Auto-Scan AFTER.",
        "- Security Access se folosește numai din documentația controllerului exact; nu se ghicește și nu se brute-forcează.",
        "- Output Tests și Basic Settings se execută numai cu condițiile și avertismentele procedurii exacte.",
        "",
        "7. CONCLUZIE AUDIT",
        (
            "Citirea este suficient de consistentă pentru analiză asistată."
            if audit["verified"]
            else "Raportul poate fi analizat, dar elementele semnalate la audit trebuie confirmate înainte de coding/adaptation/reparații."
        ),
        "",
        "Copilotul KID Diagnostic V2 oferă analiză și ghidaj; nu pretinde că a efectuat scrieri pe ECU.",
    ]
    return "\n".join(lines)


class V2AICopilot:
    def __init__(self):
        self.base_url = os.environ.get("KID_V2_AI_BASE_URL", "").strip().rstrip("/")
        self.model = os.environ.get("KID_V2_AI_MODEL", "").strip()
        self.api_key = os.environ.get("KID_V2_AI_API_KEY", "").strip()

    @property
    def external_model_ready(self) -> bool:
        if not (self.base_url and self.model):
            return False
        parsed = urlparse(self.base_url)
        if parsed.scheme.lower() == "https":
            return True
        return parsed.scheme.lower() == "http" and (parsed.hostname or "").lower() in {
            "localhost",
            "127.0.0.1",
            "::1",
        }

    def ask(
        self,
        question: str,
        selected_vehicle: str = "",
        scan: Any | None = None,
        plans: list | None = None,
        report_text: str = "",
    ) -> str:
        local = self._local_answer(question, selected_vehicle, scan, plans, report_text)
        if not self.external_model_ready:
            return local
        try:
            return self._external_answer(question, local, selected_vehicle, scan)
        except Exception:
            return local + "\n\n[Modelul extern nu a răspuns; este afișat răspunsul local verificabil.]"

    def _local_answer(self, question: str, vehicle: str, scan: Any | None, plans: list | None, report_text: str) -> str:
        q = (question or "").strip()
        upper = q.upper()
        audit = getattr(scan, "audit", None) if scan is not None else None

        if scan is not None and any(x in upper for x in ("REFĂ RAPORT", "REFA RAPORT", "REFACE RAPORT", "GENEREAZĂ RAPORT", "GENEREAZA RAPORT", "RECONSTRUI")):
            return "Am refăcut raportul din dovezile citite din Auto-Scan.\n\n" + build_verified_report(scan, plans, vehicle, audit)

        if any(x in upper for x in ("SECURITY ACCESS", "LOGIN-CODING", "LOGIN CODING", "COD ACCES", "COD DE ACCES")):
            return self._security_answer(q, vehicle, scan)

        if scan is not None and any(x in upper for x in ("VERIFIC", "AUDIT", "CITIT CORECT", "RAPORT")):
            audit = audit or audit_scan_result(scan)
            lines = [
                f"Audit Auto-Scan: {audit['score']}/100 • încredere {audit['confidence']} • {'VERIFICAT' if audit['verified'] else 'ATENȚIE'}",
            ]
            lines.extend(f"- {x['severity'].upper()}: {x['message']}" for x in audit["issues"])
            return "\n".join(lines)

        if scan is not None and any(x in upper for x in ("DTC", "EROARE", "ERORI", "CODURI")):
            return self._dtc_answer(scan, plans)

        if any(x in upper for x in ("CODING", "CODARE", "LONG CODING")):
            return self._function_answer("coding", vehicle, scan)
        if "ADAPT" in upper:
            return self._function_answer("adaptation", vehicle, scan)
        if "BASIC SETTINGS" in upper or "CALIBR" in upper:
            return self._function_answer("basic_settings", vehicle, scan)
        if "OUTPUT TEST" in upper or "ACTUATOR" in upper:
            return self._function_answer("output_tests", vehicle, scan)
        if any(x in upper for x in ("LIVE", "MEASUR", "VALORI")):
            return self._function_answer("measuring", vehicle, scan)
        if any(x in upper for x in ("FUNCȚII VCDS", "FUNCTII VCDS", "CE POȚI", "CE POTI")):
            names = "\n".join(f"- {x['name']}: {x['summary']}" for x in VCDS_FUNCTIONS.values())
            return (
                "Pot verifica Auto-Scan-ul, explica DTC-urile, reface raportul, păstra Coding BEFORE și ghida funcțiile VCDS fără valori inventate.\n\n"
                + names
            )

        return (
            "KID V2 AI Copilot este pregătit pentru Auto-Scan, DTC, Coding, Adaptation, Basic Settings, Output Tests, Live Data și raport verificat.\n"
            "Încarcă un Auto-Scan pentru răspunsuri ancorate în Address, DTC, Coding și identificarea controllerelor."
        )

    def _module_evidence(self, scan: Any | None) -> list[str]:
        if scan is None:
            return []
        lines = []
        for module in getattr(scan, "modules", []) or []:
            lines.append(
                f"Address {module.address} {module.name} | SW {getattr(module, 'part_no_sw', '') or getattr(module, 'part_no', '') or '—'}"
                f" | HW {getattr(module, 'part_no_hw', '') or '—'} | Component {getattr(module, 'component', '') or '—'}"
                f" | ASAM {getattr(module, 'asam_dataset', '') or '—'} | Coding ORIGINAL {getattr(module, 'coding', '') or '—'}"
            )
        return lines

    def _function_answer(self, key: str, vehicle: str, scan: Any | None) -> str:
        data = VCDS_FUNCTIONS[key]
        lines = [f"VCDS — {data['name']}", data["summary"], "", f"Vehicul: {_vehicle_text(vehicle)}", ""]
        evidence = self._module_evidence(scan)
        if evidence:
            lines.append("Dovezi din Auto-Scan:")
            lines.extend(f"- {x}" for x in evidence[:12])
            lines.append("")
        lines.append("Pași siguri:")
        lines.extend(f"{i}. {step}" for i, step in enumerate(data["steps"], start=1))
        if key in ("coding", "adaptation", "basic_settings"):
            lines.append("\nNu dau o valoare exactă dacă identificarea controllerului și funcția dorită nu o susțin.")
        return "\n".join(lines)

    def _security_answer(self, question: str, vehicle: str, scan: Any | None) -> str:
        data = VCDS_FUNCTIONS["security_access"]
        lines = [f"VCDS — {data['name']}", data["summary"], "", f"Vehicul: {_vehicle_text(vehicle)}"]
        address = re.search(r"(?:ADDRESS|ADRESA|MODUL(?:UL)?)\s*[:#-]?\s*([0-9A-F]{2})\b", question, re.IGNORECASE)
        if scan is not None:
            modules = getattr(scan, "modules", []) or []
            chosen = None
            if address:
                chosen = next((m for m in modules if str(m.address).upper() == address.group(1).upper()), None)
            if chosen is None and len(modules) == 1:
                chosen = modules[0]
            if chosen is not None:
                lines += [
                    "",
                    f"ECU: Address {chosen.address} {chosen.name}",
                    f"SW/HW: {getattr(chosen, 'part_no_sw', '') or getattr(chosen, 'part_no', '') or '—'} / {getattr(chosen, 'part_no_hw', '') or '—'}",
                    f"Component: {getattr(chosen, 'component', '') or '—'}",
                    f"ASAM: {getattr(chosen, 'asam_dataset', '') or '—'}",
                    f"Coding ORIGINAL: {getattr(chosen, 'coding', '') or '—'}",
                ]
        lines += ["", "Pași siguri:"]
        lines.extend(f"{i}. {step}" for i, step in enumerate(data["steps"], start=1))
        lines.append("\nNu inventez și nu brute-forcez coduri Security Access.")
        return "\n".join(lines)

    def _dtc_answer(self, scan: Any, plans: list | None) -> str:
        faults = getattr(scan, "faults", []) or []
        if not faults:
            return "Auto-Scan-ul curent nu conține DTC-uri extrase."
        ordered = sorted(
            faults,
            key=lambda f: (
                0 if "MIL ON" in str(getattr(f, "status", "")).upper() else 1,
                str(getattr(f, "module_address", "")),
            ),
        )
        lines = [f"DTC-uri extrase: {len(ordered)}", ""]
        for idx, fault in enumerate(ordered, 1):
            plan = _plan_for_fault(plans, fault)
            code = getattr(fault, "code", "") or getattr(fault, "vag_code", "") or "DTC"
            lines.append(f"{idx}. {code} • Address {getattr(fault, 'module_address', '')} {getattr(fault, 'module_name', '')}")
            lines.append(f"   Auto-Scan: {getattr(fault, 'title', '') or '—'}")
            lines.append(f"   Stare: {getattr(fault, 'status', '') or 'nespecificată'}")
            if plan:
                if plan.get("description"):
                    lines.append(f"   Ce înseamnă: {plan['description']}")
                if plan.get("causes"):
                    lines.append(f"   Cauze posibile: {plan['causes']}")
                if plan.get("parameters"):
                    lines.append(f"   Verifică în VCDS: {plan['parameters']}")
                if plan.get("diagnosis"):
                    lines.append(f"   Primii pași: {plan['diagnosis']}")
            else:
                lines.append("   Nu există o fișă locală suficientă; nu presupun cauza sau piesa.")
        return "\n".join(lines)

    def _external_answer(self, question: str, local_answer: str, vehicle: str, scan: Any | None) -> str:
        context = "\n".join(self._module_evidence(scan)[:16])
        system = (
            "Ești KID Diagnostic V2 AI Copilot pentru VCDS. Răspunde în română, tehnic și explicit. "
            "Nu inventa Long Coding, Security Access, canale/valori Adaptation, part number, DTC-uri sau rezultate de test. "
            "Nu pretinde că ai scris pe ECU. Păstrează răspunsul local verificat ca sursă de adevăr; poți doar să-l structurezi și explici. "
            "Când lipsesc dovezi pentru o valoare exactă, spune ce identificare/documentație este necesară."
        )
        payload = {
            "model": self.model,
            "temperature": 0.1,
            "messages": [
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": (
                        f"Vehicul: {_vehicle_text(vehicle)}\n"
                        f"Întrebare: {question}\n\n"
                        f"Dovezi Auto-Scan:\n{context or 'Nicio scanare încărcată'}\n\n"
                        f"Răspuns local verificat:\n{local_answer}"
                    ),
                },
            ],
        }
        url = self.base_url
        if not url.endswith("/chat/completions"):
            url = url + "/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        request = Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urlopen(request, timeout=25) as response:
            body = json.loads(response.read().decode("utf-8"))
        answer = body.get("choices", [{}])[0].get("message", {}).get("content", "")
        return str(answer).strip() or local_answer
