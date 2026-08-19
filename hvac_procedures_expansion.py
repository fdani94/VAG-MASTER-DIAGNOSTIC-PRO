"""HVAC / Climatronic procedures expansion for KID Diagnostic.
References Ross-Tech model-specific procedures; never assumes one universal Basic Setting.
"""

def _src(con,title,url):
    con.execute("INSERT OR IGNORE INTO sources(title,publisher,url,source_type,notes) VALUES(?,?,?,?,?)",(title,"Ross-Tech",url,"official/wiki","HVAC procedure reference"))
    r=con.execute("SELECT id FROM sources WHERE url=?",(url,)).fetchone(); return r[0] if r else None

def _ensure(con):
    cols={r[1] for r in con.execute("PRAGMA table_info(procedures)").fetchall()}
    for n,t in {"system":"TEXT","applicability":"TEXT","verification":"TEXT","warning":"TEXT","source_id":"INTEGER"}.items():
        if n not in cols: con.execute(f"ALTER TABLE procedures ADD COLUMN {n} {t}")

def _add(con,title,category,module,steps,app,verify,warn,src):
    row=con.execute("SELECT id FROM procedures WHERE title=? LIMIT 1",(title,)).fetchone()
    vals=(category,module,steps,"HVAC",app,verify,warn,src)
    if row:
        con.execute("UPDATE procedures SET category=?,module=?,steps=?,system=?,applicability=?,verification=?,warning=?,source_id=? WHERE id=?",vals+(row[0],))
    else:
        con.execute("INSERT INTO procedures(title,category,module,steps,system,applicability,verification,warning,source_id) VALUES(?,?,?,?,?,?,?,?,?)",(title,)+vals)

