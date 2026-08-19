"""Lighting / Xenon / AFS / LED / Headlight Range procedure expansion.
Data is deliberately controller/generation-specific; do not apply a procedure only by model name.
"""

def _src(con, title, url):
    con.execute("INSERT OR IGNORE INTO sources(title,publisher,url,source_type,notes) VALUES(?,?,?,?,?)",
                (title, "Ross-Tech", url, "official/wiki", "Lighting/Headlight Range procedure"))
    r = con.execute("SELECT id FROM sources WHERE url=?", (url,)).fetchone()
    return r[0] if r else None


def _ensure(con):
    cols = {r[1] for r in con.execute("PRAGMA table_info(procedures)").fetchall()}
    wanted = {"system":"TEXT","controller":"TEXT","applicability":"TEXT","prerequisites":"TEXT","verification":"TEXT","source_id":"INTEGER"}
    for n,t in wanted.items():
        if n not in cols:
            con.execute(f"ALTER TABLE procedures ADD COLUMN {n} {t}")


def _add(con, title, category, path, steps, notes, system, controller, applicability, prereq, verify, sid):
    # Work with the common project schema without assuming model-specific linkage columns.
    row = con.execute("SELECT id FROM procedures WHERE title=? LIMIT 1", (title,)).fetchone()
    values=(category,path,steps,notes,system,controller,applicability,prereq,verify,sid)
    if row:
        con.execute("UPDATE procedures SET category=?,vcds_path=?,steps=?,notes=?,system=?,controller=?,applicability=?,prerequisites=?,verification=?,source_id=? WHERE id=?", values+(row[0],))
    else:
        con.execute("INSERT INTO procedures(title,category,vcds_path,steps,notes,system,controller,applicability,prerequisites,verification,source_id) VALUES(?,?,?,?,?,?,?,?,?,?,?)", (title,)+values)


