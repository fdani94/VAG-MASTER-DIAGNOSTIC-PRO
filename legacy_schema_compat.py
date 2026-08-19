"""Compatibility layer for older expansion packs that still write to `procedures`.
Creates a temporary-compatible schema and migrates rows into `procedure_library`.
"""

LEGACY_SCHEMA = """
CREATE TABLE IF NOT EXISTS procedures(
    id INTEGER PRIMARY KEY,
    title TEXT,
    category TEXT,
    module TEXT,
    module_address TEXT,
    vcds_path TEXT,
    steps TEXT,
    notes TEXT,
    system TEXT,
    controller TEXT,
    applicability TEXT,
    applies_to TEXT,
    prerequisites TEXT,
    verification TEXT,
    expected_result TEXT,
    warning TEXT,
    warnings TEXT,
    source_id INTEGER,
    verified INTEGER DEFAULT 0,
    models TEXT,
    years TEXT
);
"""


def ensure_legacy_schema(con):
    con.executescript(LEGACY_SCHEMA)
    cols = {r[1] for r in con.execute("PRAGMA table_info(procedures)").fetchall()}
    wanted = {
        "title":"TEXT", "category":"TEXT", "module":"TEXT", "module_address":"TEXT",
        "vcds_path":"TEXT", "steps":"TEXT", "notes":"TEXT", "system":"TEXT",
        "controller":"TEXT", "applicability":"TEXT", "applies_to":"TEXT",
        "prerequisites":"TEXT", "verification":"TEXT", "expected_result":"TEXT",
        "warning":"TEXT", "warnings":"TEXT", "source_id":"INTEGER",
        "verified":"INTEGER DEFAULT 0", "models":"TEXT", "years":"TEXT",
    }
    for name, typ in wanted.items():
        if name not in cols:
            con.execute(f"ALTER TABLE procedures ADD COLUMN {name} {typ}")
    con.commit()


def _clean(value):
    return str(value).strip() if value not in (None, "") else ""


def migrate_legacy_procedures(con):
    """Copy legacy rows into the canonical procedure_library table without losing text."""
    rows = con.execute("SELECT * FROM procedures").fetchall()
    for row in rows:
        keys = set(row.keys())
        def g(name):
            return _clean(row[name]) if name in keys else ""

        title = g("title")
        if not title:
            continue
        category = g("category") or g("system") or "Procedură VCDS"
        module_address = g("module_address") or g("module")
        path = g("vcds_path")
        purpose_bits = [g("system"), g("controller"), g("models"), g("years")]
        purpose = " | ".join(x for x in purpose_bits if x)
        prereq_bits = [g("prerequisites"), g("applicability"), g("applies_to")]
        prereq = " | ".join(x for x in prereq_bits if x)
        steps = g("steps")
        success = g("verification") or g("expected_result")
        warning_bits = [g("warning"), g("warnings"), g("notes")]
        warnings = " | ".join(x for x in warning_bits if x)
        rule = g("applicability") or g("applies_to") or "Condițional"
        verified = 1 if g("verified") in ("1", "True", "true") else 0
        source_id = row["source_id"] if "source_id" in keys else None

        existing = con.execute("SELECT id FROM procedure_library WHERE title=? LIMIT 1", (title,)).fetchone()
        vals = (category, module_address, path, purpose, prereq, steps, success, warnings, rule, verified, source_id)
        if existing:
            con.execute(
                """UPDATE procedure_library SET category=?,module_address=?,vcds_path=?,purpose=?,prerequisites=?,steps=?,success_criteria=?,warnings=?,applicability_rule=?,verified=?,source_id=? WHERE id=?""",
                vals + (existing[0],)
            )
        else:
            con.execute(
                """INSERT INTO procedure_library(title,category,module_address,vcds_path,purpose,prerequisites,steps,success_criteria,warnings,applicability_rule,verified,source_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (title,) + vals
            )
    con.commit()
