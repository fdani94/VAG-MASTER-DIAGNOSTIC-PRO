"""KID Diagnostic - broad 1996-2024 VAG catalog + common VCDS procedure coverage.

This pack fills important generation gaps and attaches Ross-Tech common procedures
as CONDITIONAL procedures. Exact applicability still depends on controller,
engine/transmission code, PR codes and protocol.
"""


def _brand_id(con, name):
    row = con.execute("SELECT id FROM brands WHERE name=?", (name,)).fetchone()
    if row:
        return row[0]
    return con.execute("INSERT INTO brands(name) VALUES(?)", (name,)).lastrowid


def _model_id(con, brand, model):
    bid = _brand_id(con, brand)
    row = con.execute("SELECT id FROM models WHERE brand_id=? AND name=?", (bid, model)).fetchone()
    if row:
        return row[0]
    return con.execute("INSERT INTO models(brand_id,name) VALUES(?,?)", (bid, model)).lastrowid


def _gen(con, brand, model, name, y1, y2, chassis, platform, url="https://wiki.ross-tech.com/wiki/index.php/Diagnostic_Procedures"):
    mid = _model_id(con, brand, model)
    row = con.execute("SELECT id FROM generations WHERE model_id=? AND name=?", (mid, name)).fetchone()
    if row:
        con.execute("UPDATE generations SET year_from=?,year_to=?,chassis=?,platform=?,ross_tech_url=? WHERE id=?",
                    (y1, y2, chassis, platform, url, row[0]))
        return row[0]
    return con.execute("INSERT INTO generations(model_id,name,year_from,year_to,chassis,platform,ross_tech_url) VALUES(?,?,?,?,?,?,?)",
                       (mid, name, y1, y2, chassis, platform, url)).lastrowid


def _source(con, title, url, notes=""):
    con.execute("INSERT OR IGNORE INTO sources(title,publisher,url,source_type,notes) VALUES(?,?,?,?,?)",
                (title, "Ross-Tech", url, "Oficial", notes))
    row = con.execute("SELECT id FROM sources WHERE url=?", (url,)).fetchone()
    return row[0] if row else None


