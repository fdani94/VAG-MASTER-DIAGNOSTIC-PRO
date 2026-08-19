"""Transmission-specific VCDS procedures. Keep applicability conditional and controller-specific."""


def _src(con, title, url):
    con.execute("INSERT OR IGNORE INTO sources(title,publisher,url,source_type,notes) VALUES(?,?,?,?,?)",
                (title, "Ross-Tech", url, "Oficial/Wiki", "Procedură transmisie VCDS"))
    r=con.execute("SELECT id FROM sources WHERE url=?",(url,)).fetchone()
    return r[0] if r else None


def _proc(con,title,category,path,purpose,pre,steps,success,warn,source_id):
    r=con.execute("SELECT id FROM procedure_library WHERE title=?",(title,)).fetchone()
    vals=(category,"02",path,purpose,pre,steps,success,warn,"Condițional",1,source_id)
    if r:
        con.execute("UPDATE procedure_library SET category=?,module_address=?,vcds_path=?,purpose=?,prerequisites=?,steps=?,success_criteria=?,warnings=?,applicability_rule=?,verified=?,source_id=? WHERE id=?",vals+(r[0],))
        return r[0]
    return con.execute("INSERT INTO procedure_library(title,category,module_address,vcds_path,purpose,prerequisites,steps,success_criteria,warnings,applicability_rule,verified,source_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(title,)+vals).lastrowid


def install(con):
    s01m=_src(con,"Ross-Tech 01M Automatic Transmission","https://wiki.ross-tech.com/wiki/index.php/4-Speed_Automatic_Transmission_(01M)")
    s01j=_src(con,"Ross-Tech 01J Multitronic","https://wiki.ross-tech.com/wiki/index.php/6-Speed_Automatic_Transmission_(01J/Multitronic)")
    s09g=_src(con,"Ross-Tech 09G/09M/09K","https://wiki.ross-tech.com/wiki/index.php/6-Speed_Automatic_Transmission_(09G/09M/09K)")
    s02e=_src(con,"Ross-Tech DSG 02E","https://wiki.ross-tech.com/wiki/index.php/6-Speed_Direct_Shift_Gearbox_(DSG/02E)")

    _proc(con,"01M - Basic Setting transmisie","Transmisie","02-Auto Trans > Basic Settings-04 > Group 000",
          "Reinițializare/adaptare de bază pentru controlerul 01M.",
          "Fără DTC în transmisie; TBA efectuat dacă se aplică; contact ON, motor OFF; nu apăsa accelerația înainte de procedură.",
          "Select 02-Auto Trans; Basic Settings-04; Group 000; Go; apasă accelerația complet 3-5 secunde; Done/Go Back; eliberează pedala.",
          "Procedura se finalizează fără DTC nou; unele controlere nu oferă confirmare explicită.",
          "NUMAI 01M. Nu aplica Group 000 altor transmisii doar fiindcă sunt automate.",s01m)

    _proc(con,"01J Multitronic - Adaptare și test drive","Transmisie","02-Transmission > Adaptation-10 > Channel 00; MVB 010/011",
          "Adaptarea Multitronic după recodare sau înlocuirea componentelor relevante.",
          "Motor pornit; fără DTC; ulei transmisie 60-90°C (dacă nu reușește, Ross-Tech recomandă peste 80°C); condus/frânare la sarcină parțială.",
          "Adaptation Channel 00 > Read > Save; apoi MVB 010 și 011. În D: aprox. 20 m înainte, oprire și ține frâna 10 sec; în R: aprox. 20 m înapoi, oprire și frână 10 sec. Repetă 5-10 cicluri până la ADP OK.",
          "Câmpurile relevante din MVB indică ADP OK.",
          "NUMAI 01J/Multitronic compatibil. Pe A6 4F poate exista Component Protection după înlocuirea TCM; VCDS nu elimină Component Protection.",s01j)

    _proc(con,"09G/09M/09K - Kick-Down Basic Setting","Transmisie","02-Auto Trans > Basic Settings-04 > Group 001",
          "Basic Setting Kick-Down pentru familia Aisin 09G/09M/09K.",
          "Fără DTC în transmisie; TBA efectuat când se aplică; contact ON, motor OFF; nu atinge accelerația.",
          "Select 02-Auto Trans; Basic Settings-04; Group 001; Go; nu apăsa accelerația; așteaptă starea System in Grundeinstellung; Done/Go Back.",
          "System in Grundeinstellung și lipsa DTC-urilor asociate.",
          "NUMAI controlere 09G/09M/09K compatibile. La înlocuirea TCM folosește coding-ul original/diagrama specifică vehiculului.",s09g)

    _proc(con,"02E/DQ250 - Basic Settings complet","Transmisie","02-Transmission > Basic Settings-04",
          "Calibrare toleranțe/ambreiaje după intervenții la DSG 02E/DQ250.",
          "Ulei 30-100°C și nivel corect; selector P; contact ON; motor la ralanti cel puțin un minut; frână apăsată pe toată procedura; accelerația neatinsă; cruise OFF.",
          "Rulează secvența Basic Settings exact în ordinea documentată pentru controler, apoi Defined Test Drive. Pentru calibrarea toleranțelor Ross-Tech documentează Group 061; restul grupurilor depind de etapa procedurii/controler.",
          "Basic Settings finalizate fără eroare și test drive definit complet; adaptările se stabilizează.",
          "NUMAI DSG 02E/DQ250. Salvează Auto-Scan și coding-ul înainte de înlocuirea mecatronicii; unitatea nouă trebuie comandată/confirmată după VIN și PR-codes.",s02e)
    con.commit()
