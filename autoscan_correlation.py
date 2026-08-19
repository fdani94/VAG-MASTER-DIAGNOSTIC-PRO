"""KID Diagnostic - Auto-Scan correlation engine.
Groups DTCs, detects likely secondary faults, common causes and priority order.
"""

from collections import Counter, defaultdict

SECONDARY_MAP = {
    "P1649": "03", "P1653": "03", "P1847": "03", "P1853": "03",
    "01316": "03", "01314": "01", "01315": "02",
}

POWER_CODES = {"00446", "00668", "P068A"}
NETWORK_PREFIXES = ("U0", "U1")
AIRBAG_ADDR = {"15"}
ABS_ADDR = {"03"}
ENGINE_ADDR = {"01"}
TRANS_ADDR = {"02"}


def _code(f):
    return (getattr(f, "code", "") or getattr(f, "vag_code", "") or "").upper().strip()


def _addr(f):
    return (getattr(f, "module_address", "") or "").upper().strip()


def _status_weight(f):
    s = (getattr(f, "status", "") or "").lower()
    if "static" in s or "confirmed" in s or "permanent" in s:
        return 30
    if "intermittent" in s or "sporadic" in s:
        return 5
    return 15


def correlate(result, plans):
    faults = [fp[0] for fp in plans]
    codes = [_code(f) for f in faults]
    addrs = [_addr(f) for f in faults]
    code_set = set(codes)
    addr_counts = Counter(addrs)

    secondary = set()
    reasons = {}
    for i, f in enumerate(faults):
        code = codes[i]
        target = SECONDARY_MAP.get(code)
        if target and target in addrs and _addr(f) != target:
            secondary.add(i)
            reasons[i] = f"Probabil secundar: codul indică verificarea modulului {target}."

    network_count = sum(1 for c in codes if c.startswith(NETWORK_PREFIXES) or c in {"01312","01329","01336","02071"})
    power_count = sum(1 for c in codes if c in POWER_CODES or "under-voltage" in (getattr(faults[codes.index(c)], 'title', '') or '').lower()) if codes else 0

    common_causes = []
    if power_count >= 2 or "00446" in code_set:
        common_causes.append(("Alimentare / subtensiune", "Verifică bateria, tensiunea la pornire, alternatorul, masele și Terminal 30/15 înainte de module."))
    if network_count >= 3:
        common_causes.append(("CAN/LIN / modul comun offline", "Mai multe erori de comunicație simultane indică posibil o alimentare comună, Gateway, CAN/LIN sau un modul sursă offline."))
    if all(c in code_set for c in ["01331","01332"]) or sum(1 for c in ["01331","01332","01333","01334"] if c in code_set) >= 2:
        common_causes.append(("Comfort CAN / alimentare comună uși", "Mai multe module de ușă afectate simultan: verifică întâi alimentarea comună, masele și magistrala Comfort."))
    if "01316" in code_set or any(c in code_set for c in ["P1649","P1653","P1847","P1853"]):
        common_causes.append(("ABS/ESP posibilă cauză principală", "Intră întâi în 03-Brake Electronics și rezolvă DTC-urile primare de acolo."))

    ranked = []
    for i, (f, plan) in enumerate(plans):
        code = codes[i]
        addr = addrs[i]
        score = _status_weight(f)
        if i in secondary:
            score -= 25
        if code in POWER_CODES:
            score += 40
        if addr in AIRBAG_ADDR:
            score += 30
        if addr in ABS_ADDR:
            score += 25
        if addr in ENGINE_ADDR:
            score += 20
        if addr in TRANS_ADDR:
            score += 15
        sev = (plan.get("severity") or "").lower()
        if sev in ("critical", "critic", "high", "ridicat"):
            score += 25
        ranked.append((score, i, f, plan))
    ranked.sort(key=lambda x: x[0], reverse=True)

    primary = [x for x in ranked if x[1] not in secondary][:5]
    secondary_rows = [x for x in ranked if x[1] in secondary]

    return {
        "primary": primary,
        "secondary": secondary_rows,
        "secondary_reasons": reasons,
        "common_causes": common_causes,
        "network_count": network_count,
        "power_count": power_count,
    }


def render_correlation(corr):
    lines = []
    lines.append("PLAN DE DIAGNOSTIC AUTOMAT\n")
    if corr["common_causes"]:
        lines.append("CAUZE COMUNE POSIBILE")
        for title, text in corr["common_causes"]:
            lines.append(f"• {title}: {text}")
        lines.append("")

    lines.append("PRIMELE VERIFICĂRI")
    if not corr["primary"]:
        lines.append("• Nu s-a putut stabili o prioritate clară.")
    else:
        for n, (score, idx, f, plan) in enumerate(corr["primary"], 1):
            code = _code(f) or "DTC"
            mod = f"{_addr(f)} {getattr(f, 'module_name', '')}".strip()
            lines.append(f"{n}. {code} • {mod} • {plan.get('title') or getattr(f, 'title', '')}")
            diag = (plan.get("diagnosis") or "").strip()
            if diag:
                lines.append(f"   → {diag[:500]}")

    lines.append("")
    lines.append(f"ERORI PROBABIL SECUNDARE: {len(corr['secondary'])}")
    for score, idx, f, plan in corr["secondary"][:12]:
        code = _code(f) or "DTC"
        lines.append(f"• {code} • {_addr(f)} {getattr(f, 'module_name', '')} — {corr['secondary_reasons'].get(idx, 'Probabil secundar.')}")

    lines.append("")
    lines.append("REGULĂ DE LUCRU")
    lines.append("Rezolvă întâi alimentarea/comunicația și DTC-urile primare, apoi șterge erorile, fă ciclul de contact/test drive cerut și rulează din nou Auto-Scan. Nu schimba o piesă doar pentru că apare într-un DTC secundar.")
    return "\n".join(lines)