def _proc(con, title, category, module, path, purpose, prerequisites, steps, success, warnings, rule, source_id, verified=1):
    row = con.execute("SELECT id FROM procedure_library WHERE title=? AND category=? LIMIT 1", (title, category)).fetchone()
    vals = (module, path, purpose, prerequisites, steps, success, warnings, rule, verified, source_id)
    if row:
        con.execute("""UPDATE procedure_library SET module_address=?,vcds_path=?,purpose=?,prerequisites=?,steps=?,success_criteria=?,warnings=?,applicability_rule=?,verified=?,source_id=? WHERE id=?""", vals + (row[0],))
        return row[0]
    return con.execute("""INSERT INTO procedure_library(title,category,module_address,vcds_path,purpose,prerequisites,steps,success_criteria,warnings,applicability_rule,verified,source_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                       (title, category) + vals).lastrowid


def _attach(con, proc_id, where_sql, args=(), note="Procedură comună Ross-Tech; confirmă exact controllerul și configurația înainte de executare."):
    rows = con.execute("SELECT id FROM generations WHERE " + where_sql, args).fetchall()
    for r in rows:
        con.execute("INSERT OR IGNORE INTO vehicle_procedures(generation_id,procedure_id,applicability,notes) VALUES(?,?,?,?)",
                    (r[0], proc_id, "Condițional", note))


def install(con):
    # Important generation gaps across the 1996-2024 VAG passenger/light-commercial range.
    generations = [
        ("Volkswagen","Bora / Jetta","1J/9M",1998,2005,"1J/9M","PQ34"),
        ("Volkswagen","Jetta","5C/1K",2005,2011,"1K","PQ35"),
        ("Volkswagen","Jetta","16/AJ",2011,2018,"16/AJ","PQ35"),
        ("Volkswagen","New Beetle","1C/9C",1998,2010,"1C/9C","PQ34"),
        ("Volkswagen","Beetle","5C",2012,2019,"5C","PQ35"),
        ("Volkswagen","Sharan","7M",1996,2010,"7M","7M"),
        ("Volkswagen","Sharan","7N",2010,2022,"7N","PQ46"),
        ("Volkswagen","Eos","1F",2006,2015,"1F","PQ35"),
        ("Volkswagen","CC","35",2008,2017,"35","PQ46"),
        ("Volkswagen","Polo","AW",2017,2024,"AW","MQB A0"),
        ("Volkswagen","Up!","AA",2012,2023,"AA","NSF"),
        ("Volkswagen","Crafter","2E/2F",2006,2016,"2E/2F","LT3"),
        ("Volkswagen","Crafter","SY/SZ",2017,2024,"SY/SZ","Crafter 2"),
        ("Audi","A2","8Z",2000,2005,"8Z","PQ24"),
        ("Audi","A5","8T/8F",2008,2016,"8T/8F","MLB"),
        ("Audi","A7","4G",2011,2018,"4G","MLB"),
        ("Audi","TT","8N",1999,2006,"8N","PQ34"),
        ("Audi","TT","8J",2007,2014,"8J","PQ35"),
        ("Audi","TT","8S",2015,2023,"8S","MQB"),
        ("Audi","Q3","8U",2011,2018,"8U","PQ35"),
        ("Audi","Q5","8R",2008,2017,"8R","MLB"),
        ("Škoda","Roomster","5J",2006,2015,"5J","PQ25"),
        ("Škoda","Yeti","5L",2009,2017,"5L","PQ35"),
        ("Škoda","Rapid","NH",2012,2019,"NH","PQ25"),
        ("SEAT / Cupra","Toledo","1M",1999,2004,"1M","PQ34"),
        ("SEAT / Cupra","Toledo","5P",2004,2009,"5P","PQ35"),
        ("SEAT / Cupra","Toledo","KG",2012,2019,"KG","PQ25"),
        ("SEAT / Cupra","Altea","5P",2004,2015,"5P","PQ35"),
        ("SEAT / Cupra","Alhambra","7M",1996,2010,"7M","7M"),
        ("SEAT / Cupra","Alhambra","7N",2010,2020,"7N","PQ46"),
        ("SEAT / Cupra","Exeo","3R",2009,2013,"3R","PL46"),
        ("SEAT / Cupra","Ibiza","KJ",2017,2024,"KJ","MQB A0"),
    ]
    for row in generations:
        _gen(con, *row)

    src_common = _source(con, "Ross-Tech Common Procedures", "https://wiki.ross-tech.com/wiki/index.php/Common_Procedures")
    src_tba = _source(con, "Ross-Tech Throttle Body Alignment", "https://wiki.ross-tech.com/wiki/index.php/Throttle_Body_Alignment_(TBA)")
    src_batt = _source(con, "Ross-Tech Battery Replacement", "https://wiki.ross-tech.com/wiki/index.php/Battery_Replacement")
    src_epb = _source(con, "Ross-Tech EPB Rear Brake Service", "https://wiki.ross-tech.com/wiki/index.php/Working_on_the_Electro-Mechanical_Parking_Brake_(EPB)")
    src_02e = _source(con, "Ross-Tech DSG 02E", "https://wiki.ross-tech.com/wiki/index.php/6-Speed_Direct_Shift_Gearbox_(DSG/02E)")
    src_0am = _source(con, "Ross-Tech DSG 0AM", "https://wiki.ross-tech.com/wiki/index.php/7-Speed_Direct_Shift_Gearbox_(DSG/0AM)")
    src_sri = _source(con, "Ross-Tech SRI Reset", "https://wiki.ross-tech.com/wiki/index.php/SRI_Reset_Procedure")
    src_dpf = _source(con, "Ross-Tech DPF Emergency Regeneration", "https://wiki.ross-tech.com/wiki/index.php/Diesel_Particle_Filter_Emergency_Regeneration")
    src_level = _source(con, "Ross-Tech Level Control non-UDS", "https://wiki.ross-tech.com/wiki/index.php/Suspension_Level_Control_Calibration_(non-UDS)")

    p_tba = _proc(con, "Adaptare / reset clapetă accelerație (TBA) - procedură comună", "Adaptări", "01",
        "[01-Engine] → [Basic Settings] / canalul sau funcția indicată de controller",
        "Reînvățarea pozițiilor clapetei după curățare, demontare, ECU/baterie sau intervenții relevante.",
        "Motor benzină cu clapetă motorizată; fără DTC în Engine; baterie ≥11.5 V; accelerația neatinsă; clapeta curată; lichid răcire aproximativ 5–95 °C.",
        "1) Salvează Auto-Scan. 2) Intră în 01-Engine. 3) Verifică Fault Codes și condițiile. 4) Deschide Basic Settings. 5) Folosește grupul/canalul indicat pentru protocolul ECU (KW1281/KWP/CAN/UDS). 6) Pornește adaptarea și așteaptă confirmarea controllerului. 7) Clear DTC doar după finalizare și verifică ralantiul.",
        "Basic Setting terminat cu succes / ADP OK sau echivalentul controllerului; ralanti stabil și fără DTC relevant.",
        "Nu aplica pe dieselurile vechi fără clapetă motorizată și nu ghici canalul. Procedura exactă diferă după protocol/ECU.",
        "Motoare pe benzină; aplicabilitatea exactă se confirmă după ECU și protocol.", src_tba, 1)
    _attach(con, p_tba, "year_to>=1996")

    p_sri = _proc(con, "Reset interval service / ulei (SRI)", "Resetări", "17",
        "[Applications] → [SRI Reset] sau [17-Instruments] → [Adaptation] pe clusterele care cer procedură manuală",
        "Resetarea mesajului de service după efectuarea mentenanței.",
        "Revizia trebuie efectuată; contact pus; valori originale salvate dacă se modifică manual Adaptation.",
        "1) Deschide VCDS și SRI Reset. 2) Lasă VCDS să citească valorile service. 3) Alege operația potrivită regiunii/clusterului. 4) Perform SRI. 5) Ciclu contact și verifică afișajul. Pe unele clustere 2010+ folosește 17-Instruments → Adaptation → ESI: Resetting ESI și, dacă este necesar, resetează timpul/distanța de la inspecție.",
        "Mesajul de service dispare după ciclul de contact și valorile de service sunt coerente.",
        "Nu reseta service-ul înainte de efectuarea lucrărilor. Audi-urile și clusterele UDS moderne pot avea canale diferite.",
        "Majoritatea modelelor moderne; procedura diferă pe clustere foarte vechi și UDS.", src_sri, 1)
    _attach(con, p_sri, "year_to>=1996")

    p_batt = _proc(con, "Înlocuire și înregistrare baterie / BEM", "Înlocuire piese", "19/61",
        "[61-Battery Regulation] SAU [19-CAN Gateway] → [Long Adaptation]/[Adaptation], după configurație",
        "Înregistrarea bateriei noi în sistemul de management energetic.",
        "Baterie nouă montată; contact ON, motor OFF; identifică dacă mașina folosește Address 61, Gateway CAN sau Gateway UDS; salvează valoarea originală.",
        "1) Auto-Scan înainte de înlocuire. 2) Identifică BEM/J367 și modulul care gestionează bateria. 3) Pentru Gateway CAN, Ross-Tech documentează 19-CAN Gateway → Long Adaptation-0A → Channel 004 și formatul piesă/vendor/serial. 4) Pentru UDS folosește canalele Battery adaptation oferite de controller. 5) Salvează și verifică datele bateriei în Measuring Values.",
        "Controllerul acceptă datele bateriei și nu apar DTC-uri noi de management energetic.",
        "Nu inventa part number/vendor/serial. Nu toate modelele cer înregistrare; procedura exactă depinde de configurația BEM.",
        "Condițional: vehicule echipate cu management baterie/BEM/J367.", src_batt, 1)
    _attach(con, p_batt, "year_from>=2003", note="Condițional numai dacă Auto-Scan arată Battery Regulation/BEM/J367 sau Battery Management în Gateway.")

    p_epb = _proc(con, "Schimb plăcuțe spate cu frână de parcare electrică (EPB)", "Înlocuire piese", "53/03",
        "[53-Parking Brake] → [Basic Settings-04] sau [03-ABS] pe platformele MQB",
        "Deschiderea modului service EPB, înlocuirea plăcuțelor și închiderea/finalizarea modului service.",
        "Încărcător de baterie conectat; Auto-Scan salvat; EPB funcțional; sistem complet asamblat înainte de Basic Settings; EPB OFF înainte de deschidere.",
        "1) Identifică din Auto-Scan dacă EPB este Address 53 sau integrat în 03-ABS. 2) Rulează Basic Setting-ul specific platformei pentru Open Rear Parking Brake. 3) Așteaptă aproximativ 30 s după oprirea mișcărilor. 4) Efectuează mecanic lucrarea. 5) Reasamblează complet. 6) Rulează Basic Setting-ul pentru Close/End lining change mode. 7) Când procedura platformei cere, rulează Function Test. 8) Verifică Fault Codes.",
        "EPB funcționează normal, modul service este închis și nu rămân DTC-uri după verificare.",
        "Grupurile Basic Settings diferă între platforme; nu folosi un număr de grup de la alt model. Tensiunea joasă poate întrerupe procedura.",
        "Numai vehicule cu EPB electric.", src_epb, 1)
    _attach(con, p_epb, "platform IN ('PQ46','MQB','MQB Evo','MLB','MLB Evo','PL71','PL72','D3','D4') OR year_from>=2015")

    p_02e = _proc(con, "DSG 6 trepte 02E/DQ250 - Basic Settings + test drive", "Adaptări", "02",
        "[02-Transmission] → [Basic Settings-04]",
        "Calibrarea transmisiei 02E/DQ250 după intervenții compatibile, inclusiv mecatronică, când documentația o cere.",
        "NUMAI 02E/DQ250; ulei 30–100 °C și nivel corect; selector P; motor la ralanti ≥1 min; frâna apăsată continuu; accelerația neatinsă; cruise OFF.",
        "Secvența Ross-Tech include 061 (toleranțe), 060 (punct sincronizare), apoi 062 sau 067 în funcție de software, 068, 065, 063 și 069 unde se aplică. Așteaptă finalizarea fiecărui grup, apoi contact OFF ~10 s, verifică DTC și efectuează Defined Test Drive conform procedurii 02E.",
        "Basic Settings finalizate și transmisia trece testul definit fără DTC relevant.",
        "NU aplica procedura 02E pe 0AM/DQ200, DQ500, 0B5 sau alte cutii. Identifică exact transmisia din Auto-Scan/PR-code.",
        "Numai transmisie 02E/DQ250.", src_02e, 1)
    _attach(con, p_02e, "platform IN ('PQ35','PQ46','MQB')", note="Condițional NUMAI dacă transmisia identificată este 02E/DQ250.")

    p_0am = _proc(con, "DSG 7 trepte 0AM/DQ200 - Basic Settings", "Adaptări", "02",
        "[02-Transmission] → [Basic Settings-04] → Group 060 (0AM)",
        "Basic Settings pentru transmisia 0AM/DQ200 după intervenții compatibile.",
        "NUMAI 0AM/DQ200; fără DTC în TCM în afară de basic setting; ulei 30–60 °C (G510, MVB 011.1); selector P; contact ON; motor OFF inițial; EPB aplicat; frâna apăsată; accelerația neatinsă.",
        "1) Group 060 → Go/ON-OFF-Next dacă este necesar. 2) Așteaptă 4|0|0; pornește imediat motorul numai după acest rezultat. 3) Așteaptă confirmarea finală 254|0|0. 4) Done/Go Back, ciclu contact, verifică DTC. 5) Efectuează Defined Test Drive specific 0AM.",
        "Rezultat final 254|0|0 și test drive/adaptări fără DTC relevant.",
        "Nu porni motorul dacă 4|0|0 nu apare. 255|0|0 indică întrerupere/eșec. NU aplica pe alte DSG, în special 0B5 longitudinal.",
        "Numai transmisie 0AM/DQ200.", src_0am, 1)
    _attach(con, p_0am, "platform IN ('PQ25','PQ35','PQ46')", note="Condițional NUMAI dacă transmisia identificată este 0AM/DQ200.")

    p_dpf = _proc(con, "DPF - regenerare de urgență / verificare încărcare", "Regenerare", "01",
        "[01-Engine] → [Security Access/Coding-II] → [Basic Settings] / funcția de regenerare indicată de ECU",
        "Regenerare DPF când specificațiile ECU permit și cauza care a dus la încărcare este rezolvată.",
        "Motor diesel cu DPF; fără defecte care interzic regenerarea; temperaturi/încărcare în limitele ECU; capotă închisă; condițiile exacte diferă după ECU. Respectă avertismentele termice.",
        "1) Citește soot mass/particle filter load și temperaturile din Measuring Values. 2) Confirmă că sarcina este sub limita permisă de ECU/procedura specifică. 3) Folosește Security Access afișat de VCDS și Basic Setting-ul «Regeneration while Standing» sau procedura specifică ECU. 4) Urmează instrucțiunile VCDS până la final. 5) Verifică după regenerare soot mass și DTC. Pe ECU mai vechi pot exista MVB/grupuri și Coding-II specifice motorului.",
        "Regenerare terminată fără abort și încărcarea DPF scade semnificativ; nu rămân DTC-uri care blochează regenerarea.",
        "Temperaturile evacuării devin foarte ridicate. Nu forța regenerarea peste limita de funingine documentată pentru ECU; unele cazuri cer înlocuirea/curățarea profesională a DPF.",
        "Numai diesel cu DPF și numai când ECU permite procedura.", src_dpf, 1)
    _attach(con, p_dpf, "year_to>=2005", note="Condițional: numai motoare diesel echipate cu DPF; verifică ECU/cod motor înainte de procedură.")

    p_level = _proc(con, "Suspensie pneumatică - calibrare nivel non-UDS", "Calibrări", "34",
        "[34-Level Control] → [Security Access-16] 31564 → [Adaptation-10] Channels 01-05",
        "Calibrarea înălțimii pe sistemele Level Control non-UDS.",
        "NUMAI non-UDS; mașină pe suprafață plană; motor la ralanti; frâna de parcare aplicată; uși/capotă/portbagaj închise; ruletă metrică; măsoară vertical centru roată → margine aripă.",
        "1) Security Access 31564. 2) Adaptation Channel 01 stânga față: introdu valoarea măsurată în mm. 3) Channel 02 dreapta față. 4) Channel 03 stânga spate. 5) Channel 04 dreapta spate. 6) Channel 05 → New Value 1 → Test/Save. 7) Done/Go Back și verifică DTC.",
        "Calibrarea se finalizează și 34-Level Control rămâne fără DTC relevant.",
        "Nu utiliza această procedură pe UDS. Pentru UDS există procedură diferită; evită Resetting of all adaptations deoarece pe anumite module poate produce B2013 și necesar de parametrizare online.",
        "Sisteme non-UDS Level Control, tipic A6/A8/Q7/Phaeton/Touareg din generațiile compatibile.", src_level, 1)
    _attach(con, p_level, "platform IN ('D1','D3','PL71','PL72','PL47','MLB') OR chassis IN ('3D','4E','4F/FB','4L/FE','7L/A9','7P/BP')",
            note="Condițional numai dacă Auto-Scan arată 34-Level Control non-UDS (ex. LUFTFDR.-CDC/J197 LUFTFEDER).")

    con.commit()
