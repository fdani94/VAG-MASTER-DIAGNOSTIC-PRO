"""Local OBD DTC recognition index for KID Diagnostic V2.

Adds numeric P/B/C/U code slots without overwriting detailed workshop rows.
These records are deliberately marked `index-only`: they improve Auto-Scan
recognition/search coverage but never pretend to be an exact repair procedure.
"""

from datetime import date

FAMILIES = {
    "P": ("Powertrain", "Motor / transmisie / emisii"),
    "B": ("Body", "Caroserie / confort / habitaclu"),
    "C": ("Chassis", "Șasiu / frâne / direcție / suspensie"),
    "U": ("Network", "Comunicație / CAN / rețea module"),
}
START = 0
END = 3999
SOURCE_URL = "kid-diagnostic://v2/obd-pbcu-index"


def _ensure_columns(con):
    cols = {r[1] for r in con.execute("PRAGMA table_info(dtcs)")}
    wanted = {
        "component": "TEXT", "component_location": "TEXT",
        "vcds_parameters": "TEXT", "expected_values": "TEXT",
        "test_path": "TEXT", "replacement_steps": "TEXT",
        "confidence": "TEXT", "module_hint": "TEXT",
    }
    for name, typ in wanted.items():
        if name not in cols:
            con.execute(f"ALTER TABLE dtcs ADD COLUMN {name} {typ}")


def _source(con):
    row = con.execute("SELECT id FROM sources WHERE url=?", (SOURCE_URL,)).fetchone()
    if row:
        return row[0]
    return con.execute(
        "INSERT INTO sources(title,publisher,url,accessed,source_type,notes) VALUES(?,?,?,?,?,?)",
        (
            "KID Diagnostic V2 - index OBD P/B/C/U",
            "KID Diagnostic",
            SOURCE_URL,
            date.today().isoformat(),
            "Index local",
            "Recunoaștere locală a formatelor OBD P/B/C/U. Denumirea și procedura exactă se confirmă din Auto-Scan și documentația controllerului.",
        ),
    ).lastrowid


def install(con):
    _ensure_columns(con)
    src = _source(con)
    existing = {str(r[0]).upper() for r in con.execute(
        "SELECT code FROM dtcs WHERE length(code)=5 AND upper(substr(code,1,1)) IN ('P','B','C','U')"
    )}

    rows = []
    for prefix, (family_name, module_hint) in FAMILIES.items():
        for number in range(START, END + 1):
            code = f"{prefix}{number:04d}"
            if code in existing:
                continue
            rows.append((
                code,
                f"{code} - index local {family_name}",
                "Cod OBD recunoscut de indexul local. Denumirea exactă se păstrează din Auto-Scan VCDS atunci când este disponibilă.",
                "Simptomele depind de controller, statusul DTC, Freeze Frame și echiparea vehiculului.",
                "Nu presupune o piesă defectă doar din cod. Verifică mai întâi DTC-urile asociate, alimentarea, masele, cablajul, conectorii și datele live.",
                "1) Salvează Auto-Scan-ul complet. 2) Identifică modulul raportor și textul exact. 3) Verifică status/Freeze Frame. 4) Verifică alimentare, masă și cablaj. 5) Compară datele live relevante. 6) Aplică Output Tests/Basic Settings/Coding doar dacă procedura controllerului le cere.",
                "Repară numai cauza confirmată; șterge DTC și repetă Auto-Scan-ul după intervenție.",
                "Necunoscut",
                0,
                src,
                "De stabilit din textul exact al DTC-ului și modulul raportor",
                "Poziția exactă depinde de model, platformă, motor și controller.",
                "Freeze Frame; status DTC; tensiune; parametrii specifici sistemului",
                "Nu există o valoare universală pentru o fișă index-only; folosește specificația controllerului exact.",
                "Auto-Scan > modul raportor > Fault Codes > Advanced Measuring Values",
                "După înlocuire: coding/adaptation/basic setting numai dacă procedura specifică o cere; apoi test funcțional și Auto-Scan final.",
                "index-only",
                module_hint,
            ))
            if len(rows) >= 2000:
                con.executemany(
                    """INSERT OR IGNORE INTO dtcs(
                        code,title,description,symptoms,causes,diagnosis,repair,severity,verified,source_id,
                        component,component_location,vcds_parameters,expected_values,test_path,replacement_steps,
                        confidence,module_hint
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    rows,
                )
                rows.clear()

    if rows:
        con.executemany(
            """INSERT OR IGNORE INTO dtcs(
                code,title,description,symptoms,causes,diagnosis,repair,severity,verified,source_id,
                component,component_location,vcds_parameters,expected_values,test_path,replacement_steps,
                confidence,module_hint
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            rows,
        )
    con.commit()
