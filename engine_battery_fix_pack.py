def _ensure_engine(con, code, fuel, displacement, family, power_hp=0):
    r = con.execute("SELECT id FROM engines WHERE code=?", (code,)).fetchone()
    if r:
        return r[0]
    cur = con.execute(
        "INSERT INTO engines(code,fuel,displacement,power_hp,family) VALUES(?,?,?,?,?)",
        (code, fuel, displacement, power_hp or None, family),
    )
    return cur.lastrowid


def _map_engine(con, eid, sql, args=()):
    for r in con.execute("SELECT id,year_from,year_to FROM generations WHERE " + sql, args):
        con.execute(
            "INSERT OR IGNORE INTO vehicle_engines(generation_id,engine_id,year_from,year_to) VALUES(?,?,?,?)",
            (r[0], eid, r[1], r[2]),
        )


def _source(con, title, url):
    r = con.execute("SELECT id FROM sources WHERE url=?", (url,)).fetchone()
    if r:
        return r[0]
    cur = con.execute(
        "INSERT INTO sources(title,publisher,url,accessed,source_type,notes) VALUES(?,?,?,?,?,?)",
        (title, "Ross-Tech", url, "2026-08-19", "Oficial", "Procedură baterie VCDS"),
    )
    return cur.lastrowid


def _proc(con, title, module, path, steps, prereq, result, warnings, source_id, rule):
    r = con.execute("SELECT id FROM procedure_library WHERE title=?", (title,)).fetchone()
    if r:
        con.execute(
            "UPDATE procedure_library SET category='Baterie',module_address=?,vcds_path=?,steps=?,prerequisites=?,success_criteria=?,warnings=?,applicability_rule=?,verified=1,source_id=? WHERE id=?",
            (module, path, steps, prereq, result, warnings, rule, source_id, r[0]),
        )
        return r[0]
    cur = con.execute(
        """INSERT INTO procedure_library(title,category,module_address,vcds_path,purpose,prerequisites,steps,success_criteria,warnings,applicability_rule,verified,source_id)
           VALUES(?,?,?,?,?,?,?,?,?,?,1,?)""",
        (title, "Baterie", module, path, "Adaptare / înregistrare baterie nouă", prereq, steps, result, warnings, rule, source_id),
    )
    return cur.lastrowid


def _map_proc(con, pid, sql="1=1", args=(), applicability="Condițional"):
    for r in con.execute("SELECT id FROM generations WHERE " + sql, args):
        con.execute(
            "INSERT OR IGNORE INTO vehicle_procedures(generation_id,procedure_id,applicability,notes) VALUES(?,?,?,?)",
            (r[0], pid, applicability, "Confirmă controllerul real prin Auto-Scan înainte de salvare."),
        )


