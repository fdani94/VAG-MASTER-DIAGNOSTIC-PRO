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


def _proc(con, title, category, module, path, purpose, prereq, steps, success, warnings, rule, verified, source_id):
    r = con.execute("SELECT id FROM procedure_library WHERE title=?", (title,)).fetchone()
    if r:
        return r[0]
    cur = con.execute("""INSERT INTO procedure_library(
        title,category,module_address,vcds_path,purpose,prerequisites,steps,
        success_criteria,warnings,applicability_rule,verified,source_id)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
        (title,category,module,path,purpose,prereq,steps,success,warnings,rule,verified,source_id))
    return cur.lastrowid


def _map(con, pid, where_sql="1=1", args=(), applicability="Condițional", notes="Confirmă Auto-Scan, part number, software și echiparea înainte de aplicare."):
    for r in con.execute("SELECT id FROM generations WHERE " + where_sql, args):
        con.execute("INSERT OR IGNORE INTO vehicle_procedures(generation_id,procedure_id,applicability,notes) VALUES(?,?,?,?)",
                    (r[0], pid, applicability, notes))


def install(con):
    src_batt = _source(con, "Battery Replacement", "https://wiki.ross-tech.com/wiki/index.php/Battery_Replacement")
    src_tba = _source(con, "Throttle Body Alignment", "https://wiki.ross-tech.com/wiki/index.php/Throttle_Body_Alignment_%28TBA%29")
    src_r8_abs = _source(con, "Audi R8 42 Brake Electronics", "https://wiki.ross-tech.com/wiki/index.php/Audi_R8_%2842%29_Brake_Electronics")
    src_a6_abs = _source(con, "Audi A6 4F Brake Electronics", "https://wiki.ross-tech.com/wiki/index.php/Audi_A6_%284F%29_Brake_Electronics")
    src_a4_abs = _source(con, "Audi A4 8E Brake Electronics Bosch 8.0", "https://wiki.ross-tech.com/wiki/index.php/Audi_A4_%288E%29_Brake_Electronics_%28Bosch_8.0%29")
    src_golf_mk20 = _source(con, "VW Golf 1J Brake Electronics MK20", "https://wiki.ross-tech.com/wiki/index.php/VW_Golf_%281J%29_Brake_Electronics_%28MK20%29")
    src_mqb_abs = _source(con, "MK60EC1 Brake Electronics", "https://wiki.ross-tech.com/wiki/index.php/VW_Eos_%281F%29_Brake_Electronics_%28MK60EC1%29")
    src_touareg_g85 = _source(con, "Touareg 7P Steering Wheel Electronics", "https://wiki.ross-tech.com/wiki/index.php/VW_Touareg_%287P%29_Steering_Wheel_Electronics")
    src_a6_4g_g85 = _source(con, "Audi A6 4G Steering Wheel Electronics", "https://wiki.ross-tech.com/wiki/index.php/Audi_A6_%284G%29_Steering_Wheel_Electronics")
    src_xenon = _source(con, "Xenon Basic Settings BCM1 J519", "https://wiki.ross-tech.com/wiki/index.php/Xenon_Basic_Settings_in_BCM1/09-Cent._Elect._%28J519%29_controller")
    src_bcm1 = _source(con, "MLB BCM1 J519", "https://wiki.ross-tech.com/wiki/index.php/MLB_based_Cent._Elect._%28J519%29_BCM1")

    # Battery replacement - exact older CAN Gateway long adaptation path
    pid = _proc(con,
        "Înlocuire baterie - 19 CAN Gateway Long Adaptation Channel 004",
        "Înlocuire / Calibrare piese și module", "19",
        "[19-CAN Gateway] > [Long Adaptation-0A] > Channel 004",
        "Înregistrează bateria nouă pe sisteme BEM unde bateria este gestionată prin CAN Gateway.",
        "Bateria nouă instalată; contact ON; motor OFF; ai part number, vendor și serial valide sau echivalente conforme.",
        "1) Select > 19-CAN Gateway. 2) Long Adaptation-0A. 3) Channel 004 > Read. 4) Add to Log pentru valoarea veche. 5) Introdu noua valoare în format 11 caractere part number + spațiu + 3 caractere vendor + spațiu + 10 caractere serial (26 caractere total cu spații). 6) Test. 7) Save. 8) Done, Go Back. 9) Close Controller. 10) Verifică Measuring Blocks 017/018/019/020 unde sunt suportate.",
        "Valoarea nouă este acceptată și informațiile bateriei sunt coerente în blocurile de măsură suportate.",
        "Nu inventa date dacă bateria aftermarket nu furnizează informațiile necesare. Salvează întotdeauna valoarea originală.",
        "Sisteme BEM cu 19-CAN Gateway CAN și Long Adaptation Channel 004", 1, src_batt)
    _map(con,pid,"year_from>=2007 AND year_from<=2014",applicability="Exact/Condițional")

    # Generic UDS battery adaptation path
    pid = _proc(con,
        "Înlocuire baterie - Gateway UDS / Battery adaptation",
        "Înlocuire / Calibrare piese și module", "19",
        "[19-CAN Gateway] > [Adaptation-10] > Battery adaptation/replacement channels",
        "Înregistrează bateria nouă pe vehicule UDS unde J533/J367 gestionează bateria.",
        "Bateria nouă instalată; contact ON; motor OFF; salvează valorile originale.",
        "1) 19-CAN Gateway > Adaptation-10. 2) Caută canalele battery adaptation / battery replacement disponibile. 3) Notează valorile vechi. 4) Introdu capacitatea, tehnologia, producătorul și/sau serialul exact în câmpurile oferite de controller. 5) Save. 6) Verifică DTC și valorile de management energetic.",
        "Noile valori sunt salvate și nu există DTC de adaptare baterie.",
        "Denumirile câmpurilor diferă după software; folosește exact opțiunile afișate de controller.",
        "Gateway UDS cu management baterie", 1, src_batt)
    _map(con,pid,"year_from>=2012",applicability="Condițional")

    # TBA
    pid = _proc(con,
        "După înlocuire/curățare clapetă - Throttle Body Alignment UDS",
        "Înlocuire / Calibrare piese și module", "01",
        "[01-Engine] > [Basic Settings-04] > IDE00754 Checking throttle valve adaptation / Throttle Valve Adaptation",
        "Reînvață pozițiile clapetei după curățare, demontare/reinstalare, înlocuire, deconectare baterie sau ECU.",
        "Lichid răcire cald; contact ON; motor OFF; nu atinge accelerația; fără defecte care împiedică adaptarea.",
        "1) Select > 01-Engine. 2) Basic Settings-04. 3) Alege IDE00754-Checking throttle valve adaptation; dacă nu există, alege varianta denumită Throttle Valve Adaptation. 4) Go. 5) Așteaptă Finished Correctly. 6) Stop. 7) Lasă aproximativ 30 secunde în Basic Settings. 8) Done, Go Back.",
        "Finished Correctly / adaptarea este acceptată.",
        "Motorul trebuie să fie oprit. Nu atinge pedala de accelerație.",
        "Motoare benzină UDS compatibile", 1, src_tba)
    _map(con,pid,"year_from>=2008",applicability="Condițional")

    # ABS replacement workflow
    pid = _proc(con,
        "După înlocuire modul ABS - copiere coding original + G85",
        "Înlocuire / Calibrare piese și module", "03",
        "[03-ABS Brakes] > [Coding-07] > coding original > apoi [Basic Settings-04] G85",
        "Finalizează înlocuirea unui modul ABS pe familii unde Ross-Tech recomandă reutilizarea coding-ului original și calibrarea G85.",
        "Ai Auto-Scan/coding original salvat înainte de înlocuire; piesa este compatibilă; tensiune stabilă.",
        "1) 03-ABS Brakes. 2) Coding-07 și introdu exact coding-ul original din vechiul modul/Auto-Scan. 3) Acceptă coding-ul. 4) Execută calibrarea G85 conform procedurii specifice controllerului. 5) Fault Codes-02 și șterge erorile după calibrare. 6) Confirmă că martorii ABS/ESP sunt stinși.",
        "Coding acceptat, G85 calibrat, fără DTC persistente și martorii ABS/ESP stinși.",
        "Nu calcula la întâmplare coding-ul dacă nu ai datele originale. Unele module necesită SVM/online sau Security Access specific.",
        "Bosch/MK20/MK60/MK60EC1 și alte familii documentate", 1, src_r8_abs)
    _map(con,pid,"platform IN ('PQ34','PQ35','PQ46','PL45','PL46','PL47')",applicability="Condițional")

    # G85 exact common Bosch 8.0 / Touareg/A6 type
    pid = _proc(con,
        "G85 după înlocuire - Security 40168 + Basic Settings Group 001",
        "Înlocuire / Calibrare piese și module", "03/16",
        "[03-ABS] sau [16-Steering Wheel] > [Security Access-16] 40168 > [Basic Settings-04] Group 001",
        "Calibrează senzorul de unghi volan G85 după înlocuire senzor, slip ring, coloană, ABS sau lucrări relevante pe direcție.",
        "Motor pornit unde procedura o cere; volan aproape drept; confirmă address-ul corect pentru chassis; tensiune stabilă.",
        "1) Intră în controllerul specific chassis-ului (03 sau 16). 2) Mișcă volanul cel puțin 30° și revino drept. 3) Security Access-16 > 40168 > Do It. 4) Basic Settings-04 > Group 001 > Go. 5) ON/OFF/Next dacă este disponibil. 6) Confirmă Field 3 = OK. 7) Verifică Measuring Blocks pentru unghiul G85 conform chassis-ului. 8) Fault Codes-02 și verifică finalizarea.",
        "Field 3 = OK și unghiul G85 este aproape 0° în toleranța specifică chassis-ului.",
        "Adresa, grupul de măsură și toleranța diferă după model. Folosește procedura specifică mașinii selectate.",
        "Controller documentat cu 40168/Group 001", 1, src_touareg_g85)
    _map(con,pid,"year_from>=2001 AND year_from<=2016",applicability="Condițional")

    # Steering rack replacement / end stops
    pid = _proc(con,
        "După înlocuire casetă / modul servodirecție - G85 + end stops",
        "Înlocuire / Calibrare piese și module", "44/16",
        "G85 Basic Setting > apoi adaptare steering end stops prin lock-to-lock",
        "Finalizează adaptarea după înlocuirea casetei electrice/J500, G85 sau slip ring pe sisteme unde apare C10AC/03803.",
        "Piesa compatibilă și codificată; G85 calibrat sau pregătit pentru calibrare; motor pornit.",
        "1) Efectuează procedura G85 specifică chassis-ului. 2) Dacă apare Steering End Stops Not Learned/C10AC, cu motorul pornit virează complet dreapta și menține 5-10 secunde până la confirmarea sonoră dacă sistemul o oferă. 3) Virează complet stânga și menține 5-10 secunde. 4) Centrează roțile și așteaptă 5-10 secunde. 5) Re-scanează DTC înainte de test drive.",
        "Martorii steering/traction se sting și DTC de end stops/basic setting nu revine.",
        "Unele casete necesită characteristic curve/parametrizare sau proceduri online; VCDS nu poate înlocui toate funcțiile ODIS/SVM.",
        "EPS electric cu G85/end-stop learning", 1, src_a6_4g_g85)
    _map(con,pid,"year_from>=2005",applicability="Condițional")

    # Xenon headlight adjustment
    pid = _proc(con,
        "După înlocuire far / senzor nivel / BCM1 - Basic Settings xenon Group 011",
        "Înlocuire / Calibrare piese și module", "09",
        "[09-Cent. Elect.] > [Basic Settings-04] > Group 011",
        "Inițializează reglajul de bază pentru faruri xenon pe BCM1/J519 compatibil după lucrări la faruri/senzori/nivelare.",
        "Vehicul pe suprafață plană; faruri și senzori de nivel complet montați și funcționali; switch faruri ON, nu Auto; BCM1 fără defecte relevante cu excepțiile admise de procedură.",
        "1) 09-Cent. Elect. 2) Basic Settings-04. 3) Group 011 > Go. 4) Verifică starea Reg. Position / Learned. 5) ON/OFF/Next pentru a activa modul Adjust. 6) Reglează mecanic farurile conform manualului de reparații și echipamentului de reglaj. 7) Finalizează Basic Setting conform stării afișate. 8) Verifică DTC.",
        "Basic Setting este memorat și sistemul de nivelare funcționează fără DTC persistente.",
        "Reglajul mecanic al fasciculului necesită procedura/echipamentul corect. Nu folosi ca substitut pentru reglaj optic profesional.",
        "MLB BCM1/J519 xenon compatibil", 1, src_xenon)
    _map(con,pid,"platform IN ('MLB','MLB Evo','PL71','PL72')",applicability="Condițional")

    # Component protection warning as a procedure card
    pid = _proc(con,
        "Înlocuire BCM1 / modul cu Component Protection - limită VCDS",
        "Înlocuire / Calibrare piese și module", "09",
        "Coding/Adaptation locală în VCDS; Component Protection necesită tool factory + online GeKo",
        "Explică pașii corecți după înlocuirea unui modul MLB protejat și ce nu poate face VCDS singur.",
        "Modul compatibil fizic/electric; coding original salvat dacă este posibil.",
        "1) Salvează Auto-Scan și coding/adaptation din modulul vechi dacă comunică. 2) Montează modulul corect. 3) Reaplică coding/adaptations locale numai dacă sunt documentate și acceptate. 4) Dacă apare Component Protection, finalizarea necesită Factory Tool cu conexiune online GeKo / procedura autorizată. 5) După eliminarea CP, re-verifică coding, adaptations, Basic Settings și DTC.",
        "Component Protection este eliminată prin procedură autorizată și modulul funcționează normal.",
        "VCDS singur nu poate învăța/dezactiva Component Protection pe modulele unde Ross-Tech indică GeKo online.",
        "MLB/vehicule cu Component Protection", 1, src_bcm1)
    _map(con,pid,"platform IN ('MLB','MLB Evo')",applicability="Exact/Limitare")

    con.commit()
