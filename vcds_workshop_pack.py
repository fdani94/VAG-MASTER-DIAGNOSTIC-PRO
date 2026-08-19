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


def _map_all(con, pid, applicability="Condițional"):
    for r in con.execute("SELECT id FROM generations"):
        con.execute("INSERT OR IGNORE INTO vehicle_procedures(generation_id,procedure_id,applicability,notes) VALUES(?,?,?,?)",
                    (r[0], pid, applicability, "VCDS-only. Confirmă Auto-Scan, controller, software, motor și echiparea înainte de aplicare."))


def install(con):
    src_main = _source(con, "VCDS Function Index", "https://www.ross-tech.com/vcds/tour/main_screen.php", "Index funcții VCDS")
    src_adv = _source(con, "Advanced Measuring Values", "https://www.ross-tech.com/vcds/tour/adv-meas-blocks.php")
    src_out = _source(con, "Output Tests", "https://www.ross-tech.com/vcds/tour/out_test.php")
    src_bs = _source(con, "Basic Settings", "https://www.ross-tech.com/vcds/tour/b-settings.php")
    src_ad = _source(con, "Adaptation", "https://www.ross-tech.com/vcds/tour/adaptation_screen.php")

    rows = [
        ("Motor - parametri live esențiali", "Parametri live", "01", "[01-Engine] > [Adv. Meas. Values] / [Meas. Blocks-08]", "Diagnostic motor prin valori live.", "Motor pornit sau contact ON după parametrul urmărit.", "Caută turație, temperatură lichid, MAF, MAP/boost, rail pressure, EGR, lambda, DPF soot/ash și temperaturi EGT unde sunt disponibile. Compară specified vs actual și salvează Log.", "Valorile sunt coerente cu starea motorului și cu cererea ECU.", "Denumirile și grupurile diferă după ECU; nu folosi grupuri numerice universale pe UDS.", "General/Condițional", 1, src_adv),
        ("Motor - Output Tests actuatori", "Output Tests", "01", "[01-Engine] > [Output Tests-03]", "Testează actuatori comandați de ECU.", "Vehicul securizat; tensiune stabilă; fără risc mecanic în zona actuatorului.", "Rulează doar testele oferite de controller: EGR, N75/boost control, throttle, pompe, ventilatoare, clapete, relee sau injectoare unde sunt suportate. Observă reacția și eventual valorile live simultan.", "Actuatorul răspunde la comandă fără DTC suplimentare.", "Lista de teste este controller-specific; nu există aceeași ordine pe toate ECU-urile.", "Condițional", 1, src_out),
        ("Motor - Basic Settings după înlocuire componentă", "Basic Settings", "01", "[01-Engine] > [Basic Settings-04]", "Rulează învățări/calibrări după schimbarea unei componente.", "Componenta este montată corect și controllerul oferă funcția exactă.", "Selectează numai funcția denumită de ECU pentru componenta schimbată: throttle, EGR, intake flap, fuel metering, turbo actuator etc. Urmează condițiile afișate de VCDS.", "Finished Correctly / ADP OK sau criteriul controllerului.", "Nu experimenta cu Basic Settings necunoscute.", "Condițional", 1, src_bs),
        ("DSG/TCM - valori live ambreiaje și temperatură", "Parametri live", "02", "[02-Auto Trans] > [Adv. Meas. Values] / [Meas. Blocks-08]", "Analiză cutie DSG/automată.", "Cutia trebuie identificată exact din Auto-Scan.", "Urmărește temperatura uleiului, pozițiile selectorului, slip/adaptation clutch, presiuni și stări Basic Settings unde sunt expuse. Salvează log înainte și după adaptare.", "Valorile nu indică alunecare/anomalii în condițiile testului.", "Parametrii diferă major între 02E, 0AM/DQ200, 0B5, 09G etc.", "Condițional", 1, src_adv),
        ("ABS/ESP - senzori viteză roți live", "Parametri live", "03", "[03-ABS Brakes] > [Adv. Meas. Values]", "Identifică senzor de roată/cablaj cu semnal anormal.", "Vehicul ridicat în siguranță sau test rutier asistat.", "Selectează vitezele celor patru roți și compară simultan. La rulare dreaptă valorile trebuie să fie apropiate; o roată care cade la 0/intermitent indică senzor, inel magnetic, rulment sau cablaj de verificat.", "Cele patru viteze sunt coerente între ele.", "Nu conduce și nu opera laptopul simultan fără a doua persoană.", "General/Condițional", 1, src_adv),
        ("ABS/ESP - G85/G200/G201 parametri", "Parametri live", "03", "[03-ABS Brakes] > [Adv. Meas. Values]", "Verifică unghi volan, accelerație laterală și presiune frână.", "Volan drept; vehicul pe plan drept pentru comparații de zero.", "Caută Steering Angle Sensor, Lateral Acceleration și Brake Pressure. Verifică plauzibilitatea înainte de a rula calibrarea specifică platformei.", "Valorile sunt plauzibile și apropiate de zero în condițiile corecte.", "Nu calibra un senzor care are problemă de cablaj/alimentare.", "Condițional", 1, src_adv),
        ("Steering Assist - parametri cuplu/unghi", "Parametri live", "44", "[44-Steering Assist] > [Adv. Meas. Values]", "Diagnoză servodirecție și G85/G269 după echipare.", "Volan centrat; baterie încărcată.", "Urmărește steering angle, torque sensor, supply voltage și motor current unde sunt disponibile. Compară stânga/dreapta și verifică offset-ul cu volanul drept.", "Valorile sunt simetrice/plauzibile.", "Pe unele platforme G85 este în ABS, nu în 44.", "Condițional", 1, src_adv),
        ("Climatizare - temperaturi și clapete", "Parametri live", "08", "[08-Auto HVAC] > [Adv. Meas. Values]", "Diagnoză temperaturi, senzori și flap motors.", "Motor pornit; climatizarea activă.", "Urmărește temperaturile interioară/exterioară/evaporator, presiunea agentului dacă este disponibilă, requested/actual flap positions și compresor request. Compară zonele stânga/dreapta.", "Valorile corespund temperaturilor reale și clapetele urmăresc cererea.", "Presiunea AC nu înlocuiește verificarea cu manometre unde este necesară.", "Condițional", 1, src_adv),
        ("Climatizare - Output Tests clapete/ventilatoare", "Output Tests", "08", "[08-Auto HVAC] > [Output Tests-03]", "Testează clapete, suflantă și actuatori HVAC.", "Acces liber la gurile de ventilație; tensiune stabilă.", "Rulează secvența de Output Tests și observă fiecare motor de clapetă/suflantă. Corelează cu zgomote, blocaje și poziția actuală.", "Actuatoarele rulează fără blocare și fără DTC.", "Nu forța mecanic clapetele în timpul testului.", "Condițional", 1, src_out),
        ("Central Electrics - verificare becuri și ieșiri", "Output Tests", "09", "[09-Cent. Elect.] > [Output Tests-03]", "Testează ieșiri lumini/relee suportate de BCM.", "Vehicul staționar; contacte electrice sigure.", "Rulează Output Tests pentru becuri/LED/relee disponibile și verifică fizic răspunsul. Folosește DTC și measuring values pentru circuit open/short dacă sunt disponibile.", "Ieșirea răspunde corect.", "LED-urile moderne pot fi comandate prin module separate de far.", "Condițional", 1, src_out),
        ("Gateway - inventar module instalate", "Diagnostic", "19", "[19-CAN Gateway] > [Installation List] / Auto-Scan", "Confirmă modulele instalate și lipsurile de comunicație.", "Auto-Scan salvat.", "Compară Installation List cu modulele fizic prezente. Dacă un modul lipsește din scanare, verifică alimentare, masă și CAN înainte de recodare.", "Lista corespunde echipării reale și nu există DTC de module fictive.", "Nu bifa module inexistente doar pentru a elimina o eroare.", "General/Condițional", 1, src_main),
        ("Instruments - parametri service și avertizări", "Parametri live", "17", "[17-Instruments] > [Adv. Meas. Values]/[Adaptation-10]", "Verifică intervale service, senzori și stări afișate de cluster.", "Salvează harta de adaptări înainte de modificări.", "Caută ESI/SIA/SRI, oil quality, distance/time since service, warning thresholds și door/seatbelt states unde sunt disponibile.", "Valorile sunt coerente cu istoricul de service și starea vehiculului.", "Canalele diferă mult între Immo3, CAN și UDS clusters.", "Condițional", 1, src_ad),
        ("TPMS - diagnoză senzori/sistem indirect", "Diagnostic", "65", "[65-Tire Pressure] sau [03-ABS] > [Adv. Meas. Values]", "Identifică tipul TPMS și cauza avertizării.", "Confirmă dacă sistemul este direct sau indirect.", "La TPMS direct verifică ID/pressure/status dacă sunt disponibile în 65. La indirect verifică 03-ABS și procedura de reset/learn oferită de controller.", "Toate roțile sunt recunoscute / resetul este acceptat.", "Nu introduce ID-uri sau presiuni inventate.", "Condițional", 1, src_adv),
        ("Headlight Range - senzori nivel live", "Parametri live", "55", "[55-Headlight Range] > [Adv. Meas. Values]", "Diagnoză senzori nivel și autoleveling.", "Mașina pe plan drept; suspensie stabilă.", "Urmărește front/rear level sensor values, supply voltage și actuator positions. Mișcă ușor suspensia pentru a confirma reacția senzorilor.", "Senzorii răspund lin și plauzibil.", "După înlocuire poate fi necesară Basic Settings specifică modulului.", "Condițional", 1, src_adv),
        ("Parking Aid - senzori distanță live", "Parametri live", "76", "[76-Park Assist] / [10-Park/Steer Assist] > [Adv. Meas. Values]", "Găsește senzor ultrasonic defect.", "Sistem activ; zonă sigură în jurul mașinii.", "Selectează distanțele individuale ale senzorilor. Apropie un obiect controlat de fiecare senzor și verifică variația. Un senzor fix/absurd indică senzor/cablaj/poziționare.", "Toți senzorii reacționează coerent.", "Nu concluziona doar din lipsa clicului auditiv; verifică și DTC/cablaj.", "Condițional", 1, src_adv),
        ("Battery/energy management - valori live", "Parametri live", "61", "[61-Battery Regulation] sau [19-CAN Gateway] > [Adv. Meas. Values]", "Verifică SOC, tensiune, curent și management energetic.", "Baterie conectată corect; clamp sensor prezent unde este echipat.", "Urmărește battery voltage, current, state of charge, state of health și generator request unde sunt disponibile. Compară motor oprit/pornit și consumatori activați.", "Încărcarea și SOC sunt plauzibile.", "Nu folosi o singură valoare SOC pentru a condamna bateria; confirmă cu test de baterie.", "Condițional", 1, src_adv),
        ("Scanare după reparație - control final", "Proceduri", "", "Auto-Scan > Save", "Validează reparația și documentează starea finală.", "Reparația/adaptarea terminată.", "1) Șterge DTC doar după remediere. 2) Ciclizează contactul dacă procedura o cere. 3) Rulează test static sau rutier. 4) Auto-Scan complet. 5) Salvează scanarea finală și compar-o cu cea inițială.", "Nu rămân DTC relevante și funcția reparată operează corect.", "Nu considera reparația finalizată doar pentru că becul din bord s-a stins.", "General", 1, src_main),
    ]

    for row in rows:
        pid = _proc(con, row)
        _map_all(con, pid)

    con.commit()
