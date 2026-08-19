from datetime import datetime


def _source(con, title, url, notes=""):
    r = con.execute("SELECT id FROM sources WHERE url=?", (url,)).fetchone()
    if r:
        return r[0]
    cur = con.execute("INSERT INTO sources(title,publisher,url,accessed,source_type,notes) VALUES(?,?,?,?,?,?)",
                      (title,"Ross-Tech",url,datetime.now().date().isoformat(),"Oficial",notes))
    return cur.lastrowid


def _proc(con, row):
    r = con.execute("SELECT id FROM procedure_library WHERE title=?", (row[0],)).fetchone()
    if r:
        return r[0]
    cur = con.execute("""INSERT INTO procedure_library(title,category,module_address,vcds_path,purpose,prerequisites,steps,success_criteria,warnings,applicability_rule,verified,source_id)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""", row)
    return cur.lastrowid


def _map(con, pid, where_sql="1=1", args=(), applicability="Condițional", notes="Confirmă Auto-Scan, part number, protocolul și codul motor înainte de aplicare."):
    for r in con.execute("SELECT id FROM generations WHERE " + where_sql, args):
        con.execute("INSERT OR IGNORE INTO vehicle_procedures(generation_id,procedure_id,applicability,notes) VALUES(?,?,?,?)",
                    (r[0],pid,applicability,notes))


def _add_col(con, table, col, definition):
    cols={r[1] for r in con.execute(f"PRAGMA table_info({table})")}
    if col not in cols:
        con.execute(f"ALTER TABLE {table} ADD COLUMN {col} {definition}")


