from datetime import datetime


def _source(con, title, url, notes=''):
    r=con.execute('SELECT id FROM sources WHERE url=?',(url,)).fetchone()
    if r: return r[0]
    c=con.execute('INSERT INTO sources(title,publisher,url,accessed,source_type,notes) VALUES(?,?,?,?,?,?)',(title,'Comunitate VAG',url,datetime.now().date().isoformat(),'COMUNITATE - NECONFIRMAT',notes))
    return c.lastrowid


def _proc(con,row):
    r=con.execute('SELECT id FROM procedure_library WHERE title=?',(row[0],)).fetchone()
    if r:return r[0]
    return con.execute('''INSERT INTO procedure_library(title,category,module_address,vcds_path,purpose,prerequisites,steps,success_criteria,warnings,applicability_rule,verified,source_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''',row).lastrowid


def _map(con,pid,sql,args=()):
    for g in con.execute('SELECT id FROM generations WHERE '+sql,args):
        con.execute('INSERT OR IGNORE INTO vehicle_procedures(generation_id,procedure_id,applicability,notes) VALUES(?,?,?,?)',(g[0],pid,'COMUNITATE - NECONFIRMAT','Fă Auto-Scan și backup Coding/Adaptation înainte. Confirmă part number, software și echiparea. Dacă denumirea/canalul nu există exact, NU aplica.'))


def install(con):
    s_leon=_source(con,'Seat Leon 5F VCDS Adaptions','https://garryscorner.wordpress.com/2017/04/07/seat-leon-5f-vcds-adaptions/','Autorul raportează testare pe Leon 5F 2016; verifică controllerul înainte de aplicare.')
    s_b8=_source(con,'Passat B8 VCDS Tweaks community','https://www.vwwatercooled.com/forum/vw-passat/passat-b8-onwards/97211-vcds-tweaks','MQB; există diferențe între module și ani.')
    s_mqb=_source(con,'MQB VCDS/OBD11 community collection','https://www.trackdaysforum.de/viewtopic.php?t=41','Colecție comunitară; unele setări influențează comportamentul dinamic și nu trebuie aplicate fără validare.')
    s_oct=_source(con,'Octavia 5E useful VCDS adaptations','https://octavia-forum.de/viewtopic.php?t=73705','Listă comunitară de funcții raportate pe Octavia III.')

    rows=[
      ('MQB - Lap Timer cluster Byte 1 Bit 3 (Leon 5F raportat)','Long Coding','17','[17-Instruments] > [Coding-07] > [Long Coding Helper] > Byte 1 > Bit 3','Activează Lap Timer pe clustere compatibile.','MQB/Leon 5F; salvează coding original.','1) 17-Instruments. 2) Coding-07. 3) Long Coding Helper. 4) Byte 1. 5) Activează Bit 3 numai dacă helper-ul îl descrie ca Lap Timer. 6) Do It!. 7) Ciclu contact și verificare meniu.','Lap Timer apare în cluster/MFD.','COMUNITATE - NECONFIRMAT universal. Byte/Bit poate diferi după software; nu aplica dacă eticheta nu corespunde.','Leon 5F/MQB compatibil',0,s_leon),
      ('MQB - Cornering prin proiectoare Leuchte12/13 (Leon 5F raportat)','Adaptation','09','[09-Cent. Elect.] > [Security Access-16] 31347 > [Adaptation-10] > Leuchte12NL/Leuchte13NL','Folosește proiectoarele ca lumină de viraj pe BCM compatibil.','Proiectoare instalate; BCM MQB cu canalele Leuchte; backup Adaptation Map.','1) 09. 2) Security Access 31347 dacă este acceptat. 3) Adaptation. 4) Leuchte12NL LB45 - Lichtfunktion B 12 = Abbiegelicht links. 5) Leuchte13NL RB5/RB45 - Lichtfunktion B 13 = Abbiegelicht rechts. 6) Salvează fiecare canal. 7) Test la viteză mică.','Proiectorul corespunzător se aprinde la viraj în condițiile controllerului.','Nu confunda Abbiegelicht cu Abblendlicht. Denumirea exactă poate varia. COMUNITATE - NECONFIRMAT pe alte modele.','MQB cu BCM Leuchte compatibil',0,s_leon),
      ('MQB - proiectoare la marșarier (Leon 5F raportat)','Adaptation','09','[09-Cent. Elect.] > [Security Access-16] 31347 > [Adaptation-10] > static AFS light-bei Rueckwaertsfahrt','Aprinde luminile statice de viraj/proiectoarele la selectarea marșarierului.','BCM MQB compatibil; backup Adaptation Map.','1) 09. 2) Security Access 31347. 3) Adaptation. 4) Caută static AFS light-bei Rueckwaertsfahrt. 5) Schimbă Off în Double sided numai dacă opțiunea există. 6) Save. 7) Test R.','Ambele lumini configurate se aprind în R.','COMUNITATE - NECONFIRMAT universal; hardware-ul și denumirile diferă.','MQB compatibil',0,s_leon),
      ('MQB - Rain Closing community workflow','Adaptation','09','[09-Cent. Elect.] > [Security Access-16] 31347 > [Adaptation-10] + subsystem RLHS/RLS','Activează închiderea geamurilor la ploaie când senzorul și BCM suportă funcția.','Senzor ploaie compatibil; backup BCM și RLHS/RLS; funcția poate lipsi pe anumite revizii.','1) 09. 2) Security Access 31347 dacă este acceptat. 3) Adaptation: caută Menuesteuerung Regenschliessen și Regenschliessen_ein_aus și activează numai dacă există. 4) Regenschliessen_art = permanent, dacă există. 5) Intră în subsystem RLHS/RLS și activează biții/opțiunile Rain Closing numai dacă Long Coding Helper le identifică. 6) Ciclu contact. 7) Activează funcția în meniul Car dacă apare.','Geamurile se închid la simularea ploii în condițiile suportate.','Funcția este foarte dependentă de senzor/revizie; există rapoarte Passat B8 unde valorile sunt acceptate dar funcția nu lucrează. Nu forța coding-ul.','Golf 7/Passat B8/Octavia 5E/Leon 5F compatibil',0,s_b8),
      ('MQB - listă funcții confort de cercetat per controller','Proceduri','09/17/5F','Vehicle Workspace > caută funcția exactă în Long Coding/Adaptation','Index de funcții comunitare întâlnite pe MQB: rear DRL, DRL menu, needle sweep, fuel quantity to refill, comfort blink, fan display AUTO, CH/LH pe proiectoare, mirror fold, acoustic lock confirmation.','Selectează vehiculul exact și verifică existența canalului în controller.','1) Fă Auto-Scan. 2) Fă Controller Channel Map/Adaptation Map. 3) Caută denumirea funcției. 4) Dacă există exact, salvează valoarea originală. 5) Modifică o singură setare. 6) Test. 7) Dacă nu există, nu încerca un canal de pe alt model.','Funcția lucrează fără DTC noi.','Aceasta este o listă de descoperire, NU o codare universală. Unele funcții cer hardware, parametrizare sau SFD.','MQB',0,s_oct),
    ]
    for row in rows:
        pid=_proc(con,row)
        if 'Leon 5F' in row[0]: _map(con,pid,"name LIKE '%5F%'")
        elif 'Rain Closing' in row[0]: _map(con,pid,"platform LIKE '%MQB%' OR name LIKE '%B8%' OR name LIKE '%5E%' OR name LIKE '%5F%'")
        else: _map(con,pid,"platform LIKE '%MQB%' OR name LIKE '%5E%' OR name LIKE '%5F%' OR name LIKE '%B8%'")
    con.commit()