def install(con):
    # Common powertrain families so the vehicle selector is never stuck on 'Nespecificat'.
    engines = [
        ("1.4 MPI", "Benzină", 1.4, "MPI"),
        ("1.6 MPI", "Benzină", 1.6, "MPI"),
        ("1.2 TSI/TFSI", "Benzină", 1.2, "TSI/TFSI"),
        ("1.4 TSI/TFSI", "Benzină", 1.4, "TSI/TFSI"),
        ("1.5 TSI", "Benzină", 1.5, "EA211 evo"),
        ("1.8 TSI/TFSI", "Benzină", 1.8, "EA888"),
        ("2.0 TSI/TFSI", "Benzină", 2.0, "EA888"),
        ("2.5 TFSI", "Benzină", 2.5, "EA855"),
        ("3.0 TFSI", "Benzină", 3.0, "V6 TFSI"),
        ("1.4 TDI", "Diesel", 1.4, "TDI"),
        ("1.9 TDI", "Diesel", 1.9, "TDI"),
        ("2.0 TDI", "Diesel", 2.0, "TDI"),
        ("2.5 TDI", "Diesel", 2.5, "V6/R5 TDI"),
        ("2.7 TDI", "Diesel", 2.7, "V6 TDI"),
        ("3.0 TDI", "Diesel", 3.0, "V6 TDI"),
        ("1.4 eHybrid/PHEV", "Hibrid", 1.4, "PHEV"),
        ("1.5 eTSI MHEV", "Hibrid", 1.5, "MHEV"),
        ("2.0 TFSI eHybrid", "Hibrid", 2.0, "PHEV"),
        ("Electric MEB", "Electric", 0.0, "MEB"),
    ]
    ids = {code: _ensure_engine(con, code, fuel, disp, fam) for code, fuel, disp, fam in engines}

    # Era/platform based backfill. These are family-level choices, not exact engine-code claims.
    _map_engine(con, ids["1.4 MPI"], "year_from<=2008 AND platform IN ('PQ24','PQ34')")
    _map_engine(con, ids["1.6 MPI"], "year_from<=2013 AND platform IN ('PQ24','PQ25','PQ34','PQ35')")
    _map_engine(con, ids["1.9 TDI"], "year_from<=2011 AND platform IN ('PQ24','PQ34','PQ35','PQ46','PL45','PL46')")
    _map_engine(con, ids["2.0 TDI"], "year_to>=2004 AND platform NOT IN ('MEB')")
    _map_engine(con, ids["1.4 TDI"], "platform IN ('PQ24','PQ25','PQ26')")
    _map_engine(con, ids["1.2 TSI/TFSI"], "year_to>=2009 AND year_from<=2017")
    _map_engine(con, ids["1.4 TSI/TFSI"], "year_to>=2006 AND year_from<=2020")
    _map_engine(con, ids["1.5 TSI"], "year_to>=2017 AND platform IN ('MQB','MQB A0','MQB Evo')")
    _map_engine(con, ids["1.8 TSI/TFSI"], "year_to>=2007 AND year_from<=2018")
    _map_engine(con, ids["2.0 TSI/TFSI"], "year_to>=2005 AND platform NOT IN ('MEB')")
    _map_engine(con, ids["2.5 TFSI"], "model_id IN (SELECT id FROM models WHERE name IN ('A3','TT')) AND year_to>=2009")
    _map_engine(con, ids["2.5 TDI"], "year_from<=2010 AND platform IN ('PL45','PL46','PL71','T5')")
    _map_engine(con, ids["2.7 TDI"], "platform IN ('MLB','PL47') AND year_from<=2011")
    _map_engine(con, ids["3.0 TDI"], "platform IN ('MLB','MLB Evo','PL71','PL72','D3','D1','PL47')")
    _map_engine(con, ids["3.0 TFSI"], "platform IN ('MLB','MLB Evo','PL72') AND year_to>=2008")
    _map_engine(con, ids["1.4 eHybrid/PHEV"], "year_to>=2014 AND platform IN ('MQB','MQB Evo')")
    _map_engine(con, ids["1.5 eTSI MHEV"], "year_to>=2020 AND platform IN ('MQB Evo','MQB A0')")
    _map_engine(con, ids["2.0 TFSI eHybrid"], "year_to>=2015 AND platform IN ('MLB','MLB Evo','MQB','MQB Evo')")
    _map_engine(con, ids["Electric MEB"], "platform='MEB'")

    src = _source(con, "Battery Replacement", "https://wiki.ross-tech.com/wiki/index.php/Battery_Replacement")

    p1 = _proc(
        con,
        "Baterie nouă - 61 Battery Regulation / Adaptation",
        "61",
        "[61-Battery Regulation] > [Adaptation-10] > Channel 004",
        "1) Contact ON, motor OFF.\n2) Select > 61-Battery Regulation.\n3) Adaptation-10.\n4) Channel 004 > Read.\n5) SALVEAZĂ valoarea originală.\n6) Introdu datele bateriei noi în formatul cerut de controller.\n7) Test.\n8) Save.\n9) Confirmă mesajul de salvare.\n10) Fault Codes-02 și verifică să nu rămână DTC de battery regulation.\n11) Verifică Measuring Blocks / Advanced Measuring Values pentru tensiune, SOC și curent baterie.",
        "Bateria este deja montată; contact ON; motor OFF; tensiune stabilă. Controllerul 61 trebuie să existe în Auto-Scan.",
        "Noua valoare este acceptată și managementul energetic nu raportează DTC persistente.",
        "Nu folosi această cale dacă 61-Battery Regulation nu există. Nu inventa capacitate/tehnologie/serial dacă controllerul cere date exacte.",
        src,
        "VAG cu Address 61 Battery Regulation",
    )
    _map_proc(con, p1, "year_from>=2004 AND year_from<=2014")

    p2 = _proc(
        con,
        "Baterie nouă - 19 CAN Gateway / Long Adaptation Channel 004",
        "19",
        "[19-CAN Gateway] > [Long Adaptation-0A] > Channel 004",
        "1) Contact ON, motor OFF.\n2) Select > 19-CAN Gateway.\n3) Long Adaptation-0A.\n4) Channel 004 > Read.\n5) Copiază valoarea ORIGINALĂ într-un fișier.\n6) Completează valoarea nouă: Part Number (11 caractere) + spațiu + Vendor (3 caractere) + spațiu + Serial (10 caractere), dacă exact acest format este cerut de controller.\n7) Test.\n8) Save.\n9) Done, Go Back.\n10) Verifică MVB 017 / 018 / 019 / 020 dacă sunt disponibile.\n11) Fault Codes-02 și verifică rezultatul.",
        "Controller 19 cu Long Adaptation și Channel 004; baterie nouă instalată; datele bateriei disponibile.",
        "Channel 004 acceptă datele și valorile de management al bateriei sunt coerente.",
        "Nu presupune că toate Gateway-urile folosesc Channel 004. Dacă nu apare, folosește procedura UDS sau Address 61 dacă există.",
        src,
        "CAN Gateway cu BEM / Channel 004",
    )
    _map_proc(con, p2, "year_from>=2007 AND year_from<=2015")

    p3 = _proc(
        con,
        "Baterie nouă - UDS Battery adaptation",
        "19",
        "[19-CAN Gateway] > [Adaptation-10] > caută 'battery' / 'Batterie'",
        "1) Contact ON, motor OFF.\n2) Select > 19-CAN Gateway.\n3) Adaptation-10.\n4) În Search scrie battery / Batterie.\n5) Notează valorile originale pentru: capacity, technology/type, manufacturer/vendor și serial, dacă apar.\n6) Modifică NUMAI câmpurile oferite de controller.\n7) Save fiecare canal modificat.\n8) Revino în Fault Codes-02 și șterge doar DTC generate de procedură după ce confirmi că sunt rezolvate.\n9) Advanced Measuring Values: verifică battery voltage, state of charge, current și energy management status.",
        "Gateway UDS cu management baterie; baterie nouă instalată; contact ON; motor OFF.",
        "Canalele noi sunt salvate și nu există DTC de adaptare/energy management.",
        "Denumirile IDE/MAS diferă după software. Nu folosi un canal din alt model dacă nu apare în controllerul mașinii tale.",
        src,
        "Gateway UDS / J367 battery management",
    )
    _map_proc(con, p3, "year_to>=2012")

    # Migrate older battery entries to a dedicated category.
    con.execute("UPDATE procedure_library SET category='Baterie' WHERE lower(title) LIKE '%baterie%' OR lower(purpose) LIKE '%baterie%'")
    con.commit()
