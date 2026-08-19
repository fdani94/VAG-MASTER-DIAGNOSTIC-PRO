"""Platform-aware baseline gap filler for the 1996-2024 VAG catalog.

Important: these entries intentionally use verified=0. They are navigation/diagnostic
baselines, not claims that every controller/engine variant is exhaustively documented.
The coverage audit will therefore show PARȚIAL until a verified model/controller-specific
procedure is linked.
"""

AREAS = {
    "Motor": ("01", "Motor", "Engine"),
    "Cutie": ("02", "Cutie", "Transmission"),
    "ABS/ESP": ("03", "ABS/ESP", "ABS"),
    "Airbag": ("15", "Airbag", "Airbag"),
    "HVAC": ("08", "HVAC", "HVAC"),
    "Lighting": ("09/55/4B", "Lighting", "Lighting"),
    "Comfort": ("46/09/42/52", "Comfort", "Comfort"),
    "Battery": ("61/19", "Battery", "Battery"),
    "Gateway": ("19", "Gateway", "Gateway"),
    "Service/SRI": ("17/SRI", "Service/SRI", "Service"),
    "Long Coding": ("variază", "Long Coding", "Coding"),
}

KEYWORDS = {
    "Motor": ("motor", "engine", "tdi", "tsi", "tfsi", "fsi", "mpi", "dpf", "egr", "inject"),
    "Cutie": ("transmission", "dsg", "dq", "01m", "01j", "09g", "multitronic", "gearbox", "cutie"),
    "ABS/ESP": ("abs", "esp", "brake", "g85", "steering angle"),
    "Airbag": ("airbag", "occupancy", "j706"),
    "HVAC": ("hvac", "climat", "air conditioning", "compressor", "flap"),
    "Lighting": ("light", "headlamp", "xenon", "led", "afs", "drl", "j519"),
    "Comfort": ("comfort", "door", "window", "mirror", "remote", "central convenience"),
    "Battery": ("battery", "bem", "energy management"),
    "Gateway": ("gateway", "installation list", "can"),
    "Service/SRI": ("service", "sri", "oil", "inspection"),
    "Long Coding": ("long coding", "coding"),
}


def _txt(row):
    return " ".join(str(row[k] or "") for k in row.keys()).lower()


def _platform_family(platform):
    p = (platform or "").upper()
    if "MEB" in p:
        return "MEB"
    if "MQB EVO" in p:
        return "MQB EVO"
    if "MQB" in p:
        return "MQB"
    if "MLB EVO" in p:
        return "MLB EVO"
    if "MLB" in p:
        return "MLB"
    if "PQ" in p:
        return "PQ"
    return "LEGACY"


def _source(con, title, url, notes):
    con.execute("INSERT OR IGNORE INTO sources(title,publisher,url,source_type,notes) VALUES(?,?,?,?,?)",
                (title, "Ross-Tech", url, "official/wiki", notes))
    row = con.execute("SELECT id FROM sources WHERE url=?", (url,)).fetchone()
    return row[0] if row else None


