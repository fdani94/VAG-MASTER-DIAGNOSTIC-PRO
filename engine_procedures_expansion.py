"""Engine-family VCDS procedures for KID Diagnostic.
Procedures are deliberately conditional: exact ECU/engine-code documentation wins.
"""


def _source(con, title, url):
    con.execute("INSERT OR IGNORE INTO sources(title,publisher,url,source_type,notes) VALUES(?,?,?,?,?)",
                (title, "Ross-Tech", url, "official/wiki", "Engine procedure reference"))
    r = con.execute("SELECT id FROM sources WHERE url=?", (url,)).fetchone()
    return r[0] if r else None


def _proc(con, title, category, path, purpose, prereq, steps, success, warnings, rule, source_id):
    r = con.execute("SELECT id FROM procedure_library WHERE title=?", (title,)).fetchone()
    vals = (category, "01", path, purpose, prereq, steps, success, warnings, rule, 1, source_id)
    if r:
        con.execute("""UPDATE procedure_library SET category=?,module_address=?,vcds_path=?,purpose=?,prerequisites=?,steps=?,success_criteria=?,warnings=?,applicability_rule=?,verified=?,source_id=? WHERE id=?""", vals + (r[0],))
        return r[0]
    return con.execute("""INSERT INTO procedure_library(title,category,module_address,vcds_path,purpose,prerequisites,steps,success_criteria,warnings,applicability_rule,verified,source_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                       (title,) + vals).lastrowid


def install(con):
    s_common = _source(con, "Ross-Tech Common Procedures", "https://wiki.ross-tech.com/wiki/index.php/Common_Procedures")
    s_tdi = _source(con, "Ross-Tech TDI VCDS Info", "https://www.ross-tech.com/vag-com/cars/tdi.html")
    s_cr = _source(con, "Ross-Tech 2.0L CR TDI", "https://wiki.ross-tech.com/wiki/index.php/2.0L_CR_TDI")
    s_dpf = _source(con, "Ross-Tech DPF Emergency Regeneration", "https://wiki.ross-tech.com/wiki/index.php/Diesel_Particle_Filter_Emergency_Regeneration")
    s_ready = _source(con, "Ross-Tech Readiness Test UDS", "https://wiki.ross-tech.com/wiki/index.php/Readiness_Test_%28UDS_only%29")

    _proc(con, "VE TDI - verificare dinamica MAF si turbo", "Motor / Diesel / VE TDI",
          "01-Engine -> Measuring Blocks -> Group 003 (MAF) / Group 011 (boost) -> Log",
          "Diagnostic debit aer si control presiune turbo pe TDI-urile vechi unde aceste grupuri sunt documentate.",
          "Motor la temperatura; fara conditii nesigure; procedura trebuie confirmata pentru ECU/cod motor.",
          "MAF: logheaza Group 003 conform documentatiei motorului. Turbo: Group 011, log requested vs actual in sarcina. Interpreteaza abaterea, nu doar o valoare instantanee.",
          "Actual urmareste requested in limitele documentate pentru motor; fara abatere persistenta majora.",
          "Valorile istorice Ross-Tech sunt exemple pentru anumite TDI; nu le transforma in specificatie universala pentru toate motoarele.",
          "VE/EDC15 si alte TDI compatibile numai daca label/repair data confirma grupurile.", s_tdi)

    _proc(con, "VE TDI - TDI Timing Checker", "Motor / Diesel / VE TDI",
          "01-Engine -> Measuring Blocks/Basic Settings -> Group 000 (unele V6: Group 004) -> TDI Timing",
          "Verificare timing pompa de injectie pe VE TDI.",
          "Motor cald; Ross-Tech indica lichid de racire peste aproximativ 85 C pentru procedura istorica.",
          "Intra in grupul documentat, treci in Basic Settings si foloseste TDI Timing Checker; compara timing/fuel temperature cu graficul motorului.",
          "Punctul se afla in zona acceptata a graficului corespunzator motorului.",
          "NU se aplica PD, PPD sau CR TDI. Nu modifica mecanic timing-ul fara procedura de reparatie specifica.",
          "Doar VE TDI compatibil.", s_tdi)

    _proc(con, "PD/PPD/CR TDI - amorsare pompa combustibil", "Motor / Diesel / Alimentare combustibil",
          "01-Engine -> Basic Settings -> Fuel Pump / Transfer Fuel Pump (denumirea depinde de ECU)",
          "Amorsarea circuitului dupa interventii la sistemul de combustibil.",
          "Configuratia trebuie sa aiba functia documentata; baterie stabila; combustibil suficient.",
          "Selecteaza Basic Setting-ul disponibil pentru pompa si urmeaza indicatiile ECU/VCDS. Repeta numai conform procedurii motorului.",
          "Circuit amorsat, fara aer anormal/scurgeri, motorul porneste si nu apar DTC-uri de alimentare.",
          "CR TDI nu trebuie operat fara combustibil; dupa reparatii la sistemul de combustibil, amorsarea corecta este importanta.",
          "PD, PPD si CR TDI unde ECU ofera Basic Setting-ul.", s_common)

    _proc(con, "CR TDI - codare/calibrare injectoare IMA/ISA", "Motor / Diesel / Common Rail",
          "01-Engine -> Adaptation / Long Adaptation -> Injector correction/calibration values",
          "Introducerea valorilor individuale ale injectorului dupa inlocuire, pe sistemele care folosesc IMA/ISA.",
          "Identifica exact cod motor, ECU si formatul codului inscriptionat pe injector; salveaza Auto-Scan si valorile vechi.",
          "Alege canalul injectorului corespunzator cilindrului, introdu exact valoarea de calibrare documentata, Test/Save unde este disponibil; repeta numai pentru injectoarele schimbate si verifica DTC-urile/ralantiul.",
          "Valorile sunt acceptate de ECU, fara DTC de calibrare si functionare stabila dupa procedura.",
          "Nu copia coduri intre injectoare. Lungimea/formatul si canalele difera intre ECU-uri; pe UDS foloseste denumirile din lista, nu numere de canal presupuse.",
          "CR TDI cu functie IMA/ISA documentata.", s_cr)

    _proc(con, "DPF - diagnostic incarcare si regenerare conditionata", "Motor / Diesel / DPF",
          "01-Engine -> Measuring Values/MVB -> soot/load/temperatures -> Security Access/Basic Settings/Adaptation dupa ECU",
          "Evaluare DPF si regenerare de service numai cand incarcarea si conditiile permit.",
          "Verifica DTC-uri, combustibil, temperatura, soot/load si toate conditiile specifice familiei PD/PPD/CR CAN/CR UDS.",
          "Identifica familia motorului. Citeste soot mass/load si temperaturile. Daca valorile sunt sub limita documentata, foloseste exact rutina de regenerare disponibila pentru ECU si urmeaza instructiunile VCDS. Verifica valorile dupa regenerare.",
          "Regenerare finalizata si incarcarea scade; fara DTC-uri active care impiedica regenerarea.",
          "NU forta regenerarea peste limita documentata: Ross-Tech avertizeaza asupra riscului de incendiu/deteriorare. Procedurile si pragurile difera intre PD/PPD, CR CAN si UDS.",
          "Diesel cu DPF, numai dupa identificarea exacta a familiei/ECU.", s_dpf)

    _proc(con, "Benzina - diagnostic Fuel Trim", "Motor / Benzina / Fuel Trim",
          "01-Engine -> Measuring Blocks/Advanced Measuring Values -> fuel trim/lambda values",
          "Separarea orientativa a problemelor de amestec: vacuum/admisie, masurare aer, combustibil, lambda.",
          "Motor in closed loop si la temperatura; fara a presupune aceleasi grupuri pentru toate ECU-urile.",
          "Citeste valorile de fuel trim/lambda disponibile si compara comportamentul la ralanti cu cel la sarcina/rpm. Coreleaza cu MAF/MAP, presiune combustibil si DTC-uri.",
          "Corectiile revin spre zona normala documentata dupa reparatie si DTC-ul nu revine.",
          "Nu schimba sonda lambda doar pentru un trim mare; poate fi efectul unei prize false de aer sau al alimentarii.",
          "MPI/FSI/TSI/TFSI cu parametri de fuel trim disponibili.", s_common)

    _proc(con, "Benzina - Throttle Body Alignment", "Motor / Benzina / Clapeta",
          "01-Engine -> Basic Settings -> Throttle Body Alignment / Adaptation of throttle valve",
          "Reinvatarea clapetei dupa curatare/inlocuire sau pierderea adaptarilor, unde ECU o cere.",
          "Respecta procedura ECU; fara DTC-uri incompatibile; tensiune stabila. Ross-Tech documenteaza TBA ca procedura comuna, dar cu diferente intre ECU-uri.",
          "Selecteaza rutina TBA oferita de ECU/label, porneste Basic Setting-ul si asteapta finalizarea fara a actiona pedala daca procedura nu cere altceva.",
          "ECU raporteaza adaptare finalizata/OK si ralanti stabil.",
          "Nu presupune Group 060/098 universal; foloseste label-ul/denumirea Basic Setting-ului pentru ECU-ul concret.",
          "Motoare pe benzina si unele configuratii compatibile unde TBA este documentat.", s_common)

    _proc(con, "Benzina - diagnostic Misfire", "Motor / Benzina / Aprindere",
          "01-Engine -> Fault Codes -> Measuring Blocks/Advanced Measuring Values -> misfire counters",
          "Identificarea cilindrului si separarea aprinderii, injectorului, compresiei si amestecului.",
          "Motor in conditii sigure; salveaza Freeze Frame si nu sterge DTC-urile inainte de a nota contextul.",
          "Citeste contoarele misfire per cilindru si conditiile de aparitie. Verifica aprinderea, injectorul, compresia si cauzele de amestec in ordinea potrivita; mutarea controlata a bobinei/bujiei poate confirma doar daca procedura mecanica este sigura.",
          "Contorul nu mai creste anormal si DTC-ul nu revine dupa testul relevant.",
          "Misfire nu inseamna automat bobina defecta; evita inlocuirea de piese fara confirmare.",
          "MPI/FSI/TSI/TFSI unde ECU expune contoare misfire.", s_common)

    _proc(con, "UDS benzina - Readiness Automatic Test Sequence", "Motor / Benzina / UDS Readiness",
          "01-Engine -> Basic Settings -> Automatic test sequence/procedure -> Show Measuring Data",
          "Refacerea/testarea readiness dupa reparatii sau stergerea DTC-urilor pe ECU UDS compatibile.",
          "Motor pornit; consumatori electrici opriti; fara DTC-uri active; lichid racire cel putin 80 C; zona bine ventilata.",
          "Selecteaza Automatic test sequence. Afiseaza IDE00450, IDE00451, IDE00030, IDE00727, IDE00021 si IDE00025 daca ECU le ofera. Porneste rutina si urmeaza instructiunile ECU, inclusiv frana+acceleratie cand se cere.",
          "IDE00450 indica System OK/Finished correctly, iar pasii ramasi ajung la zero.",
          "Doar ECU benzina UDS care ofera rutina. Nu aplica procedura non-UDS. Gazele si temperaturile evacuarii impun ventilatie si distanta fata de materiale combustibile.",
          "ECU benzina UDS cu Automatic test sequence disponibil.", s_ready)

    con.commit()
