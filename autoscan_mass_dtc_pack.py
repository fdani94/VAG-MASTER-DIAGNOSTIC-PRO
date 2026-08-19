"""Mass Auto-Scan DTC coverage for KID Diagnostic.

Adds broad VAG DTC coverage. Detailed rows are evidence-oriented; fallback rows
are intentionally marked unverified and provide a safe diagnostic direction
rather than pretending an exact Basic Setting/Coding value is universal.
"""

SOURCE_TITLE = "Ross-Tech Wiki - Fault Codes index"
SOURCE_URL = "https://wiki.ross-tech.com/wiki/index.php/Category:Fault_Codes"


def _ensure_columns(con):
    cols = {r[1] for r in con.execute("PRAGMA table_info(dtcs)")}
    wanted = {
        "component": "TEXT", "component_location": "TEXT",
        "vcds_parameters": "TEXT", "expected_values": "TEXT",
        "test_path": "TEXT", "replacement_steps": "TEXT",
        "confidence": "TEXT", "module_hint": "TEXT",
    }
    for name, typ in wanted.items():
        if name not in cols:
            con.execute(f"ALTER TABLE dtcs ADD COLUMN {name} {typ}")


def _source(con):
    con.execute("INSERT OR IGNORE INTO sources(title,publisher,url,source_type,notes) VALUES(?,?,?,?,?)",
                (SOURCE_TITLE, "Ross-Tech", SOURCE_URL, "official-index", "Fault-code index; exact applicability depends on controller/platform."))
    row = con.execute("SELECT id FROM sources WHERE title=?", (SOURCE_TITLE,)).fetchone()
    return row[0] if row else None


