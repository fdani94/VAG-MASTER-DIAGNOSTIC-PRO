"""Detailed Auto-Scan DTC guidance for common Audi B8/PQ-style faults.
Built to improve real VCDS PDF analysis; official Ross-Tech entries are marked
verified, while inferred/platform-dependent repair guidance remains unverified.
"""


def _ensure_columns(con):
    cols = {r[1] for r in con.execute("PRAGMA table_info(dtcs)").fetchall()}
    for name, typ in {
        "component": "TEXT", "component_location": "TEXT", "vcds_parameters": "TEXT",
        "expected_values": "TEXT", "test_path": "TEXT", "replacement_steps": "TEXT",
    }.items():
        if name not in cols:
            con.execute(f"ALTER TABLE dtcs ADD COLUMN {name} {typ}")


def _source(con, title, url, official=True):
    con.execute("INSERT OR IGNORE INTO sources(title,publisher,url,source_type,notes) VALUES(?,?,?,?,?)",
                (title, "Ross-Tech" if official else "KID Diagnostic", url,
                 "official/wiki" if official else "community/probable",
                 "Auto-Scan diagnostic reference"))
    row = con.execute("SELECT id FROM sources WHERE url=?", (url,)).fetchone()
    return row[0] if row else None


def _upsert(con, code, title, description, symptoms, causes, diagnosis, repair, severity,
            component, location, params, expected, path, replacement, source_id, verified):
    row = con.execute("SELECT id FROM dtcs WHERE UPPER(code)=UPPER(?) LIMIT 1", (code,)).fetchone()
    vals = (title, description, symptoms, causes, diagnosis, repair, severity, verified, source_id,
            component, location, params, expected, path, replacement)
    if row:
        con.execute("""UPDATE dtcs SET title=?,description=?,symptoms=?,causes=?,diagnosis=?,repair=?,
                    severity=?,verified=?,source_id=?,component=?,component_location=?,vcds_parameters=?,
                    expected_values=?,test_path=?,replacement_steps=? WHERE id=?""", vals + (row[0],))
    else:
        con.execute("""INSERT INTO dtcs(code,title,description,symptoms,causes,diagnosis,repair,severity,
                    verified,source_id,component,component_location,vcds_parameters,expected_values,
                    test_path,replacement_steps) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (code,) + vals)


def install(con):
    _ensure_columns(con)
    s_p261a = _source(con, "Ross-Tech P261A Coolant Pump 2", "https://wiki.ross-tech.com/wiki/index.php/P261A/009754")
    s_key = _source(con, "Ross-Tech 00955 Key 1", "https://wiki.ross-tech.com/wiki/index.php/00955")
    s_energy = _source(con, "Ross-Tech 03041 Energy Management Active", "https://wiki.ross-tech.com/wiki/index.php/03041")
    s_cap = _source(con, "Ross-Tech 02616 Fuel Tank Cap Unlock", "https://wiki.ross-tech.com/wiki/index.php/02616")
    s_cp = _source(con, "Ross-Tech 02095 Component Protection Active", "https://wiki.ross-tech.com/wiki/index.php/02095")
    s_body = _source(con, "KID Diagnostic - body locking probable guidance", "kid://autoscan/body-locking", False)
    s_lambda = _source(con, "KID Diagnostic - P2196 TDI contextual guidance", "kid://autoscan/p2196-tdi", False)

    _upsert(con, "P261A", "Pompa de lichid de răcire 2 - circuit întrerupt",
            "ECU comandă pompa electrică auxiliară, dar circuitul este deschis sau pompa nu răspunde.",
            "MIL aprins; pompa auxiliară nu funcționează; răcirea EGR/after-run poate fi afectată.",
            "Pompa de răcire 2 defectă sau deconectată; mufă/cablaj întrerupt; alimentare/siguranță; mai rar comandă ECU.",
            "1) Verifică Freeze Frame. 2) Cu motorul oprit inspectează mufa și cablajul pompei. 3) Verifică alimentarea și masa conform schemei. 4) În 01-Engine caută în Advanced Measuring Values comanda pompei / EGR cooler pump. 5) Dacă există Output Tests pentru pompă, comand-o și verifică dacă pornește. 6) Dacă are alimentare și comandă dar nu funcționează, pompa este suspectă.",
            "Repară circuitul sau înlocuiește pompa după confirmare; apoi Clear DTC și repetă testul.",
            "high", "Coolant Pump 2 / pompă electrică auxiliară de răcire",
            "În compartimentul motor, în circuitul auxiliar de răcire; poziția exactă se confirmă după codul motor.",
            "EGR cooler pump specified/actual; activation; Terminal 30; coolant temperatures",
            "La comandă mare, pompa trebuie să fie alimentată și să funcționeze; nu există o valoare universală de curent pentru toate ECU-urile.",
            "[01-Engine] -> [Advanced Measuring Values] / [Output Tests] -> coolant pump / EGR cooler pump",
            "După montaj verifică nivelul/aerisirea circuitului conform manualului, rulează Output Test dacă este disponibil, Clear DTC și Auto-Scan.", s_p261a, 1)

    _upsert(con, "00955", "Cheia 1 - limita inferioară depășită",
            "Pentru varianta Lower Limit Exceeded, Ross-Tech indică în principal bateria slabă/defectă din telecomandă.",
            "Telecomanda poate funcționa intermitent sau poate avea rază redusă.",
            "Bateria telecomenzii este descărcată sau defectă.",
            "Începe prin înlocuirea bateriei din cheia 1 cu tipul corect. Verifică apoi funcția de lock/unlock. Dacă problema rămâne, verifică sincronizarea/adaptarea specifică platformei.",
            "Înlocuiește bateria cheii și sincronizează/adaptează numai dacă este necesar.",
            "low", "Cheie / telecomandă", "În cheia/telecomanda nr. 1.",
            "Remote/key status dacă modulul oferă Measuring Values", "Telecomanda trebuie să răspundă constant după schimbarea bateriei.",
            "[05-Acc/Start Auth.] / [46-Central Convenience] -> Measuring Values/Adaptation conform platformei",
            "După bateria cheii testează toate comenzile; adaptarea cheilor se face doar cu procedura potrivită vehiculului.", s_key, 1)

    _upsert(con, "03041", "Management energie activ",
            "Sistemul de management al energiei a redus/oprit consumatori pentru a proteja bateria.",
            "Infotainment, climatizare, lumini interioare, geamuri sau alte funcții pot fi limitate temporar.",
            "Baterie descărcată/uzată; consum parazit; uneori problemă de încărcare sau codare baterie necorespunzătoare.",
            "1) Verifică tensiunea bateriei înainte de pornire și în timpul pornirii. 2) Verifică încărcarea alternatorului. 3) Verifică starea/codarea bateriei în 19-CAN Gateway/BEM. 4) Dacă bateria este bună, verifică consumul în repaus. 5) Nu schimba Gateway-ul pentru acest DTC singur.",
            "Încarcă/testează sau înlocuiește bateria dacă este slabă; codează/adaptează bateria nouă unde platforma cere; repară eventualul consum parazit.",
            "medium", "Baterie / BEM / sistem management energie", "Bateria și J367/BEM; Gateway gestionează informația de energie.",
            "Battery voltage; battery state/energy management; alternator charging; quiescent current",
            "Tensiunea și capacitatea trebuie evaluate cu tester de baterie; DTC-ul este adesea simptom, nu defect Gateway.",
            "[19-CAN Gateway] -> Fault Codes / Advanced Measuring Values / Adaptation (Battery) după caz",
            "După înlocuirea bateriei efectuează Battery Adaptation/Coding dacă este cerută de platformă, apoi Clear DTC și rescanare.", s_energy, 1)

    for code, action in (("02615", "blocare"), ("02616", "deblocare")):
        _upsert(con, code, f"Capac rezervor - {action}",
                f"Circuitul actuatorului pentru {action} capac rezervor este întrerupt sau scurt la masă.",
                "Capacul/clapeta rezervorului poate să nu se blocheze/deblocheze corect.",
                "Cablaj/mufă actuator; actuator de blocare capac rezervor defect; alimentare/masă.",
                "1) Comandă lock/unlock și ascultă actuatorul. 2) Verifică mufa și cablajul la actuator. 3) Verifică alimentarea în timpul comenzii. 4) Folosește Output Tests în 46-Central Convenience dacă sunt disponibili. 5) Dacă alimentarea/comanda sunt corecte și actuatorul nu se mișcă, înlocuiește actuatorul.",
                "Repară cablajul sau înlocuiește actuatorul de blocare al clapetei rezervorului după confirmare.",
                "medium", "Actuator blocare clapetă/capac rezervor",
                "În zona clapetei rezervorului, accesibil din zona laterală a portbagajului/aripii în funcție de caroserie.",
                "Lock/unlock status; Output Test actuator", "Starea trebuie să urmărească comanda lock/unlock fără DTC electric.",
                "[46-Central Convenience] -> [Output Tests] / [Advanced Measuring Values] -> fuel flap/tank cap lock",
                "După înlocuire verifică mecanic blocarea/deblocarea, Clear DTC și Auto-Scan.", s_cap if code == "02616" else s_body, 1 if code == "02616" else 0)

    _upsert(con, "01699", "Motor închidere centralizată hayon/portbagaj (V53)",
            "Modulul detectează circuit deschis/scurt la masă pe motorul de închidere al hayonului/portbagajului.",
            "Portbagajul poate să nu se blocheze/deblocheze sau poate funcționa intermitent.",
            "Motor/actuator V53; cablaj în burduful hayonului; mufă; broască mecanic blocată.",
            "1) Testează deschiderea/închiderea. 2) Inspectează cablajul în zona flexibilă a hayonului. 3) Verifică mufa și alimentarea actuatorului. 4) Rulează Output Tests/MVB în 46 dacă sunt disponibile. 5) Dacă alimentarea e corectă, verifică actuatorul/broasca.",
            "Repară cablajul sau înlocuiește actuatorul/broasca după confirmare.",
            "medium", "V53 / actuator închidere portbagaj", "În ansamblul broaștei hayonului/portbagajului.",
            "Trunk latch status; lock/unlock command; Output Test", "Feedback-ul broaștei trebuie să urmărească poziția reală.",
            "[46-Central Convenience] -> [Measuring Blocks/Advanced Measuring Values] / [Output Tests] -> trunk/hatch lock",
            "După montaj verifică manual și electric broasca, șterge DTC și rescanează.", s_body, 0)

    _upsert(con, "02115", "Unitate de închidere centralizată - semnal implauzibil",
            "Feedback-ul broaștei/ușii nu corespunde comenzii de lock/unlock.",
            "Ușa poate rămâne blocată/deblocată, poate raporta stare greșită sau poate funcționa intermitent.",
            "Broască/actuator uzat; microswitch intern; mecanism rigid; cablaj/mufă; alimentare.",
            "1) Notează ce ușă/modul a raportat codul. 2) Urmărește în Measuring Values starea lock/safe/door contact în timp ce închizi/deschizi. 3) Verifică mecanica broaștei. 4) Inspectează cablajul dintre caroserie și ușă. 5) Rulează Output Test dacă este disponibil. 6) Dacă feedback-ul rămâne implauzibil cu alimentare/cablaj bune, broasca este suspectă.",
            "Repară cablajul/mecanica sau înlocuiește unitatea de închidere a ușii afectate după confirmare.",
            "medium", "Broască / locking unit ușă", "În interiorul ușii care raportează DTC-ul, integrată în ansamblul broaștei.",
            "Door contact; lock status; safe status; actuator command", "Stările trebuie să se schimbe coerent cu comanda și poziția ușii.",
            "[52/62/72/42-Door Electronics] -> [Advanced Measuring Values/Measuring Blocks] -> locking/door status; [Output Tests] dacă există",
            "După înlocuire copiază codingul dacă modulul a fost schimbat; pentru broască simplă verifică funcțiile, Clear DTC și Auto-Scan.", s_body, 0)

    _upsert(con, "02095", "Protecție componentă activă",
            "Component Protection este activă și poate limita funcția modulului, frecvent după montarea unui modul provenit din alt vehicul.",
            "Funcții limitate; sunet/infotainment sau alte funcții pot fi restricționate.",
            "Component Protection activă.",
            "Confirmă modulul și istoricul înlocuirii. VCDS poate citi DTC-ul și codingul, dar Ross-Tech precizează că dezactivarea/învățarea Component Protection necesită unealtă de fabrică și conexiune online.",
            "Nu se rezolvă prin Clear DTC sau Long Coding obișnuit. E necesară procedura online de Component Protection la service/dealer sau cu instrumentația oficială compatibilă.",
            "medium", "Component Protection / modul infotainment sau alt modul protejat", "Modulul care raportează 02095.",
            "Module identification; component protection status", "DTC-ul trebuie să dispară după procedura online corectă de CP.",
            "[modulul cu 02095] -> [Fault Codes]; eliminarea CP nu se face prin funcție VCDS standard",
            "După eliminarea CP verifică coding/adaptations, funcționarea modulului și execută Auto-Scan final.", s_cp, 1)

    _upsert(con, "P2196", "Sondă Lambda B1 S1 - semnal prea mare / amestec bogat",
            "ECU vede semnalul sondei lambda înainte de catalizator ca fiind excesiv în direcția bogat. Pe diesel interpretarea trebuie făcută în contextul strategiei EGR/air mass și al senzorului wideband.",
            "MIL aprins; posibil consum/emisii anormale; uneori fără simptome evidente.",
            "Sondă lambda/cablaj; contaminare; problemă de aer măsurat/EGR; scăpări/condiții de evacuare; mai rar problemă ECU. Cauza exactă depinde de motor.",
            "1) Nu schimba sonda direct. 2) Verifică alte DTC-uri de aer/EGR/MAF. 3) Inspectează cablajul și mufa B1S1. 4) În 01-Engine urmărește lambda actuală, heater activation, air mass actual/spec și EGR. 5) Verifică dacă valorile sunt plauzibile la ralanti și în sarcină. 6) Dacă semnalul rămâne blocat cu cablaj bun, testează/înlocuiește sonda conform manualului.",
            "Repară mai întâi cauza de aer/EGR/cablaj dacă există; înlocuiește sonda numai după confirmare.",
            "high", "Sondă lambda Bank 1 Sensor 1", "Pe evacuare înainte de catalizator/DPF în funcție de configurația motorului.",
            "Lambda signal; lambda heater activation; actual air mass; EGR values; exhaust temperature/context",
            "Valorile trebuie să fie dinamice și plauzibile; pragurile exacte sunt specifice ECU/motorului.",
            "[01-Engine] -> [Advanced Measuring Values] -> lambda B1S1 / heater / air mass / EGR",
            "După reparație Clear DTC, verifică live data, test drive și Auto-Scan; resetările de adaptare se fac numai dacă sunt documentate pentru ECU.", s_lambda, 0)

    con.commit()
