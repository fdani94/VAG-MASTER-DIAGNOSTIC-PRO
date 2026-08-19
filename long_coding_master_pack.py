from datetime import date


def _source(con,title,url,publisher='Ross-Tech',stype='Oficial',notes=''):
    r=con.execute('SELECT id FROM sources WHERE url=?',(url,)).fetchone()
    if r:return r[0]
    return con.execute('INSERT INTO sources(title,publisher,url,accessed,source_type,notes) VALUES(?,?,?,?,?,?)',
                       (title,publisher,url,date.today().isoformat(),stype,notes)).lastrowid


def _proc(con,title,category,module,path,purpose,prereq,steps,success,warnings,rule,verified,src):
    r=con.execute('SELECT id FROM procedure_library WHERE title=?',(title,)).fetchone()
    if r:return r[0]
    return con.execute('''INSERT INTO procedure_library(title,category,module_address,vcds_path,purpose,prerequisites,steps,success_criteria,warnings,applicability_rule,verified,source_id)
                          VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''',
                       (title,category,module,path,purpose,prereq,steps,success,warnings,rule,verified,src)).lastrowid


def _map(con,pid,where,args=(),app='Exact/Condițional',notes='Salvează Auto-Scan și coding-ul original înainte de modificare.'):
    for r in con.execute('SELECT id FROM generations WHERE '+where,args):
        con.execute('INSERT OR IGNORE INTO vehicle_procedures(generation_id,procedure_id,applicability,notes) VALUES(?,?,?,?)',(r[0],pid,app,notes))


