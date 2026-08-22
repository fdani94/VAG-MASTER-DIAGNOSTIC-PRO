"""Large local VAG numeric DTC reference index for KID Diagnostic V2.

This pack intentionally separates *coverage* from *verified workshop detail*.
Existing detailed DTC rows always win. Missing five-digit VAG codes receive an
index-only row so the local database can recognise/search tens of thousands of
codes without pretending that a generic description is an exact Ross-Tech
repair instruction.
"""

from datetime import date

START_CODE = 0
END_CODE = 39999
SOURCE_URL = "kid-diagnostic://v2/vag-numeric-dtc-index"


def _ensure_columns(con):
    cols = {r[1] for r in con.execute("PRAGMA table_info(dtcs)")}
    wanted = {
        "component": "TEXT",
        "component_location": "TEXT",
        "vcds_parameters": "TEXT",
        "expected_values": "TEXT",
        "test_path": "TEXT",
        "replacement_steps": "TEXT",
        "confidence": "TEXT",
        "module_hint": "TEXT",
    }
    for name, typ in wanted.items():
        if name not in cols:
            con.execute(f"ALTER TABLE dtcs ADD COLUMN {name} {typ}")


def _source(con):
    row = con.execute("SELECT id FROM sources WHERE url=?", (SOURCE_URL,)).fetchone()
    if row:
        return row[0]
    cur = con.execute(
        "INSERT INTO sources(title,publisher,url,accessed,source_type,notes) VALUES(?,?,?,?,?,?)",
        (
            "KID Diagnostic V2 - index numeric DTC VAG",
            "KID Diagnostic",
            SOURCE_URL,
            date.today().isoformat(),
            "Index local",
            "Index de recunoaștere/căutare. Textul exact și modulul se iau din Auto-Scan; nu reprezintă o fișă Ross-Tech verificată.",
        ),
    )
    return cur.lastrowid


def install(con):
    _ensure_columns(con)
    src = _source(con)

    existing = {r[0] for r in con.execute(
        "SELECT code FROM dtcs WHERE length(code)=5 AND code GLOB '[0-9][0-9][0-9][0-9][0-9]'"
    )}

    rows = []
    for number in range(START_CODE, END_CODE + 1):
        code = f"{number:05d}"
        if code in existing:
            continue
        rows.append((
            code,
            f"DTC VAG {code} - index local",
            "Cod numeric VAG recunoscut de indexul local. Pentru denumirea exactă se folosește textul extras din Auto-Scan VCDS.",
            "Simptomele depind de modulul și textul complet al DTC-ului din vehicul.",
            "Nu presupune o piesă defectă doar din cod. Cauza exactă depinde de modul, status, Freeze Frame, alimentare, cablaj și valorile măsurate.",
            "1) Salvează Auto-Scan-ul complet. 2) Identifică modulul care raportează codul. 3) Folosește denumirea exactă din raport. 4) Verifică DTC-urile asociate și Freeze Frame. 5) Verifică alimentare/masă/cablaj și date live relevante. 6) Aplică Coding/Adaptation/Basic Settings numai când controllerul și procedura exactă le cer.",
            "Repară doar cauza confirmată prin măsurători și procedura specifică platformei; după intervenție șterge DTC și repetă Auto-Scan-ul.",
            "Necunoscut",
            0,
            src,
            "De stabilit din textul Auto-Scan și modulul raportor",
            "Poziția exactă depinde de model, generație, motor și modul.",
            "Freeze Frame; status DTC; tensiune; date live relevante sistemului",
            "Folosește valorile/limitele controllerului exact; nu există un prag universal pentru un cod index-only.",
            "Auto-Scan > modulul raportor > Fault Codes > Advanced Measuring Values",
            "După înlocuirea unei piese: coding/adaptation/basic setting numai dacă procedura specifică o cere; apoi test funcțional și Auto-Scan final.",
            "index-only",
            "VAG numeric",
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
