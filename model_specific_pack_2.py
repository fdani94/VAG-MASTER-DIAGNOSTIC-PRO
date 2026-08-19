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


def _proc(con, row):
    r = con.execute("SELECT id FROM procedure_library WHERE title=?", (row[0],)).fetchone()
    if r:
        return r[0]
    cur = con.execute("""INSERT INTO procedure_library(
        title,category,module_address,vcds_path,purpose,prerequisites,steps,
        success_criteria,warnings,applicability_rule,verified,source_id)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""", row)
    return cur.lastrowid


def _map(con, pid, sql, args=(), applicability="Exact/Condițional", notes="Confirmă Auto-Scan, part number, software și echiparea înainte de aplicare."):
    for r in con.execute("SELECT id FROM generations WHERE " + sql, args):
        con.execute("INSERT OR IGNORE INTO vehicle_procedures(generation_id,procedure_id,applicability,notes) VALUES(?,?,?,?)",
                    (r[0], pid, applicability, notes))


def install(con):
    src_a3_mk70 = _source(con, "Audi A3 8P / Golf 1K ABS MK70", "https://wiki.ross-tech.com/wiki/index.php/Audi_A3_(8P)_Brake_Electronics_(MK70)")
    src_a3_eps = _source(con, "Audi A3 8P Steering Assist", "https://wiki.ross-tech.com/wiki/index.php/Audi_A3_(8P)_Steering_Assist")
    src_a4 = _source(con, "Audi A4/A5 8K/8T Tweaks", "https://wiki.ross-tech.com/wiki/index.php/Audi_A4/S4/A5/S5_(8K/8T)_Tweaks")
    src_tig = _source(con, "VW Tiguan 5N Brake Electronics", "https://wiki.ross-tech.com/wiki/index.php/VW_Tiguan_(5N)_Brake_Electronics")
    src_a3_8v = _source(con, "Audi A3/S3 8V/FF", "https://wiki.ross-tech.com/wiki/index.php/Audi_A3/S3_(8V/FF)")
    src_bcm2 = _source(con, "MLB BCM2", "https://wiki.ross-tech.com/wiki/index.php/MLB_based_Acc/Start_Auth_(J393)_BCM2")

    rows = [
        ("A3 8P / Leon 1P / Octavia 1Z - TPMS reset MK70 Group 042", "Resetări", "03",
         "[03-ABS Brakes] > [Basic Settings-04] > Group 042",
         "Resetează TPMS indirect bazat pe ABS la controllere MK70 compatibile.",
         "Contact ON; sistem MK70; presiuni anvelope corecte.",
         "1) 03-ABS Brakes. 2) Basic Settings-04. 3) Group 042 > Go. 4) Activează Basic Setting cu ON/OFF/Next. 5) Ieși. 6) Verifică presiunile. 7) Ține apăsate simultan butoanele TPMS și ASR/ESP ~2 secunde dacă echiparea folosește această confirmare. 8) Confirmă stingerea martorului.",
         "Martorul TPMS se stinge după confirmare și sistemul reînvață referința.",
         "Se aplică numai MK70 cu TPMS ABS-based; nu aplica pe MQB/TPMS direct.",
         "A3 8P / Leon 1P / Octavia 1Z / Golf 1K cu MK70", 1, src_a3_mk70),

        ("A3 8P - G85 pe Steering Assist pentru MK70", "Calibrări", "44",
         "[44-Steering Assist] > [Basic Settings-04] > procedura G85 pentru MK70",
         "Calibrează G85 pe vehicule cu ABS Continental/Teves MK70 unde Ross-Tech cere procedura în 44-Steering Assist.",
         "Motor pornit; drum drept scurt sub 20 km/h; volan rotit o tură stânga/dreapta; roți drepte; tensiune >=12 V.",
         "1) Pornește motorul. 2) Execută mișcarea stânga/dreapta și un scurt drum drept. 3) Oprește cu roțile drepte și nu mai mișca volanul. 4) 44-Steering Assist. 5) Rulează Basic Setting G85 conform etichetei/controllerului. 6) Verifică lipsa DTC și adaptează steering limit stop dacă este cerut.",
         "G85 este acceptat și nu mai există DTC de basic setting.",
         "Această procedură NU se aplică MK60/MK60EC1; verifică tipul ABS din Auto-Scan.",
         "Audi A3 8P / platforme PQ35 cu MK70", 1, src_a3_eps),

        ("Audi A4/A5 8K/8T - Needle Sweep / Staging", "Long Coding", "17",
         "[17-Instruments] > [Coding-07] > [Long Coding Helper] > Gauge Test/Needle Sweep active",
         "Activează testul acelor la pornire pe instrument clusters compatibile.",
         "Auto-Scan și coding original salvate; cluster compatibil.",
         "1) 17-Instruments. 2) Coding-07. 3) Long Coding Helper. 4) Activează opțiunea etichetată Gauge Test/Needle Sweep active. 5) Exit. 6) Do It!. 7) Contact OFF/ON și verifică sweep-ul.",
         "Acele fac sweep la pornire.",
         "Nu toate instrument clusters suportă funcția.",
         "Audi A4/S4/A5/S5 8K/8T", 1, src_a4),

        ("Audi A4/A5 8K/8T - Coming Home / Leaving Home", "Long Coding", "09",
         "[09-Cent. Elect.] > [Coding-07] > [Long Coding Helper]",
         "Activează Coming Home / Leaving Home unde BCM1 suportă opțiunile.",
         "Auto-Scan și coding original salvate; verifică senzorul de lumină și echiparea.",
         "1) 09-Cent. Elect. 2) Coding-07. 3) Long Coding Helper. 4) Activează Coming-Home active și/sau Leaving-Home active. 5) Dacă apar canale suplimentare în Adaptation, setează timpul/activarea dorită. 6) Do It!/Save. 7) Testează cu luminile și închiderea centralizată.",
         "Funcțiile CH/LH lucrează conform setării și fără DTC noi.",
         "Opțiunile diferă după BCM1/software; salvează PLA înainte de Adaptation.",
         "Audi A4/S4/A5/S5 8K/8T și Q5 8R compatibil", 1, src_a4),

        ("Audi A4/A5 8K/8T - geamuri confort din telecomandă", "Coding", "46",
         "[46-Comfort System] > [Coding-07] > [Long Coding Helper] + Adaptation key personalization",
         "Activează comfort operation via remote control.",
         "Coding original + PLA salvate; BCM2 compatibil.",
         "1) 46-Comfort System. 2) Coding-07 > Long Coding Helper. 3) Activează Comfort Operation: Remote Control. 4) Do It!. 5) Adaptation-10: verifică personalizarea cheilor în Channels 001-004 și opțiunile comfort din 061/062 dacă există. 6) Salvează fără a suprascrie opțiunile existente. 7) Testează ținând apăsat lock/unlock.",
         "Geamurile se deschid/închid din telecomandă conform personalizării.",
         "Canalele sunt sume de opțiuni; nu înlocui Stored Value cu o valoare generică.",
         "Audi 8K/8T/Q5 8R cu BCM2 compatibil", 1, src_a4),

        ("Tiguan 5N - G85 Security 40168 Group 060", "Calibrări", "03",
         "[03-Brake Electronics] > [Security Access-16] 40168 > [Basic Settings-04] Group 060",
         "Calibrează senzorul de unghi volan G85 pe ABS compatibil Tiguan 5N.",
         "Motor pornit; scurt drum drept sub 20 km/h; roți și volan drepte; tensiune >=12 V.",
         "1) 03-Brake Electronics. 2) Security Access-16 > 40168 > Do It!. 3) Basic Settings-04 > Group 060 > Go. 4) ON/OFF/Next. 5) Câmpul trebuie să indice OK. 6) Measuring Blocks-08 > Group 004 > Field 1 trebuie să fie între -1.5 și +1.5°. 7) Adaptează Steering Limit Stop după procedură.",
         "Group 060 = OK și G85 este în intervalul -1.5…+1.5° cu roțile drepte.",
         "Nu opri motorul în timpul procedurii.",
         "VW Tiguan 5N", 1, src_tig),

        ("Tiguan 5N - G200/G202/G251 Security 40168 Group 061", "Calibrări", "03",
         "[03-Brake Electronics] > [Measuring Blocks-08] Group 004 > [Security Access-16] 40168 > [Basic Settings-04] Group 061",
         "Calibrează senzorii accelerație laterală/longitudinală și yaw rate.",
         "Tensiune >=12 V; vehicul staționar pe suprafață plană.",
         "1) MVB Group 004: Fields 2/3/4 trebuie să fie aprox. -1.5…+1.5 m/s² sau °/s. 2) Security Access 40168. 3) Basic Settings Group 061. 4) ON/OFF/Next. 5) Field 2 trebuie să indice OK. 6) Re-verifică Group 004.",
         "Group 061 = OK și valorile senzorilor rămân în intervalul aproximativ -1.5…+1.5.",
         "Execută pe suprafață plană, fără mișcarea vehiculului.",
         "VW Tiguan 5N", 1, src_tig),

        ("Tiguan 5N - G201 Group 066", "Calibrări", "03",
         "[03-Brake Electronics] > [Measuring Blocks-08] Group 005 > [Security Access-16] 40168 > [Basic Settings-04] Group 066",
         "Calibrează senzorul de presiune frână G201.",
         "Tensiune >=12 V; fără presiune intenționată pe pedală în momentul calibrării.",
         "1) MVB Group 005 Field 1: înainte de calibrare trebuie să fie între -8 și +8 bar. 2) Security Access 40168. 3) Basic Settings Group 066. 4) ON/OFF/Next. 5) Field 3 = OK. 6) Re-verifică Group 005; după calibrare Field 1 trebuie să fie între -3.8 și +3.8 bar.",
         "Group 066 = OK și presiunea este în intervalul -3.8…+3.8 bar după calibrare.",
         "Dacă presiunea nu revine aproape de zero, diagnostichează senzorul/hidraulica înainte de a repeta adaptarea.",
         "VW Tiguan 5N", 1, src_tig),

        ("Audi A3 8V - pregătire modificări 09 prin Channel Map", "Proceduri", "09",
         "[09-Cent. Elect.] > Applications/Controller Channels Map > Adaptation Map înainte de modificări",
         "Salvează harta completă a canalelor de Adaptation înainte de codări pe MQB.",
         "Interfață compatibilă; 09-Cent. Elect. comunică normal.",
         "1) Auto-Scan complet. 2) Creează Controller Channel Map pentru Address 09. 3) Salvează fișierul PLA/CSV. 4) Abia apoi modifică Adaptation/Long Coding. 5) După modificări, creează o a doua hartă pentru comparație.",
         "Ai backup înainte/după al adaptărilor BCM.",
         "Pe MQB multe funcții sunt în Adaptation, nu în Byte/Bit clasic.",
         "Audi A3/S3 8V/FF", 1, src_a3_8v),

        ("MLB BCM2 - avertizare înlocuire modul 05/46", "Înlocuire / Calibrare", "05",
         "[05-Acc/Start Auth.] / [46-Central Conv.] > Auto-Scan + Coding backup",
         "Documentează ce poate face VCDS înainte de înlocuirea BCM2.",
         "Auto-Scan complet și coding salvat.",
         "1) Salvează Auto-Scan și Long Coding. 2) Identifică part number, HW, SW și Component BCM2. 3) VCDS poate citi/coda funcțiile suportate, dar dacă modulul este înlocuit și apar probleme de imobilizator/Component Protection, nu încerca proceduri improvizate în VCDS. 4) Marchează operația ca incompletă în aplicație.",
         "Coding și configurația veche sunt documentate; aplicația avertizează că finalizarea înlocuirii nu este VCDS-only.",
         "Nu există o procedură VCDS completă pentru Component Protection/immobilizer matching la BCM2 MLB.",
         "Audi 8K/8T/Q5 8R/A6 4G/A8 4H cu BCM2", 1, src_bcm2),
    ]

    ids = {row[0]: _proc(con, row) for row in rows}

    maps = {
        "A3 8P / Leon 1P / Octavia 1Z - TPMS reset MK70 Group 042": "(name LIKE '8P%' OR name LIKE 'II 1Z%' OR name LIKE 'II 1P%')",
        "A3 8P - G85 pe Steering Assist pentru MK70": "name LIKE '8P%'",
        "Audi A4/A5 8K/8T - Needle Sweep / Staging": "(name LIKE 'B8 8K%' OR name LIKE '8T%')",
        "Audi A4/A5 8K/8T - Coming Home / Leaving Home": "(name LIKE 'B8 8K%' OR name LIKE '8T%')",
        "Audi A4/A5 8K/8T - geamuri confort din telecomandă": "(name LIKE 'B8 8K%' OR name LIKE '8T%' OR name LIKE '8R%')",
        "Tiguan 5N - G85 Security 40168 Group 060": "name LIKE '5N%'",
        "Tiguan 5N - G200/G202/G251 Security 40168 Group 061": "name LIKE '5N%'",
        "Tiguan 5N - G201 Group 066": "name LIKE '5N%'",
        "Audi A3 8V - pregătire modificări 09 prin Channel Map": "name LIKE '8V%'",
        "MLB BCM2 - avertizare înlocuire modul 05/46": "(platform LIKE 'MLB%' OR name LIKE 'B8 8K%' OR name LIKE '8R%')",
    }
    for title, where in maps.items():
        _map(con, ids[title], where)

    con.commit()
