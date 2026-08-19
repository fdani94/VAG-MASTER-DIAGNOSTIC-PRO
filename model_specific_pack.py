from datetime import datetime


def _source(con, title, url):
    r = con.execute("SELECT id FROM sources WHERE url=?", (url,)).fetchone()
    if r:
        return r[0]
    cur = con.execute(
        "INSERT INTO sources(title,publisher,url,accessed,source_type,notes) VALUES(?,?,?,?,?,?)",
        (title, "Ross-Tech", url, datetime.now().date().isoformat(), "Oficial", "Procedură model-specific VCDS"),
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


def _map(con, pid, sql, args=(), note="Procedură exactă pentru controller/platformă compatibilă. Confirmă Auto-Scan și part number-ul înainte."):
    for r in con.execute("SELECT id FROM generations WHERE " + sql, args):
        con.execute("INSERT OR IGNORE INTO vehicle_procedures(generation_id,procedure_id,applicability,notes) VALUES(?,?,?,?)",
                    (r[0], pid, "VERIFICAT / MODEL-SPECIFIC", note))


def install(con):
    src_mk60 = _source(con, "Golf 1K Brake Electronics MK60", "https://wiki.ross-tech.com/wiki/index.php/VW_Golf_%281K%29_Brake_Electronics_%28MK60%29")
    src_mk60ec1 = _source(con, "Golf 1K Brake Electronics MK60EC1", "https://wiki.ross-tech.com/wiki/index.php/VW_Eos_%281F%29_Brake_Electronics_%28MK60EC1%29")
    src_p3c_epb = _source(con, "Passat 3C Parking Brake", "https://wiki.ross-tech.com/wiki/index.php/VW_Passat_%283C%29_Parking_Brake")
    src_p3c_abs = _source(con, "Passat 3C Brake Electronics", "https://wiki.ross-tech.com/wiki/index.php/VW_Passat_%283C%29_Brake_Electronics")
    src_g5k_cluster = _source(con, "Golf 5K Instrument Cluster", "https://wiki.ross-tech.com/wiki/index.php/VW_Golf_%285K%29_Instrument_Cluster")

    rows = []

    rows.append((
        "PQ35 MK60 - G85 Steering Angle exact", "Calibrări", "03",
        "[03-Brake Electronics] > MVB 004 field 1 > Security Access/Coding-II 40168 > Basic Settings Group 060",
        "Calibrare senzor unghi volan G85.",
        "Motor pornit; tensiune >=12.0 V; roți drepte; după scurtă deplasare <20 km/h. MVB 004 field 1 trebuie să fie între -1.5 și +1.5 grade.",
        "1) 03-Brake Electronics. 2) Measuring Blocks 08 > Group 004. 3) Confirmă field 1 între -1.5 și +1.5°. 4) Done. 5) Security Access 16 sau Coding-II 11 > 40168 > Do It. 6) Basic Settings 04 > Group 060 > Go. 7) Așteaptă field 2 = OK. 8) Done/Go Back. 9) Adaptează Steering Limit Stop dacă este cerut.",
        "Group 060 field 2 = OK; G85 rămâne aproape de 0° cu volanul drept.",
        "Nu continua dacă valoarea G85 este în afara ±1.5°.",
        "PQ35 MK60", 1, src_mk60))

    rows.append((
        "PQ35 MK60 - G200 Lateral Acceleration exact", "Calibrări", "03",
        "[03-Brake Electronics] > MVB 004 field 2 > Security Access 40168 > Basic Settings Group 063",
        "Calibrare senzor accelerație laterală G200.",
        "Tensiune >=12 V; vehicul pe suprafață plană; MVB 004 field 2 între -1.5 și +1.5 m/s².",
        "1) 03 > Measuring Blocks 08 > Group 004. 2) Verifică field 2. 3) Security Access/Coding-II > 40168. 4) Basic Settings 04 > Group 063 > Go. 5) ON/OFF/Next. 6) Așteaptă field 2 = OK. 7) Revino în MVB 004 și reconfirmă valoarea.",
        "Field 2 = OK și valoarea G200 rămâne în ±1.5 m/s².",
        "Nu calibra pe rampă sau cu vehiculul înclinat.",
        "PQ35 MK60", 1, src_mk60))

    rows.append((
        "PQ35 MK60 - G201 Brake Pressure Sensor exact", "Calibrări", "03",
        "[03-Brake Electronics] > MVB 005 field 1 > Security Access 40168 > Basic Settings Group 066",
        "Calibrare senzor presiune frână G201.",
        "Tensiune >=12 V; pedala de frână eliberată. Înainte de calibrare MVB 005 field 1 trebuie să fie între -8 și +8 bar.",
        "1) 03 > Measuring Blocks 08 > Group 005. 2) Verifică field 1. 3) Security Access/Coding-II 40168. 4) Basic Settings 04 > Group 066 > Go. 5) ON/OFF/Next. 6) Așteaptă OK. 7) Revino în MVB 005. 8) După calibrare valoarea trebuie să fie aproximativ între -3.8 și +3.8 bar.",
        "Group 066 = OK și MVB 005 field 1 în aproximativ ±3.8 bar.",
        "Dacă presiunea nu este aproape de zero cu pedala eliberată, verifică sistemul înainte de calibrare.",
        "PQ35 MK60", 1, src_mk60))

    rows.append((
        "PQ35 MK60 - G251 Longitudinal Acceleration exact", "Calibrări", "03",
        "[03-Brake Electronics] > MVB 006 field 1 > Security Access 40168 > Basic Settings Group 069",
        "Calibrare G251 pe AWD/Hill Hold.",
        "Doar vehicule cu G251; tensiune >=12 V; suprafață plană; MVB 006 field 1 între -1.5 și +1.5 m/s².",
        "1) 03 > MVB 006. 2) Confirmă field 1. 3) Security Access/Coding-II 40168. 4) Basic Settings 04 > Group 069. 5) ON/OFF/Next. 6) Așteaptă OK. 7) Reconfirmă MVB 006.",
        "Group 069 = OK și G251 în ±1.5 m/s².",
        "Nu se aplică vehiculelor fără G251.",
        "PQ35 MK60 cu AWD/HHC", 1, src_mk60))

    rows.append((
        "PQ35 MK60 - TPMS ABS reset Group 042", "Resetări", "03",
        "[03-Brake Electronics] > [Basic Settings-04] > Group 042",
        "Resetare sistem TPMS bazat pe ABS, PR-7K1/7K6.",
        "Contact ON; sistem TPMS indirect instalat.",
        "1) 03-Brake Electronics. 2) Basic Settings 04 > Group 042 > Go. 3) ON/OFF/Next. 4) Corectează presiunile. 5) Ține apăsat butonul TPMS împreună cu ASR/ESP aproximativ 2 secunde dacă echiparea folosește această secvență. 6) Confirmă stingerea martorului după finalizare.",
        "Reset acceptat și martor TPMS stins după inițializare.",
        "Se aplică doar TPMS indirect PR-7K1/7K6.",
        "PQ35 MK60 cu TPMS indirect", 1, src_mk60))

    rows.append((
        "MK60EC1 - Hydraulic Intake Valves Group 025", "Calibrări", "03",
        "[03-Brake Electronics] > Security Access 40168 > Basic Settings Group 025",
        "Calibrare valve intake după înlocuire modul ABS când DTC 00003 indică basic setting incomplet.",
        "Temperatura pompei sub 27°C; motor pornit; sistem frână aerisit; se face înainte de Group 026.",
        "1) 03 > Security Access 16 > 40168. 2) Basic Settings 04 > Group 025. 3) ON/OFF/Next. 4) Urmează presiunile cerute de controller apăsând pedala până când valoarea reală intră în intervalul afișat. 5) Menține până la [000/000]. 6) Repetă până apare Calibrated. 7) Deactivate și continuă cu Group 026.",
        "Controllerul afișează Calibrated pentru valvele intake.",
        "Doar după înlocuire modul/hidraulică și doar dacă procedura este disponibilă; menține temperatura pompei sub 27°C.",
        "MK60EC1 compatibil", 1, src_mk60ec1))

    rows.append((
        "Passat 3C EPB - Open Rear Parking Brake Group 007", "Service", "53",
        "[53-Parking Brake] > [Basic Settings-04] > Group 007",
        "Deschidere EPB pentru service plăcuțe spate.",
        "Încărcător baterie conectat; contact ON, motor OFF; EPB OFF; confirmă MVB 012.2 = Open.",
        "1) Apasă pedala de frână și ciclizează EPB ON apoi OFF. 2) 53-Parking Brake. 3) Basic Settings 04 > Group 007 > Go. 4) ON/OFF/Next. 5) Așteaptă deschiderea. 6) După oprirea motoarelor așteaptă 30 secunde. 7) Done/Go Back și Close Controller. 8) Contact OFF înainte de intervenție.",
        "EPB este în poziția de service/open.",
        "Nu executa cu frânele demontate; așteptarea de 30 secunde este importantă pe unele module.",
        "Passat 3C EPB Gen II", 1, src_p3c_epb))

    rows.append((
        "Passat 3C EPB - Close Rear Parking Brake Group 006", "Service", "53",
        "[53-Parking Brake] > [Basic Settings-04] > Group 006",
        "Închidere EPB după montarea plăcuțelor.",
        "Plăcuțe și etriere montate corect; încărcător baterie; EPB OFF.",
        "1) 53 > Basic Settings 04 > Group 006. 2) ON/OFF/Next. 3) Așteaptă închiderea completă. 4) Așteaptă 30 secunde după oprirea motoarelor. 5) Done/Go Back. 6) Rulează Function Test Group 010.",
        "EPB închis fără DTC noi.",
        "Nu rula dacă etrierele/plăcuțele nu sunt montate complet.",
        "Passat 3C EPB Gen II", 1, src_p3c_epb))

    rows.append((
        "Passat 3C EPB - Function Test Group 010", "Calibrări", "53",
        "[53-Parking Brake] > [Basic Settings-04] > Group 010",
        "Test funcțional EPB după service/reparație.",
        "Încărcător baterie; EPB OFF; sistem complet montat.",
        "1) 53 > Basic Settings 04 > Group 010. 2) ON/OFF/Next. 3) Sistemul deschide/închide frânele de 3 ori. 4) După oprire așteaptă 30 secunde. 5) Done/Go Back. 6) Șterge DTC și verifică din nou.",
        "Ciclul se termină fără DTC persistente.",
        "Nu face Function Test cu frânele demontate.",
        "Passat 3C EPB Gen II", 1, src_p3c_epb))

    rows.append((
        "Passat 3C - G85 Group 060 exact", "Calibrări", "03",
        "[03-Brake Electronics] > Security Access 40168 > Basic Settings Group 060",
        "Calibrare G85 pe Passat 3C.",
        "Motor pornit; scurtă deplasare <20 km/h cu viraj dreapta/stânga; roți drepte; tensiune >=12 V.",
        "1) 03-Brake Electronics. 2) Security Access 16 > 40168 > Do It. 3) Basic Settings 04 > Group 060 > Go. 4) ON/OFF/Next. 5) Așteaptă field 2 = OK. 6) Done. 7) Measuring Blocks 08 > Group 004 și verifică unghiul cu volanul drept.",
        "Group 060 = OK și G85 aproape de 0°.",
        "Ține volanul drept și nu opri motorul pe durata procedurii.",
        "Passat 3C", 1, src_p3c_abs))

    rows.append((
        "Golf 5K - Reset Oil Service ESI exact", "Resetări", "17",
        "[17-Instruments] > [Adaptation-10] > ESI: Resetting ESI > Reset",
        "Resetare Oil Change Service Reminder.",
        "Service efectuat; cluster UDS compatibil.",
        "1) 17-Instruments. 2) Adaptation 10. 3) Alege ESI: Resetting ESI. 4) Selectează Reset. 5) Do It!. 6) Ciclizează contactul dacă avertizarea nu dispare imediat.",
        "Avertizarea oil service este resetată.",
        "Nu modifica intervalele de service fără să cunoști schema fixed/flexible și PR-code-urile vehiculului.",
        "Golf 5K / cluster compatibil", 1, src_g5k_cluster))

    rows.append((
        "Golf 5K - Reset Distance/Time Inspection exact", "Resetări", "17",
        "[17-Instruments] > [Adaptation-10] > FIX: Distance covered since last mileage-dependent inspection / FIX: Time since last time-dependent inspection",
        "Resetare separată pentru inspecția bazată pe distanță și timp.",
        "Vehicul cu canalele FIX disponibile.",
        "1) 17 > Adaptation 10. 2) FIX: Distance covered since last mileage-dependent inspection > New Value 0 > Do It. 3) FIX: Time since last time-dependent inspection > New Value 0 > Do It. 4) Ciclizează contactul.",
        "Ambele contoare sunt resetate la 0.",
        "Canalele nu există pe toate clusterele; nu forța valori pe clustere fără aceste canale.",
        "Golf 5K / cluster compatibil", 1, src_g5k_cluster))

    ids = {r[0]: _proc(con, r) for r in rows}

    pq35_sql = "platform='PQ35' OR chassis IN ('1K/5M','1Z','8P/FM','1P')"
    for title in [
        "PQ35 MK60 - G85 Steering Angle exact",
        "PQ35 MK60 - G200 Lateral Acceleration exact",
        "PQ35 MK60 - G201 Brake Pressure Sensor exact",
        "PQ35 MK60 - G251 Longitudinal Acceleration exact",
        "PQ35 MK60 - TPMS ABS reset Group 042",
        "MK60EC1 - Hydraulic Intake Valves Group 025",
    ]:
        _map(con, ids[title], pq35_sql)

    for title in [
        "Passat 3C EPB - Open Rear Parking Brake Group 007",
        "Passat 3C EPB - Close Rear Parking Brake Group 006",
        "Passat 3C EPB - Function Test Group 010",
        "Passat 3C - G85 Group 060 exact",
    ]:
        _map(con, ids[title], "name LIKE 'B6 3C%' OR chassis='3C/AN'")

    for title in ["Golf 5K - Reset Oil Service ESI exact", "Golf 5K - Reset Distance/Time Inspection exact"]:
        _map(con, ids[title], "name LIKE 'VI 5K%' OR chassis='5K/52/AJ'")

    con.commit()
