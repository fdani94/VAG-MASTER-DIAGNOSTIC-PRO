"""ABS/ESP, steering-angle, TPMS and EPB procedures.
Rules are controller/platform specific; never treat a group number as universal.
"""


def _source(con,title,url):
    con.execute("INSERT OR IGNORE INTO sources(title,publisher,url,source_type,notes) VALUES(?,?,?,?,?)",(title,"Ross-Tech",url,"official/wiki","ABS/ESP/steering reference"))
    r=con.execute("SELECT id FROM sources WHERE url=?",(url,)).fetchone(); return r[0] if r else None


def _proc(con,title,path,purpose,pre,steps,success,warnings,rule,src):
    r=con.execute("SELECT id FROM procedure_library WHERE title=?",(title,)).fetchone()
    vals=("ABS / ESP / Steering / TPMS / EPB","03",path,purpose,pre,steps,success,warnings,rule,1,src)
    if r:
        con.execute("UPDATE procedure_library SET category=?,module_address=?,vcds_path=?,purpose=?,prerequisites=?,steps=?,success_criteria=?,warnings=?,applicability_rule=?,verified=?,source_id=? WHERE id=?",vals+(r[0],)); return r[0]
    return con.execute("INSERT INTO procedure_library(title,category,module_address,vcds_path,purpose,prerequisites,steps,success_criteria,warnings,applicability_rule,verified,source_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(title,)+vals).lastrowid


def install(con):
    s_old=_source(con,"Audi A4 8D Bosch 5.3 ABS", "https://wiki.ross-tech.com/wiki/index.php/Audi_A4_(8D)_Brake_Electronics_(Bosch_5.3_ABS/EDS/ASR/ESP)")
    s_mk60=_source(con,"VW Golf 1K MK60 ABS", "https://wiki.ross-tech.com/wiki/index.php/VW_Golf_(1K)_Brake_Electronics_(MK60)")
    s_mk70=_source(con,"VW Golf 1K MK70 ABS", "https://wiki.ross-tech.com/wiki/index.php/VW_Golf_(1K)_Brake_Electronics_(MK70)")
    s_3c=_source(con,"VW Passat 3C Brake Electronics", "https://wiki.ross-tech.com/wiki/index.php/VW_Passat_(3C)_Brake_Electronics")
    s_mqb=_source(con,"VW Golf VII ABS Brakes", "https://wiki.ross-tech.com/wiki/index.php/VW_Golf_VII_(5G/AU)_ABS_Brakes")

    _proc(con,"G85 - Bosch 5.3/5.7 legacy calibration","03-Brake Electronics -> MVB 005 -> Login 40168 -> Basic Settings 001","Calibrare senzor unghi volan pe anumite Bosch 5.3/5.7 ESP.","Volan drept; identificare exacta controller; coding corect.","Verifica MVB 005 field 1 aproape de 0°. Login 40168. Basic Settings Group 001. Verifica DTC dupa procedura.","DTC G85 dispar; valoarea este plauzibila cu rotile drepte.","NU aplica doar dupa anul masinii. Coding-ul ABS poate depinde de chassis, frane, motor, transmisie si PR-codes.","Bosch 5.3/5.7 ESP documentat; conditional dupa controller",s_old)
    _proc(con,"G85 - MK60 calibration","03-Brake Electronics -> Security Access 40168 -> Basic Settings 060","Calibrare G85 pe anumite MK60.","Motor pornit unde procedura o cere; masina dreapta; tensiune stabila.","Security Access 40168; Basic Settings Group 060; apoi verifica Measuring Blocks si Fault Codes.","Basic Setting OK si unghi plauzibil.","MK60 are si calibrari G200/G201/G251 in functie de configuratie. Nu confunda cu MK70 sau MQB.","MK60/PQ35 numai unde controllerul corespunde",s_mk60)
    _proc(con,"G85 - MK70 via Steering Assist","44-Steering Assist -> Basic Settings","Calibrare G85 cand MK70 cere efectuarea procedurii in Steering Assist.","Identifica MK70; volan/roti drepte; fara defect mecanic de geometrie.","Deschide 44-Steering Assist si foloseste procedura G85 disponibila controllerului; verifica apoi 03-ABS.","G85 calibrat si martorii ABS/ESP se sting dupa conditiile cerute.","Pe MK70 procedura nu se face ca MK60 in 03-ABS.","MK70 documentat pe platformele compatibile",s_mk70)
    _proc(con,"TPMS ABS-based reset - MK70","03-Brake Electronics -> Basic Settings 042","Reset TPMS indirect pe anumite MK70.","Presiuni corecte; contact ON.","Basic Settings Group 042; apoi urmeaza secventa butoanelor TPMS + ASR/ESP daca vehiculul o foloseste.","Martor TPMS se stinge dupa reset conform procedurii.","Numai pentru sistemul ABS-based si echiparea documentata; nu pentru senzori directi in roti.","MK70 cu TPMS indirect compatibil",s_mk70)
    _proc(con,"Passat 3C ABS replacement/calibration chain","03-Brake Electronics -> coding + Basic Settings; 53-Parking Brake","Finalizare dupa inlocuire J104 pe Passat 3C.","Auto-Scan si coding vechi salvate; VIN/PR-codes disponibile; tensiune >=12V pentru calibrari.","Codeaza J104; calibreaza G85; apoi G200, G201, G202 si G251 conform controllerului; codeaza J540; efectueaza Parking Brake Function Test.","Fara DTC relevante; ABS/ESP/EPB functionale.","Coding-ul poate necesita PR-codes/SVM. Nu inventa coding din alta masina.","Passat 3C cu sistemul documentat",s_3c)
    _proc(con,"MQB G85 calibration route","44-Steering Assist -> Basic Settings","Calibrare G85 pe sistemele MQB unde ABS indica Address 44.","Identifica platforma/controllerul; roti drepte; tensiune stabila.","Executa calibrarea G85 in 44-Steering Assist; apoi verifica 03-ABS pentru G201/G200/G251 si DTC-uri ramase.","Basic Setting finalizat; valori plauzibile; fara DTC de calibrare.","Pe MQB G85 nu trebuie presupus automat in 03-ABS. Unele functii pot fi protejate pe generatii moderne.","MQB ESC documentat, inclusiv Golf 7-based",s_mqb)
    _proc(con,"MQB EPB open/close rear parking brake","03-ABS -> Basic Settings -> Open/Close Rear Parking Brake","Retragere si inchidere EPB pentru service frane spate pe sistemele MQB compatibile.","Vehicul securizat; incarcator baterie recomandat; controller compatibil confirmat.","Foloseste Basic Settings denumit explicit Open Rear Parking Brake inainte de interventie; dupa montaj foloseste Close Rear Parking Brake si procedura/function test ceruta de controller.","EPB inchis corect, fara DTC, frana de parcare functionala.","Nu aplica procedura 53-EPB de pe platforme mai vechi unui MQB doar fiindca masina are frana electrica.","MQB ESC cu EPB integrat documentat",s_mqb)
    con.commit()
