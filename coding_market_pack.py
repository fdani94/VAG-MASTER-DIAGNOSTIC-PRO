from datetime import datetime


def _source(con, title, url, notes=""):
    r=con.execute("SELECT id FROM sources WHERE url=?",(url,)).fetchone()
    if r: return r[0]
    c=con.execute("INSERT INTO sources(title,publisher,url,accessed,source_type,notes) VALUES(?,?,?,?,?,?)",(title,"Ross-Tech",url,datetime.now().date().isoformat(),"Oficial",notes))
    return c.lastrowid


def _proc(con,row):
    r=con.execute("SELECT id FROM procedure_library WHERE title=?",(row[0],)).fetchone()
    if r: return r[0]
    return con.execute("""INSERT INTO procedure_library(title,category,module_address,vcds_path,purpose,prerequisites,steps,success_criteria,warnings,applicability_rule,verified,source_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",row).lastrowid


def _map(con,pid,sql,args=()):
    for r in con.execute("SELECT id FROM generations WHERE "+sql,args):
        con.execute("INSERT OR IGNORE INTO vehicle_procedures(generation_id,procedure_id,applicability,notes) VALUES(?,?,?,?)",(r[0],pid,"Exact/Condițional","Confirmă part number, protocol, PR-codes și etichetele afișate de VCDS înainte de salvare."))


def install(con):
    s1=_source(con,"Golf/Jetta/Bora 1K/5M Tweaks","https://wiki.ross-tech.com/wiki/index.php/VW_Golf/Jetta/Bora_%281K/5M%29_Tweaks")
    s2=_source(con,"Golf/Golf Plus 5K/52 Tweaks","https://wiki.ross-tech.com/wiki/index.php/VW_Golf/Golf_Plus_%285K/52%29_Tweaks")
    s3=_source(con,"Audi A4/A5 8K/8T Tweaks","https://wiki.ross-tech.com/wiki/index.php/Audi_A4/S4/A5/S5_%288K/8T%29_Tweaks")
    s4=_source(con,"Golf 5K Climatronic","https://wiki.ross-tech.com/wiki/index.php/VW_Golf_%285K%29_Climatronic")
    s5=_source(con,"Golf 5K Instrument Cluster","https://wiki.ross-tech.com/wiki/index.php/VW_Golf_%285K%29_Instrument_Cluster")
    s6=_source(con,"Golf 1K Door Electronics Passenger","https://wiki.ross-tech.com/wiki/index.php/VW_Golf_%281K%29_Door_Electronics_Passenger")
    rows=[
      ("Geamuri confort din telecomandă - Golf 1K","Long Coding","46","[46-Comfort System] > [Coding-07] > [Long Coding Helper]","Activează deschiderea/închiderea geamurilor din telecomandă.","Golf/Jetta/Bora 1K/5M cu modul 46 compatibil; Auto-Scan salvat.","1) 46-Comfort System. 2) Coding-07 > Long Coding Helper. 3) Activează etichetele Comfort opening power windows via remote control și Comfort closing power windows via remote control. 4) Dacă dorești, activează Closing sunroof via remote control. 5) Exit > Do It!. 6) Testează ținând apăsat Unlock/Lock.","Geamurile răspund la telecomandă fără DTC noi.","Byte/Bit diferă după versiunea modulului; folosește eticheta exactă din Long Coding Helper.","Golf/Jetta/Bora 1K/5M; A3 8P vechi compatibil",1,s1),
      ("Închidere automată geamuri/trapă la ploaie - Golf 5K","Long Coding","09","[09-Cent. Elect.] > [Coding-07] > [Long Coding Helper] + Sub-System RLS","Activează Rain Closing când există senzor RLS și hardware compatibil.","RLS instalat și funcțional; Auto-Scan și coding original salvate.","1) 09-Cent. Elect. > Coding-07 > Long Coding Helper. 2) În Byte 4 activează Comfort Operation Windows/Sunroof via Rain Sensor și Rain Closing active. 3) Selectează Sub-System RLS din dropdown. 4) Coding > Long Coding Helper > activează Rain Closing active. 5) Do It! și testează cu RLS.","Rain closing funcționează conform echipării.","Necesită RLS; nu activa pe vehicule fără hardware-ul necesar.","Golf/Golf Plus 5K/52 și platforme PQ35 compatibile",1,s2),
      ("Staging / Needle Sweep - Golf 5K","Adaptation","17","[17-Instruments] > [Adaptation-10] > Staging","Activează testul acelor la pornire.","Cluster care expune canalul Staging.","1) 17-Instruments. 2) Adaptation-10. 3) Alege Staging. 4) New value = On. 5) Save. 6) Ciclează contactul și verifică.","Acele fac sweep la pornire.","Nu este suportat de toate clusterele.","Golf/Golf Plus 5K/52 cu cluster compatibil",1,s2),
      ("Staging / Needle Sweep - Audi 8K/8T","Long Coding","17","[17-Instruments] > [Coding-07] > [Long Coding Helper]","Activează Gauge Test/Needle Sweep.","Cluster compatibil; coding original salvat.","1) 17-Instruments. 2) Coding-07 > Long Coding Helper. 3) Activează opțiunea Gauge Test/Needle Sweep active. 4) Do It!. 5) Ciclează contactul.","Needle sweep este executat la pornire.","Nu este suportat de toate instrument clusters.","Audi A4/A5 8K/8T compatibil",1,s3),
      ("Lap Timer - Audi 8K/8T","Long Coding","17","[17-Instruments] > [Coding-07] > [Long Coding Helper]","Activează Lap Timer când clusterul suportă.","Cluster compatibil și backup coding.","1) 17-Instruments. 2) Coding-07 > Long Coding Helper. 3) Activează opțiunea Lap Timer. 4) Do It!. 5) Verifică meniul clusterului.","Lap Timer apare în cluster.","Disponibilitatea depinde de cluster/software.","Audi A4/A5 8K/8T compatibil",1,s3),
      ("Reset service ulei - Golf 5K","Resetări","17","[17-Instruments] > [Adaptation-10] > ESI: Resetting ESI","Resetează Oil Change Service Reminder.","Service efectuat; contact pus; baterie stabilă.","1) 17-Instruments. 2) Adaptation-10. 3) Alege ESI: Resetting ESI. 4) Selectează Reset. 5) Do It!. 6) Ciclează contactul dacă mesajul nu dispare imediat.","Mesajul de service ulei este resetat.","Pentru intervale flexibile și alte tipuri de service folosește SRI Reset și configurația corectă, nu modifica arbitrar canalele.","Golf/Golf Plus 5K/52 și clustere UDS similare",1,s5),
      ("Calibrare clapete Climatronic după motor/modul înlocuit","Calibrări","08","[08-Heating/Air Conditioning] > [Basic Settings-04] > Adapt flap end stops","Calibrează capetele de cursă ale clapetelor HVAC.","Climatronic J255 sau motor clapetă înlocuit; fără blocaj mecanic.","1) 08-Heating/Air Conditioning. 2) Basic Settings-04. 3) Selectează Adapt flap end stops. 4) Go!. 5) Activează Basic Setting cu ON/OFF/Next dacă VCDS cere. 6) Așteaptă aproximativ 20 secunde. 7) Done, Go Back. 8) Șterge DTC și verifică temperaturile/distribuția aerului.","Basic Setting se finalizează corect și clapetele ating capetele de cursă.","Dacă procedura eșuează, verifică motorul clapetei, angrenajele și blocajele mecanice.","Golf 5K Climatronic și controlere compatibile",1,s4),
      ("Codare modul ușă după înlocuire + învățare geam","Codare","42/52","[42/52-Door Elect.] > [Coding-07] + învățare limit stops","Transferă coding-ul original și reînvață pinch protection după înlocuirea modulului ușii.","Modul Generation 1-3 compatibil; Auto-Scan anterior disponibil; WSC/Importer/Equipment non-zero dacă este necesar.","1) Montează modulul compatibil. 2) 42 sau 52 > Coding-07. 3) Introdu coding-ul ORIGINAL din Auto-Scan, nu de pe alt vehicul. 4) Salvează. 5) Rulează geamul complet jos și complet sus pentru învățarea limit stops/pinch protection. 6) Clear DTC. 7) Testează toate funcțiile și fă Auto-Scan final.","Coding acceptat, geamul are one-touch/pinch protection și DTC nu revin.","Codarea diferă după generație și echipare. Exemplu documentat pe unele module: +4096 Folding Mirrors installed MY2008+; nu aplica dacă hardware-ul nu există.","Golf 1K/5K/52 module ușă CAN Gen 1-3",1,s6),
    ]
    for row in rows:
        pid=_proc(con,row)
        t=row[0]
        if "Audi 8K" in t or "Audi 8K/8T" in row[9]: _map(con,pid,"name LIKE '%8K%' OR name LIKE '%8T%'")
        elif "Golf 1K" in t or "ușă" in t: _map(con,pid,"name LIKE '%1K%' OR name LIKE '%5M%'")
        else: _map(con,pid,"name LIKE '%5K%' OR name LIKE '%52%'")
    con.commit()
