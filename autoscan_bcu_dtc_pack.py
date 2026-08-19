"""KID Diagnostic - Auto-Scan B/C/U diagnostic expansion.

Adds body/chassis/network DTC guidance. Entries may be official-context or
community/probable guidance; confidence is stored in verified/source fields.
"""


def _ensure_columns(con):
    cols = {r[1] for r in con.execute("PRAGMA table_info(dtcs)").fetchall()}
    additions = {
        "component": "TEXT", "component_location": "TEXT",
        "vcds_parameters": "TEXT", "expected_values": "TEXT",
        "test_path": "TEXT", "replacement_steps": "TEXT",
    }
    for name, typ in additions.items():
        if name not in cols:
            con.execute(f"ALTER TABLE dtcs ADD COLUMN {name} {typ}")


def _source(con, title, url, notes=""):
    con.execute("INSERT OR IGNORE INTO sources(title,publisher,url,source_type,notes) VALUES(?,?,?,?,?)",
                (title, "Ross-Tech", url, "official/wiki", notes))
    row = con.execute("SELECT id FROM sources WHERE url=?", (url,)).fetchone()
    return row[0] if row else None


def _upsert(con, code, title, desc, symptoms, causes, diagnosis, repair, severity,
            component, location, params, expected, path, replacement, source_id,
            verified=1):
    row = con.execute("SELECT id FROM dtcs WHERE UPPER(code)=UPPER(?) LIMIT 1", (code,)).fetchone()
    vals = (title, desc, symptoms, causes, diagnosis, repair, severity, verified, source_id,
            component, location, params, expected, path, replacement)
    if row:
        con.execute("""UPDATE dtcs SET title=?,description=?,symptoms=?,causes=?,diagnosis=?,repair=?,
                    severity=?,verified=?,source_id=?,component=?,component_location=?,vcds_parameters=?,
                    expected_values=?,test_path=?,replacement_steps=? WHERE id=?""", vals + (row[0],))
    else:
        con.execute("""INSERT INTO dtcs(code,title,description,symptoms,causes,diagnosis,repair,severity,
                    verified,source_id,component,component_location,vcds_parameters,expected_values,
                    test_path,replacement_steps) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (code,) + vals)


def install(con):
    _ensure_columns(con)
    src_cat = _source(con, "Ross-Tech Wiki - Fault Codes", "https://wiki.ross-tech.com/wiki/index.php/Category:Fault_Codes",
                      "Index oficial de DTC-uri; verificati pagina exacta si contextul modulului.")
    src_b2000 = _source(con, "Ross-Tech Wiki - B2000", "https://wiki.ross-tech.com/wiki/index.php/B2000")
    src_c1011 = _source(con, "Ross-Tech Wiki - C1011", "https://wiki.ross-tech.com/wiki/index.php/C1011")
    src_u1122 = _source(con, "Ross-Tech Wiki - U1122", "https://wiki.ross-tech.com/wiki/index.php/U1122")

    _upsert(con, "B2000", "Control Module: Defective", "Defect intern raportat de un modul.",
            "Martor sistem; functie indisponibila; DTC persistent.",
            "Defect intern modul; alimentare instabila; pe unele module efect dupa interventii externe.",
            "1) Identifica adresa exacta din Auto-Scan. 2) Salveaza coding/part number. 3) Verifica tensiunea, masele si alimentarea. 4) Daca DTC revine imediat, urmeaza procedura specifica modulului. Pentru Airbag, nu incerca repararea controllerului.",
            "Remediaza alimentarea daca este defecta. Daca modulul este confirmat defect, inlocuieste cu piesa corecta si efectueaza coding/adaptare conform platformei.",
            "high", "Control module", "Depinde de adresa Auto-Scan; modulul identificat de DTC.",
            "Supply voltage; terminal 30/15; module identification; coding", "Tensiune stabila si coding compatibil cu vehiculul.",
            "[Auto-Scan] -> modulul cu B2000 -> [Fault Codes] / [Advanced ID] / [Coding]",
            "Salveaza Auto-Scan/coding inainte. Airbag: foloseste modul nou/corect conform documentatiei producatorului; dupa montaj coding/basic settings/component protection unde se aplica.", src_b2000)

    _upsert(con, "C1011", "Brake Pad Replacement Mode Active", "Modul de schimbare placute este inca activ.",
            "Avertizare frana; functia parking brake poate fi indisponibila; LED/martor poate clipi.",
            "Procedura de service a franei de parcare nu a fost finalizata.",
            "Finalizeaza mecanic lucrarea. Intra in modulul franei de parcare/ABS conform platformei si ruleaza Basic Settings pentru End lining change mode. Actioneaza frana conform instructiunilor afisate.",
            "Nu schimba modulul pentru acest cod singur. Finalizeaza replacement mode si confirma disparitia DTC-ului.",
            "medium", "Electronic parking brake / rear brake service mode", "Etriere spate + modul EPB/ABS, dupa platforma.",
            "Brake pad replacement mode; parking brake status", "Replacement mode trebuie sa fie inactiv dupa finalizarea procedurii.",
            "[53-Parking Brake] sau modulul relevant -> [Basic Settings] -> End lining change mode",
            "Dupa placute/etrier/motoras: inchide modul service, actioneaza frana, sterge DTC si rescaneaza.", src_c1011)

    _upsert(con, "U1122", "Databus: Implausible Message", "Un modul primeste un mesaj CAN/databus considerat implauzibil.",
            "Functie asistenta indisponibila; martori; DTC secundar in unul sau mai multe module.",
            "DTC primar in modulul sursa; coding/configuratie; software; tensiune; CAN/cablaj in anumite cazuri.",
            "1) Nu schimba direct modulul care raporteaza U1122. 2) Analizeaza toate DTC-urile din Auto-Scan si Freeze Frame. 3) Cauta erori primare in modulul care furnizeaza semnalul. 4) Verifica alimentarea si configuratia. 5) Daca exista multe U-codes, verifica CAN. 6) Pe unele configuratii Q3 F3/3C Lane Change exista caz documentat de software de fabrica.",
            "Repara DTC-ul sursa/cablajul/configuratia. Pentru cazurile software documentate verifica update/TSB, nu inlocui piese la intamplare.",
            "medium", "CAN/Data bus / source control module", "Reteaua CAN si modulele indicate de Auto-Scan.",
            "Module communication status; supply voltage; relevant source signal; Freeze Frame", "Semnalele sursa trebuie sa fie plauzibile si modulele online.",
            "[Auto-Scan] -> identifica modulul cu U1122 -> verifica DTC-urile celorlalte module -> [Advanced Measuring Values]",
            "Dupa repararea cauzei: sterge DTC-urile, ciclu contact, test drive si Auto-Scan complet.", src_u1122)

    generic = [
        ("B2005","Data Record Invalid / control module data issue","Body/control module","Verifica identificarea modulului, coding/adaptation si alimentarea; compara cu Auto-Scan anterior."),
        ("B2010","No Basic Setting / configuration issue","Body/control module","Verifica Basic Settings si parametrizarea specifica modulului; nu copia valori de pe alta masina fara compatibilitate."),
        ("B2012","Data Set / configuration fault","Body/control module","Verifica coding, dataset/configuratie si DTC-urile asociate."),
        ("B2013","Control module configuration fault","Body/control module","Salveaza coding, verifica configuratia si procedura de inlocuire a modulului."),
        ("B201A","Software/configuration related fault","Body/control module","Verifica versiunea software, coding si eventuale informatii tehnice pentru platforma."),
        ("C10AC","Chassis/steering calibration related DTC","Steering/chassis","Verifica DTC text exact, alimentarea si Basic Settings/calibrarea ceruta de modul."),
        ("C10AD","Chassis/steering limit/calibration DTC","Steering/chassis","Verifica unghi/directie, senzori si Basic Settings conform modulului."),
        ("C10E2","Chassis function/configuration DTC","Chassis module","Verifica Freeze Frame, coding si senzorii relevanti in Advanced Measuring Values."),
        ("C123E","Chassis/ABS related DTC","ABS/ESP/chassis","Citeste textul complet, verifica senzorii ABS/ESP si erorile primare in 03-Brake Electronics."),
        ("U0103","Lost Communication with Gear Shift Control Module","CAN / transmission selector","Verifica daca modulul selector este online, sigurante, alimentare, masa si CAN; apoi DTC in 02/selector."),
        ("U0155","Lost Communication with Instrument Panel Cluster","CAN / instrument cluster","Verifica 17-Instruments, Gateway installation list, alimentare cluster si CAN."),
        ("U0212","Lost Communication with Steering Column Control Module","CAN / steering column","Verifica 16-Steering Wheel/coloana, alimentare, conectori si CAN."),
        ("U0429","Invalid Data Received From Steering Column Control Module","CAN / steering column","Verifica DTC-urile din modulul coloanei, unghi/semnale si coding inainte de cablaj CAN."),
        ("U1013","Control Module Not Coded / network configuration context","CAN / coding","Verifica textul complet al DTC, codingul modulului si Gateway installation list."),
        ("U1100","Databus missing/invalid message","CAN/Data bus","Identifica modulul sursa din textul complet; verifica DTC primar, alimentare si CAN."),
        ("U1101","Databus missing/invalid message","CAN/Data bus","Coreleaza toate U-codes; verifica mai intai modulul care lipseste din retea."),
        ("U1400","Function restriction due to network/message context","CAN/Data bus","Verifica Freeze Frame, tensiune si DTC-urile sursa; nu inlocui modulul doar pe baza codului."),
        ("U102F","Databus communication DTC","CAN/Data bus","Verifica textul complet VCDS, modulele online, alimentarea si semnalul sursa."),
        ("U1052","Databus communication DTC","CAN/Data bus","Foloseste Auto-Scan pentru a identifica modulul sursa; verifica tensiune/CAN/coding."),
    ]
    for code, title, comp, advice in generic:
        _upsert(con, code, title, "DTC B/C/U dependent de modul si platforma; foloseste textul complet din Auto-Scan.",
                "Martori sau functie indisponibila; poate fi secundar altui DTC.",
                "Alimentare/cablaj; modul sursa; coding/configuratie; software; comunicatie CAN/LIN.",
                "1) Salveaza Auto-Scan complet. 2) Identifica adresa si textul exact. 3) Verifica tensiunea si sigurantele. 4) Rezolva DTC-urile primare din modulul sursa. 5) Verifica live data/coding. 6) Abia apoi testeaza CAN/LIN sau modulul. " + advice,
                "Repara intai cauza primara. Dupa interventie sterge DTC, ciclu contact, test functional si Auto-Scan final.",
                "medium", comp, "Depinde de platforma; foloseste adresa modulului si schema electrica a vehiculului.",
                "Supply voltage; module status; communication; relevant source signals", "Module online, tensiune stabila, semnale plauzibile.",
                "[Auto-Scan] -> modulul cu DTC -> [Fault Codes] -> [Advanced Measuring Values] / [Coding] / [Basic Settings] dupa caz",
                "Daca se inlocuieste un modul: salveaza coding/adaptations, monteaza piesa compatibila, codeaza/adapteaza si rescaneaza. Pot exista Component Protection/parametrizari ce nu se rezolva doar cu VCDS.", src_cat, verified=0)

    con.commit()
