"""Coverage audit for VAG MASTER Diagnostic PRO.
Builds a per-generation matrix showing which diagnostic areas have procedures/data.
This is a development/QA aid: a green cell means data is linked, not that every engine/ECU variant is exhaustively documented.
"""

AREAS = {
    "Motor": ("motor", "engine", "tdi", "tsi", "tfsi", "fsi", "mpi", "dpf", "egr", "inject"),
    "Cutie": ("transmission", "dsg", "dq", "01m", "01j", "09g", "multitronic", "gearbox"),
    "ABS/ESP": ("abs", "esp", "brake", "g85", "steering angle"),
    "Airbag": ("airbag", "occupancy", "j706"),
    "HVAC": ("hvac", "climat", "air conditioning", "compressor", "flap"),
    "Lighting": ("light", "headlamp", "xenon", "led", "afs", "drl", "j519"),
    "Comfort": ("comfort", "door", "window", "mirror", "remote", "central convenience"),
    "Battery": ("battery", "bem", "energy management"),
    "Gateway": ("gateway", "installation list", "can"),
    "Service/SRI": ("service", "sri", "oil", "inspection"),
    "Long Coding": ("long coding", "coding"),
}


def _text(row):
    return " ".join(str(row[k] or "") for k in row.keys()).lower()


def _generation_rows(con):
    return con.execute("""
        SELECT g.id, b.name brand, m.name model, g.name generation,
               g.year_from, g.year_to, g.chassis, g.platform
        FROM generations g
        JOIN models m ON m.id=g.model_id
        JOIN brands b ON b.id=m.brand_id
        WHERE COALESCE(g.year_to, 2024) >= 1996 AND COALESCE(g.year_from, 2024) <= 2024
        ORDER BY b.name,m.name,g.year_from
    """).fetchall()


def _procedures(con, gid):
    return con.execute("""
        SELECT p.* FROM procedure_library p
        JOIN vehicle_procedures vp ON vp.procedure_id=p.id
        WHERE vp.generation_id=?
    """, (gid,)).fetchall()


def _area_status(proc_rows, keywords):
    hits = [r for r in proc_rows if any(k in _text(r) for k in keywords)]
    if not hits:
        return "LIPSEȘTE", 0
    verified = sum(1 for r in hits if int(r["verified"] or 0) == 1)
    return ("ACOPERIT" if verified else "PARȚIAL"), len(hits)


def audit(con):
    results = []
    for g in _generation_rows(con):
        procs = _procedures(con, g["id"])
        row = {
            "brand": g["brand"], "model": g["model"], "generation": g["generation"],
            "years": f'{g["year_from"] or "?"}-{g["year_to"] or "2024+"}',
            "chassis": g["chassis"] or "", "platform": g["platform"] or "",
            "procedure_count": len(procs), "areas": {},
        }
        missing = 0
        for area, keys in AREAS.items():
            status, count = _area_status(procs, keys)
            row["areas"][area] = {"status": status, "count": count}
            if status == "LIPSEȘTE":
                missing += 1
        # DTC is global today; flag database availability separately rather than pretending per-model exhaustiveness.
        dtc_count = con.execute("SELECT COUNT(*) FROM dtcs").fetchone()[0]
        row["areas"]["DTC"] = {"status": "GLOBAL / NECESITĂ MAPARE", "count": dtc_count}
        row["missing_areas"] = missing
        results.append(row)
    return results


def summary(con):
    rows = audit(con)
    total = len(rows)
    incomplete = sum(1 for r in rows if r["missing_areas"])
    by_brand = {}
    for r in rows:
        b = by_brand.setdefault(r["brand"], {"generations": 0, "incomplete": 0})
        b["generations"] += 1
        b["incomplete"] += int(bool(r["missing_areas"]))
    return {"total_generations": total, "incomplete_generations": incomplete, "by_brand": by_brand, "rows": rows}


def write_report(con, path):
    data = summary(con)
    lines = [
        "AUDIT ACOPERIRE VAG 1996-2024",
        "=" * 88,
        f'Generații în catalog: {data["total_generations"]}',
        f'Generații cu cel puțin o zonă lipsă: {data["incomplete_generations"]}',
        "",
        "Legendă: ACOPERIT = există cel puțin o procedură verificată legată de generație;",
        "PARȚIAL = există date, dar fără procedură verificată; LIPSEȘTE = nu există legătură în baza curentă.",
        "DTC este marcat separat deoarece simpla existență a unui cod global nu dovedește aplicabilitatea pe fiecare model.",
        "",
    ]
    for r in sorted(data["rows"], key=lambda x: (-x["missing_areas"], x["brand"], x["model"], x["generation"])):
        lines.append(f'{r["brand"]} | {r["model"]} | {r["generation"]} | {r["years"]} | {r["chassis"]} | {r["platform"]}')
        parts = []
        for area, info in r["areas"].items():
            parts.append(f'{area}: {info["status"]} ({info["count"]})')
        lines.append("  " + " | ".join(parts))
        lines.append("")
    from pathlib import Path
    Path(path).write_text("\n".join(lines), encoding="utf-8")
    return data
