"""Romanian presentation helpers for KID Diagnostic Auto-Scan.
Keeps exact VCDS function names/codes unchanged while translating user-facing text.
"""

import re

STATUS_MAP = {
    "intermittent": "Intermitentă",
    "sporadic": "Sporadică",
    "static": "Statică",
    "confirmed": "Confirmată",
    "pending": "În așteptare",
    "mil on": "Martor MIL aprins",
    "no signal": "Fără semnal",
    "implausible": "Semnal implauzibil",
    "not confirmed": "Neconfirmată",
    "permanent": "Permanentă",
}

MODULE_MAP = {
    "Engine": "Motor",
    "Auto Trans": "Transmisie automată",
    "ABS Brakes": "ABS / frâne",
    "Brakes": "Frâne",
    "Steering Assist": "Asistență direcție",
    "Steering Wheel": "Volan / coloană direcție",
    "Airbags": "Airbag / SRS",
    "Airbag": "Airbag / SRS",
    "Instruments": "Tablou de bord",
    "CAN Gateway": "Gateway CAN",
    "Central Electrics": "Electronică centrală / BCM",
    "Cent. Elect.": "Electronică centrală / BCM",
    "HVAC": "Climatizare",
    "Radio": "Radio",
    "Information Electr.": "Multimedia / infotainment",
    "Headlight Range": "Reglaj înălțime faruri",
    "Parking Brake": "Frână de parcare electrică",
    "Door Elect, Driver": "Ușă șofer",
    "Door Elect, Pass.": "Ușă pasager",
    "Comfort System": "Sistem confort",
    "Central Conv.": "Confort / închidere centralizată",
    "Level Control": "Control nivel / suspensie",
}

PHRASES = [
    (r"Control Module", "Modul de comandă"),
    (r"No Communication", "Fără comunicație"),
    (r"Lost Communication with", "Comunicare pierdută cu"),
    (r"Implausible Signal", "Semnal implauzibil"),
    (r"Implausible Message", "Mesaj implauzibil"),
    (r"Signal too Low", "Semnal prea mic"),
    (r"Signal too High", "Semnal prea mare"),
    (r"Short to Ground", "Scurt la masă"),
    (r"Short to Plus", "Scurt la plus"),
    (r"Open Circuit", "Circuit întrerupt"),
    (r"Electrical Malfunction", "Defecțiune electrică"),
    (r"Mechanical Malfunction", "Defecțiune mecanică"),
    (r"Incorrectly Coded", "Codare incorectă"),
    (r"Not Coded", "Necodat"),
    (r"Basic Setting Not Performed", "Basic Setting neefectuat"),
    (r"Basic Setting", "Basic Setting"),
    (r"Adaptation", "Adaptation"),
    (r"System Too Lean", "Amestec prea sărac"),
    (r"System Too Rich", "Amestec prea bogat"),
    (r"Insufficient Flow", "Debit insuficient"),
    (r"Control Range Not Reached", "Domeniu de reglare neatins"),
    (r"Pressure Too Low", "Presiune prea mică"),
    (r"Pressure Too High", "Presiune prea mare"),
    (r"Under-Voltage", "Subtensiune"),
    (r"Over-Voltage", "Supratensiune"),
    (r"Defective", "Defect"),
    (r"Malfunction", "Defecțiune"),
    (r"Sensor", "Senzor"),
    (r"Actuator", "Actuator"),
    (r"Valve", "Supapă"),
    (r"Pressure", "Presiune"),
    (r"Temperature", "Temperatură"),
    (r"Range/Performance", "Domeniu / performanță"),
    (r"Too Low", "Prea mic"),
    (r"Too High", "Prea mare"),
]


def ro_status(text):
    if not text:
        return "Nespecificat în raport"
    parts = [p.strip() for p in re.split(r"[,;/]", text) if p.strip()]
    out = []
    for part in parts:
        out.append(STATUS_MAP.get(part.lower(), part))
    return ", ".join(out)


def ro_module(name):
    if not name:
        return "Modul necunoscut"
    for en, ro in MODULE_MAP.items():
        if en.lower() in name.lower():
            return ro
    return name


def ro_title(text):
    """Translate common DTC wording; preserve codes, VCDS terms and unknown technical text."""
    if not text:
        return "Eroare fără descriere"
    out = str(text)
    for pattern, repl in PHRASES:
        out = re.sub(pattern, repl, out, flags=re.I)
    return out


def ro_confidence(found, verified):
    if verified:
        return "VERIFICAT / INDEXAT"
    if found:
        return "INDEXAT – soluție orientativă / comunitate"
    return "NEINDEXAT – diagnostic orientativ"


def ro_vcds_note():
    return (
        "Denumirile exacte din VCDS precum Advanced Measuring Values, Measuring Blocks, "
        "Output Tests, Basic Settings, Adaptation, Security Access și Long Coding sunt păstrate "
        "în engleză ca să le găsești identic în program. Explicația și ordinea de lucru sunt în română."
    )