def _baseline(area, platform):
    family = _platform_family(platform)
    addr, cat, _ = AREAS[area]

    common_warning = (
        "Procedură baseline de acoperire, nu procedură finală per ECU. Rulează și salvează Auto-Scan înainte de modificări. "
        "Confirmă part number, Component, protocol (K-Line/CAN/UDS), cod motor/cutie și echiparea înainte de Coding/Adaptation/Basic Settings."
    )

    if area == "Gateway":
        return (
            "Baseline Gateway / Installation List",
            "[19-CAN Gateway] → Installation List / Fault Codes",
            "Inventarierea modulelor instalate și identificarea modulelor lipsă sau adăugate.",
            "1) Salvează Auto-Scan. 2) Deschide 19-CAN Gateway. 3) Verifică Installation List unde funcția există. "
            "4) Compară modulele declarate cu cele care răspund. 5) Nu bifa/debifa module fără a confirma retrofitul/configurația.",
            "Lista este coerentă cu echiparea reală și Auto-Scan-ul nu arată module așteptate fără comunicare.",
            common_warning,
        )
    if area == "Battery":
        path = "[61-Battery Regulation] sau [19-CAN Gateway] → Adaptation/Long Adaptation, după generație"
        return (
            "Baseline Battery / Energy Management",
            path,
            "Identificarea tipului de battery management și verificarea necesității de înregistrare a bateriei.",
            "1) Salvează Auto-Scan. 2) Caută 61-Battery Regulation sau BEM/J367 ca subsystem în 19-CAN Gateway. "
            "3) Dacă există management de baterie, urmează procedura specifică acelui controller. 4) Dacă nu există, nu inventa o procedură BEM.",
            "Controllerul acceptă datele noii baterii sau sistemul este confirmat ca neavând procedură de înregistrare.",
            common_warning + " Pe unele MLB, Battery Management este subsystem al Gateway-ului; pe altele există Address 61 separat.",
        )
    if area == "Service/SRI":
        return (
            "Baseline Service / SRI",
            "[SRI Reset] sau [17-Instruments] → Adaptation, după cluster",
            "Resetarea intervalului de service numai după identificarea strategiei Fixed/Flexible și a clusterului.",
            "1) Salvează valorile curente. 2) Încearcă funcția SRI Reset. 3) Dacă modelul folosește Adaptation în 17, verifică exact canalele afișate de controller. "
            "4) Nu schimba aleator valori de service life/distance/time.",
            "Mesajul de service este resetat fără valori imposibile sau intervale neconforme.",
            common_warning,
        )
    if area == "Lighting":
        return (
            "Baseline Lighting / Headlamp Control",
            "[09-Central Electronics] / [55-Headlight Range] / [4B-Multifunction Module], după echipare",
            "Determinarea controllerului corect pentru halogen/Xenon/LED/AFS și a metodei de Basic Setting/Coding.",
            "1) Verifică Auto-Scan pentru 09, 55 și/sau 4B. 2) Confirmă tipul farului și part number. 3) Citește DTC-urile înainte de calibrare. "
            "4) Folosește Basic Settings numai din controllerul prezent pe mașină. 5) Pentru tweak-uri, salvează coding/adaptation map înainte.",
            "Farurile nu au DTC de calibrare/coding și reglajul funcționează pe controllerul corect.",
            common_warning + " MQB poate folosi 55 sau 4B; unele sisteme Xenon mai vechi folosesc direct 09/J519.",
        )
    if area == "ABS/ESP":
        return (
            "Baseline ABS/ESP / G85",
            "[03-ABS Brakes] și, unde este cazul, [44-Steering Assist]",
            "Identificarea generației ABS și a controllerului în care se calibrează G85/senzorii.",
            "1) Salvează Auto-Scan și codingul ABS. 2) Rezolvă subtensiunea și DTC-urile de comunicație. 3) Confirmă generația ABS din Component/part number. "
            "4) Calibrează G85 numai în 03 sau 44 conform controllerului. 5) După lucrări EPB, folosește doar Basic Settings specifice controllerului.",
            "ABS/ESP nu mai are DTC de Basic Setting/coding și valorile senzorilor sunt plauzibile.",
            common_warning,
        )
    if area == "HVAC":
        return (
            "Baseline HVAC / Climatronic",
            "[08-Auto HVAC] → Fault Codes / Advanced Measuring Values / Basic Settings",
            "Diagnosticarea clapetelor, temperaturilor, presiunii și condiției de oprire a compresorului.",
            "1) Citește DTC. 2) Verifică temperaturile și presiunea agentului. 3) Verifică shut-off condition/compressor request dacă sunt disponibile. "
            "4) După înlocuirea motoarelor de clapetă sau compresorului, rulează Basic Setting/Run-In doar dacă controllerul îl oferă.",
            "Fără DTC relevante; clapetele ajung la capete; compresorul este comandat și valorile sunt plauzibile.",
            common_warning,
        )
    if area == "Airbag":
        return (
            "Baseline Airbag / Occupancy",
            "[15-Airbags] → Fault Codes / Advanced Measuring Values / Basic Settings unde este documentat",
            "Diagnosticarea sistemului SRS fără ștergere crash data sau dezactivarea dispozitivelor de siguranță.",
            "1) Salvează Auto-Scan și codingul. 2) Nu măsura circuitele pirotehnice cu instrumente nepotrivite. 3) Verifică alimentări/conectori conform reparației oficiale. "
            "4) Calibrarea occupancy se face numai dacă controllerul/vehiculul o cere și condițiile sunt îndeplinite.",
            "DTC-urile SRS sunt eliminate prin repararea cauzei, nu prin bypass/emulator.",
            common_warning + " Permanent crash data nu se tratează ca un simplu Clear DTC.",
        )
    if area == "Comfort":
        controller = "46-Central Convenience / 09-BCM / 42-52 Door Electronics"
        return (
            "Baseline Comfort / Doors / Windows",
            f"[{controller}] → Fault Codes / Coding / Adaptation",
            "Identificarea arhitecturii Comfort și a controllerului pentru yale, geamuri, oglinzi și telecomenzi.",
            "1) Verifică dacă mașina folosește 46 separat sau funcțiile sunt în 09-BCM. 2) La erori multiple de uși, verifică întâi tensiune/CAN/alimentare comună. "
            "3) După modul de ușă, copiază codingul dacă este compatibil și reînvață limitele geamului.",
            "Funcțiile Comfort operează corect și Auto-Scan-ul nu mai arată erori de comunicație/coding.",
            common_warning,
        )
    if area == "Cutie":
        return (
            "Baseline Transmission Identification",
            "[02-Auto Trans] → Identification / Fault Codes / Advanced Measuring Values",
            "Identificarea exactă a cutiei înainte de orice Basic Setting sau Adaptation.",
            "1) Salvează Auto-Scan. 2) Notează part number, Component și codul cutiei. 3) Determină familia: 01M/01J/09G/02E/0AM/DQ etc. "
            "4) Nu rula Basic Settings până când familia și procedura specifică nu sunt confirmate.",
            "Familia cutiei este identificată și se poate selecta procedura corectă, fără a aplica grupuri de la altă transmisie.",
            common_warning,
        )
    if area == "Motor":
        return (
            "Baseline Engine Identification & Live Data",
            "[01-Engine] → Identification / Fault Codes / Measuring Blocks sau Advanced Measuring Values",
            "Identificarea ECU și familiei motorului înainte de adaptări, DPF, EGR, TBA sau injector coding.",
            "1) Salvează Auto-Scan. 2) Notează cod motor/ECU/Component. 3) Separă VE TDI, PD/PPD, CR TDI, MPI/FSI/TSI/TFSI și UDS. "
            "4) Verifică întâi DTC + freeze frame + live data. 5) Rulează procedurile speciale numai pentru familia confirmată.",
            "Familia ECU este identificată iar procedura aleasă corespunde motorului și protocolului.",
            common_warning,
        )
    # Long Coding
    note = "Pe MQB/MQB Evo unele module folosesc Adaptation în loc de Long Coding; pe generații moderne pot exista SFD/Diagnostic Firewall."
    return (
        f"Baseline Coding Strategy - {family}",
        "Controller relevant → Coding/Long Coding Helper sau Adaptation, după controller",
        "Determinarea mecanismului corect de configurare fără a presupune că toate modulele au Long Coding.",
        "1) Salvează Auto-Scan și coding/adaptation map. 2) Confirmă part number și protocol. 3) Dacă Long Coding este disponibil, folosește Helper. "
        "4) Dacă Coding este zero/indisponibil, verifică Adaptation. 5) Respectă SFD/Component Protection/parametrizarea online când apar.",
        "Modificarea este acceptată, fără DTC de Incorrectly Coded și cu posibilitate de revenire la valorile salvate.",
        common_warning + " " + note,
    )


