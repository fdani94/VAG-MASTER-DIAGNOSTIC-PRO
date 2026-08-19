from datetime import datetime


def _source(con, title, url, notes=""):
    r = con.execute("SELECT id FROM sources WHERE url=?", (url,)).fetchone()
    if r:
        return r[0]
    cur = con.execute(
        "INSERT INTO sources(title,publisher,url,accessed,source_type,notes) VALUES(?,?,?,?,?,?)",
        (title, "Ross-Tech", url, datetime.now().date().isoformat(), "Oficial", notes),
    )
    return cur.lastrowid


def _add_col(con, table, col, definition):
    cols = {r[1] for r in con.execute(f"PRAGMA table_info({table})")}
    if col not in cols:
        con.execute(f"ALTER TABLE {table} ADD COLUMN {col} {definition}")


def _model_id(con, brand, model):
    r = con.execute("""SELECT m.id FROM models m JOIN brands b ON b.id=m.brand_id
                     WHERE b.name=? AND m.name=?""", (brand, model)).fetchone()
    return r[0] if r else None


def _ensure_model(con, brand, model):
    bid = con.execute("SELECT id FROM brands WHERE name=?", (brand,)).fetchone()
    if not bid:
        cur = con.execute("INSERT INTO brands(name) VALUES(?)", (brand,))
        bid = (cur.lastrowid,)
    con.execute("INSERT OR IGNORE INTO models(brand_id,name) VALUES(?,?)", (bid[0], model))
    return _model_id(con, brand, model)


def _ensure_generation(con, brand, model, name, yf, yt, chassis, platform, url):
    mid = _ensure_model(con, brand, model)
    r = con.execute("SELECT id FROM generations WHERE model_id=? AND name=?", (mid, name)).fetchone()
    if r:
        return r[0]
    cur = con.execute("INSERT INTO generations(model_id,name,year_from,year_to,chassis,platform,ross_tech_url) VALUES(?,?,?,?,?,?,?)",
                      (mid,name,yf,yt,chassis,platform,url))
    return cur.lastrowid