def install(con):
    _ensure(con)
    s_old=_src(con,"VW Polo 6N Headlight Aim Control","https://wiki.ross-tech.com/wiki/index.php/VW_Polo_%286N%29_Headlight_Aim_Control")
    s_audi=_src(con,"Headlight Aim Control Audi 8K/8T","https://wiki.ross-tech.com/wiki/index.php/Headlight_Aim_Control_Audi_%288K%29_/_%288T%29")
    s_bcm1=_src(con,"Xenon Basic Settings BCM1 J519","https://wiki.ross-tech.com/wiki/index.php/Xenon_Basic_Settings_in_BCM1/09-Cent._Elect._%28J519%29_controller")
    s_mqb=_src(con,"VW MQB Headlight Regulation","https://wiki.ross-tech.com/wiki/index.php/VW_MQB_Headlight_Regulation")
    s_led=_src(con,"Audi A6 4G/4H Headlight Regulation Basic","https://wiki.ross-tech.com/wiki/index.php/Audi_A6_%284G/4H%29_Headlight_Regulation_Basic")
    s_afs=_src(con,"Audi A6 4G/4H Advanced Front System","https://wiki.ross-tech.com/wiki/index.php/Audi_A6_%284G/4H%29_Advanced_Front_System")
    s_pq35=_src(con,"VW Golf 5K BCM","https://wiki.ross-tech.com/wiki/index.php/VW_Golf_%285K%29_Body_Control_Module")

    _add(con,"Reglaj faruri Xenon clasic - Address 55 Group 001/002","Lighting / Headlight Range","55-Headlight Range -> Basic Settings",
         "1. Identifica exact controllerul din Auto-Scan. 2. Masina pe suprafata plana. 3. Intra in 55. 4. Basic Settings Group 001; asteapta starea de reglaj. 5. Regleaza mecanic farurile. 6. Pe sistemele vechi documentate finalizeaza cu Group 002. 7. Clear DTC si rescaneaza.",
         "Nu folosi Group 002 pe un controller care cere o alta procedura. Codarea controllerului depinde de vehicul.","Xenon / Headlight Range","55 - Headlight Range","Sisteme vechi compatibile, inclusiv familia documentata Polo 6N/Lupo/Fabia 6Y/Ibiza 6L; confirma controllerul in Auto-Scan.","Faruri si senzori functionali; suspensie asezata; teren plan.","DTC 01539 absent; pozitia invatata; fascicul verificat fizic.",s_old)

    _add(con,"Audi 8K/8T Xenon - Basic Setting Group 001","Lighting / Xenon","55-Xenon Range -> Basic Settings -> Group 001",
         "1. Salveaza Auto-Scan. 2. Select 55. 3. Daca recodezi, foloseste Security Access afisat de VCDS. 4. Basic Settings Group 001. 5. Asteapta Adjust Headlights. 6. Regleaza mecanic. 7. ON/OFF/Next pentru memorare. 8. Clear DTC.",
         "Tourist Solution este documentata separat in Adaptation Channel 010: 0 dezactivat, 1 activat. Nu confunda aceasta adaptare cu reglajul de baza.","Xenon / AFS","55 - Xenon Range","Audi 8K/8T cu controller diagnostic 55 compatibil.","Teren plan; sistem fara defect mecanic relevant.","Basic Setting invatat si fara DTC relevant dupa reglaj.",s_audi)

    _add(con,"BCM1/J519 Xenon - reglaj fara Address 55","Lighting / BCM","09-Central Electronics -> Basic Settings -> Group 011",
         "1. Confirma in Auto-Scan ca masina NU are controller diagnostic 55 pentru acest sistem. 2. Faruri ON, nu AUTO. 3. 09-Cent. Elect. 4. Basic Settings Group 011. 5. Activeaza; starea devine Adjust Headlights. 6. Regleaza mecanic. 7. Dezactiveaza Basic Setting pentru memorare. 8. Clear DTC.",
         "Aceasta procedura este pentru Xenon de fabrica controlat prin BCM1/J519. Nu o aplica unui vehicul cu 55-Headlight Range diagnosticabil.","Xenon / BCM1","09 - Central Electronics J519","Audi/MLB si alte configuratii documentate cu Xenon in BCM1 fara Address 55 diagnosticabil.","Teren plan; faruri/suspensie functionale; far switch ON; J519 fara DTC incompatibile.","Campul revine la Reg. Position/Learned; DTC-urile sunt sterse si nu reapar.",s_bcm1)

    _add(con,"MQB Headlight Regulation - IDE03675/IDE03676","Lighting / MQB","55-Xenon Range sau 4B-Multifunc. Module -> Basic Settings",
         "1. Identifica in Auto-Scan daca sistemul foloseste 55/J745 sau 4B/J745. 2. Masina pe teren plan si suspensia asezata. 3. Ruleaza IDE03675 Basic headlamp setting. 4. Cand este Running, regleaza mecanic. 5. Stop. 6. Ruleaza IDE03676 Acknowledge basic setting. 7. Stop. 8. Clear DTC.",
         "Pe unele facelift MQB LED se foloseste Address 4B in loc de 55. Security Access nu este necesar pentru Basic Settings pe sistemul documentat.","LED/Xenon / MQB Headlight Regulation","55 J745 / 4B J745","MQB/MLB controllers cu ASAM compatibil; confirma adresa si datasetul din Auto-Scan.","Teren plan; suspensie asezata; faruri si senzori functionali.","IDE03676 finalizat; fara DTC de reglaj; fascicul verificat.",s_mqb)

    _add(con,"Audi 4G/4H Basic LED - Headlight Adjustment","Lighting / LED","55-Xenon Range -> Basic Settings",
         "1. Confirma EV_HeadlRegulBasic sau controller compatibil in Auto-Scan. 2. Basic Settings -> Basic headlamp setting -> Go. 3. Regleaza mecanic. 4. Stop. 5. Acknowledge basic setting -> Go. 6. Stop. 7. Clear DTC.",
         "Procedura se aplica sistemului Basic LED documentat, nu automat tuturor farurilor LED Audi.","LED Headlight Regulation","55 - J431","Audi A4 8K facelift si A6/A7/A8 4G/4H cu Headlight Regulation Basic compatibil.","Teren plan si suspensie asezata.","Acknowledge basic setting finalizat si fara DTC relevant.",s_led)

    _add(con,"Audi 4G/4H Advanced Front System - AFS","Lighting / AFS","55-Xenon Range -> Basic Settings",
         "1. Salveaza Auto-Scan INAINTE de deconectarea/inlocuirea farurilor. 2. Confirma Advanced Front System in Auto-Scan. 3. Dupa reparatie recodeaza conform valorii originale daca este necesar. 4. Basic headlamp setting. 5. Regleaza mecanic. 6. Acknowledge basic setting. 7. Clear DTC si Auto-Scan final.",
         "Ross-Tech avertizeaza ca la acest sistem codingul poate fi pierdut cand slave-urile farurilor sunt deconectate. Nu inventa coding daca scanarea originala lipseste.","AFS / Xenon / LED slaves","55 J431 + 09 J519 subsystems","Audi A6/A7/A8 4G/4H cu Advanced Front System compatibil.","Auto-Scan original salvat; teren plan; slave-urile online.","Coding corect, Basic Setting acceptat, slave-urile comunica, fara DTC relevant.",s_afs)

    _add(con,"PQ35 BCM Lighting - Long Coding Helper","Lighting / Coding","09-Central Electronics -> Coding -> Long Coding Helper",
         "1. Salveaza Auto-Scan si codingul original. 2. Deblocheaza toate usile daca BCM-ul nu comunica. 3. 09-Cent. Elect. 4. Coding -> Long Coding Helper. 5. Modifica numai optiunea documentata pentru controllerul respectiv. 6. Do It. 7. Verifica luminile si rescaneaza.",
         "DRL, Coming/Leaving Home si alte functii variaza cu BCM, software, piata si echiparea farurilor. Nu afisa un Byte/Bit universal daca VCDS nu il documenteaza pentru controllerul conectat.","BCM / Exterior Lighting","09 - J519 BCM PQ35","Golf 5K/52 si alte PQ35 BCM compatibile; foloseste informatia Long Coding Helper din controller.","Backup Auto-Scan/coding; tensiune stabila.","Functia ceruta opereaza corect; fara DTC noi; coding salvat.",s_pq35)
    con.commit()