def _get_or_create_proc(con, area, platform, source_id):
    title, path, purpose, steps, success, warnings = _baseline(area, platform)
    platform_family = _platform_family(platform)
    full_title = f"{title} [{platform_family}]"
    row = con.execute("SELECT id FROM procedure_library WHERE title=? LIMIT 1", (full_title,)).fetchone()
    if row:
        return row[0]
    addr, category, _ = AREAS[area]
    cur = con.execute("""INSERT INTO procedure_library
        (title,category,module_address,vcds_path,purpose,prerequisites,steps,success_criteria,warnings,applicability_rule,verified,source_id)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
        (full_title, category, addr, path, purpose,
         "Auto-Scan complet salvat; tensiune stabilă; controller/part number identificat.",
         steps, success, warnings,
         f"Baseline condițional pentru platforme {platform_family}; necesită confirmare per controller/echipare.",
         0, source_id))
    return cur.lastrowid


def _has_area(con, gid, area):
    rows = con.execute("""SELECT p.* FROM procedure_library p
        JOIN vehicle_procedures vp ON vp.procedure_id=p.id WHERE vp.generation_id=?""", (gid,)).fetchall()
    keys = KEYWORDS[area]
    return any(any(k in _txt(r) for k in keys) for r in rows)


def install(con):
    src_common = _source(con, "Ross-Tech Common Procedures", "https://wiki.ross-tech.com/wiki/index.php/Common_Procedures",
                         "Generic procedures may still have model-specific requirements.")
    _source(con, "Ross-Tech Battery Replacement", "https://wiki.ross-tech.com/wiki/index.php/Battery_Replacement",
            "Battery management differs between Address 61, CAN Gateway CAN and UDS implementations.")
    _source(con, "Ross-Tech VW Golf VII 5G/AU", "https://wiki.ross-tech.com/wiki/index.php/VW_Golf_VII_(5G/AU)",
            "Example MQB architecture; controller presence and coding strategy vary by equipment/year.")
    _source(con, "Ross-Tech Audi CAN Gateway CAN", "https://wiki.ross-tech.com/wiki/index.php/Audi_CAN_Gateway_using_CAN_protocol",
            "MLB CAN Gateway installation list, battery management and replacement notes.")

    gens = con.execute("""SELECT g.id,g.platform,g.year_from,g.year_to,b.name brand,m.name model,g.name generation
        FROM generations g JOIN models m ON m.id=g.model_id JOIN brands b ON b.id=m.brand_id
        WHERE COALESCE(g.year_to,2024)>=1996 AND COALESCE(g.year_from,2024)<=2024""").fetchall()

    for g in gens:
        for area in AREAS:
            if _has_area(con, g["id"], area):
                continue
            pid = _get_or_create_proc(con, area, g["platform"], src_common)
            con.execute("""INSERT OR IGNORE INTO vehicle_procedures(generation_id,procedure_id,applicability,notes)
                VALUES(?,?,?,?)""",
                (g["id"], pid, "Baseline / necesită verificare",
                 f"Adăugat automat de gap-filler pentru {g['brand']} {g['model']} {g['generation']}; nu înlocuiește procedura specifică ECU/controller."))
    con.commit()
