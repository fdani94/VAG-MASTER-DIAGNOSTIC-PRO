"""Comfort/Doors/Gateway/Multimedia procedure expansion for VAG 1996-2024.
Conservative applicability: exact channels/coding must match controller/platform.
"""

def _ensure(con):
    cols={r[1] for r in con.execute('PRAGMA table_info(procedures)').fetchall()}
    return cols


def _add(con,title,category,models,years,module,path,steps,notes):
    cols=_ensure(con)
    data={"title":title,"category":category,"models":models,"years":years,"module":module,
          "vcds_path":path,"steps":steps,"notes":notes}
    use=[k for k in data if k in cols]
    if not use: return
    q='INSERT INTO procedures ('+','.join(use)+') VALUES ('+','.join('?' for _ in use)+')'
    try: con.execute(q,[data[k] for k in use])
    except Exception: pass


def install(con):
    rows=[
      ("Telecomenzi - stergere si asociere (Comfort clasic)","Comfort / Remote",
       "Golf 1K; Jetta 1K; Passat 3C; Octavia 1Z; Leon 1P; platforme cu J393 compatibil","2003-2012","46-Central Convenience / J393",
       "46-Central Convenience -> Adaptation -> Ch 000 clear; Ch 001 matching",
       "Salveaza Auto-Scan. Ai toate telecomenzile prezente. Ch000 sterge pozitiile memorate; Ch001 porneste asocierea, apoi confirma fiecare telecomanda conform procedurii controllerului.",
       "Nu confunda asocierea telecomenzii cu adaptarea imobilizatorului/cheii. KESSY poate urma alta procedura."),
      ("Auto-Lock / Auto-Unlock / confirmari / Comfort", "Comfort / Coding",
       "Golf 1K; Passat 3C si platforme Comfort compatibile","2003-2012","46-Central Convenience / J393",
       "46 -> Adaptation / Long Coding Helper",
       "Citeste valoarea originala. Activeaza numai canalul/functia existenta pe controller: selective locking, auto-lock, auto-unlock, confirmari, comfort remote. Testeaza dupa salvare.",
       "Canalele difera dupa controller; nu aplica numere de canal universal pe MQB/UDS."),
      ("BCM PQ35 - telecomenzi si Factory Mode", "Comfort / BCM",
       "Golf 6 5K; Jetta; Touran; Tiguan; Octavia/Leon compatibile BCM PQ35","2009-2015","09-Central Electronics / J519",
       "09-Central Electronics -> Adaptation / Long Coding",
       "Pe BCM PQ35 functiile vechiului 46 sunt integrate in 09. Deblocheaza usile, salveaza Auto-Scan/coding, apoi foloseste canalele documentate pentru remote matching/factory mode si Long Coding Helper pentru echipare.",
       "Absenta unui 46 separat poate fi normala. Nu declara modul lipsa doar din acest motiv."),
      ("Modul usa inlocuit - coding si verificare", "Doors / Replacement",
       "VAG cu module 42/52/62/72 sau slave doors","2003-2024","42/52/62/72 Door Electronics",
       "Auto-Scan -> modul usa -> Coding/Long Coding -> Adaptation/Basic Settings daca exista",
       "Inainte de demontare salveaza Auto-Scan si coding. Monteaza piesa compatibila, transfera codingul documentat, sterge DTC, reinvata limitele geamurilor daca este necesar si verifica inchidere, oglinda, geam, iluminare si safe-lock.",
       "Pe generatii noi usile spate pot fi slave ale 42/52; lipsa adreselor 62/72 nu inseamna automat defect."),
      ("Geam electric - reinvatare limite", "Doors / Windows",
       "VAG cu one-touch/anti-pinch","1998-2024","Door Electronics / Window regulator",
       "Procedura controllerului + comenzi geam; VCDS Fault Codes/Measuring Values unde sunt disponibile",
       "Dupa pierdere alimentare sau inlocuire regulator/modul, verifica DTC si starea contactelor. Reinvata capetele de cursa conform procedurii modelului, apoi testeaza one-touch si anti-pinch.",
       "Secventa fizica exacta variaza; aplica numai procedura documentata pentru model/controller."),
      ("CAN Gateway - Installation List", "Gateway / Configuration",
       "VAG CAN/UDS cu J533 Installation List","2004-2024","19-CAN Gateway / J533",
       "19-CAN Gateway -> Installation List",
       "Salveaza Auto-Scan. Compara lista modulelor instalate cu echiparea reala. Bifeaza/debifeaza numai module montate/eliminate legitim, scrie lista, ciclu contact si Auto-Scan final.",
       "Restore original value din ecran nu inseamna restaurarea configuratiei de fabrica; salveaza valorile inainte."),
      ("Gateway replacement - transfer Installation List", "Gateway / Replacement",
       "VAG CAN/UDS","2004-2024","19-CAN Gateway / J533",
       "19 -> Installation List / Direct coding unde este suportat",
       "Salveaza Auto-Scan si Installation List inainte. Dupa inlocuire transfera configuratia numai daca piesa este compatibila; verifica toate modulele asteptate si elimina DTC-urile de configuratie dupa confirmare.",
       "Pe unele UDS/CAN exista Direct coding pentru transfer; pentru retrofituri foloseste lista de instalare conform documentatiei."),
      ("RNS510 retrofit - Gateway + Navigation coding", "Multimedia / Retrofit",
       "Golf 5/6; Octavia 1Z; Passat 3C si platforme compatibile RNS510","2005-2015","19-CAN Gateway + 37-Navigation/56-Radio",
       "19 -> Installation List; 37-Navigation -> Coding/Long Coding Helper",
       "Verifica part number/software Gateway pentru compatibilitate si consum parazit. Inregistreaza 37 Navigation si, dupa configuratie, 56 Radio; codeaza unitatea conform echiparii si efectueaza Auto-Scan final.",
       "Gateway-uri vechi incompatibile pot ramane active dupa oprirea contactului si descarca bateria. Nu presupune compatibilitate doar fiindca mufa se potriveste."),
      ("RNS310 retrofit - Gateway + Navigation coding", "Multimedia / Retrofit",
       "Golf/Passat/Octavia si platforme compatibile RNS310","2008-2015","19-CAN Gateway + 37-Navigation",
       "19 -> Installation List; 37-Navigation -> Coding/Long Coding Helper",
       "Confirma Gateway compatibil, adauga 37 Navigation in Installation List, codeaza unitatea dupa echipare si verifica DTC 01042/control module not coded.",
       "Pe RNS310 diagnosticul principal este la 37; existenta intrarii 56 in lista nu inseamna ca unitatea comunica la 56."),
      ("Radio/Navigation replacement - backup si verificare", "Multimedia / Replacement",
       "VAG Radio/Navigation/MIB","2004-2024","5F/37/56 + 19 Gateway",
       "Auto-Scan -> 19 Installation List -> 5F/37/56 Coding/Adaptation",
       "Salveaza Auto-Scan, part number, software, coding si adaptari disponibile. Dupa montaj verifica Installation List, coding, DTC, sunet, antene, display, comenzi volan si comunicarea cu clusterul.",
       "Pe generatii moderne pot exista Component Protection/SFD/parametrizare online; VCDS nu trebuie prezentat ca metoda de ocolire."),
    ]
    for r in rows: _add(con,*r)
    con.commit()