def install(con):
    s5k=_source(con,'VW Golf/Golf Plus 5K/52 Tweaks','https://wiki.ross-tech.com/wiki/index.php/VW_Golf/Golf_Plus_%285K/52%29_Tweaks')
    s36=_source(con,'VW Passat 36 Tweaks','https://wiki.ross-tech.com/wiki/index.php/VW_Passat_%2836%29_Tweaks')
    s8k=_source(con,'Audi A4/A5 8K/8T Tweaks','https://wiki.ross-tech.com/wiki/index.php/Audi_A4/S4/A5/S5_%288K/8T%29_Tweaks')
    s1k=_source(con,'VW Golf/Jetta/Bora 1K/5M Tweaks','https://wiki.ross-tech.com/wiki/index.php/VW_Golf/Jetta/Bora_%281K/5M%29_Tweaks')
    smqb=_source(con,'VW Golf VII 5G/AU','https://wiki.ross-tech.com/wiki/index.php/VW_Golf_VII_%285G/AU%29')
    solx=_source(con,'OLX - servicii VCDS cerute pe piață','https://www.olx.ro/d/oferta/codari-activari-functii-opel-audi-vw-seat-skoda-diagnoza-IDcNlcl.html','OLX','Piață/Comunitate','Folosit doar pentru identificarea funcțiilor cerute; valorile tehnice se verifică separat.')

    rows=[]
    rows.append(('Golf 5K - Windows up/down din telecomandă','Long Coding / Activări','09','[09-Cent. Elect.] > [Adaptation-10] > Channel 006','Activează Comfort Operation pentru geamuri din telecomandă.','Golf 5K/52 cu BCM compatibil.','1) Salvează Auto-Scan. 2) 09-Cent. Elect. 3) Adaptation-10. 4) Channel 006. 5) Read. 6) New Value=1 (On). 7) Test. 8) Save. 9) Testează ținând apăsat Lock/Unlock.','Geamurile răspund la telecomandă fără DTC noi.','Pe unele BCM-uri trebuie activată și opțiunea aferentă din Long Coding Helper.','Golf 5K/52',1,s5k,'name LIKE \'VI 5K%\' OR name LIKE \'III 5F%\''))
    rows.append(('Golf 5K - Rain Closing geamuri/trapă','Long Coding / Activări','09','[09-Cent. Elect.] > [Coding-07] > [Long Coding Helper] > Byte 4 + Sub-System RLS','Închide geamurile/trapa la ploaie dacă există senzor RLS.','Necesită RLS și echipare compatibilă.','1) 09-Cent. Elect. 2) Coding-07 > Long Coding Helper. 3) Byte 4: activează Comfort Operation Windows/Sunroof via Rain Sensor și Rain Closing active. 4) Selectează Sub-System RLS. 5) Activează Rain Closing active. 6) Exit > Do It!. 7) Testează cu RLS.','Funcția apare și lucrează fără DTC.','Nu activa fără RLS montat și funcțional.','Golf 5K/52',1,s5k,'name LIKE \'VI 5K%\''))
    rows.append(('Passat B7/CC - Cornering pe proiectoare','Long Coding / Activări','09','[09-Cent. Elect.] > [Coding-07] > [Long Coding Helper]','Activează Cornering Lights via Front Fog Lights.','Passat 36/CC cu BCM compatibil și proiectoare.','1) 09-Cent. Elect. 2) Coding-07. 3) Long Coding Helper. 4) Caută și bifează Cornering Lights via Front Fog Lights active. 5) Exit. 6) Do It!. 7) Test la viteză mică și cu semnalizare/viraj.','Proiectorul corespunzător se aprinde la viraj fără erori.','Byte-ul exact depinde de versiunea BCM; folosește eticheta din Long Coding Helper.','Passat B7/CC',1,s36,'name LIKE \'B7 36%\' OR name LIKE \'B8 3G%\''))
    rows.append(('Passat B7/CC - DRL pe proiectoare','Long Coding / Activări','09','[09-Cent. Elect.] > [Coding-07] > [Long Coding Helper] > Byte 11/14/15','Folosește proiectoarele ca DRL pe configurații suportate.','Identifică dacă mașina are PRL prin low beam sau DRL separat.','1) Salvează coding. 2) 09 > Coding-07 > Long Coding Helper. 3) Pentru PRL: Byte 11 dezactivează Daytime Running Lights via Low Beam; Byte 14 activează DRL via Fog Lights. 4) Pentru DRL separat: Byte 15 dezactivează DRL separat; Byte 14 activează DRL via Fog Lights. 5) Do It!.','DRL funcționează pe proiectoare conform configurației.','Byte 18 poate influența luminile de poziție; verifică efectul înainte de livrare.','Passat 36 BCM',1,s36,'name LIKE \'B7 36%\''))
    rows.append(('Audi 8K/8T - Needle Sweep / Gauge Test','Long Coding / Activări','17','[17-Instruments] > [Coding-07] > [Long Coding Helper]','Activează testul acelor la punerea contactului.','Cluster compatibil.','1) 17-Instruments. 2) Coding-07. 3) Long Coding Helper. 4) Activează Gauge Test/Needle Sweep active. 5) Exit. 6) Do It!. 7) Ciclare contact.','Acele fac sweep la pornire.','Nu toate clusterele suportă funcția.','Audi 8K/8T/8R',1,s8k,"name LIKE 'B8 8K%' OR chassis LIKE '8R%'") )
    rows.append(('Audi 8K/8T - Lap Timer','Long Coding / Activări','17','[17-Instruments] > [Coding-07] > [Long Coding Helper]','Activează Lap Timer unde clusterul suportă.','Cluster compatibil.','1) 17-Instruments. 2) Coding-07. 3) Long Coding Helper. 4) Activează Lap Timer. 5) Exit > Do It!. 6) Ciclare contact și verifică meniul DIS/FIS.','Lap Timer este disponibil în instrument cluster.','Poate lipsi pe anumite clustere/software.','Audi 8K/8T',1,s8k,"name LIKE 'B8 8K%'") )
    rows.append(('Audi 8K/8T - Auto-Lock 15 km/h','Long Coding / Activări','46','[46-Comfort System] > [Coding-07] > [Long Coding Helper] + [Adaptation-10]','Activează blocarea automată și personalizarea pe cheie.','BCM2 compatibil.','1) 46-Comfort. 2) Coding-07 > Long Coding Helper > Auto-Lock active. 3) Do It!. 4) Adaptation-10: Channel 001-004 pentru cheia dorită. 5) Read. 6) Adaugă +00004 la valoarea existentă. 7) Test/Save.','Auto-Lock funcționează pentru cheia selectată.','Nu înlocui valoarea existentă cu 4; adaugă 4 la suma existentă.','Audi 8K/8T/8R',1,s8k,"platform='MLB' AND year_from>=2008") )
    rows.append(('Audi 8K/8T - Auto-Unlock la scoaterea cheii','Long Coding / Activări','46','[46-Comfort System] > [Coding-07] > [Long Coding Helper] + [Adaptation-10]','Activează Auto-Unlock.','BCM2 compatibil.','1) Activează Auto-Unlock în Long Coding Helper. 2) Adaptation Channel 001-004 pentru cheia dorită. 3) Adaugă +00008 la Stored Value. 4) Test/Save.','Auto-Unlock funcționează pentru cheia configurată.','Valoare aditivă; păstrează celelalte opțiuni existente.','Audi 8K/8T/8R',1,s8k,"platform='MLB' AND year_from>=2008") )
    rows.append(('Golf 1K - Coming Home / Leaving Home','Long Coding / Activări','09','[09-Cent. Elect.] > [Coding-07] > [Long Coding Helper]','Activează Coming Home / Leaving Home în funcție de echipare.','Pentru automat este necesar RLS și de regulă comutator Auto.','1) 09-Cent. Elect. 2) Coding-07 > Long Coding Helper. 3) Activează Coming-Home active și opțiunile de logică dorite. 4) Pentru Leaving Home activează Assistance Driving Light & Leaving Home active / varianta disponibilă. 5) Do It!. 6) Verifică Adaptation pentru durate.','CH/LH lucrează conform dotării.','Fără RLS, Coming Home poate funcționa doar manual prin maneta de fază lungă.','Golf/Jetta/Bora 1K/5M',1,s1k,"name LIKE 'V 1K%'") )
    rows.append(('MQB - Regula de lucru: Adaptation înainte de Long Coding','Long Coding / Activări','09','[09-Cent. Elect.] > [Adaptation-10] / [Coding-07]','Arată unde trebuie căutate activările pe Golf 7/A3 8V/Octavia 5E/Leon 5F și alte MQB.','Auto-Scan + Controller Channel Map salvate.','1) 09-Cent. Elect. 2) Salvează Controller Channel Map. 3) Verifică Adaptation-10 pentru funcția dorită. 4) Folosește Coding-07 doar dacă controllerul are coding real. 5) Pe unele BCM din jurul MY2018+ coding-ul poate fi all zeros și modificările se fac exclusiv în Adaptation.','Funcția este modificată fără a copia coding de pe alt vehicul.','Nu forța Long Coding pe BCM care raportează coding all zeros.','MQB',1,smqb,"platform LIKE 'MQB%'") )

    # Market-demand index: discovery only, not technical bytes/bits.
    market=[
      ('Needle Sweep / Staging','17'),('Cornering Lights','09'),('US Style / Scandinavian DRL','09'),('Mirror Dip la marșarier','52/42'),
      ('Coming Home / Leaving Home','09'),('Auto-Lock / Auto-Unlock','46/09'),('Geamuri din telecomandă','46/09'),('XDS / TSC','03'),
      ('Audi Drive Select / ADS','09/44/5F'),('PDC grafic pe display','10/76/5F'),('Afișare temperatură ulei','17'),('Hidden Menu / meniuri MMI','5F'),
      ('Lumini spate cu DRL','09'),('Meniu lumini ambientale','09/5F'),('Afișare nivel baterie','5F'),('Start/Stop memory/dezactivare unde este suportat','01/09'),
      ('Comenzi volan / MFSW retrofit','16/5F'),('Tempomat retrofit','16/01'),('TPMS retrofit','03/65'),('Xenon retrofit / Headlight Range','09/55'),
      ('Camera marșarier retrofit','5F/6C'),('Portbagaj electric din telecomandă','46/6D')]
    for name,module in market:
        title='CERERE PIAȚĂ - '+name
        pid=_proc(con,title,'Long Coding / Activări',module,'Identifică modulul pe vehicul > verifică Coding/Long Coding/Adaptation disponibil',
                  'Funcție întâlnită frecvent în serviciile de codare VAG; fișa servește drept checklist pentru ce merită verificat pe mașina selectată.',
                  'Verifică dotarea fizică, Auto-Scan, part number și software.','1) Selectează vehiculul. 2) Confirmă modulul relevant în Auto-Scan. 3) Caută funcția în Long Coding Helper și Adaptation. 4) Dacă nu există etichetă/canal potrivit, nu aplica valori de pe altă mașină. 5) Salvează originalul înainte de orice modificare.',
                  'Funcția este activată doar dacă modulul și dotarea o suportă.','Această intrare provine din cererea pieței și NU conține Byte/Bit universal. Folosește doar valori confirmate pentru controllerul real.','Piață VCDS 1996-2024',0,solx)
        _map(con,pid,'year_from<=2024',app='COMUNITATE/PIAȚĂ')

    for title,cat,module,path,purpose,pre,steps,success,warn,rule,ver,src,where in rows:
        pid=_proc(con,title,cat,module,path,purpose,pre,steps,success,warn,rule,ver,src)
        _map(con,pid,where)
    con.commit()
