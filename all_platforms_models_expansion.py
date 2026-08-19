"""Broad VAG catalog expansion, 1996-2024.

Adds missing model/generation/platform rows for Volkswagen, Audi, Skoda and SEAT/Cupra.
This module expands catalog/navigation coverage only. It does NOT claim that every controller,
engine, coding or repair procedure is verified for every row. The coverage audit/gap-filler
continues to distinguish verified from conditional data.
"""

DIAG_URL = "https://wiki.ross-tech.com/wiki/index.php/Diagnostic_Procedures"

# brand, model, generation, year_from, year_to, chassis, platform
GENERATIONS = [
    # VOLKSWAGEN - legacy/PQ
    ("Volkswagen", "Bora / Jetta", "Bora/Jetta IV 1J/9M", 1998, 2005, "1J/9M", "PQ34"),
    ("Volkswagen", "Jetta", "Jetta V 1K", 2005, 2010, "1K", "PQ35"),
    ("Volkswagen", "Jetta", "Jetta VI 16/AJ", 2011, 2018, "16/AJ", "PQ35/PQ46 derivative"),
    ("Volkswagen", "New Beetle", "9C/1C", 1998, 2010, "9C/1C", "PQ34"),
    ("Volkswagen", "Beetle", "5C", 2012, 2019, "5C", "PQ35"),
    ("Volkswagen", "Sharan", "7M", 1996, 2010, "7M", "7M"),
    ("Volkswagen", "Sharan", "7N", 2010, 2022, "7N", "PQ46"),
    ("Volkswagen", "Eos", "1F", 2006, 2015, "1F", "PQ35"),
    ("Volkswagen", "CC", "35", 2008, 2017, "35", "PQ46"),
    ("Volkswagen", "Passat", "B8 3G", 2014, 2024, "3G", "MQB"),
    ("Volkswagen", "Golf", "VIII CD", 2019, 2024, "CD", "MQB Evo"),
    ("Volkswagen", "Polo", "AW", 2017, 2024, "AW", "MQB-A0"),
    ("Volkswagen", "Up!", "AA", 2011, 2023, "AA", "NSF"),
    ("Volkswagen", "Tiguan", "AD/BW", 2016, 2024, "AD/BW", "MQB"),
    ("Volkswagen", "T-Roc", "A1/AC", 2017, 2024, "A1/AC", "MQB-A1"),
    ("Volkswagen", "T-Cross", "C1/BF", 2019, 2024, "C1/BF", "MQB-A0"),
    ("Volkswagen", "Taigo", "CS", 2021, 2024, "CS", "MQB-A0"),
    ("Volkswagen", "Arteon", "3H", 2017, 2024, "3H", "MQB"),
    ("Volkswagen", "Touran", "5T", 2015, 2024, "5T", "MQB"),
    ("Volkswagen", "Caddy", "SB", 2020, 2024, "SB", "MQB"),
    ("Volkswagen", "Transporter", "T6 7E/7F", 2015, 2019, "7E/7F", "T6"),
    ("Volkswagen", "Transporter", "T6.1 SH/SJ", 2019, 2024, "SH/SJ", "T6.1"),
    ("Volkswagen", "Touareg", "CR", 2018, 2024, "CR", "MLB Evo"),
    ("Volkswagen", "ID.3", "E1", 2019, 2024, "E1", "MEB"),
    ("Volkswagen", "ID.4", "E2", 2020, 2024, "E2", "MEB"),
    ("Volkswagen", "ID.5", "E3", 2021, 2024, "E3", "MEB"),
    ("Volkswagen", "ID.7", "ED", 2023, 2024, "ED", "MEB"),
    ("Volkswagen", "ID. Buzz", "EB", 2022, 2024, "EB", "MEB"),

    # AUDI
    ("Audi", "A1", "8X", 2010, 2018, "8X", "PQ25"),
    ("Audi", "A1", "GB", 2018, 2024, "GB", "MQB-A0"),
    ("Audi", "A2", "8Z", 2000, 2005, "8Z", "A04"),
    ("Audi", "A3", "8Y", 2020, 2024, "8Y", "MQB Evo"),
    ("Audi", "A4", "B9 8W", 2015, 2024, "8W", "MLB Evo"),
    ("Audi", "A5", "8T/8F", 2007, 2016, "8T/8F", "MLB"),
    ("Audi", "A5", "F5", 2016, 2024, "F5", "MLB Evo"),
    ("Audi", "A6", "C8 4K", 2018, 2024, "4K", "MLB Evo"),
    ("Audi", "A7", "4G", 2010, 2018, "4G", "MLB"),
    ("Audi", "A7", "4K", 2018, 2024, "4K", "MLB Evo"),
    ("Audi", "A8", "4H", 2010, 2017, "4H", "MLB"),
    ("Audi", "A8", "4N", 2017, 2024, "4N", "MLB Evo"),
    ("Audi", "Q2", "GA", 2016, 2024, "GA", "MQB"),
    ("Audi", "Q3", "8U", 2011, 2018, "8U", "PQ35"),
    ("Audi", "Q3", "F3", 2018, 2024, "F3", "MQB"),
    ("Audi", "Q5", "FY", 2017, 2024, "FY", "MLB Evo"),
    ("Audi", "Q7", "4M", 2015, 2024, "4M", "MLB Evo"),
    ("Audi", "Q8", "4M", 2018, 2024, "4M", "MLB Evo"),
    ("Audi", "TT", "8N", 1998, 2006, "8N", "PQ34"),
    ("Audi", "TT", "8J", 2006, 2014, "8J", "PQ35"),
    ("Audi", "TT", "8S/FV", 2014, 2023, "8S/FV", "MQB"),
    ("Audi", "e-tron", "GE", 2018, 2024, "GE", "MLB Evo"),
    ("Audi", "Q4 e-tron", "F4", 2021, 2024, "F4", "MEB"),
    ("Audi", "e-tron GT", "FW", 2021, 2024, "FW", "J1"),

    # SKODA
    ("Škoda", "Fabia", "NJ", 2014, 2021, "NJ", "PQ26"),
    ("Škoda", "Fabia", "PJ", 2021, 2024, "PJ", "MQB-A0"),
    ("Škoda", "Octavia", "III 5E", 2013, 2020, "5E", "MQB"),
    ("Škoda", "Octavia", "IV NX", 2019, 2024, "NX", "MQB Evo"),
    ("Škoda", "Superb", "III 3V", 2015, 2024, "3V", "MQB"),
    ("Škoda", "Roomster", "5J", 2006, 2015, "5J", "PQ25"),
    ("Škoda", "Yeti", "5L", 2009, 2017, "5L", "PQ35"),
    ("Škoda", "Rapid", "NH", 2012, 2019, "NH", "PQ25"),
    ("Škoda", "Scala", "NW", 2019, 2024, "NW", "MQB-A0"),
    ("Škoda", "Kamiq", "NW", 2019, 2024, "NW", "MQB-A0"),
    ("Škoda", "Karoq", "NU", 2017, 2024, "NU", "MQB"),
    ("Škoda", "Kodiaq", "NS", 2016, 2024, "NS", "MQB"),
    ("Škoda", "Enyaq", "5A", 2020, 2024, "5A", "MEB"),
    ("Škoda", "Citigo", "NF", 2011, 2020, "NF", "NSF"),

    # SEAT / CUPRA
    ("SEAT / Cupra", "Ibiza", "KJ", 2017, 2024, "KJ", "MQB-A0"),
    ("SEAT / Cupra", "Leon", "5F", 2012, 2020, "5F", "MQB"),
    ("SEAT / Cupra", "Leon", "KL", 2020, 2024, "KL", "MQB Evo"),
    ("SEAT / Cupra", "Toledo", "5P", 2004, 2009, "5P", "PQ35"),
    ("SEAT / Cupra", "Toledo", "KG", 2012, 2019, "KG", "PQ25"),
    ("SEAT / Cupra", "Altea", "5P", 2004, 2015, "5P", "PQ35"),
    ("SEAT / Cupra", "Alhambra", "7N", 2010, 2020, "7N", "PQ46"),
    ("SEAT / Cupra", "Exeo", "3R", 2008, 2013, "3R", "PL46"),
    ("SEAT / Cupra", "Ateca", "KH", 2016, 2024, "KH", "MQB"),
    ("SEAT / Cupra", "Arona", "KJ", 2017, 2024, "KJ", "MQB-A0"),
    ("SEAT / Cupra", "Tarraco", "KN", 2018, 2024, "KN", "MQB"),
    ("SEAT / Cupra", "Mii", "KF", 2011, 2021, "KF", "NSF"),
    ("SEAT / Cupra", "Formentor", "KM", 2020, 2024, "KM", "MQB Evo"),
    ("SEAT / Cupra", "Born", "K1", 2021, 2024, "K1", "MEB"),
]