def install(con):
    _ensure(con)
    golf=_src(con,"VW Golf 5K Climatronic","https://wiki.ross-tech.com/wiki/index.php/VW_Golf_%285K%29_Climatronic")
    climatic=_src(con,"VW Golf 5K Climatic","https://wiki.ross-tech.com/wiki/index.php/VW_Golf_%285K%29_Climatic")
    a5=_src(con,"Audi A5 8T HVAC KLIMA 3 ZONEN","https://wiki.ross-tech.com/wiki/index.php/Audi_A5_%288T%29_Heating/Air_Conditioning_KLIMA_3_ZONEN")
    manual=_src(con,"VW Jetta AJ Manual HVAC","https://wiki.ross-tech.com/wiki/index.php/VW_Jetta_%28AJ/16%29_Manual_Heating/Air_Conditioning")

    _add(con,"Climatronic - adaptare capete cursa clapete (PQ35/5K)","Basic Settings","08 - Heating/Air Conditioning",
         "Salveaza Auto-Scan si DTC. Intra 08 -> Basic Settings-04 -> selecteaza Adapt flap end stops -> Go/Start. Asteapta finalizarea (~20 s pe controlerele documentate). Sterge DTC si verifica din nou toate clapetele.",
         "Climatronic J255 compatibil cu procedura 5K; necesar dupa inlocuire J255 sau motor(e) clapeta si util pentru autodiagnoza.",
         "Basic Setting trebuie sa termine corect; recirculare, distributie si temperatura trebuie sa raspunda fara DTC persistent.",
         "Nu presupune Group 001 pe orice HVAC. Pe UDS foloseste denumirea exacta oferita de controller.",golf)

    _add(con,"Climatic - adaptare capete cursa clapete UDS","Basic Settings","08 - Heating/Air Conditioning",
         "08 -> Basic Settings-04 -> IDE01546-ENG167462 Adapt flap end stops -> Go. Asteapta Finished Correctly (~20 s), apoi Stop si rescaneaza.",
         "J301/Climatic compatibil, inclusiv dupa inlocuirea motorului de clapeta sau a unitatii de comanda.",
         "Finished Correctly; DTC de basic setting nu revine.",
         "ID-ul exact poate varia cu dataset/ROD; selecteaza functia dupa nume daca ID-ul difera.",climatic)

    _add(con,"A/C compressor first run-in - Climatronic/Climatic","Basic Settings","08 - Heating/Air Conditioning",
         "Motor la ralanti; cutie P/N; nu opri contactul; efectueaza intai adaptarea clapetelor; ventilator habitaclu ON; gurile deschise; load management inactiv. 08 -> Basic Settings -> Compressor Run In / automatic start. Pe controlerele documentate asteapta aproximativ 120 s chiar daca apare completed devreme.",
         "Dupa inlocuire J255/J301 si, pe unele sisteme, dupa inlocuirea compresorului. Foloseste numai procedura specifica controllerului.",
         "LED A/C inceteaza sa clipeasca si DTC-ul aferent run-in se sterge; verifica racirea si DTC final.",
         "Nu rula daca exista probleme mecanice/frigorifice cunoscute sau daca procedura nu este oferita de controller.",golf)

    _add(con,"Audi 8T KLIMA 3 ZONEN - flap alignment","Basic Settings","08 - Auto HVAC (J255)",
         "08 -> Basic Settings-04 -> Group 001 -> Go -> ON/OFF/Next. Asteapta aproximativ 40 s pana apare Performed.",
         "Audi A5 8T si controlere KLIMA 3 ZONEN corespunzatoare paginii Ross-Tech; dupa motoare HVAC sau pentru autodiagnoza.",
         "Status Performed si lipsa DTC-urilor de pozitie/basic setting.",
         "Nu transfera Group 001 automat pe alte generatii HVAC.",a5)

    _add(con,"Audi 8T KLIMA 3 ZONEN - compressor run-in","Basic Settings","08 - Auto HVAC (J255)",
         "Cu motorul la ralanti, executa imediat inainte Group 001 flap alignment. Apoi Basic Settings Group 003 -> Go -> ON/OFF/Next; asteapta circa 120 s si finalizarea Performed.",
         "Dupa compresor inlocuit cu DTC 03023 sau dupa inlocuire J255, pe controlerele KLIMA 3 ZONEN documentate.",
         "Performed; LED A/C nu mai clipeste; DTC se sterge; compresorul functioneaza normal.",
         "Inlocuirea J255 poate declansa Component Protection; aceasta nu se elimina prin simplu coding VCDS.",a5)

    _add(con,"A/C nu raceste - diagnostic VCDS N280 / presiune / shut-off","Diagnostic","08 - Heating/Air Conditioning",
         "1) Auto-Scan complet. 2) 08 -> Fault Codes. 3) Advanced Measuring Values/MVB: refrigerant pressure, compressor shut-off condition, compressor current actual/specified, compressor speed/load, evaporator temp, outside temp, Terminal 30. 4) Daca exista 00898 verifica sigurante, cablaj/conector N280, N280 si Output Test daca este suportat. 5) Daca presiunea este neplauzibila, verifica senzorul/circuitul si sistemul frigorific cu echipament adecvat.",
         "Diagnostic general ghidat de parametrii disponibili in controller; valorile si denumirile difera dupa generatie.",
         "Shut-off condition trebuie sa explice de ce compresorul este oprit; actual/spec trebuie corelate. Dupa reparatie Clear DTC si test temperatura la guri.",
         "VCDS nu masoara cantitatea de agent frigorific si nu inlocuieste manometrele/statie A/C. Nu deschide circuitul frigorific fara echipament si calificare adecvate.",golf)

    _add(con,"Jetta/Beetle Manual HVAC - activare compresor dupa J301","Basic Settings","08 - Auto HVAC",
         "Seteaza blower pe treapta 1 sau 2; distributia pe Vent; temperatura complet Cold. Porneste motorul in P/N. Tine simultan AC + Defrost pana se aprind AC si recirculation. Opreste/reporneste contactul si verifica DTC + functionarea HVAC.",
         "VW Jetta AJ/16 si Beetle 5C/AT cu Manual Heating/Air Conditioning documentat; dupa J301 sau cand 00898-005 nu se sterge.",
         "00898-005 se sterge si sistemul A/C functioneaza corect.",
         "Aceasta procedura este specifica sistemului manual documentat si nu trebuie aplicata Climatronic-ului.",manual)
    con.commit()
