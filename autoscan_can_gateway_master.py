"""KID Diagnostic - CAN/Gateway Master pack.
Correlates common VAG network DTCs and prioritizes root-cause diagnosis.
"""


def _ensure_columns(con):
    cols = {r[1] for r in con.execute("PRAGMA table_info(dtcs)").fetchall()}
    for name, typ in {
        "component": "TEXT", "component_location": "TEXT", "vcds_parameters": "TEXT",
        "expected_values": "TEXT", "test_path": "TEXT", "replacement_steps": "TEXT",
    }.items():
        if name not in cols:
            con.execute(f"ALTER TABLE dtcs ADD COLUMN {name} {typ}")


def _source(con, title, url):
    con.execute("INSERT OR IGNORE INTO sources(title,publisher,url,source_type,notes) VALUES(?,?,?,?,?)",
                (title, "Ross-Tech", url, "official/wiki", "CAN/Gateway diagnostic reference"))
    row = con.execute("SELECT id FROM sources WHERE url=?", (url,)).fetchone()
    return row[0] if row else None


def _upsert(con, code, title, desc, causes, diagnosis, repair, component, path, source_id, verified=1):
    row = con.execute("SELECT id FROM dtcs WHERE UPPER(code)=UPPER(?) LIMIT 1", (code,)).fetchone()
    vals = (title, desc, "Martori multipli; functie indisponibila; DTC-uri secundare in mai multe module.",
            causes, diagnosis, repair, "medium", verified, source_id, component,
            "Reteaua CAN/LIN si modulul sursa indicat de Auto-Scan; locatia fizica depinde de platforma.",
            "Supply voltage; module communication status; CAN source signal; Freeze Frame; MVB/Advanced Measuring Values",
            "Tensiune stabila; modulele asteptate online; mesaje sursa plauzibile.", path,
            "Dupa reparatie: Clear DTC -> ciclu contact -> test functional/test drive -> Auto-Scan complet.")
    if row:
        con.execute("""UPDATE dtcs SET title=?,description=?,symptoms=?,causes=?,diagnosis=?,repair=?,severity=?,verified=?,source_id=?,component=?,component_location=?,vcds_parameters=?,expected_values=?,test_path=?,replacement_steps=? WHERE id=?""", vals + (row[0],))
    else:
        con.execute("""INSERT INTO dtcs(code,title,description,symptoms,causes,diagnosis,repair,severity,verified,source_id,component,component_location,vcds_parameters,expected_values,test_path,replacement_steps) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (code,) + vals)


def install(con):
    _ensure_columns(con)
    src_01312 = _source(con, "Ross-Tech 01312 Powertrain Data Bus", "https://wiki.ross-tech.com/wiki/index.php/01312")
    src_02071 = _source(con, "Ross-Tech 02071 Local Databus", "https://wiki.ross-tech.com/wiki/index.php/02071")
    src_p1649 = _source(con, "Ross-Tech P1649", "https://wiki.ross-tech.com/wiki/index.php/18057/P1649/005705")
    src_p1853 = _source(con, "Ross-Tech P1853", "https://wiki.ross-tech.com/wiki/index.php/18261/P1853/006227")

    _upsert(con, "01312", "Powertrain Data Bus - communication fault",
            "Eroare de comunicatie pe magistrala powertrain; poate genera o cascada de DTC-uri secundare.",
            "Modul powertrain offline; alimentare/masa; CAN H/L; conector; Gateway/configuratie; subtensiune.",
            "1) Salveaza Auto-Scan complet. 2) Noteaza toate modulele fara comunicatie. 3) Verifica tensiunea bateriei si erorile de subtensiune. 4) Verifica Gateway installation list. 5) Intra in modulul sursa daca raspunde. 6) Verifica sigurante/alimentare/masa. 7) Daca mai multe module de pe aceeasi magistrala lipsesc, verifica CAN H/L si punctele comune inainte de a condamna modulele.",
            "Repara mai intai alimentarea, masa sau modulul/cablajul comun. Nu inlocui mai multe module doar pentru ca raporteaza erori de comunicatie.",
            "CAN Powertrain / Gateway", "[Auto-Scan] -> [19-CAN Gateway] -> Installation List -> module sursa -> Fault Codes / MVB", src_01312)

    _upsert(con, "02071", "Local Databus - communication fault",
            "Problema pe o magistrala locala/LIN; mai multe componente slave pot disparea din cauza unei singure defectiuni.",
            "Slave defect; fir LIN intrerupt/scurt; conector; alimentare slave; master; apa/coroziune.",
            "1) Identifica modulul master din Auto-Scan. 2) Vezi ce slave lipsesc. 3) Daca lipsesc mai multe simultan, cauta alimentarea/firul comun. 4) Verifica conectorii si coroziunea. 5) Deconecteaza/testeaza componentele numai conform schemei electrice. 6) Ruleaza Output Tests/Advanced Measuring Values daca modulul le ofera.",
            "Repara firul/alimentarea sau componenta care blocheaza magistrala. Rescaneaza dupa fiecare interventie pentru a vedea daca reapar slave-urile.",
            "LIN / Local Databus", "[Auto-Scan] -> modul master -> Fault Codes -> Advanced Measuring Values / Output Tests", src_02071)

    _upsert(con, "P1649", "Missing Message from ABS/Brake Electronics",
            "ECU motor nu primeste corect informatia asteptata de la sistemul ABS/ESP.",
            "DTC primar in J104/03-ABS; ABS offline; alimentare; CAN; coding/configuratie.",
            "1) Nu diagnostica ECU motor primul. 2) Intra in 03-Brake Electronics. 3) Rezolva DTC-urile ABS primare. 4) Verifica alimentarea J104 si comunicatia CAN daca 03 nu raspunde. 5) Sterge codurile din toate modulele si rescaneaza.",
            "Repara cauza din ABS/ESP sau comunicatia catre J104; apoi sterge P1649 si efectueaza test drive.",
            "ABS/ESP J104 -> Engine", "[01-Engine] P1649 -> [03-Brake Electronics] -> Fault Codes", src_p1649)

    _upsert(con, "P1853", "Powertrain Data Bus / ABS message context",
            "DTC de comunicatie care poate fi secundar unei probleme ABS si, pe anumite DSG 02E, poate necesita Basic Setting dupa remedierea comunicatiei.",
            "ABS/ESP DTC; comunicatie CAN; configuratie; adaptare DSG incompleta.",
            "1) Verifica 03-Brake Electronics si rezolva DTC-urile primare. 2) Verifica MVB/communication status. 3) Pe 02E, numai daca procedura se aplica exact configuratiei, verifica procedura Basic Settings Group 069 din documentatia Ross-Tech. 4) Nu aplica Group 069 altor cutii doar dupa numele DTC-ului.",
            "Repara intai cauza ABS/CAN. Daca vehiculul are DSG 02E si documentatia o cere, finalizeaza Basic Setting-ul specific si rescaneaza.",
            "CAN Powertrain / ABS / DSG 02E context", "[03-Brake Electronics] -> Fault Codes; apoi [02-Transmission] -> [Basic Settings-04] -> Group 069 numai pentru configuratia documentata", src_p1853)

    # Additional relationship rules represented as DTC guidance entries.
    generic = [
        ("P1650", "Missing/implausible message from instrument cluster", "Instrument cluster J285 / CAN", "Verifica 17-Instruments, alimentarea clusterului, Gateway si CAN; rezolva DTC-ul sursa inainte de ECU."),
        ("P1637", "Missing/implausible message from central electronics", "BCM/J519 / CAN", "Verifica 09-Central Electronics, alimentarea J519, coding si CAN; cauta DTC-ul primar in 09."),
        ("P1625", "Missing message from transmission control", "TCM/J217 / CAN", "Verifica 02-Transmission, alimentare/masa, CAN si MVB communication status; nu condamna ECU motor pentru cod secundar."),
        ("01315", "Transmission Control Module - No Communication", "TCM / CAN", "Verifica daca 02-Transmission raspunde, sigurante, alimentare, masa si CAN; apoi erorile primare ale TCM."),
        ("01316", "ABS Control Module - No Communication / DTC stored", "ABS J104 / CAN", "Verifica 03-Brake Electronics, alimentare/masa/CAN si DTC-urile ABS; poate fi secundar in alte module."),
    ]
    for code, title, component, advice in generic:
        _upsert(con, code, title, "DTC de retea care trebuie corelat cu toate modulele din Auto-Scan.",
                "Modul sursa offline sau cu DTC primar; alimentare; masa; CAN; coding/configuratie; subtensiune.",
                "1) Salveaza Auto-Scan. 2) Identifica modulul sursa. 3) Verifica tensiunea si erorile comune. 4) Intra direct in modulul sursa. 5) Rezolva DTC-urile lui. 6) Daca nu comunica, verifica sigurante/alimentare/masa/CAN. " + advice,
                "Repara cauza primara, apoi Clear DTC in toate modulele afectate si rescaneaza.",
                component, "[Auto-Scan] -> modul sursa -> Fault Codes -> Advanced Measuring Values / communication status", src_01312, verified=0)

    con.commit()