PLATFORM_FAMILIES = {
    "Legacy K-Line": ("PQ24", "PQ25", "PQ26", "PQ34", "PL45", "PL46", "PL47", "7M", "A04", "NSF"),
    "PQ CAN": ("PQ35", "PQ46", "PL71", "PL72", "T5", "T6", "T6.1"),
    "MQB": ("MQB", "MQB-A0", "MQB-A1", "MQB Evo"),
    "MLB": ("MLB", "MLB Evo"),
    "Electric": ("MEB", "J1"),
}


def _brand_id(con, brand):
    row = con.execute("SELECT id FROM brands WHERE name=?", (brand,)).fetchone()
    if row:
        return row[0]
    return con.execute("INSERT INTO brands(name) VALUES(?)", (brand,)).lastrowid


def _model_id(con, brand, model):
    bid = _brand_id(con, brand)
    row = con.execute("SELECT id FROM models WHERE brand_id=? AND name=?", (bid, model)).fetchone()
    if row:
        return row[0]
    return con.execute("INSERT INTO models(brand_id,name) VALUES(?,?)", (bid, model)).lastrowid


def _generation_exists(con, mid, name, chassis):
    return con.execute(
        "SELECT id FROM generations WHERE model_id=? AND name=? AND COALESCE(chassis,'')=? LIMIT 1",
        (mid, name, chassis),
    ).fetchone()


