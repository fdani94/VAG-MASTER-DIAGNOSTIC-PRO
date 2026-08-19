from autoscan_dtc_pack import _source, _upsert


def install(con):
    """Auto-Scan expansion: ABS/ESP, DSG, CAN/Gateway and coding faults."""
    s_01316 = _source(con, "Ross-Tech 01316 - ABS Control Module", "https://wiki.ross-tech.com/wiki/index.php/01316")
    s_01486 = _source(con, "Ross-Tech 01486 - System Function Test", "https://wiki.ross-tech.com/wiki/index.php/01486")
    s_01130 = _source(con, "Ross-Tech 01130 - ABS Operation", "https://wiki.ross-tech.com/wiki/index.php/01130")
    s_01044 = _source(con, "Ross-Tech 01044 - Control Module Incorrectly Coded", "https://wiki.ross-tech.com/wiki/index.php/01044")
    s_p1847 = _source(con, "Ross-Tech 18255/P1847 - Check ABS DTC Memory", "https://wiki.ross-tech.com/wiki/index.php/18255/P1847/006215")
    s_p1853 = _source(con, "Ross-Tech 18261/P1853 - Implausible Message ABS", "https://wiki.ross-tech.com/wiki/index.php/18261/P1853/006227")
    s_dsg = _source(con, "Ross-Tech DSG 02E Basic Settings", "https://wiki.ross-tech.com/wiki/index.php/6-Speed_Direct_Shift_Gearbox_%28DSG/02E%29")

    _upsert(con, "01316", "ABS Control Module - No Signal/Communication / Check DTC Memory",
        "Alt modul nu comunică cu J104 sau indică faptul că memoria de erori ABS trebuie verificată.",
        "Martori ABS/ESP; erori secundare în motor, transmisie, steering sau gateway.",
        "DTC în 03-ABS; alimentare/masă J104; cablaj sau CAN; conector ABS.",
        "J104 - Brake Electronics Control Module", "Integrat de regulă în ansamblul hidraulic ABS din compartimentul motor; poziția exactă depinde de platformă.",
        "Status comunicație CAN; pe platforme vechi MVB 125+ pot arăta partenerii de comunicație.",
        "03-ABS trebuie să răspundă stabil. Dacă răspunde, erorile din el au prioritate față de 01316 memorat în alte module.",
        "Auto-Scan > [03-Brake Electronics] > [Fault Codes-02]; dacă nu comunică, verifică alimentări/mase/CAN.",
        "1) Intră direct în 03-ABS. 2) Dacă răspunde, repară DTC-urile din ABS. 3) Dacă nu răspunde, verifică siguranțe, alimentare, masă și CAN. 4) Verifică Gateway pentru alte module offline.",
        "Repară eroarea principală din ABS sau comunicația. Nu înlocui J104 înainte de verificarea alimentărilor și rețelei.",
        "După înlocuirea J104 pot fi necesare coding, G85/basic settings și alte calibrări specifice sistemului ABS.", "Ridicat", 1, s_01316)

    _upsert(con, "01486", "ESP System Function Test Activated",
        "Testul funcțional ESP/Brake Electronics a fost activat și nu a fost finalizat.",
        "Martori ABS/ESP aprinși după lucrări sau basic settings.",
        "Function Test activat; alte DTC-uri powertrain pot împiedica finalizarea.",
        "J104 ABS/ESP + G200/G202/G201", "Senzorii pot fi integrați/separați în funcție de generație; J104 este la unitatea ABS.",
        "Brake pressure, steering angle, lateral acceleration și yaw rate, dacă sunt disponibile.",
        "Ross-Tech cere ca 01486 să fie singura eroare din 03-ABS și 44-Steering Assist să fie fără erori înainte de test.",
        "[03-Brake Electronics] > Fault Codes; apoi ESP System Function Test conform sistemului.",
        "1) Repară celelalte DTC-uri. 2) Motor pornit, vehicul staționar. 3) Inițiază/continuă Function Test. 4) Execută testul rutier controlat conform procedurii sistemului. 5) Rescanează.",
        "Nu schimba senzori doar pentru 01486; codul indică în primul rând un test activ/nefinalizat.",
        "După lucrări majore ABS poate fi necesar Function Test și/sau calibrări G85/G200/G202/G201 în funcție de sistem.", "Mediu", 1, s_01486)

    _upsert(con, "01130", "ABS Operation - Implausible Signal",
        "J104 detectează o condiție implauzibilă în funcționarea ABS.",
        "Martor ABS/ESP; codul poate rămâne până la un test drive.",
        "Siguranțe; retrofit/modificări incompatibile; cablaj/interferențe; J104.",
        "J104 / alimentare și rețea ABS", "Unitatea ABS în compartiment motor; verifică și traseele electrice către aceasta.",
        "Tensiune alimentare, wheel speeds și status comunicație; verifică discrepanțe evidente.",
        "Ross-Tech notează că DTC-ul poate necesita rulare peste aproximativ 20 km/h pentru a putea fi șters după remediere.",
        "[03-Brake Electronics] > [Fault Codes-02] + Measuring Values pentru wheel speed/alimentare.",
        "1) Verifică siguranțe. 2) Elimină temporar retrofituri suspecte. 3) Inspectează cablajul J104. 4) Compară wheel speeds. 5) După remediere efectuează test drive și rescanează.",
        "Repară alimentarea/cablajul sau cauza confirmată. J104 este ultima suspiciune după verificările externe.",
        "Dacă J104 este înlocuit, păstrează Auto-Scan/coding-ul vechi și execută calibrările cerute de sistem.", "Ridicat", 1, s_01130)

    _upsert(con, "01044", "Control Module Incorrectly Coded",
        "Un modul este codat incompatibil cu echiparea/configurația vehiculului.",
        "Funcționalitate redusă; MIL sau DTC-uri în module dependente.",
        "Coding greșit; Gateway Installation List incorect; modul/variantă hardware nepotrivită.",
        "Modulul care memorează DTC + 19-CAN Gateway", "Depinde de adresa modulului raportată în Auto-Scan.",
        "Coding curent, part number/component, Gateway Installation List și DTC-uri asociate.",
        "Coding-ul trebuie să corespundă exact echipării. Unele platforme au excepții/bug-uri documentate, deci nu modifica orbește coding-ul.",
        "Modulul cu DTC > [Coding-07]; [19-CAN Gateway] > Installation List/Coding unde este relevant.",
        "1) Salvează Auto-Scan. 2) Compară part number și coding cu echiparea. 3) Verifică Installation List. 4) Verifică module unreachable. 5) Corectează doar opțiunea confirmată și rescanează.",
        "Corectează coding-ul/configurația sau montează modulul compatibil. Nu copia coding de la altă mașină fără verificarea echipării.",
        "După modul nou: coding/long coding, eventual basic settings/adaptations și verificarea tuturor DTC-urilor dependente.", "Ridicat", 1, s_01044)

    for code in ("P1847", "18255", "006215"):
        _upsert(con, code, "Please Check DTC Memory of ABS Controller",
            "Un modul powertrain cere verificarea memoriei de erori din Brake Electronics J104.",
            "MIL și/sau erori secundare în transmisie/motor.", "Există un DTC relevant în 03-Brake Electronics.",
            "J104 - Brake Electronics", "Unitatea ABS/ESP.", "Fault Codes din 03-ABS.",
            "Rezolvă întâi DTC-ul principal din ABS; acest cod este de regulă secundar.",
            "[03-Brake Electronics] > [Fault Codes-02]", "1) Deschide 03-ABS. 2) Notează toate DTC-urile. 3) Repară eroarea principală. 4) Șterge erorile și rescanează modulele dependente.",
            "Repararea ABS rezolvă de regulă și codul secundar.", "Nu înlocui transmisia/ECU pe baza acestui cod secundar.", "Mediu", 1, s_p1847)

    for code in ("P1853", "18261", "006227"):
        _upsert(con, code, "Powertrain Data Bus - Implausible Message from ABS Controller",
            "Un modul powertrain primește date ABS implauzibile.", "MIL; transmisia poate memora eroarea după schimbări de module/coding.",
            "Cablaj/conector CAN; J104; listă parteneri comunicație schimbată după înlocuire/update.",
            "CAN Powertrain / J104", "Rețeaua CAN între ABS, transmisie, motor și gateway/instruments, în funcție de platformă.",
            "MVB 125+ pe platformele care le suportă; status parteneri CAN și DTC 03-ABS.",
            "Partenerii CAN trebuie să fie prezenți și mesajele plauzibile.",
            "Module implicate > Measuring Blocks 125+ unde există; [03-ABS] > Fault Codes.",
            "1) Verifică DTC ABS. 2) Verifică CAN/conectori. 3) Confirmă coding/configurația după înlocuiri. 4) Pe DSG 02E, Ross-Tech documentează Reset ESP & Tip Cruise Control Installation în Basic Settings Group 069 când este cazul.",
            "Repară rețeaua/coding-ul sau cauza din ABS. Aplică resetul DSG numai pe 02E și numai când situația corespunde.",
            "Pentru DSG 02E: după intervenție pot fi necesare Basic Settings și Defined Test Drive conform procedurii Ross-Tech.", "Ridicat", 1, s_p1853)

    con.commit()
