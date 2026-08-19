from datetime import datetime


def _source(con, title, url, notes=""):
    row = con.execute("SELECT id FROM sources WHERE url=?", (url,)).fetchone()
    if row:
        return row[0]
    cur = con.execute(
        "INSERT INTO sources(title,publisher,url,accessed,source_type,notes) VALUES(?,?,?,?,?,?)",
        (title, "Ross-Tech", url, datetime.now().date().isoformat(), "Oficial", notes),
    )
    return cur.lastrowid


def _insert_proc(con, row):
    title = row[0]
    exists = con.execute("SELECT id FROM procedure_library WHERE title=?", (title,)).fetchone()
    if exists:
        return exists[0]
    cur = con.execute(
        """INSERT INTO procedure_library(
        title,category,module_address,vcds_path,purpose,prerequisites,steps,
        success_criteria,warnings,applicability_rule,verified,source_id)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
        row,
    )
    return cur.lastrowid


def install(con):
    """Idempotent expansion for the VAG MASTER v5 database."""
    src_main = _source(con, "VCDS Function Index", "https://www.ross-tech.com/vcds/tour/main_screen.php", "Funcțiile de bază VCDS")
    src_mb = _source(con, "Measuring Blocks", "https://www.ross-tech.com/vcds/tour/m-blocks.php")
    src_adv = _source(con, "Advanced Measuring Values", "https://www.ross-tech.com/vcds/tour/adv-meas-blocks.php")
    src_out = _source(con, "Output Tests", "https://www.ross-tech.com/vcds/tour/out_test.php")
    src_bs = _source(con, "Basic Settings", "https://www.ross-tech.com/vcds/tour/b-settings.php")
    src_adapt = _source(con, "Adaptation", "https://www.ross-tech.com/vcds/tour/adaptation_screen.php")
    src_map = _source(con, "Controller Channels Map", "https://www.ross-tech.com/vcds/tour/controller-channels-map.php")
    src_tba = _source(con, "Throttle Body Alignment", "https://wiki.ross-tech.com/wiki/index.php/Throttle_Body_Alignment_(TBA)")
    src_epb = _source(con, "Electro-Mechanical Parking Brake", "https://wiki.ross-tech.com/wiki/index.php/Working_on_the_Electro-Mechanical_Parking_Brake_(EPB)")
    src_mk60 = _source(con, "VW Golf 1K Brake Electronics MK60", "https://wiki.ross-tech.com/wiki/index.php/VW_Golf_%281K%29_Brake_Electronics_%28MK60%29")
    src_mk60ec1 = _source(con, "VW Golf 1K Brake Electronics MK60EC1", "https://wiki.ross-tech.com/wiki/index.php/VW_Golf_%281K%29_Brake_Electronics_%28MK60EC1%29")
    src_02e = _source(con, "6-Speed DSG 02E", "https://wiki.ross-tech.com/wiki/index.php/6-Speed_Direct_Shift_Gearbox_%28DSG/02E%29")
    src_0am = _source(con, "7-Speed DSG 0AM", "https://wiki.ross-tech.com/wiki/index.php/7-Speed_Direct_Shift_Gearbox_%28DSG/0AM%29")
    src_0b5 = _source(con, "7-Speed S-Tronic 0B5", "https://wiki.ross-tech.com/wiki/index.php/7-Speed_S-Tronic_Direct-Shift_Gearbox_%28DSG/0B5%29")

    generic = [
        ("Identificare controller / part number", "Diagnostic", "", "[Select] > [modul]", "Identifică part number, componenta și protocolul modulului.", "Contact ON; comunicație stabilă.", "Intră în modul și notează VAG Number, Component, Soft. Coding și protocolul. Compară cu Auto-Scan-ul salvat.", "Modul identificat fără ambiguitate.", "Nu aplica proceduri după numele modelului fără confirmarea controllerului real.", "General", 1, src_main),
        ("Auto-Scan înainte de intervenție", "Diagnostic", "", "Auto-Scan", "Creează fotografia inițială a mașinii.", "Interfață conectată; contact ON.", "Rulează Auto-Scan complet și salvează fișierul înainte de ștergeri, coding sau adaptări.", "Raport salvat.", "Este baza pentru rollback și comparație.", "General", 1, src_main),
        ("Auto-Scan după intervenție", "Diagnostic", "", "Auto-Scan", "Verifică rezultatul după reparație/codare.", "Intervenția terminată.", "Rulează din nou Auto-Scan și compară DTC/coding cu raportul inițial.", "Nu apar DTC noi și funcția este corectă.", "Un singur test local nu înlocuiește verificarea completă.", "General", 1, src_main),
        ("Citire Fault Codes", "Diagnostic", "", "[Select] > [modul] > [Fault Codes - 02]", "Citește DTC-ul modulului selectat.", "Contact ON.", "Notează cod, text, status și freeze-frame atunci când este disponibil.", "DTC documentat.", "Interpretează codul în contextul modulului și al simptomelor.", "General", 1, src_main),
        ("Clear Codes după reparație", "Diagnostic", "", "[Select] > [modul] > [Fault Codes - 02] > [Clear Codes - 05]", "Șterge DTC după remedierea cauzei.", "Raport salvat; cauza reparată.", "Șterge DTC, ciclu contact dacă procedura cere, apoi rescanează.", "DTC nu reapare.", "Ștergerea nu repară defectul.", "General", 1, src_main),
        ("Measuring Blocks - citire live", "Live Data", "", "[Select] > [modul] > [Meas. Blocks - 08]", "Citește valori live pe module non-UDS.", "Controller compatibil.", "Selectează grupul documentat și compară valorile actuale cu cele cerute/nominale.", "Valori coerente cu condițiile testului.", "Nu folosi Basic Settings ca substitut pentru Measuring Blocks.", "Condițional", 1, src_mb),
        ("Advanced Measuring Values", "Live Data", "", "[Select] > [modul] > [Adv. Meas. Values]", "Citește parametri denumiți pe module compatibile.", "Controller compatibil.", "Selectează doar parametrii relevanți și urmărește relația specified/actual.", "Date stabile și interpretabile.", "Prea mulți parametri pot reduce rata de eșantionare.", "Condițional", 1, src_adv),
        ("Data Logging CSV", "Live Data", "", "Valori live > [Log]", "Înregistrează valori pentru analiză.", "Parametri selectați; test sigur.", "Pornește logul, execută testul, oprește și păstrează CSV împreună cu Auto-Scan-ul.", "Fișier CSV creat.", "Nu opera laptopul în timpul condusului.", "General", 1, src_mb),
        ("Comparație specified vs actual", "Live Data", "01", "[01-Engine] > valori live", "Compară cererea ECU cu răspunsul real.", "Motor la condiția de test documentată.", "Selectează perechi relevante: boost, air mass, rail pressure etc. și loghează diferența în sarcină.", "Abaterea poate fi corelată cu simptomul.", "Canalele exacte diferă după ECU/protocol.", "Condițional", 1, src_adv),
        ("Output Tests - flux sigur", "Test actuatori", "", "[Select] > [modul] > [Output Tests - 03]", "Testează ieșiri comandate de controller.", "Vehicul securizat; componenta poate fi activată în siguranță.", "Pornește Output Tests și urmează secvența impusă de modul; observă reacția actuatorului.", "Actuatorul răspunde conform așteptărilor.", "Ordinea și testele sunt stabilite de controller; unele rulează o singură dată pe sesiune.", "Condițional", 1, src_out),
        ("Basic Settings - flux sigur", "Basic Settings", "", "[Select] > [modul] > [Basic Settings - 04]", "Rulează o calibrare documentată.", "Condițiile procedurii specifice îndeplinite.", "Selectează exclusiv grupul/funcția documentată și urmărește statusul până la finalizare.", "ADP OK / Finished Correctly / criteriul documentat.", "Basic Settings poate acționa componente; nu experimenta cu grupuri necunoscute.", "Condițional", 1, src_bs),
        ("Adaptation - backup valoare", "Adaptation", "", "[Select] > [modul] > [Adaptation - 10]", "Salvează valoarea înainte de modificare.", "Canal identificat corect.", "Notează Stored Value, canalul/denumirea și captura/Auto-Scan înainte de New Value.", "Valoarea originală este documentată.", "Fără backup, revenirea poate deveni dificilă.", "General", 1, src_adapt),
        ("Adaptation - modificare controlată", "Adaptation", "", "[Select] > [modul] > [Adaptation - 10]", "Modifică o singură adaptare.", "Valoarea originală salvată.", "Alege canalul documentat, introdu New Value, folosește Test când este disponibil, apoi Save și verifică DTC.", "Valoare acceptată și funcție verificată.", "Denumirile și intervalele diferă după software.", "Condițional", 1, src_adapt),
        ("Coding - backup original", "Coding", "", "[Select] > [modul] > [Coding - 07]", "Păstrează coding-ul inițial.", "Auto-Scan disponibil.", "Copiază Soft Coding/Long Coding înainte de orice schimbare.", "Coding original salvat.", "Nu te baza doar pe memorie.", "General", 1, src_main),
        ("Coding - modificare unică", "Coding", "", "[Select] > [modul] > [Coding - 07]", "Aplică o schimbare controlată.", "Coding original salvat; documentație pentru modul.", "Modifică o singură opțiune, Do It, rescanează și testează funcția.", "Coding acceptat; fără DTC noi.", "Nu copia coding complet de pe altă mașină.", "Condițional", 1, src_main),
        ("Long Coding Helper", "Coding", "", "[Coding - 07] > Long Coding Helper", "Editează byte/bit pe module compatibile.", "Long Coding disponibil.", "Schimbă doar bitul/opțiunea documentată, transferă coding-ul și verifică rezultatul.", "Coding acceptat.", "Etichetele pot diferi după part number și software.", "Condițional", 1, src_main),
        ("Security Access - procedură controlată", "Security Access", "", "[Select] > [modul] > [Security Access - 16]", "Deblochează o funcție protejată.", "Cod specific controllerului confirmat din documentație/VCDS.", "Introdu doar codul documentat și continuă imediat procedura pentru care a fost cerut.", "Security Access accepted.", "Nu ghici coduri; pot exista timpi de blocare.", "Condițional", 1, src_main),
        ("Controller Channels Map", "Documentare", "", "Applications > Controller Channels Map", "Inventariază canale și valori suportate.", "Controller comunicant; tensiune stabilă.", "Generează map pentru controller și arhivează fișierul cu Auto-Scan-ul.", "Map creat.", "Poate dura pe module mari.", "General", 1, src_map),
        ("Gateway Installation List - verificare", "Rețea CAN", "19", "[19-CAN Gateway] > Installation List", "Compară modulele declarate cu cele reale.", "Gateway compatibil.", "Verifică modulele bifate și corelează cu Auto-Scan și echiparea reală.", "Lista corespunde echipării.", "Nu bifa module inexistente.", "Condițional", 1, src_main),
        ("Test tensiune înainte de coding", "Siguranță", "", "Auto-Scan / condiții atelier", "Previne întreruperi la coding/adaptation.", "Sursă stabilizată disponibilă când operația este lungă.", "Verifică tensiunea și menține alimentarea stabilă înainte de operații sensibile.", "Tensiune stabilă pe durata intervenției.", "Căderea tensiunii poate întrerupe comunicația.", "General", 1, src_main),
        ("SRI / reset service - verificare", "Service", "17", "Applications > SRI Reset", "Resetează service când este suportat.", "Revizia efectuată; tip service cunoscut.", "Citește valorile SRI, aplică operația potrivită și verifică afișajul clusterului.", "Interval afișat corect.", "Fixed și flexible service pot folosi valori diferite.", "Condițional", 1, src_main),
        ("Readiness - verificare emisii", "Emisii", "01", "[01-Engine] > [Readiness - 15]", "Verifică monitoarele OBD.", "ECU compatibil.", "Citește readiness și documentează monitoarele incomplete.", "Starea monitoarelor este cunoscută.", "Readiness resetat după ștergere DTC/deconectare baterie.", "Condițional", 1, src_main),
        ("DPF - verificare înainte de regenerare", "DPF", "01", "[01-Engine] > valori live", "Evaluează dacă o regenerare este justificată și sigură.", "Motor fără defecțiuni critice; nivel ulei corect.", "Verifică soot load, presiune diferențială, temperaturi evacuare și cauzele regenerărilor eșuate.", "Cauza și gradul de încărcare sunt înțelese.", "Nu porni regenerare forțată doar pentru că există un DTC DPF.", "Condițional", 1, src_adv),
        ("EGR - diagnostic prin valori live", "Motor", "01", "[01-Engine] > valori live", "Verifică răspunsul EGR.", "Motor la regimul specific testului.", "Compară comanda EGR cu masa de aer/poziția raportată și verifică vacuum/cablaj unde este cazul.", "Comanda și răspunsul pot fi corelate.", "Canalele exacte diferă după ECU.", "Condițional", 1, src_adv),
        ("Turbo underboost - diagnostic log", "Motor", "01", "[01-Engine] > valori live > Log", "Diagnostichează presiunea sub cerere.", "Traseu verificabil; test rutier sigur.", "Loghează boost specified/actual și comanda actuatorului; verifică pierderi, vacuum și actuator.", "Se identifică zona de abatere.", "Nu condamna turbina doar pe baza unui singur cod.", "Condițional", 1, src_adv),
        ("MAF - verificare specified/actual", "Motor", "01", "[01-Engine] > valori live", "Evaluează debitmetrul în context.", "Admisie și filtru verificabile.", "Compară masa de aer cerută/reală în condiții documentate și corelează cu EGR/boost.", "Valorile pot fi interpretate în ansamblu.", "Nu înlocui MAF fără verificarea falsului aer/EGR.", "Condițional", 1, src_adv),
        ("Injector balance / smooth running", "Motor", "01", "[01-Engine] > valori live", "Compară corecțiile cilindrilor pe ECU compatibile.", "Motor la temperatură stabilă.", "Selectează valorile de smooth running/injector deviation disponibile și compară cilindrii.", "Abaterile sunt documentate.", "Limitele sunt specifice ECU/motorului.", "Condițional", 1, src_adv),
        ("Climatizare - Output Tests actuatori", "Climatizare", "08", "[08-HVAC] > [Output Tests - 03]", "Testează clapete/ventilatoare unde sunt expuse de modul.", "Sistem securizat.", "Rulează Output Tests și observă fiecare actuator oferit de controller.", "Actuatorul răspunde.", "Lista diferă după HVAC și software.", "Condițional", 1, src_out),
        ("Faruri - verificare modul 55", "Iluminare", "55", "[55-Headlight Range]", "Verifică DTC și valorile sistemului de nivelare.", "Vehicul pe suprafață plană.", "Citește DTC și valorile senzorilor înainte de basic setting/calibrare specifică.", "Defectul este localizat înainte de calibrare.", "Nu face basic setting pentru a masca un senzor defect.", "Condițional", 1, src_main),
        ("Baterie - identificare modul management", "Baterie", "61", "[61-Battery Regulation] / [19-CAN Gateway]", "Identifică unde se face adaptarea bateriei pe vehiculul real.", "Auto-Scan salvat.", "Verifică dacă mașina are 61-Battery Regulation sau funcția este integrată în Gateway/alt modul, apoi folosește procedura specifică.", "Modulul corect este identificat.", "Nu presupune aceeași cale pentru toate generațiile.", "Condițional", 1, src_main),
        ("ABS - citire senzori viteză roată", "Frâne", "03", "[03-ABS] > valori live", "Compară vitezele celor patru roți.", "Vehicul ridicat/test rutier executat în siguranță.", "Monitorizează simultan wheel speeds și caută o abatere/dropout.", "Semnalul problematic poate fi identificat.", "Respectă siguranța la testul rutier.", "Condițional", 1, src_adv),
    ]

    generic_ids = [_insert_proc(con, r) for r in generic]

    exact = [
        ("TBA DBW non-UDS - Group 060", "Basic Settings", "01", "[01-Engine] > [Basic Settings - 04] > Group 060", "Aliniere clapetă accelerație pe ECU DBW compatibile.", "Contact ON; motor OPRIT; accelerația neatinsă; condițiile ECU îndeplinite.", "Intră în Group 060 și Go. Lasă procedura aproximativ 30 secunde; urmărește ADP RUN/ADP OK.", "ADP OK / adaptare finalizată.", "Nu este universală; UDS folosește funcții denumite.", "Condițional - numai ECU compatibil", 1, src_tba),
        ("TBA UDS - throttle valve adaptation", "Basic Settings", "01", "[01-Engine] > [Basic Settings - 04] > IDE00754 / variantă Throttle Valve Adaptation", "Aliniere clapetă pe ECU UDS compatibile.", "Motor oprit; contact ON; lichid de răcire cald conform procedurii; accelerația neatinsă.", "Selectează Checking throttle valve adaptation sau varianta disponibilă, Go și așteaptă Finished Correctly, apoi Stop.", "Finished Correctly.", "Denumirea poate varia după ECU.", "Condițional - UDS", 1, src_tba),
        ("ABS MK60 - G85 Steering Angle Basic Setting", "Frâne", "03", "[03-ABS] > MB 004 > Security Access 40168 > Basic Settings 060", "Calibrează G85 pe MK60 compatibil.", "Motor pornit; o rotație dreapta/stânga; deplasare scurtă drept sub 20 km/h; volan drept; tensiune minim 12.0 V.", "În MB Group 004 verifică G85 între -1.5 și +1.5°. Security Access/Coding-II 40168. Basic Settings Group 060; după succes field 2 trebuie OK.", "Field 2 = OK.", "Confirmă că ABS este MK60; alte variante au proceduri diferite.", "Exact - MK60", 1, src_mk60),
        ("ABS MK60 - Steering Limit Stop", "Frâne", "03", "[03-ABS] > Security Access 40168 > Basic Settings 066", "Adaptează steering limit stop după G85.", "G85 basic setting terminat.", "Security Access 40168, Basic Settings Group 066, activează Basic Setting și așteaptă OK.", "Field 2 = OK.", "Se execută conform procedurii MK60.", "Exact - MK60", 1, src_mk60),
        ("ABS MK60 - G251 Longitudinal Acceleration", "Frâne", "03", "[03-ABS] > MB 006 > Security Access 40168 > Basic Settings 069", "Calibrează G251 când este echipat.", "Tensiune minim 12 V; G251 prezent (de ex. AWD/Hill Hold conform echipării).", "Verifică MB Group 006 field 1 aproximativ -1.5...+1.5 m/s²; Security Access 40168; Basic Settings Group 069.", "Basic setting finalizat.", "Se aplică numai vehiculelor cu G251 prezent.", "Exact - MK60 condițional", 1, src_mk60),
        ("DSG 02E - precondiții Basic Settings", "Transmisie", "02", "[02-Transmission] > [Basic Settings - 04]", "Pregătește DSG 02E pentru adaptări.", "Ulei 30-100°C; nivel corect; selector P; contact ON; motor la ralanti >=1 min; frâna apăsată continuu; accelerația neatinsă; cruise OFF.", "Confirmă toate condițiile înainte de a începe secvența Ross-Tech.", "Toate precondițiile îndeplinite.", "Nu începe secvența dacă temperatura/nivelul sunt incorecte.", "Exact - numai DSG 02E", 1, src_02e),
        ("DSG 02E - Toleranțe engaged calibration 061", "Transmisie", "02", "[02-Transmission] > [Basic Settings - 04] > Group 061", "Calibrare toleranțe DSG 02E.", "Precondițiile DSG 02E îndeplinite.", "Rulează Group 061 și așteaptă până când valorile nu se mai mișcă și Basic Settings trece ON.", "Basic Settings = ON; valorile s-au stabilizat.", "Zgomotele mecanice în timpul calibrării pot fi normale.", "Exact - numai DSG 02E", 1, src_02e),
        ("DSG 02E - Synch Point 060", "Transmisie", "02", "[02-Transmission] > [Basic Settings - 04] > Group 060", "Măsurare punct sincronizare DSG 02E.", "Precondițiile DSG 02E îndeplinite.", "Rulează Group 060 și așteaptă finalizarea/stabilizarea valorilor.", "Basic Settings = ON.", "Nu întrerupe prematur secvența.", "Exact - numai DSG 02E", 1, src_02e),
        ("DSG 02E - Clutch Adaptation 062/067", "Transmisie", "02", "[02-Transmission] > [Basic Settings - 04] > Group 062 sau 067", "Adaptare ambreiaje DSG 02E.", "Precondițiile DSG 02E; versiunea software TCM identificată.", "Pentru software <0800 Ross-Tech indică Group 062; pentru >=0800 Group 067. Activează Basic Setting dacă este necesar și așteaptă finalizarea.", "Basic Settings finalizat.", "Alege grupul după versiunea software; nu le trata ca interschimbabile.", "Exact - numai DSG 02E", 1, src_02e),
        ("DSG 02E - Reset clutch safety 068", "Transmisie", "02", "[02-Transmission] > [Basic Settings - 04] > Group 068", "Resetează valorile clutch safety function.", "Precondițiile DSG 02E.", "Rulează Group 068 și activează Basic Setting conform VCDS.", "Basic Setting finalizat.", "Parte din secvența documentată; urmează ordinea Ross-Tech.", "Exact - numai DSG 02E", 1, src_02e),
        ("DSG 02E - Reset pressure adaptation 065", "Transmisie", "02", "[02-Transmission] > [Basic Settings - 04] > Group 065", "Resetează pressure adaptation.", "Precondițiile DSG 02E.", "Rulează Group 065 și activează Basic Setting.", "Basic Setting finalizat.", "Urmează secvența completă și test drive-ul definit.", "Exact - numai DSG 02E", 1, src_02e),
        ("DSG 02E - Defined Test Drive", "Transmisie", "02", "După Basic Settings > test rutier definit", "Finalizează adaptările după Basic Settings.", "Ulei 30-100°C; fără cruise control.", "În Tiptronic urcă până în treapta 6; menține 3 sau 5 aproximativ 5 min și 4 sau 6 aproximativ 5 min, în fereastra 1200-3500 rpm. Evaluează creep/start-off și verifică scurgeri.", "Schimbări și puncte de plecare evaluate; fără DTC relevante.", "Execută numai în condiții de trafic sigure.", "Exact - numai DSG 02E", 1, src_02e),
        ("DSG 0AM - Basic Settings Group 060", "Transmisie", "02", "[02-Transmission] > [Basic Settings - 04] > Group 060", "Basic Settings pentru DSG 7 trepte 0AM.", "Fără DTC relevante; ulei 30-60°C; selector P; contact ON; motor OFF inițial; parking brake aplicată; frâna apăsată; accelerația neatinsă.", "Rulează Group 060; ON/OFF/Next poate fi necesar. Așteaptă afișarea 4 | 0 | 0, apoi pornește motorul imediat și lasă-l la ralanti conform procedurii.", "Secvența ajunge la starea documentată.", "Numai TCM 0AM confirmat.", "Exact - numai DSG 0AM", 1, src_0am),
        ("S-Tronic 0B5 - precondiții Basic Settings", "Transmisie", "02", "[02-Auto Trans] > [Basic Settings - 04]", "Pregătește 0B5 pentru Basic Settings.", "Nivel ulei corect; temperatură 40-100°C; TCM fără erori; contact ON; motor OFF; selector P.", "Verifică precondițiile și execută cele trei operații de Basic Settings în ordinea documentată de Ross-Tech.", "Toate operațiile se finalizează.", "Numai 0B5 confirmat; Component Protection poate apărea după înlocuire.", "Exact - numai 0B5", 1, src_0b5),
        ("EPB - intrare service frâne spate", "Frâne", "53", "[53-Parking Brake] sau [03-ABS pe MQB] > Basic Settings", "Pregătește etrierele EPB pentru schimb plăcuțe.", "EPB funcțional; tensiune stabilă; procedura chassis-ului identificată.", "Folosește funcția Open Rear Parking Brake specifică platformei, execută lucrarea mecanică, apoi Close Rear Parking Brake și Function Test.", "EPB funcționează fără DTC.", "Pe MQB funcția este de regulă în 03-ABS, nu în 53.", "Condițional - EPB", 1, src_epb),
    ]

    exact_ids = [_insert_proc(con, r) for r in exact]

    # Every generation gets a professional baseline >30 procedures.
    generations = [r[0] for r in con.execute("SELECT id FROM generations")]
    for gid in generations:
        for pid in generic_ids:
            con.execute(
                "INSERT OR IGNORE INTO vehicle_procedures(generation_id,procedure_id,applicability,notes) VALUES(?,?,?,?)",
                (gid, pid, "General/Condițional", "Confirmă modulul, protocolul și echiparea prin Auto-Scan."),
            )

    # Exact/conditional specialist procedures are mapped by platform/chassis families, while still requiring controller confirmation.
    specialist_rules = [
        ("TBA DBW non-UDS - Group 060", "1=1"),
        ("TBA UDS - throttle valve adaptation", "year_to>=2008"),
        ("EPB - intrare service frâne spate", "platform IN ('PQ46','MQB','MLB','PL47','PL71','PL72')"),
        ("DSG 02E - precondiții Basic Settings", "platform IN ('PQ35','PQ46')"),
        ("DSG 02E - Toleranțe engaged calibration 061", "platform IN ('PQ35','PQ46')"),
        ("DSG 02E - Synch Point 060", "platform IN ('PQ35','PQ46')"),
        ("DSG 02E - Clutch Adaptation 062/067", "platform IN ('PQ35','PQ46')"),
        ("DSG 02E - Reset clutch safety 068", "platform IN ('PQ35','PQ46')"),
        ("DSG 02E - Reset pressure adaptation 065", "platform IN ('PQ35','PQ46')"),
        ("DSG 02E - Defined Test Drive", "platform IN ('PQ35','PQ46')"),
        ("DSG 0AM - Basic Settings Group 060", "platform IN ('PQ25','PQ35','PQ46')"),
        ("S-Tronic 0B5 - precondiții Basic Settings", "platform IN ('MLB')"),
    ]
    for title, where_sql in specialist_rules:
        row = con.execute("SELECT id FROM procedure_library WHERE title=?", (title,)).fetchone()
        if not row:
            continue
        pid = row[0]
        for r in con.execute(f"SELECT id FROM generations WHERE {where_sql}"):
            con.execute(
                "INSERT OR IGNORE INTO vehicle_procedures(generation_id,procedure_id,applicability,notes) VALUES(?,?,?,?)",
                (r[0], pid, "Condițional", "Se aplică numai dacă Auto-Scan confirmă controllerul/sistemul exact."),
            )

    # MK60 procedures specifically on 1K family. Other vehicles need their own ABS page/controller confirmation.
    for title in ["ABS MK60 - G85 Steering Angle Basic Setting", "ABS MK60 - Steering Limit Stop", "ABS MK60 - G251 Longitudinal Acceleration"]:
        row = con.execute("SELECT id FROM procedure_library WHERE title=?", (title,)).fetchone()
        if row:
            for r in con.execute("SELECT id FROM generations WHERE chassis LIKE '1K%' OR chassis LIKE '5M%'"):
                con.execute(
                    "INSERT OR IGNORE INTO vehicle_procedures(generation_id,procedure_id,applicability,notes) VALUES(?,?,?,?)",
                    (r[0], row[0], "Exact dacă ABS=MK60", "Verifică Component/part number ABS; MK60EC1/MK70 folosesc proceduri diferite."),
                )

    con.commit()
