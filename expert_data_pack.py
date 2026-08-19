from datetime import datetime


def _add_col(con, table, col, definition):
    cols = {r[1] for r in con.execute(f"PRAGMA table_info({table})")}
    if col not in cols:
        con.execute(f"ALTER TABLE {table} ADD COLUMN {col} {definition}")


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
    title = row[0]
    r = con.execute("SELECT id FROM procedure_library WHERE title=?", (title,)).fetchone()
    if r:
        return r[0]
    cur = con.execute("""INSERT INTO procedure_library(
        title,category,module_address,vcds_path,purpose,prerequisites,steps,
        success_criteria,warnings,applicability_rule,verified,source_id)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""", row)
    return cur.lastrowid


def _map(con, pid, sql, args=(), applicability="Exact/Condițional", notes="Confirmă Auto-Scan, part number, software și echiparea înainte de salvare."):
    for r in con.execute("SELECT id FROM generations WHERE " + sql, args):
        con.execute("INSERT OR IGNORE INTO vehicle_procedures(generation_id,procedure_id,applicability,notes) VALUES(?,?,?,?)",
                    (r[0], pid, applicability, notes))


def install(con):
    _add_col(con, "dtcs", "vcds_parameters", "TEXT DEFAULT ''")
    _add_col(con, "dtcs", "expected_values", "TEXT DEFAULT ''")
    _add_col(con, "dtcs", "replacement_steps", "TEXT DEFAULT ''")

    src_coding = _source(con, "VCDS Coding / Long Coding", "https://www.ross-tech.com/vcds/tour/recode_screen.php", "Coding și Long Coding Helper")
    src_adapt = _source(con, "VCDS Adaptation", "https://www.ross-tech.com/vcds/tour/adaptation_screen.php", "Adaptation și Long Adaptation")
    src_gateway = _source(con, "Gateway Installation List", "https://www.ross-tech.com/vcds/tour/installation-list.php")
    src_golf1k = _source(con, "Golf/Jetta/Bora 1K/5M Tweaks", "https://wiki.ross-tech.com/wiki/index.php/VW_Golf/Jetta/Bora_%281K/5M%29_Tweaks")
    src_golf1k_comfort = _source(con, "Golf 1K Comfort System", "https://wiki.ross-tech.com/wiki/index.php/VW_Golf_%281K%29_Comfort_System")
    src_golf5k = _source(con, "Golf 5K Tweaks", "https://wiki.ross-tech.com/wiki/index.php/VW_Golf/Golf_Plus_%285K/52%29_Tweaks")
    src_audi8k = _source(con, "Audi A4/A5 8K/8T Tweaks", "https://wiki.ross-tech.com/wiki/index.php/Audi_A4/S4/A5/S5_%288K/8T%29_Tweaks")
    src_gw1k = _source(con, "Golf 1K CAN Gateway", "https://wiki.ross-tech.com/wiki/index.php/VW_Golf_%281K%29_CAN-Gateway")

    rows = [
        ("Long Coding - flux profesional cu backup", "Long Coding", "", "[Select] > [modul] > [Coding-07] > [Long Coding Helper]",
         "Modifică Byte/Bit numai când eticheta/controllerul documentează opțiunea.",
         "Salvează Auto-Scan; copiază coding-ul original integral; notează part number și Component/Software.",
         "1) Selectează modulul. 2) Coding-07. 3) Copiază coding-ul original într-un fișier. 4) Deschide Long Coding Helper. 5) Selectează Byte-ul documentat și bifează/debifează numai Bit-ul documentat. 6) Închide Helper pentru transferul coding-ului. 7) Do It!. 8) Dacă este UDS și funcția nu se aplică imediat, folosește Soft Reset dacă este documentat sau ciclul de contact. 9) Rescanează modulul.",
         "Coding accepted, funcția lucrează și nu apar DTC noi.",
         "Nu copia Long Coding de pe alt vehicul; lungimea poate ajunge la sute de caractere și opțiunile diferă după software/hardware.",
         "General", 1, src_coding),

        ("Golf 1K/5M - Long Coding iluminare în 09 Central Electronics", "Long Coding", "09", "[09-Cent. Elect.] > [Coding-07] > [Long Coding Helper]",
         "Activează/dezactivează opțiunile de iluminare documentate în Long Coding Helper, inclusiv DRL/Coming Home/Leaving Home când sunt suportate.",
         "VW Golf/Jetta/Bora 1K/5M sau Audi A3 8P compatibil; Auto-Scan salvat.",
         "1) 09-Cent. Elect. 2) Coding-07. 3) Long Coding Helper. 4) Parcurge Byte-urile și selectează NUMAI eticheta exactă afișată pentru funcția dorită, de ex. Daytime Running Lights sau Coming/Leaving Home. 5) Modifică o singură opțiune. 6) Exit din Helper. 7) Do It!. 8) Verifică funcția și rescanează.",
         "Funcția selectată este activă fără DTC noi.",
         "Byte/Bit-ul poate diferi după versiunea modulului 09; aplicația nu trebuie să inventeze un Byte universal când Ross-Tech indică folosirea etichetelor Long Coding Helper.",
         "Golf/Jetta/Bora 1K/5M și A3 8P compatibil", 1, src_golf1k),

        ("Golf 1K - Auto-Lock / Auto-Unlock", "Long Coding", "46", "[46-Comfort System] > [Coding-07] > [Long Coding Helper]",
         "Activează blocarea automată de la aproximativ 15 km/h și/sau deblocarea la scoaterea cheii, unde modulul suportă.",
         "Golf/Jetta/Bora 1K cu Address 46 prezent; salvează coding-ul original.",
         "1) 46-Comfort System. 2) Coding-07. 3) Long Coding Helper. 4) Activează opțiunea etichetată Auto-Lock (automatic locking from 15 km/h) și/sau Auto-Unlock (unlocking after removing key from ignition). 5) Exit. 6) Do It!. 7) Testează funcția.",
         "Auto-Lock/Auto-Unlock se comportă conform selecției.",
         "Nu toate modulele 46 au aceleași opțiuni/bytes.",
         "Golf 1K cu modul 46 compatibil", 1, src_golf1k),

        ("Golf 1K - potrivire telecomenzi Channel 001", "Adaptation", "46", "[46-Comfort System] > [Adaptation-10] > Channel 001",
         "Împerechează telecomenzi suplimentare.",
         "Toate telecomenzile prezente; maximum 4 poziții; dacă sunt ocupate, folosește mai întâi Channel 000 pentru clearing.",
         "1) 46-Comfort System. 2) Adaptation-10. 3) Channel 001 > Read. 4) New Value = 1. 5) Test > Save. 6) În maximum ~15 secunde, ține apăsat butonul Unlock minimum 1 secundă pe fiecare telecomandă. 7) Semnalizările confirmă fiecare telecomandă.",
         "Telecomenzile comandă închiderea/deschiderea centralizată.",
         "Dacă Test/Save sunt inactive, cele 4 poziții pot fi ocupate; folosește Channel 000 numai dacă vrei să ștergi toate telecomenzile memorate.",
         "Golf 1K cu modul 46 compatibil", 1, src_golf1k_comfort),

        ("Golf 1K - ștergere telecomenzi Channel 000", "Resetări", "46", "[46-Comfort System] > [Adaptation-10] > Channel 000",
         "Șterge toate telecomenzile memorate înainte de rematching.",
         "Confirmă că vrei să pierzi toate telecomenzile memorate și că le ai pe toate disponibile pentru rematching.",
         "1) 46-Comfort System. 2) Adaptation-10. 3) Channel 000 > Read. 4) Save pentru resetarea/clearing-ul suportat de controller. 5) Continuă cu Channel 001 pentru rematching.",
         "Lista de telecomenzi este golită și poate fi refăcută.",
         "Channel 000 este un reset special doar pe controllere care îl suportă; nu îl folosi generic pe alte module.",
         "Golf 1K cu modul 46 compatibil", 1, src_golf1k_comfort),

        ("Audi A4/A5 8K/8T - Auto-Lock personalizare cheie +00004", "Adaptation", "46", "[46-Comfort System] > [Adaptation-10] > Channel 001/002/003/004",
         "Activează Auto-Lock pentru cheia/personalizarea selectată, unde BCM2 suportă schema documentată.",
         "Audi A4/S4/A5/S5 8K/8T; salvează harta Adaptation (PLA) și valoarea originală a canalului.",
         "1) 46-Comfort System. 2) Adaptation-10. 3) Selectează canalul 001, 002, 003 sau 004 corespunzător cheii/personalizării. 4) Read și notează Stored Value. 5) Adaugă +00004 la valoarea existentă pentru Auto-Lock. 6) Test când este disponibil. 7) Save. 8) Verifică și meniul MMI Car > Central Locking.",
         "Auto-Lock este disponibil/activ pentru personalizarea selectată.",
         "Valoarea este o sumă de opțiuni; nu înlocui Stored Value cu 4, ci adaugă 4 la valoarea existentă.",
         "Audi 8K/8T și Q5 8R compatibil", 1, src_audi8k),

        ("Audi A4/A5 8K/8T - Auto-Unlock personalizare cheie +00008", "Adaptation", "46", "[46-Comfort System] > [Adaptation-10] > Channel 001/002/003/004",
         "Activează Auto-Unlock la scoaterea cheii pentru personalizarea selectată.",
         "Coding-ul Auto-Unlock trebuie să fie suportat/activ; salvează harta Adaptation și Stored Value.",
         "1) 46-Comfort System. 2) Adaptation-10. 3) Alege canalul de personalizare 001-004. 4) Read. 5) Adaugă +00008 la Stored Value. 6) Test/Save. 7) Verifică funcția și meniul MMI.",
         "Auto-Unlock funcționează conform configurării.",
         "Nu suprascrie suma existentă; +00008 se adaugă la opțiunile deja active.",
         "Audi 8K/8T și Q5 8R compatibil", 1, src_audi8k),

        ("Audi A4/A5 8K/8T - Selective Central Locking +00001", "Adaptation", "46", "[46-Comfort System] > [Adaptation-10] > Channel 001/002/003/004",
         "Activează personalizarea Selective Central Locking.",
         "Funcția de coding trebuie suportată; salvează PLA și Stored Value.",
         "1) 46-Comfort System. 2) Adaptation-10. 3) Alege canalul 001-004. 4) Read. 5) Adaugă +00001 la Stored Value. 6) Test/Save. 7) Verifică funcția și meniul MMI.",
         "Selective locking este activ pentru cheia/personalizarea respectivă.",
         "Este o valoare aditivă, nu un Stored Value universal.",
         "Audi 8K/8T și Q5 8R compatibil", 1, src_audi8k),

        ("Golf 1K Gateway - Byte 00 Bit 0 Engine Electronics", "Long Coding", "19", "[19-CAN Gateway] > [Coding-07] > [Long Coding Helper] > Byte 00 Bit 0",
         "Înregistrează/prezintă Engine Electronics în coding-ul Gateway la variantele vechi suportate.",
         "Golf 1K CAN Gateway Index through F; verifică indexul controllerului înainte de aplicare.",
         "1) 19-CAN Gateway. 2) Verifică part number/index. 3) Coding-07 > Long Coding Helper. 4) Pentru coding scheme through Index F: Byte 00 Bit 0 corespunde [01] Engine Electronics. 5) Modifică numai dacă instalația reală o cere. 6) Do It! și rescanează.",
         "Gateway Installation corespunde modulelor instalate și nu apar DTC de module incorect înregistrate.",
         "Mapping-ul Byte/Bit se schimbă pe alte indexuri; pe Gateway-urile noi se folosește Installation List.",
         "Golf 1K Gateway vechi, Index through F", 1, src_gw1k),

        ("Gateway modern - Installation List în loc de Long Coding", "Coding", "19", "[19-CAN Gateway] > [Installation List]",
         "Înregistrează/dezînregistrează module instalate pe Gateway-urile unde lista nu este expusă prin Long Coding.",
         "Auto-Scan salvat; cunoști exact ce module sunt fizic instalate.",
         "1) 19-CAN Gateway. 2) Installation List. 3) Bifează numai modulele fizic instalate. 4) Write coding. 5) Rescanează. Pentru înlocuirea Gateway-ului, Direct coding poate fi disponibil pe unele UDS/CAN Gateways.",
         "Auto-Scan nu mai raportează module lipsă sau neînregistrate incorect.",
         "Restore original value anulează doar modificările din sesiunea curentă, nu restaurează configurația din fabrică.",
         "Gateway care suportă Installation List", 1, src_gateway),
    ]

    ids = []
    for row in rows:
        ids.append((row[0], _proc(con, row)))

    mapping = {
        "Golf 1K/5M - Long Coding iluminare în 09 Central Electronics": ("name LIKE 'V 1K%'",),
        "Golf 1K - Auto-Lock / Auto-Unlock": ("name LIKE 'V 1K%'",),
        "Golf 1K - potrivire telecomenzi Channel 001": ("name LIKE 'V 1K%'",),
        "Golf 1K - ștergere telecomenzi Channel 000": ("name LIKE 'V 1K%'",),
        "Golf 1K Gateway - Byte 00 Bit 0 Engine Electronics": ("name LIKE 'V 1K%'",),
        "Audi A4/A5 8K/8T - Auto-Lock personalizare cheie +00004": ("chassis IN ('8K/FL','8K','8T','8R/FP') OR name LIKE '%8K%' OR name LIKE '%8T%' OR name LIKE '%8R%'",),
        "Audi A4/A5 8K/8T - Auto-Unlock personalizare cheie +00008": ("chassis IN ('8K/FL','8K','8T','8R/FP') OR name LIKE '%8K%' OR name LIKE '%8T%' OR name LIKE '%8R%'",),
        "Audi A4/A5 8K/8T - Selective Central Locking +00001": ("chassis IN ('8K/FL','8K','8T','8R/FP') OR name LIKE '%8K%' OR name LIKE '%8T%' OR name LIKE '%8R%'",),
    }
    for title, pid in ids:
        if title == "Long Coding - flux profesional cu backup":
            _map(con, pid, "1=1", applicability="General")
        elif title == "Gateway modern - Installation List în loc de Long Coding":
            _map(con, pid, "year_from>=2004", applicability="Condițional")
        elif title in mapping:
            _map(con, pid, mapping[title][0])

    # Improve the common DTC cards with VCDS parameter names and repair workflow.
    updates = {
        "P0299": (
            "Charge/Boost Pressure specified; Charge/Boost Pressure actual; N75/duty cycle sau actuator command când ECU îl expune; MAP/charge pressure; engine speed; accelerator/load.",
            "În sarcină, actual trebuie să urmărească specified fără abatere persistentă mare. Nu există un mbar universal pentru toate motoarele; presiunea cerută depinde de turație, sarcină și motor.",
            "1) Lasă motorul rece dacă intervenția este la turbo/evacuare. 2) Demontează capacele și traseul necesar conform codului motor. 3) Înlocuiește furtunul/colierul/N75/actuatorul doar dacă testul confirmă defectul. 4) Pentru turbină: golește/completează uleiul dacă procedura o cere, amorsează circuitul de ungere conform manualului și înlocuiește garniturile de unică folosință. 5) Șterge DTC. 6) Repetă log specified vs actual în aceleași condiții."),
        "P0401": (
            "EGR specified; EGR actual/position; Mass Air Flow specified/actual; intake manifold pressure; exhaust pressure flap position când există.",
            "La comandarea EGR trebuie să existe o reacție coerentă a poziției EGR și a masei de aer. Valorile numerice exacte sunt specifice ECU/motorului.",
            "1) Identifică valva EGR după cod motor. 2) Deconectează bateria numai dacă manualul o cere. 3) Scoate conductele/conectorul/răcitorul necesar. 4) Curăță depunerile doar dacă piesa este reparabilă și mecanismul nu este defect. 5) Dacă înlocuiești EGR, montează garnituri noi. 6) Rulează EGR adaptation/basic setting dacă motorul o cere. 7) Șterge DTC și verifică EGR specified/actual + MAF."),
        "P0101": (
            "Mass Air Flow actual; Mass Air Flow specified când există; EGR specified/actual; intake pressure; engine speed/load.",
            "MAF actual trebuie să varieze logic cu turația și sarcina și să fie coerent cu specified. Nu există g/s sau mg/str universal pentru toate motoarele VAG.",
            "1) MAF este de regulă montat imediat după cutia filtrului de aer. 2) Oprește contactul. 3) Deblochează mufa fără a trage de fire. 4) Slăbește colierele/șuruburile și montează senzorul nou în sensul corect al fluxului. 5) Nu atinge elementul sensibil. 6) Verifică etanșeitatea traseului. 7) Șterge DTC și repetă logul MAF/EGR."),
    }
    for code, values in updates.items():
        con.execute("UPDATE dtcs SET vcds_parameters=?, expected_values=?, replacement_steps=? WHERE code=?", (*values, code))

    con.commit()