def _put(con, src, code, title, system, causes, diagnosis, repair, component, location, params, expected, path, after, confidence="probabil/comunitate"):
    row = con.execute("SELECT id FROM dtcs WHERE UPPER(code)=UPPER(?)", (code,)).fetchone()
    values = (title, f"{system}: {title}", "Martor/mesaj sau funcție afectată; confirmă statusul și Freeze Frame din Auto-Scan.",
              causes, diagnosis, repair, "medium", 0 if confidence != "verificat" else 1, src,
              component, location, params, expected, path, after, confidence, system)
    if row:
        con.execute("""UPDATE dtcs SET title=?,description=?,symptoms=?,causes=?,diagnosis=?,repair=?,severity=?,verified=?,source_id=?,component=?,component_location=?,vcds_parameters=?,expected_values=?,test_path=?,replacement_steps=?,confidence=?,module_hint=? WHERE id=?""", values + (row[0],))
    else:
        con.execute("""INSERT INTO dtcs(code,title,description,symptoms,causes,diagnosis,repair,severity,verified,source_id,component,component_location,vcds_parameters,expected_values,test_path,replacement_steps,confidence,module_hint) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (code,) + values)


def install(con):
    _ensure_columns(con)
    src = _source(con)
    detailed = [
        ("P242F","DPF - acumulare/restricție cenușă","01-Engine","DPF încărcat cu cenușă; senzor presiune/furtune; utilizare/regen nereușită.","Citește masa funingine/cenușă, presiunea diferențială și temperaturile; verifică furtunele înainte de a condamna DPF.","Remediază senzor/furtune sau cauza regenerărilor eșuate; curăță/înlocuiește DPF când încărcarea fizică o cere.","DPF + senzor presiune diferențială","Pe evacuare; senzorul este în compartiment motor, legat prin furtune la DPF (poziția exactă variază).","DPF soot/ash load; differential pressure; EGT","Valorile trebuie interpretate după ECU/motor și condiția de test; nu folosi un prag universal.","[01-Engine] > Advanced Measuring Values; Basic Settings doar dacă ECU oferă procedura relevantă.","După piesă: verifică learned/adaptation values numai conform ECU; șterge DTC și rescanare."),
        ("P2BA6","SCR NOx Catalyst Performance / NOx exceedance","01-Engine","NOx ridicat; dozare AdBlue; senzor NOx; SCR; temperatură evacuare; calitate agent reducător.","Verifică toate DTC-urile SCR/NOx, nivel/calitate AdBlue, senzori NOx și parametrii de dozare înainte de înlocuire.","Repară cauza primară; înlocuiește senzor/dozator/SCR numai după confirmare.","Sistem SCR/AdBlue/NOx","Evacuare + rezervor/modul dozare; amplasarea senzorilor diferă pe platformă.","NOx upstream/downstream; reductant pressure/level; EGT; SCR status","Compară plauzibilitatea și valorile specific ECU; nu există o valoare unică pentru toate VAG.","[01-Engine] > Fault Codes > Advanced Measuring Values > Basic Settings dacă este disponibil test SCR.","După înlocuire pot fi necesare adaptation/reset learned values specifice ECU; rescanare."),
        ("P189A","Clutch 1 clearance too small","02-Transmission","Uzură/poziție ambreiaj; mecatronică; adaptare; problemă mecanică transmisie.","Identifică exact cutia; citește valori ambreiaj și toate DTC-urile transmisiei; nu aplica Basic Settings de la alt tip DSG.","Repară ambreiajul/mecatronica după măsurători și efectuează Basic Settings specific transmisiei.","Ambreiaj 1 / mecatronică DSG","În carcasa transmisiei.","Clutch adaptation/position values; transmission temperature","Specifice DQ200/DQ250/DQ500/0B5; folosește label/UDS controller.","[02-Transmission] > Advanced Measuring Values > Basic Settings conform tipului exact de cutie.","După reparație: Basic Settings și test drive de adaptare specific cutiei."),
        ("B2000","Control Module defective","Modulul care raportează DTC","Defect intern controler; alimentare/tensiune; intervenție anterioară, în funcție de modul.","Confirmă modulul, alimentările și alte DTC-uri. La Airbag nu încerca reparații improvizate ale controlerului.","Înlocuiește controlerul când defectul intern este confirmat; pentru Airbag folosește piesă corespunzătoare și procedura de codare aplicabilă.","Control module","Depinde de adresa modulului din Auto-Scan.","Supply voltage; terminal status; internal fault status","Alimentarea trebuie să fie stabilă și conform schemei vehiculului.","Deschide modulul care a raportat DTC > Fault Codes; apoi Coding/Adaptation doar dacă procedura de înlocuire o cere.","După înlocuire: coding/adaptation/component protection unde se aplică; rescanare."),
        ("U1122","Databus implausible/missing message","19-Gateway / modul raportor","Mesaj CAN lipsă/implauzibil; modul sursă cu DTC; cablaj/conector; tensiune.","Folosește Auto-Scan complet pentru a identifica modulul sursă; verifică Gateway installation list și DTC-urile din modulul indicat.","Repară mai întâi modulul/cablajul sursă, apoi șterge erorile secundare.","CAN data bus","Rețea CAN între module; traseul exact depinde de platformă.","Communication status; terminal voltage; installation list","Toate modulele configurate trebuie să comunice stabil; caută erori multiple de tip No Communication.","[19-CAN Gateway] > Fault Codes / Installation List; apoi modulul sursă.","După reparație: rescanare completă și verifică dacă DTC-ul secundar revine."),
        ("U102F","Databus communication fault","19-Gateway / modul raportor","Comunicare rețea; modul offline; alimentare; CAN/LIN în funcție de context.","Identifică modulul și contextul exact din textul Auto-Scan; verifică alimentare, masă, conectori și erorile Gateway.","Repară alimentarea/rețeaua sau modulul sursă; nu înlocui Gateway doar din acest cod.","Rețea date / control module","Depinde de modulul menționat în DTC.","Communication status; supply voltage","Confirmă pe schema și controllerul exact.","[19-CAN Gateway] + modulul menționat > Fault Codes / Advanced Measuring Values.","Rescanare completă după reparație."),
        ("U1052","Databus communication fault","19-Gateway / modul raportor","Mesaj absent/implauzibil; modul nealimentat; rețea; coding/configurație.","Corelează toate DTC-urile din scan și găsește modulul primar care nu comunică.","Repară alimentare/cablaj/configurație; recodează doar dacă Auto-Scan/coding original confirmă necesitatea.","CAN/LIN network","În rețeaua modulului implicat.","Gateway installation list; module communication; voltage","Fără prag universal; urmărește starea comunicării și alimentarea.","[19-CAN Gateway] > Installation List/Fault Codes; apoi controllerul țintă.","După reparație: clear DTC + Auto-Scan nou."),
        ("P2753","Transmission fluid cooler control circuit","02-Transmission / 01-Engine după platformă","Valvă/pompă răcire; circuit electric; conector; problemă termică.","Confirmă modulul raportor și textul exact; verifică temperaturi transmisie și activarea actuatorului dacă controllerul oferă Output Test.","Repară circuitul/actuatorul; verifică nivelul și temperatura uleiului conform procedurii cutiei.","Circuit răcire transmisie","Pe circuitul de răcire al transmisiei; poziția diferă după cutie.","Transmission fluid temperature; actuator command/status","Specifice transmisiei.","[02-Transmission] > Advanced Measuring Values / Output Tests dacă disponibil.","După piesă: verificare temperatură, scurgeri, DTC și test drive."),
    ]
    for r in detailed:
        _put(con, src, *r)

    # Broad fallback coverage. These rows intentionally avoid invented channel/byte values.
    families = {
        "Engine / senzori și combustie": ["P0030","P0087","P0100","P0101","P0102","P0103","P0104","P0116","P0117","P0118","P0130","P0131","P0134","P0140","P0141","P0171","P0172","P0234","P0236","P0299","P0300","P0301","P0302","P0303","P0304","P0401","P0420","P0671","P0672","P0673","P0674","P0675","P130A","P1558","P164B","P2002","P2015","P2122","P219C","P219D","P219E","P219F","P2263","P2431","P2432","P2433","P2453","P246E","P24D8","P2533","P2556","P2563","P261A","P3053","P307A","P310B","P310C","P320C","P334B"],
        "DSG / transmisie": ["P1757","P1888","P189C","P2755","01315","01087"],
        "ABS / ESP / Steering": ["00778","01130","01316","01486","01826","C1011","C10AC"],
        "Airbag / SRS": ["00588","00589","00590","01221","01222","01738","01739","B10B3"],
        "Gateway / Comfort / BCM / HVAC / Multimedia": ["00003","00446","00603","00668","00818","00819","00862","01044","01274","01304","01314","01329","01990","03020","03041","03396"],
    }
    for system, codes in families.items():
        for code in codes:
            exists = con.execute("SELECT 1 FROM dtcs WHERE UPPER(code)=UPPER(?)", (code,)).fetchone()
            if exists:
                continue
            _put(con, src, code, f"DTC {code} - analiză ghidată", system,
                 "Cauza exactă depinde de textul complet al DTC-ului, modul, Freeze Frame și configurația vehiculului.",
                 "1) Salvează Auto-Scan. 2) Confirmă modulul care raportează codul. 3) Verifică toate DTC-urile din acel modul și modulele sursă. 4) Verifică alimentare/masă/cablaj și live data relevante. 5) Folosește Output Test/Basic Settings numai dacă acel controller le oferă.",
                 "Remediază cauza confirmată de măsurători. Nu schimba o piesă numai după cod; repetă Auto-Scan după intervenție.",
                 "Componentă dependentă de DTC/modul", "Vezi locația specifică modelului/motorului în manualul de reparație.",
                 "Fault status; frequency; mileage; freeze frame; live data relevante modulului", "Compară cu specificația controllerului și condițiile de test; fără prag universal.",
                 "Select > modulul raportor > Fault Codes > Advanced Measuring Values; Output Tests/Basic Settings dacă sunt disponibile.",
                 "După reparație: coding/adaptation/basic setting doar dacă piesa și controllerul o cer; clear DTC + rescanare.")
    con.commit()