def _proc(con, title, category, module, path, purpose, prereq, steps, success, warnings, rule, verified, source_id):
    r = con.execute("SELECT id FROM procedure_library WHERE title=?", (title,)).fetchone()
    if r:
        return r[0]
    cur = con.execute("""INSERT INTO procedure_library(title,category,module_address,vcds_path,purpose,prerequisites,steps,
        success_criteria,warnings,applicability_rule,verified,source_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
        (title,category,module,path,purpose,prereq,steps,success,warnings,rule,verified,source_id))
    return cur.lastrowid


def _map(con, pid, where_sql, args=(), applicability="Condițional", notes="Confirmă part number, software, PR-codes și Auto-Scan înainte de aplicare."):
    for r in con.execute("SELECT id FROM generations WHERE " + where_sql, args):
        con.execute("INSERT OR IGNORE INTO vehicle_procedures(generation_id,procedure_id,applicability,notes) VALUES(?,?,?,?)",
                    (r[0], pid, applicability, notes))


def _upsert_dtc(con, code, title, description, symptoms, causes, diagnosis, repair, severity, source_id, component, location, test_path):
    r = con.execute("SELECT id FROM dtcs WHERE code=?", (code,)).fetchone()
    if r:
        con.execute("""UPDATE dtcs SET title=?,description=?,symptoms=?,causes=?,diagnosis=?,repair=?,severity=?,verified=1,source_id=?,
                     component=?,component_location=?,test_path=? WHERE code=?""",
                    (title,description,symptoms,causes,diagnosis,repair,severity,source_id,component,location,test_path,code))
    else:
        con.execute("""INSERT INTO dtcs(code,title,description,symptoms,causes,diagnosis,repair,severity,verified,source_id,component,component_location,test_path)
                     VALUES(?,?,?,?,?,?,?,?,1,?,?,?,?)""",
                    (code,title,description,symptoms,causes,diagnosis,repair,severity,source_id,component,location,test_path))


def install(con):
    _add_col(con, "dtcs", "component", "TEXT DEFAULT ''")
    _add_col(con, "dtcs", "component_location", "TEXT DEFAULT ''")
    _add_col(con, "dtcs", "test_path", "TEXT DEFAULT ''")

    src_diag = _source(con, "Diagnostic Procedures", "https://wiki.ross-tech.com/wiki/index.php/Diagnostic_Procedures", "Catalog Ross-Tech pentru chassis-uri VAG")
    src_epb = _source(con, "Electro-Mechanical Parking Brake", "https://wiki.ross-tech.com/wiki/index.php/Working_on_the_Electro-Mechanical_Parking_Brake_%28EPB%29")
    src_eps_mqb = _source(con, "EPS MQB", "https://wiki.ross-tech.com/wiki/index.php/EPS_MQB")
    src_readiness = _source(con, "Readiness Test UDS", "https://wiki.ross-tech.com/wiki/index.php/Readiness_Test_%28UDS_only%29")
    src_battery = _source(con, "Battery Replacement", "https://wiki.ross-tech.com/wiki/index.php/Battery_Replacement")
    src_egr = _source(con, "EGR Valve Adaptation", "https://wiki.ross-tech.com/wiki/index.php/Exhaust_Gas_Recirculation_%28EGR%29_Valve_Adaptation")
    src_p0299 = _source(con, "P0299 Boost Pressure", "https://wiki.ross-tech.com/wiki/index.php/16683/P0299/000665")
    src_p0401 = _source(con, "P0401 EGR", "https://wiki.ross-tech.com/wiki/index.php/16785/P0401/001025")
    src_p0101 = _source(con, "P0101 MAF", "https://wiki.ross-tech.com/wiki/index.php/16485/P0101/000257")

    G = [
        ("Volkswagen","Golf","VIII CD/CG",2020,2024,"CD/CG","MQB Evo", "https://wiki.ross-tech.com/wiki/index.php/Diagnostic_Procedures"),
        ("Volkswagen","Passat","B8 3G/CB",2015,2024,"3G/CB","MQB", "https://wiki.ross-tech.com/wiki/index.php/Diagnostic_Procedures"),
        ("Volkswagen","Polo","AW",2018,2024,"AW","MQB A0", "https://wiki.ross-tech.com/wiki/index.php/Diagnostic_Procedures"),
        ("Volkswagen","Tiguan","AD/BW",2016,2024,"AD/BW","MQB", "https://wiki.ross-tech.com/wiki/index.php/Diagnostic_Procedures"),
        ("Volkswagen","Touran","5T",2015,2024,"5T","MQB", "https://wiki.ross-tech.com/wiki/index.php/Diagnostic_Procedures"),
        ("Volkswagen","Caddy","SB",2021,2024,"SB","MQB", "https://wiki.ross-tech.com/wiki/index.php/Diagnostic_Procedures"),
        ("Volkswagen","Touareg","CR",2018,2024,"CR","MLB Evo", "https://wiki.ross-tech.com/wiki/index.php/Diagnostic_Procedures"),
        ("Volkswagen","Transporter","T6 SG",2015,2019,"SG","T6", "https://wiki.ross-tech.com/wiki/index.php/Diagnostic_Procedures"),
        ("Volkswagen","Transporter","T6.1 SH",2020,2024,"SH","T6.1", "https://wiki.ross-tech.com/wiki/index.php/Diagnostic_Procedures"),
        ("Audi","A1","GB",2019,2024,"GB","MQB A0", "https://wiki.ross-tech.com/wiki/index.php/Diagnostic_Procedures"),
        ("Audi","A3","8Y",2021,2024,"8Y","MQB Evo", "https://wiki.ross-tech.com/wiki/index.php/Diagnostic_Procedures"),
        ("Audi","A4","B9 8W",2016,2024,"8W","MLB Evo", "https://wiki.ross-tech.com/wiki/index.php/Diagnostic_Procedures"),
        ("Audi","A5","F5",2017,2024,"F5","MLB Evo", "https://wiki.ross-tech.com/wiki/index.php/Diagnostic_Procedures"),
        ("Audi","A6","C8 4K",2019,2024,"4K","MLB Evo", "https://wiki.ross-tech.com/wiki/index.php/Diagnostic_Procedures"),
        ("Audi","A7","4K",2019,2024,"4K","MLB Evo", "https://wiki.ross-tech.com/wiki/index.php/Diagnostic_Procedures"),
        ("Audi","A8","D5 4N",2018,2024,"4N","MLB Evo", "https://wiki.ross-tech.com/wiki/index.php/Diagnostic_Procedures"),
        ("Audi","Q3","F3",2019,2024,"F3","MQB", "https://wiki.ross-tech.com/wiki/index.php/Diagnostic_Procedures"),
        ("Audi","Q5","FY",2017,2024,"FY","MLB Evo", "https://wiki.ross-tech.com/wiki/index.php/Diagnostic_Procedures"),
        ("Audi","Q7","4M",2016,2024,"4M","MLB Evo", "https://wiki.ross-tech.com/wiki/index.php/Diagnostic_Procedures"),
        ("Audi","TT","8S/FV",2015,2024,"8S/FV","MQB", "https://wiki.ross-tech.com/wiki/index.php/Diagnostic_Procedures"),
        ("Škoda","Fabia","NJ",2015,2021,"NJ","PQ26", "https://wiki.ross-tech.com/wiki/index.php/Diagnostic_Procedures"),
        ("Škoda","Fabia","PJ",2022,2024,"PJ","MQB A0", "https://wiki.ross-tech.com/wiki/index.php/Diagnostic_Procedures"),
        ("Škoda","Octavia","III 5E",2013,2020,"5E","MQB", "https://wiki.ross-tech.com/wiki/index.php/Diagnostic_Procedures"),
        ("Škoda","Octavia","IV NX",2020,2024,"NX","MQB Evo", "https://wiki.ross-tech.com/wiki/index.php/Diagnostic_Procedures"),
        ("Škoda","Superb","III 3V",2015,2024,"3V","MQB", "https://wiki.ross-tech.com/wiki/index.php/Diagnostic_Procedures"),
        ("Škoda","Karoq","NU",2018,2024,"NU","MQB", "https://wiki.ross-tech.com/wiki/index.php/Diagnostic_Procedures"),
        ("Škoda","Kodiaq","NS",2017,2024,"NS","MQB", "https://wiki.ross-tech.com/wiki/index.php/Diagnostic_Procedures"),
        ("SEAT / Cupra","Ibiza","KJ",2018,2024,"KJ","MQB A0", "https://wiki.ross-tech.com/wiki/index.php/Diagnostic_Procedures"),
        ("SEAT / Cupra","Leon","III 5F",2013,2020,"5F","MQB", "https://wiki.ross-tech.com/wiki/index.php/Diagnostic_Procedures"),
        ("SEAT / Cupra","Leon","IV KL",2020,2024,"KL1/KL8/KU1/KU8","MQB Evo", "https://wiki.ross-tech.com/wiki/index.php/Diagnostic_Procedures"),
        ("SEAT / Cupra","Ateca","KH7/KHP",2016,2024,"KH7/KHP","MQB", "https://wiki.ross-tech.com/wiki/index.php/Diagnostic_Procedures"),
        ("SEAT / Cupra","Formentor","KM7",2021,2024,"KM7","MQB Evo", "https://wiki.ross-tech.com/wiki/index.php/Diagnostic_Procedures"),
        ("SEAT / Cupra","Born","K11",2022,2024,"K11","MEB", "https://wiki.ross-tech.com/wiki/index.php/Diagnostic_Procedures"),
    ]
    for g in G:
        _ensure_generation(con, *g)

    pid = _proc(con,"G85 calibrare EPS MQB / MQB Evo - Security 19249","Basic Settings","44",
        "[44-Steering Assist] > [Security Access-16] 19249 > [Basic Settings-04] > MAS00815 Steering angle sensor",
        "Calibrare G85 integrat în J500 pe EPS MQB.",
        "Motor pornit; confirmă în Auto-Scan EPS_MQB_ZFLS sau BASGEN1MQB37; unele BASGEN1MQB37 necesită SFD unlock.",
        "1) 44-Steering Assist. 2) Security Access 16 > 19249. 3) Basic Settings 04 > MAS00815 Steering angle sensor > Go. 4) Bracaj complet stânga 5 secunde. 5) Bracaj complet dreapta 5 secunde. 6) Centrează volanul. 7) Stop > Done/Go Back. 8) Repetă stânga/dreapta 5 secunde și centrează. 9) Close Controller. 10) Contact OFF 10 secunde.",
        "Procedura poate rămâne pe Running; după ciclul de contact, șterge DTC-urile databus generate.",
        "Nu aplica dacă Auto-Scan nu arată componentele compatibile; unele versiuni necesită SFD unlock.",
        "MQB/MQB Evo cu EPS compatibil",1,src_eps_mqb)
    _map(con,pid,"platform IN ('MQB','MQB Evo','MQB A0')",applicability="Exact/Condițional")

    pid = _proc(con,"Readiness UDS - Automatic test sequence","Basic Settings","01",
        "[01-Engine] > DTC clear > [Basic Settings] > Automatic test sequence/procedure > Show Measuring Data",
        "Execută automat monitoarele readiness pe ECM benzină UDS.",
        "Motor pornit; consumatori electrici OFF; fără DTC active; coolant >=80°C; exterior sau zonă bine ventilată.",
        "1) 01-Engine. 2) Verifică/șterge DTC. 3) Basic Settings. 4) Selectează Automatic test sequence/procedure. 5) Bifează Show Measuring Data. 6) Adaugă IDE00450, IDE00451, IDE00030, IDE00727 și IDE00021. 7) Urmează exact Operating Instructions până când IDE00727 ajunge la 0.",
        "IDE00727 = 0 și rutina este finalizată.",
        "Nu efectua în spațiu închis și nu ignora instrucțiunile de turație ale ECU.",
        "ECM benzină UDS compatibil",1,src_readiness)
    _map(con,pid,"year_from>=2010")

    pid = _proc(con,"Înlocuire baterie - 19 CAN Gateway UDS","Adaptation","19",
        "[19-CAN Gateway] > [Adaptation-10] > battery adaptation/replacement channels",
        "Înregistrează bateria nouă pe vehicule unde managementul bateriei este în Gateway UDS.",
        "Bateria nouă instalată; contact ON, motor OFF; notează capacitate, producător/serial unde sunt cerute.",
        "1) 19-CAN Gateway > Adaptation 10. 2) Caută canalele battery adaptation/replacement. 3) Salvează valorile originale. 4) Introdu datele bateriei noi cerute de controller. 5) Save. 6) Verifică DTC și starea managementului energetic.",
        "Valorile sunt salvate fără DTC de adaptare.",
        "Canalele diferă după Gateway/software; nu inventa part number/vendor pentru baterii aftermarket.",
        "VAG modern cu battery management în Gateway UDS",1,src_battery)
    _map(con,pid,"year_from>=2012")

    pid = _proc(con,"EPB service plăcuțe - MQB prin 03 ABS","Frâne","03",
        "[03-ABS Brakes] > [Basic Settings-04] > Open Rear Parking Brake / Close Rear Parking Brake / Function Test",
        "Retrage și readuce actuatoarele EPB pentru înlocuirea plăcuțelor.",
        "Vehicul securizat; EPB eliberat; tensiune stabilă.",
        "1) 03-ABS > Basic Settings. 2) Open Rear Parking Brake. 3) Așteaptă finalizarea și ieși din controller. 4) Schimbă plăcuțele. 5) Revino în Basic Settings. 6) Close Rear Parking Brake. 7) Function Test dacă este disponibil. 8) Șterge DTC și verifică EPB.",
        "EPB se deschide/închide și Function Test se termină fără DTC persistente.",
        "Nu acționa pistonul înainte de service mode; pe mașini mai vechi EPB poate fi în Address 53.",
        "MQB/MQB Evo cu EPB în ABS",1,src_epb)
    _map(con,pid,"platform IN ('MQB','MQB Evo')",applicability="Exact/Condițional")

    pid = _proc(con,"EGR Valve Adaptation - Group 074 benzină","Basic Settings","01",
        "[01-Engine] > [Meas. Blocks-08] Group 074 > Switch to Basic Settings",
        "Adaptează valva EGR pe motoare benzină compatibile.",
        "Contact ON; motor OFF; tensiune >=12.5 V; pentru ME7.5 coolant 10-50°C.",
        "1) Measuring Blocks 08 > Group 074. 2) Verifică 074.1 Min, 074.2 Max, 074.3 Potentiometer, 074.4 status. 3) Switch to Basic Settings. 4) Așteaptă ca 074.4 să treacă Run -> ADP OK. 5) Switch to Measuring Blocks > Close Controller.",
        "074.4 = ADP OK.",
        "Dacă eșuează, contact OFF 30 secunde și reîncearcă după verificarea condițiilor.",
        "Motoare benzină cu Group 074",1,src_egr)
    _map(con,pid,"year_from<=2012")

    _upsert_dtc(con,"P0299","Boost Pressure Regulation: Control Range Not Reached",
        "Presiunea turbo reală nu atinge cererea ECU.","Putere redusă; limp mode.",
        "Pierdere charge-air; furtun fisurat; intercooler neetanș; vacuum/N75; actuator/geometrie; turbo; diverter valve pe benzină; posibilă restricție evacuare.",
        "1) Log boost specified vs actual. 2) Inspectează turbo-intercooler-admisie. 3) Diesel: vacuum, N75/actuator, geometrie. 4) Benzină: diverter valve. 5) Dacă traseul și comanda sunt bune, verifică turbina și evacuarea.",
        "Repară cauza confirmată; înlocuiește turbina doar după confirmare. Șterge DTC și repetă logul.",
        "Ridicat",src_p0299,"Turbocharger, actuator/N75, furtunuri charge-air, intercooler.",
        "Turbo pe evacuare; intercooler frontal; traseul leagă turbo-intercooler-admisie. N75/actuatorul diferă după motor.",
        "01-Engine > Advanced Measuring Values > Charge/Boost Pressure specified + actual; Log în sarcină.")

    _upsert_dtc(con,"P0401","EGR System: Insufficient Flow Detected",
        "Debitul EGR este sub cel așteptat.","MIL; emisii crescute; posibilă lipsă de putere.",
        "EGR/țevi/răcitor colmatate; EGR defect; cablaj; exhaust pressure flap/filtru EGR pe unele CR TDI.",
        "1) Verifică DTC asociate. 2) EGR specified/actual + MAF + poziția EGR. 3) Cablaj/conector. 4) Traseu EGR pentru depuneri. 5) Output Tests/Basic Settings dacă ECU oferă test. 6) CR TDI: verifică și exhaust pressure flap dacă există DTC asociate.",
        "Curăță restricțiile, repară cablajul sau înlocuiește EGR numai după confirmare. Re-verifică actual vs specified.",
        "Mediu",src_p0401,"Valvă EGR, conducte/răcitor EGR, eventual exhaust pressure flap.",
        "EGR este între evacuare și admisie; poziția exactă diferă după motor; frecvent în zona galeriei de admisie/răcitorului EGR.",
        "01-Engine > Advanced Measuring Values > EGR specified/actual + MAF; Output Tests/Basic Settings dacă există.")

    _upsert_dtc(con,"P0101","Mass Air Flow Sensor (G70): Implausible Signal",
        "Semnalul MAF nu corespunde modelului de aer calculat.","Putere slabă; consum crescut; fum; posibil limp mode.",
        "MAF contaminat/defect; filtru aer blocat; fals aer; EGR; cablaj/conector MAF.",
        "1) Filtru și admisie după MAF. 2) Mufa/cablajul G70. 3) Air Mass specified vs actual la ralanti și sarcină. 4) Corelează cu EGR specified/actual. 5) Nu condamna MAF înainte de fals aer/EGR.",
        "Repară falsul aer/cablajul/EGR; înlocuiește MAF doar după confirmare. Șterge DTC și repetă logul.",
        "Mediu",src_p0101,"Senzor G70 MAF, filtru aer și traseu de admisie.",
        "MAF este de regulă imediat după carcasa filtrului de aer, înaintea turbo/clapetei, în funcție de motor.",
        "01-Engine > Measuring Blocks/Advanced Measuring Values > Mass/Air Flow specified + actual.")

    con.commit()