def _dtc(con, code, title, description, symptoms, causes, diagnosis, repair, severity, source_id, component, location, test_path, params, expected, replace_steps):
    r=con.execute("SELECT id FROM dtcs WHERE code=?",(code,)).fetchone()
    values=(title,description,symptoms,causes,diagnosis,repair,severity,1,source_id,component,location,test_path,params,expected,replace_steps,code)
    if r:
        con.execute("""UPDATE dtcs SET title=?,description=?,symptoms=?,causes=?,diagnosis=?,repair=?,severity=?,verified=?,source_id=?,component=?,component_location=?,test_path=?,vcds_parameters=?,expected_values=?,replacement_steps=? WHERE code=?""",values)
    else:
        con.execute("""INSERT INTO dtcs(title,description,symptoms,causes,diagnosis,repair,severity,verified,source_id,component,component_location,test_path,vcds_parameters,expected_values,replacement_steps,code)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",values)


def install(con):
    _add_col(con,"engines","powertrain_type","TEXT DEFAULT ''")
    _add_col(con,"dtcs","vcds_parameters","TEXT DEFAULT ''")
    _add_col(con,"dtcs","expected_values","TEXT DEFAULT ''")
    _add_col(con,"dtcs","replacement_steps","TEXT DEFAULT ''")

    # Normalize legacy engine fuel labels into clear user-facing categories.
    con.execute("UPDATE engines SET powertrain_type='Diesel' WHERE lower(fuel) LIKE '%diesel%' OR lower(fuel) LIKE '%tdi%'")
    con.execute("UPDATE engines SET powertrain_type='Benzină' WHERE lower(fuel) LIKE '%benzin%' OR lower(fuel) LIKE '%petrol%' OR lower(fuel) LIKE '%fsi%' OR lower(fuel) LIKE '%tsi%'")
    con.execute("UPDATE engines SET powertrain_type='Hibrid' WHERE lower(fuel) LIKE '%hybrid%' OR lower(fuel) LIKE '%hibrid%' OR lower(fuel) LIKE '%phev%'")
    con.execute("UPDATE engines SET powertrain_type='Electric' WHERE lower(fuel) LIKE '%electric%' OR lower(fuel) LIKE '%bev%'")

    src_bat=_source(con,"Battery Replacement","https://wiki.ross-tech.com/wiki/index.php/Battery_Replacement")
    src_tba=_source(con,"Throttle Body Alignment","https://wiki.ross-tech.com/wiki/index.php/Throttle_Body_Alignment_%28TBA%29")
    src_level=_source(con,"Suspension Level Control Calibration non-UDS","https://wiki.ross-tech.com/wiki/index.php/Suspension_Level_Control_Calibration_%28non-UDS%29")
    src_level_uds=_source(con,"Level Control UDS LUFE-DAEMPFER","https://wiki.ross-tech.com/wiki/index.php/Level_Control%2C_UDS_%28LUFE-DAEMPFER%29")
    src_sri=_source(con,"SRI Reset Procedure","https://wiki.ross-tech.com/wiki/index.php/SRI_Reset_Procedure")
    src_p0087=_source(con,"P0087 Fuel Rail Pressure Too Low","https://wiki.ross-tech.com/wiki/index.php/16471/P0087/000135")
    src_p0088=_source(con,"P0088 Fuel Rail Pressure Too High","https://wiki.ross-tech.com/wiki/index.php/P0088")
    src_p2002=_source(con,"P2002 DPF Malfunction","https://wiki.ross-tech.com/wiki/index.php/18434/P2002/008194")
    src_p2463=_source(con,"P2463 DPF Excessive Soot","https://wiki.ross-tech.com/wiki/index.php/18895/P2463/009315")
    src_p2015=_source(con,"P2015 Intake Manifold Flap","https://wiki.ross-tech.com/wiki/index.php/18447/P2015/008213")
    src_p0263=_source(con,"P0263 Injector Contribution","https://wiki.ross-tech.com/wiki/index.php/P0263")

    rows=[
      ("Baterie - 19 CAN Gateway Long Adaptation Channel 004","Adaptări","19","[19-CAN Gateway] > [Long Adaptation-0A] > Channel 004",
       "Înregistrează o baterie nouă la Gateway-urile CAN cu BEM/J367.",
       "Baterie nouă instalată; contact ON; motor OFF; notează Part Number 11 caractere, Vendor 3 caractere și Serial 10 caractere.",
       "1) 19-CAN Gateway. 2) Long Adaptation-0A. 3) Channel 004 > Read. 4) Add to Log pentru valoarea originală. 5) Introdu noua valoare în formatul exact NNNNNNNNNNN XXX ZZZZZZZZZZ (26 caractere incluzând spațiile). 6) Test. 7) Save. 8) Done, Go Back. 9) Verifică MVB 017/018/019/020.",
       "Noua baterie este acceptată și datele BEM sunt actualizate.",
       "Nu inventa date de baterie. Unele baterii aftermarket nu au toate câmpurile necesare.",
       "Gateway CAN cu BEM",1,src_bat),
      ("Baterie - 19 CAN Gateway UDS Adaptation","Adaptări","19","[19-CAN Gateway] > [Adaptation-10] > Battery adaptation",
       "Înregistrează bateria nouă pe Gateway UDS.",
       "Contact ON; motor OFF; baterie nouă instalată; salvează valorile originale.",
       "1) 19-CAN Gateway. 2) Adaptation-10. 3) Caută Battery adaptation. 4) Completează canalele disponibile pentru capacitate/rated battery capacity, manufacturer/vendor, serial number și technology dacă sunt prezente. 5) Salvează fiecare valoare. 6) Rescanează Gateway-ul.",
       "Datele bateriei sunt salvate fără DTC de adaptare.",
       "Denumirile IDE/MAS diferă după software. Folosește exact canalele afișate de controller.",
       "Gateway UDS",1,src_bat),
      ("Suspensie pneumatică non-UDS - calibrare 4 colțuri","Calibrări","34","[34-Level Control] > [Security Access-16] 31564 > [Adaptation-10] Channels 01-05",
       "Calibrează înălțimea suspensiei pneumatice non-UDS.",
       "Suprafață plană; motor la ralanti; frână de parcare; uși/capotă/portbagaj închise; ruletă metrică.",
       "1) Măsoară vertical centrul roții până la muchia aripii. 2) 34-Level Control. 3) Security Access 31564 (dacă nu merge, Login-11/Coding II-11 unde este documentat). 4) Adaptation-10. 5) Channel 01 = față stânga, Read, așteaptă Value, introdu mm, Test, Save. 6) Channel 02 = față dreapta. 7) Channel 03 = spate stânga. 8) Channel 04 = spate dreapta. 9) Channel 05 > New Value 1 > Test > Save. 10) Done, Go Back și verifică DTC.",
       "Fără DTC de calibrare și înălțime corectă pe toate colțurile.",
       "Doar sisteme non-UDS compatibile. Nu aplica pe LUFE-DAEMPFER UDS.",
       "A6/A8/Q7/Phaeton/Touareg și sisteme non-UDS compatibile",1,src_level),
      ("Suspensie pneumatică UDS LUFE-DAEMPFER - readaptare nivel","Calibrări","34","[34-Level Control] > [Security Access-16] 20103 > [Basic Settings-04]",
       "Readaptează suspensia UDS la poziția implicită.",
       "Contact ON; motor OFF; redresor conectat; suprafață plană; rezervor >=60%; fără persoane/încărcătură; uși închise; fără DTC în 34 exceptând basic setting lipsă/incorect.",
       "1) 34-Level Control. 2) Security Access-16 > 20103. 3) Basic Settings-04. 4) Rulează IDE03762 Calibrate level control până la Finished Correctly, apoi Stop. 5) Rulează IDE03751 Activate level control până la Finished Correctly. 6) Go Back și rescanează.",
       "Ambele Basic Settings se termină Finished Correctly.",
       "NU selecta IDE01475 Resetting of all adaptations: poate genera B2013 No End-of-Line Programming.",
       "LUFE-DAEMPFER UDS",1,src_level_uds),
      ("Clapetă accelerație - cablu Group 098/001","Calibrări","01","[01-Engine] > [Basic Settings-04] > Group 098 (unele SIMOS/Marelli Group 001)",
       "Reînvață poziția clapetei motorizate cu cablu fără ISV.",
       "Fără DTC motor; baterie >=11.5V; clapetă curată; coolant 5-95C; contact ON; motor OFF; nu atinge accelerația.",
       "1) 01-Engine. 2) Basic Settings-04. 3) Group 098 (sau 001 doar unde ECU îl cere). 4) Go. 5) Așteaptă ADP RUN și apoi finalizarea; lasă aproximativ 30 secunde. 6) Switch to Meas. Blocks. 7) Done.",
       "ADP OK/finalizare fără Error.",
       "Nu se aplică motoarelor cu ISV și nu se aplică TDI vechi fără clapetă motorizată.",
       "Benzină cable-throttle compatibilă",1,src_tba),
      ("Clapetă accelerație - DBW Group 060","Calibrări","01","[01-Engine] > [Basic Settings-04] > Group 060",
       "Reînvață clapeta Drive-by-Wire pe KW-1281/KWP-2000/CAN compatibil.",
       "Fără DTC motor; baterie >=11.5V; clapetă curată; coolant 5-95C; contact ON; motor OFF; accelerația neatinsă.",
       "1) 01-Engine. 2) Basic Settings-04. 3) Group 060 > Go. 4) Pe KWP/CAN apasă ON/OFF/Next dacă este necesar pentru Basic Settings ON. 5) Așteaptă ADP RUN și finalizarea circa 30 secunde. 6) Oprește Basic Settings și Done, Go Back.",
       "ADP OK și fără Error.",
       "Dacă ai șters erori, fă cycle ignition înainte de TBA.",
       "Benzină DBW compatibilă",1,src_tba),
      ("Clapetă accelerație UDS - IDE00754","Calibrări","01","[01-Engine] > [Basic Settings-04] > IDE00754 Checking throttle valve adaptation",
       "Reînvață clapeta pe ECU UDS/ODX.",
       "Coolant cald; contact ON; motor OFF; accelerația neatinsă; fără DTC relevante.",
       "1) 01-Engine. 2) Basic Settings-04. 3) Selectează IDE00754-Checking throttle valve adaptation sau varianta de Throttle Valve Adaptation din listă. 4) Go. 5) Așteaptă Finished Correctly. 6) Stop. 7) Lasă circa 30 secunde, apoi Done, Go Back.",
       "Finished Correctly.",
       "UDS nu folosește grupuri numerice clasice pentru această funcție.",
       "Benzină UDS compatibilă",1,src_tba),
      ("Reset service - SRI Reset automat","Resetări","17","[Applications] > [SRI Reset]",
       "Resetează reminderul de service folosind operația corectă pentru cluster/regiune.",
       "Revizia efectuată; contact ON; tensiune stabilă.",
       "1) Applications. 2) SRI Reset. 3) Așteaptă citirea automată a canalelor de service. 4) În Operation selectează operația corectă, de ex. Service Reset/Mileage based Service Reset după vehicul și regiune. 5) Perform SRI. 6) Așteaptă confirmarea salvării. 7) Ciclează contactul și verifică bordul.",
       "Reminderul de service dispare și intervalele sunt actualizate.",
       "La multe Audi 2008+ Simple/Basic Service Reset poate să nu fie operația corectă; folosește opțiunea specifică regiunii/vehiculului.",
       "Cluster compatibil SRI",1,src_sri),
    ]
    for row in rows:
        pid=_proc(con,row)
        _map(con,pid)

    _dtc(con,"P0087","Fuel Rail/System Pressure: Too Low","Presiune combustibil pe rampă prea mică.","Pierdere de putere; pornire grea sau oprire în sarcină.","Presiune joasă insuficientă; conductă strangulată; filtru înfundat; pompă debit mic; injector cu retur/pierdere; uzură mecanică la HPFP/cam follower pe unele TFSI.","1) 01-Engine > Advanced Measuring Values: rail pressure specified/actual. 2) Verifică alimentarea joasă și filtrul. 3) Verifică pierderi și retur injectoare unde procedura o permite. 4) La 2.0 TFSI inspectează hardware HPFP/cam follower conform motorului.","Repară cauza confirmată: filtru/conducte/pompă/injector/HPFP. Nu schimba pompa de înaltă doar pe baza codului.","Ridicat",src_p0087,"Sistem alimentare: pompă joasă, filtru, pompă înaltă, rampă, injectoare.","Filtrul/pompa joasă sunt în zona rezervorului sau sub mașină după model; pompa de înaltă este pe motor; rampa este pe chiulasă/admisie.","01-Engine > Advanced Measuring Values > Fuel/Rail Pressure specified & actual","Rail pressure specified; Rail pressure actual; low fuel pressure dacă ECU îl expune.","Actual trebuie să urmărească cererea; abaterea acceptabilă este ECU/motor-dependent, deci se compară cu specificația controllerului.","Depresurizează sistemul conform manualului de reparații înainte de desfacerea circuitului de înaltă presiune. Înlocuiește doar componenta confirmată și verifică etanșeitatea." )
    _dtc(con,"P0088","Fuel Rail/System Pressure: Too High","Presiunea pe rampă este prea mare.","MIL; uneori zgomot ascuțit la ralanti.","G247 rail pressure sensor; N276 regulator; N290 metering valve; alimentare/cablaj; la unele 3.6 benzină poate exista problemă de distribuție.","1) Advanced Measuring Values pentru rail pressure specified/actual. 2) Verifică G247 și cablaj. 3) Verifică alimentarea N276/N290. 4) Compară comportamentul cerut/real înainte de înlocuire.","Repară senzorul/cablajul/regulatorul confirmat. Verifică presiunea după reparație.","Ridicat",src_p0088,"G247, N276, N290 și sistemul de rampă.","Pe motor: senzorul este pe rampă; N276/N290 sunt pe sistemul de înaltă presiune în funcție de motor.","01-Engine > Advanced Measuring Values > Rail pressure specified/actual","Rail pressure specified; Rail pressure actual; metering/regulator duty dacă este disponibil.","Actual trebuie să urmărească cererea fără suprapresiune persistentă.","Circuitul este de înaltă presiune; urmează procedura OEM de depresurizare și cuplurile de strângere." )
    _dtc(con,"P2002","Particle Filter Bank 1: Malfunction","Eficiența DPF sub prag.","MIL/DPF; regenerări dese.","G450 defect; DPF încărcat/defect; problemă de regenerare.","1) Citește G450/differential pressure și soot/ash load dacă ECU le expune. 2) Verifică furtunurile G450. 3) Verifică DTC de temperatură/ardere. 4) Regenerare numai dacă încărcarea și condițiile sunt în limitele procedurii.","Înlocuiește G450 dacă este confirmat; regenerează/curăță/înlocuiește DPF conform gradului de încărcare și procedurii OEM.","Ridicat",src_p2002,"DPF și senzor diferențial G450.","DPF este pe evacuare; G450 este conectat prin două conducte/furtunuri la evacuare. La unele CBEA/CJAA G450 este în zona din spatele bușonului de ulei.","01-Engine > Advanced Measuring Values > DPF differential pressure / soot mass / ash load / exhaust temperatures","DPF differential pressure; soot mass calculated/measured; exhaust temperature sensors.","Valorile exacte depind de ECU și de condiția de test; se urmăresc plauzibilitatea și trendul înainte/după regenerare.","Lasă evacuarea să se răcească înainte de demontare. După înlocuire, execută adaptarea/resetul DPF/senzorului doar dacă procedura controllerului o cere." )
    _dtc(con,"P2463","Diesel Particle Filter: Excessive Soot Accumulation","DPF are încărcare excesivă cu funingine.","MIL/DPF; putere limitată.","Regenerări întrerupte; DPF plin; cauză de producere excesivă a funinginii.","Verifică soot load, differential pressure, temperaturile evacuării și DTC-urile cauză. Nu forța regenerarea peste limitele permise de ECU/procedură.","Remediază cauza regenerării eșuate; execută Emergency Regeneration numai în condiții permise; înlocuiește DPF dacă nu mai poate fi regenerat în siguranță.","Critic",src_p2463,"DPF, G450 și senzori temperatură evacuare.","Pe traseul de evacuare, sub mașină sau aproape de motor după platformă.","01-Engine > Advanced Measuring Values > DPF soot load / differential pressure / exhaust temperatures","Soot load calculated/measured; differential pressure; EGT pre/post DPF.","Trebuie să fie în limitele procedurii specifice înainte de regenerare.","Nu demonta fierbinte și nu iniția regenerare forțată dacă ECU/procedura o interzice." )
    _dtc(con,"P2015","Intake Manifold Flap Position Sensor: Implausible Signal","Poziția clapetelor galeriei nu este plauzibilă.","MIL; pierdere de putere.","Clapete galerie blocate; motor V157 defect/blocat; G336; cablaj; software ECU.","1) Output Tests/Basic Settings pentru V157 dacă sunt disponibile. 2) Verifică poziția commanded/actual. 3) Inspectează brațele/mecanismul galeriei. 4) Verifică mufa/cablajul.","Repară mecanismul sau cablajul; înlocuiește V157/G336 ori galeria doar după confirmare. Pe unele motoare este necesară procedură specifică/actualizare software.","Mediu",src_p2015,"Galerie admisie, motor clapete V157, senzor G336.","Pe galeria de admisie; actuatorul este montat pe lateralul galeriei, poziția exactă diferă după motor.","01-Engine > Output Tests / Basic Settings / Advanced Measuring Values","Intake manifold flap position specified/actual; actuator status dacă este disponibil.","Poziția actuală trebuie să urmărească comanda fără blocare/implausibilitate.","Depresurizează/izolează sistemele conexe conform manualului. La unele motoare actuatorul și senzorul sunt parte din ansamblul galeriei." )
    _dtc(con,"P0263","Injector Cylinder 1: Contribution/Balance Fault","Contribuția cilindrului 1 este în afara limitelor.","MIL; ralanti neregulat; vibrații.","Injector neadaptat după înlocuire; injector defect; compresie scăzută; problemă mecanică; depuneri/senzor presiune glow plug pe unele CR TDI.","1) Verifică Injector Quantity Adjustment/IMA Adaptation. 2) Verifică correction/balance values dacă ECU le oferă. 3) Test retur injector unde este aplicabil. 4) Verifică compresia dacă injecția este corectă.","Codifică/adaptează injectorul nou unde este necesar; înlocuiește injectorul doar dacă este confirmat; repară problema mecanică dacă testele indică compresie.","Ridicat",src_p0263,"Injector cilindru 1 și sistemul de injecție.","Injectorul este în chiulasă, pe cilindrul 1 conform ordinii motorului; confirmă ordinea cilindrilor în documentația motorului.","01-Engine > Adaptation pentru IMA/IQA + Advanced Measuring Values pentru injector correction/balance","Injector quantity adjustment code; cylinder balance/correction values.","Valorile trebuie comparate cu limitele ECU/motorului; nu există o limită universală VAG valabilă tuturor motoarelor.","Curăță zona înainte de demontare, înlocuiește garniturile/șuruburile de unică folosință conform manualului și introdu codul IMA/IQA al injectorului nou dacă ECU cere." )
    con.commit()