def install(con):
    # Optional platform registry for QA/filtering. Safe on existing databases.
    con.execute("""
        CREATE TABLE IF NOT EXISTS platform_registry(
            id INTEGER PRIMARY KEY,
            platform TEXT UNIQUE NOT NULL,
            family TEXT NOT NULL,
            year_scope TEXT DEFAULT '1996-2024',
            notes TEXT DEFAULT ''
        )
    """)
    for family, platforms in PLATFORM_FAMILIES.items():
        for platform in platforms:
            con.execute(
                "INSERT OR IGNORE INTO platform_registry(platform,family,notes) VALUES(?,?,?)",
                (platform, family, "Catalog/platform family; controller-level applicability remains conditional."),
            )

    for brand, model, gen, y1, y2, chassis, platform in GENERATIONS:
        mid = _model_id(con, brand, model)
        if not _generation_exists(con, mid, gen, chassis):
            con.execute(
                """INSERT INTO generations(model_id,name,year_from,year_to,chassis,platform,ross_tech_url)
                   VALUES(?,?,?,?,?,?,?)""",
                (mid, gen, y1, y2, chassis, platform, DIAG_URL),
            )
        else:
            # Fill missing metadata without overwriting a more specific existing record.
            con.execute(
                """UPDATE generations SET
                       year_from=COALESCE(year_from,?), year_to=COALESCE(year_to,?),
                       platform=CASE WHEN COALESCE(platform,'')='' THEN ? ELSE platform END,
                       ross_tech_url=CASE WHEN COALESCE(ross_tech_url,'')='' THEN ? ELSE ross_tech_url END
                   WHERE model_id=? AND name=? AND COALESCE(chassis,'')=?""",
                (y1, y2, platform, DIAG_URL, mid, gen, chassis),
            )
    con.commit()
