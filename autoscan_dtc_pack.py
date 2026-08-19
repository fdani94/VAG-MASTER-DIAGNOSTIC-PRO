from datetime import date


def _ensure_column(con, table, name, decl="TEXT DEFAULT ''"):
    cols = {r[1] for r in con.execute(f"PRAGMA table_info({table})")}
    if name not in cols:
        con.execute(f"ALTER TABLE {table} ADD COLUMN {name} {decl}")


def _source(con, title, url, publisher="Ross-Tech", stype="Oficial"):
    row = con.execute("SELECT id FROM sources WHERE url=?", (url,)).fetchone()
    if row:
        return row[0]
    return con.execute(
        "INSERT INTO sources(title,publisher,url,accessed,source_type,notes) VALUES(?,?,?,?,?,?)",
        (title, publisher, url, date.today().isoformat(), stype, "Sursă pentru fișe DTC Auto-Scan"),
    ).lastrowid


def _upsert(con, code, title, description, symptoms, causes, component, location, params, expected, test_path, diagnosis, repair, replacement, severity, verified, source_id):
    row = con.execute("SELECT id FROM dtcs WHERE UPPER(code)=?", (code.upper(),)).fetchone()
    values = (title, description, symptoms, causes, diagnosis, repair, severity, verified, source_id,
              component, location, params, expected, test_path, replacement)
    if row:
        con.execute("""UPDATE dtcs SET title=?,description=?,symptoms=?,causes=?,diagnosis=?,repair=?,severity=?,verified=?,source_id=?,
                     component=?,component_location=?,vcds_parameters=?,expected_values=?,test_path=?,replacement_steps=? WHERE id=?""",
                    values + (row[0],))
    else:
        con.execute("""INSERT INTO dtcs(code,title,description,symptoms,causes,diagnosis,repair,severity,verified,source_id,
                     component,component_location,vcds_parameters,expected_values,test_path,replacement_steps)
                     VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (code,) + values)


def install(con):
    for col in ("component", "component_location", "vcds_parameters", "expected_values", "test_path", "replacement_steps"):
        _ensure_column(con, "dtcs", col)

    s_faults = _source(con, "Ross-Tech Wiki - Fault Codes", "https://wiki.ross-tech.com/wiki/index.php/Category:Fault_Codes")
    s_g85 = _source(con, "00778 - Steering Angle Sensor G85", "https://wiki.ross-tech.com/wiki/index.php/00778")
    s_ecm = _source(con, "01314 - Engine Control Module", "https://wiki.ross-tech.com/wiki/index.php/01314")
    s_uv = _source(con, "00446 - Function Limitation due to Under-Voltage", "https://wiki.ross-tech.com/wiki/index.php/00446")
    s_p0299 = _source(con, "16683/P0299/000665", "https://wiki.ross-tech.com/wiki/index.php/16683/P0299/000665")
    s_p0087 = _source(con, "16471/P0087/000135", "https://wiki.ross-tech.com/wiki/index.php/16471/P0087/000135")
    s_p0401 = _source(con, "16785/P0401/001025", "https://wiki.ross-tech.com/wiki/index.php/16785/P0401")
    s_p2453 = _source(con, "18885/P2453/009299", "https://wiki.ross-tech.com/wiki/index.php/18885/P2453/009299")

    _upsert(con, "00778", "Steering Angle Sensor (G85)",
        "Eroare a senzorului de unghi volan sau basic setting/inițializare pierdută.",
        "Martori ABS/ESP/steering; funcțiile ESP pot fi limitate.",
        "Basic Setting pierdut; poziție/montaj incorect; lipsă comunicație; senzor sau cablaj defect.",
        "G85 - Steering Angle Sensor", "În ansamblul coloanei/spiralei volan sau integrat în steering assist, în funcție de platformă.",
        "Unghi volan G85 în 03-ABS sau 44-Steering Assist; urmărește valoarea cu roțile drepte.",
        "Cu volanul și roțile drept înainte, valoarea trebuie să fie aproape de 0°. Ross-Tech indică ±5° ca verificare generală pentru unele cazuri; procedura exactă diferă după ABS.",
        "[03-ABS] sau [44-Steering Assist] > [Measuring Values] > G85; apoi Basic Settings specific platformei.",
        "1) Pune roțile drept. 2) Citește G85. 3) Verifică DTC în 03 și 44. 4) Confirmă tipul ABS MK60/MK70/MQB. 5) Rulează Basic Setting specific. 6) Inițializează prin test drive dacă este cerut.",
        "Recalibrare dacă senzorul este sănătos; verifică montajul, cablajul și comunicația înainte de înlocuire.",
        "După înlocuire steering rack/clock spring/G85: coding dacă a fost necesar, Basic Setting G85 și test drive/inițializare conform platformei.",
        "Ridicat", 1, s_g85)

    _upsert(con, "01314", "Engine Control Module - No Communication / Check DTC Memory",
        "Un alt modul raportează lipsă comunicație cu ECU sau cere verificarea memoriei de erori a ECU.",
        "Pot apărea martori multipli; în varianta No Communication motorul poate să nu pornească.",
        "Erori stocate în ECU; alimentare ECU; CAN wiring/conectori; ECU recent programat/remapat.",
        "J623/J220 - Engine Control Module și rețeaua CAN", "ECU este de regulă în compartimentul motor/plenum; poziția exactă diferă după model.",
        "Verifică dacă 01-Engine răspunde; pe platforme vechi MVB 125+ pot indica status comunicație CAN.",
        "01-Engine trebuie să comunice stabil; tensiunea de alimentare și masele trebuie să fie corecte.",
        "Auto-Scan > [01-Engine] > [Fault Codes] și [Measuring Blocks/Advanced Measuring Values] pentru comunicație/alimentare.",
        "1) Încearcă acces direct 01-Engine. 2) Dacă răspunde, repară mai întâi DTC-urile din ECU. 3) Dacă nu răspunde, verifică siguranțe, alimentări, mase, CAN H/L și conector ECU. 4) Verifică Gateway pentru alte module offline.",
        "Repară problema din ECU sau comunicație; 01314 din alte module dispare după rezolvarea cauzei principale.",
        "Nu înlocui ECU înainte de măsurarea alimentărilor, maselor și CAN. Înlocuirea ECU poate necesita proceduri suplimentare care nu sunt VCDS-only pe unele generații.",
        "Ridicat", 1, s_ecm)

    _upsert(con, "00446", "Function Limitation due to Under-Voltage",
        "Un modul a limitat o funcție deoarece tensiunea de alimentare a fost prea mică.",
        "Martori multipli sau funcții indisponibile după baterie slabă/pornire grea.",
        "Baterie descărcată/defectă; alternator; siguranțe; căderi de tensiune/alimentare.",
        "Baterie, alternator, distribuție alimentare", "Bateria și alternatorul conform modelului; verifică și cutiile de siguranțe și punctele de masă.",
        "Tensiune terminal 30/15, battery voltage, generator voltage, energy management dacă este disponibil.",
        "Tensiunea nu trebuie să cadă anormal la pornire și sistemul de încărcare trebuie să ridice tensiunea corespunzător tipului de management energetic.",
        "[19-Gateway]/[61-Battery Regulation]/modulul care a memorat DTC > Advanced Measuring Values.",
        "1) Măsoară bateria în repaus. 2) Verifică tensiunea în timpul pornirii. 3) Verifică încărcarea. 4) Inspectează borne/masă/siguranțe. 5) Șterge DTC numai după remediere și rescanează.",
        "Încarcă sau înlocuiește bateria dacă testul o confirmă; repară alternatorul/conexiunile dacă tensiunea rămâne incorectă.",
        "După înlocuirea bateriei, fă adaptarea/înregistrarea bateriei dacă vehiculul are battery energy management și procedura este suportată de VCDS.",
        "Mediu", 1, s_uv)

    _upsert(con, "P0299", "Boost Pressure Regulation - Control Range Not Reached",
        "Presiunea de supraalimentare reală nu atinge ținta comandată de ECU.",
        "Putere redusă, limp mode, accelerație slabă.",
        "Pierderi pe furtunuri/intercooler; control actuator/N75; diverter valve la benzină; geometrie/turbo; restricție evacuare.",
        "Sistem turbo/boost", "Turbo pe evacuare; actuatorul pe turbo; N75/valve și traseul de vacuum/presiune diferă după motor.",
        "Boost pressure specified/target și actual; actuator position dacă este disponibil; MAF; duty cycle charge pressure control.",
        "La sarcină, actual trebuie să urmărească target fără abatere persistentă mare; valorile absolute diferă după motor și condiții.",
        "[01-Engine] > [Advanced Measuring Values] > boost specified/actual + charge pressure actuator; Output Tests unde controllerul permite.",
        "1) Inspectează traseul aer/vacuum. 2) Testează etanșeitatea. 3) Log specified vs actual. 4) Verifică actuator/control valve. 5) Verifică geometria/turbo și restricția evacuării.",
        "Repară scurgerea/controlul înainte de a condamna turbina. Curăță/repară actuatorul/geometria doar conform tipului de turbo.",
        "După schimbarea turbo/actuatorului verifică oil feed/return, vacuum, Basic Settings/actuator adaptation dacă ECU oferă funcția, apoi log boost și Auto-Scan.",
        "Ridicat", 1, s_p0299)

    _upsert(con, "P0087", "Fuel Rail/System Pressure - Too Low",
        "Presiunea în rampa de combustibil este sub necesarul ECU.", "Pierdere de putere, pornire grea, oprire/limp mode.",
        "Alimentare joasă insuficientă; filtru; conductă strivită/scurgere; pompă; injector cu retur/pierdere; hardware presiune înaltă.",
        "Sistem alimentare joasă + rampă common rail / high pressure", "Pompa de rezervor, filtru, pompa HP și rampa depind de motor.",
        "Fuel rail pressure specified și actual; low fuel pressure dacă există; regulator/quantity valve duty.",
        "Actual trebuie să urmărească target; abaterea persistentă sub target indică problemă de alimentare/reglare, dar pragurile diferă după motor.",
        "[01-Engine] > [Advanced Measuring Values] > fuel pressure target/actual; teste pompă unde sunt disponibile.",
        "1) Verifică nivel/calitate combustibil. 2) Filtru/conducte/scurgeri. 3) Presiune joasă. 4) Log rail target/actual. 5) Verifică pierdere pe injectoare și regulator/pompă HP conform motorului.",
        "Remediază cauza confirmată; nu schimba pompa HP doar pe baza P0087.",
        "După intervenție pe circuit: amorsează/aerisește conform procedurii, verifică scurgerile, șterge DTC și log rail pressure.",
        "Ridicat", 1, s_p0087)

    _upsert(con, "P0401", "EGR System - Insufficient Flow",
        "ECU detectează debit EGR insuficient față de cel comandat.", "MIL, emisii crescute, uneori putere redusă/regenerări afectate.",
        "EGR/galerie/depuneri; valve/cooler; filtru EGR pe unele TDI CR; cablaj; alte componente de evacuare care afectează fluxul.",
        "EGR valve/cooler/traseu EGR", "În jurul galeriei admisie/evacuare; configurația diferă mult după motor.",
        "EGR specified/actual, MAF specified/actual, EGR valve position, exhaust flap position unde există.",
        "La comandarea EGR trebuie să existe răspuns coerent al poziției/debitului; valorile exacte depind de ECU.",
        "[01-Engine] > [Advanced Measuring Values] + [Output Tests]/[Basic Settings] pentru EGR doar dacă ECU oferă testul.",
        "1) Verifică alte DTC de evacuare/MAF. 2) Inspectează EGR și traseul. 3) Log EGR/MAF. 4) Output Test. 5) Verifică depuneri/cooler/filter și cablaj.",
        "Curăță/repară traseul sau înlocuiește componenta numai după confirmarea blocajului/defectului.",
        "După EGR/throttle replacement poate fi necesar Basic Setting/Adaptation în 01-Engine; rulează doar procedura disponibilă pe controller.",
        "Mediu", 1, s_p0401)

    _upsert(con, "P2453", "DPF Differential Pressure Sensor - Implausible Signal",
        "Semnalul senzorului diferențial de presiune DPF (de regulă G450) este implauzibil.", "MIL; regenerări afectate; DPF warnings.",
        "Siguranță/alimentare; cablaj/conector; furtunașe presiune blocate/crăpate/inversate; G450 defect.",
        "G450 / Exhaust Pressure Sensor 1 și furtunașele DPF", "În compartiment motor sau zona peretelui de foc, legat prin două conducte la evacuare/DPF; poziția exactă diferă după motor.",
        "DPF differential pressure, G450 offset, soot mass calculated/measured, ash volume și EGT relevante.",
        "Cu motor oprit diferența trebuie să fie aproape de offset/zero; la debit crescut trebuie să reacționeze plauzibil. Pragurile exacte depind de ECU.",
        "[01-Engine] > [Advanced Measuring Values] > differential pressure / G450 offset / soot / ash.",
        "1) Inspectează furtunașele și orientarea. 2) Verifică alimentare/masă/semnal. 3) Citește offset cu motor oprit. 4) Compară presiunea la ralanti și turație. 5) Verifică încărcarea DPF înainte de regenerare.",
        "Curăță/înlocuiește furtunașele sau G450 dacă testele confirmă defectul.",
        "După G450 poate fi necesară adaptarea/zero calibration în 01-Engine, în funcție de ECU. Verifică apoi offset și presiunea DPF.",
        "Ridicat", 1, s_p2453)

    # Additional common OBD/VAG entries. They are intentionally diagnostic-first and avoid universal replacement advice.
    common = [
        ("P0100","Mass Air Flow Circuit Malfunction","MAF G70/cablaj","Debitul de aer măsurat are problemă de circuit sau plauzibilitate."),
        ("P0101","Mass Air Flow Range/Performance","MAF G70/admisie","MAF nu corespunde modelului de aer așteptat de ECU."),
        ("P0102","Mass Air Flow Signal Too Low","MAF G70/cablaj","Semnal MAF prea mic."),
        ("P0103","Mass Air Flow Signal Too High","MAF G70/cablaj","Semnal MAF prea mare."),
        ("P0104","Mass Air Flow Intermittent","MAF G70/cablaj","Semnal MAF intermitent."),
        ("P0116","Engine Coolant Temperature Range/Performance","G62 coolant temperature sensor","Temperatura lichidului este implauzibilă față de condiții."),
        ("P0117","Engine Coolant Temperature Signal Low","G62/cablaj","Semnal temperatură lichid prea mic."),
        ("P0118","Engine Coolant Temperature Signal High","G62/cablaj","Semnal temperatură lichid prea mare."),
        ("P0130","Oxygen Sensor Circuit Bank 1 Sensor 1","Lambda/O2 B1S1","Problemă circuit/semnal sonda lambda înainte de catalizator."),
        ("P0131","Oxygen Sensor Signal Too Low B1S1","Lambda/O2 B1S1","Semnal prea mic."),
        ("P0134","Oxygen Sensor No Activity B1S1","Lambda/O2 B1S1","ECU nu vede activitate a sondei."),
        ("P0140","Oxygen Sensor No Activity B1S2","Lambda/O2 B1S2","ECU nu vede activitate a sondei post-catalizator."),
        ("P0141","Oxygen Sensor Heater B1S2","Încălzire sondă lambda B1S2","Problemă circuit încălzire sondă post-catalizator."),
        ("P0171","System Too Lean Bank 1","Fuel trim/admisie/MAF","Amestec prea sărac; verifică aer fals, MAF și alimentarea."),
        ("P0172","System Too Rich Bank 1","Fuel trim/injecție/MAF","Amestec prea bogat; verifică măsurarea aerului și alimentarea/injectoarele."),
        ("P0300","Random/Multiple Cylinder Misfire","Aprindere/injecție/compresie","Rateuri multiple sau aleatoare."),
        ("P0301","Cylinder 1 Misfire","Cilindrul 1","Rateuri cilindrul 1."),
        ("P0302","Cylinder 2 Misfire","Cilindrul 2","Rateuri cilindrul 2."),
        ("P0303","Cylinder 3 Misfire","Cilindrul 3","Rateuri cilindrul 3."),
        ("P0304","Cylinder 4 Misfire","Cilindrul 4","Rateuri cilindrul 4."),
        ("P0420","Catalyst System Efficiency Below Threshold Bank 1","Catalizator/lambda/exhaust","Eficiența calculată a catalizatorului este sub limită; verifică mai întâi alte cauze și scurgeri."),
    ]
    for code,title,component,desc in common:
        _upsert(con, code, title, desc,
            "MIL și simptome dependente de sistem/motor.",
            "Cablaj/conector, alimentare/masă, senzor/actuator, scurgeri sau problemă mecanică relevantă sistemului.",
            component, "Locația exactă trebuie confirmată după cod motor și model.",
            "În 01-Engine caută Advanced Measuring Values corespunzătoare senzorului/sistemului și compară specified/actual când există.",
            "Folosește plauzibilitatea și limitele ECU; nu aplica o valoare universală tuturor motoarelor.",
            "[01-Engine] > [Fault Codes] > [Advanced Measuring Values]; Output Tests/Basic Settings numai dacă sunt relevante și disponibile.",
            "1) Salvează Freeze Frame. 2) Verifică DTC asociate. 3) Inspectează cablaj/conectori/scurgeri. 4) Măsoară live data. 5) Testează componenta. 6) Repară cauza și rescanează.",
            "Repară cauza confirmată; nu înlocui automat componenta doar pentru că DTC-ul o menționează.",
            "După înlocuire, verifică dacă ECU cere Basic Setting/Adaptation și confirmă funcționarea prin live data + Auto-Scan final.",
            "Mediu", 1, s_faults)

    con.commit()
