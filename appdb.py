import csv
import json
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QStandardPaths

APP_NAME = "VAG MASTER Diagnostic PRO"
APP_VERSION = "5.0.0"


def app_data_dir():
    base = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
    path = Path(base) if base else Path.home() / ".vag_master_pro"
    path.mkdir(parents=True, exist_ok=True)
    return path


APP_DATA = app_data_dir()
DB_PATH = APP_DATA / "vag_master_super_v5.db"
LOGO_PATH = APP_DATA / "custom_logo.png"

SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS brands(id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL);
CREATE TABLE IF NOT EXISTS models(id INTEGER PRIMARY KEY, brand_id INTEGER NOT NULL REFERENCES brands(id), name TEXT NOT NULL, UNIQUE(brand_id,name));
CREATE TABLE IF NOT EXISTS generations(id INTEGER PRIMARY KEY, model_id INTEGER NOT NULL REFERENCES models(id), name TEXT NOT NULL, year_from INTEGER, year_to INTEGER, chassis TEXT DEFAULT '', platform TEXT DEFAULT '', ross_tech_url TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS engines(id INTEGER PRIMARY KEY, code TEXT UNIQUE NOT NULL, fuel TEXT DEFAULT '', displacement REAL, power_hp INTEGER, family TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS vehicle_engines(generation_id INTEGER REFERENCES generations(id), engine_id INTEGER REFERENCES engines(id), year_from INTEGER, year_to INTEGER, PRIMARY KEY(generation_id,engine_id));
CREATE TABLE IF NOT EXISTS modules(id INTEGER PRIMARY KEY, address TEXT NOT NULL, name TEXT NOT NULL, family TEXT DEFAULT '', protocol TEXT DEFAULT '', description TEXT DEFAULT '', UNIQUE(address,name));
CREATE TABLE IF NOT EXISTS generation_modules(generation_id INTEGER REFERENCES generations(id), module_id INTEGER REFERENCES modules(id), applicability TEXT DEFAULT 'Posibil', PRIMARY KEY(generation_id,module_id));
CREATE TABLE IF NOT EXISTS sources(id INTEGER PRIMARY KEY, title TEXT NOT NULL, publisher TEXT DEFAULT '', url TEXT UNIQUE NOT NULL, accessed TEXT DEFAULT '', source_type TEXT DEFAULT 'Oficial', notes TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS procedure_library(
 id INTEGER PRIMARY KEY,
 title TEXT NOT NULL,
 category TEXT NOT NULL,
 module_address TEXT DEFAULT '',
 vcds_path TEXT DEFAULT '',
 purpose TEXT DEFAULT '',
 prerequisites TEXT DEFAULT '',
 steps TEXT DEFAULT '',
 success_criteria TEXT DEFAULT '',
 warnings TEXT DEFAULT '',
 applicability_rule TEXT DEFAULT 'Condițional',
 verified INTEGER DEFAULT 1,
 source_id INTEGER REFERENCES sources(id)
);
CREATE TABLE IF NOT EXISTS vehicle_procedures(
 generation_id INTEGER REFERENCES generations(id),
 procedure_id INTEGER REFERENCES procedure_library(id),
 applicability TEXT DEFAULT 'Condițional',
 notes TEXT DEFAULT '',
 PRIMARY KEY(generation_id,procedure_id)
);
CREATE TABLE IF NOT EXISTS dtcs(
 id INTEGER PRIMARY KEY,
 code TEXT UNIQUE NOT NULL,
 title TEXT NOT NULL,
 description TEXT DEFAULT '',
 symptoms TEXT DEFAULT '',
 causes TEXT DEFAULT '',
 diagnosis TEXT DEFAULT '',
 repair TEXT DEFAULT '',
 severity TEXT DEFAULT 'Mediu',
 verified INTEGER DEFAULT 0,
 source_id INTEGER REFERENCES sources(id)
);
CREATE TABLE IF NOT EXISTS coding(id INTEGER PRIMARY KEY,title TEXT,module_address TEXT,coding_type TEXT,effect TEXT,applicability TEXT,restore_method TEXT,warnings TEXT,verified INTEGER DEFAULT 0,source_id INTEGER REFERENCES sources(id));
CREATE TABLE IF NOT EXISTS adaptations(id INTEGER PRIMARY KEY,title TEXT,module_address TEXT,channel TEXT,effect TEXT,applicability TEXT,restore_method TEXT,warnings TEXT,verified INTEGER DEFAULT 0,source_id INTEGER REFERENCES sources(id));
CREATE TABLE IF NOT EXISTS notes(id INTEGER PRIMARY KEY,entity_type TEXT,entity_key TEXT,note TEXT,created_at TEXT);
CREATE TABLE IF NOT EXISTS favorites(id INTEGER PRIMARY KEY,entity_type TEXT,entity_key TEXT,label TEXT,created_at TEXT,UNIQUE(entity_type,entity_key));
CREATE TABLE IF NOT EXISTS activity_log(id INTEGER PRIMARY KEY,action TEXT,entity_type TEXT,entity_key TEXT,details TEXT,created_at TEXT);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT DEFAULT '');
CREATE INDEX IF NOT EXISTS idx_gen_model ON generations(model_id);
CREATE INDEX IF NOT EXISTS idx_vehicle_proc ON vehicle_procedures(generation_id);
CREATE INDEX IF NOT EXISTS idx_proc_cat ON procedure_library(category);
CREATE INDEX IF NOT EXISTS idx_dtc_code ON dtcs(code);
"""


def connect_db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    con.executescript(SCHEMA)
    seed(con)
    return con


def scalar(con, sql, args=()):
    row = con.execute(sql, args).fetchone()
    return row[0] if row else 0


def log(con, action, entity_type="", entity_key="", details=""):
    con.execute("INSERT INTO activity_log(action,entity_type,entity_key,details,created_at) VALUES(?,?,?,?,?)",
                (action, entity_type, str(entity_key), details, datetime.now().isoformat(timespec="seconds")))
    con.commit()


def _source(con, title, url, notes=""):
    row = con.execute("SELECT id FROM sources WHERE url=?", (url,)).fetchone()
    if row:
        return row[0]
    cur = con.execute("INSERT INTO sources(title,publisher,url,accessed,source_type,notes) VALUES(?,?,?,?,?,?)",
                      (title, "Ross-Tech", url, datetime.now().date().isoformat(), "Oficial", notes))
    return cur.lastrowid


def seed(con):
    src_main = _source(con, "VCDS Function Index", "https://www.ross-tech.com/vcds/tour/main_screen.php", "Index oficial al funcțiilor VCDS")
    src_diag = _source(con, "Diagnostic Procedures", "https://wiki.ross-tech.com/wiki/index.php/Diagnostic_Procedures", "Catalog oficial pe marcă și chassis")
    src_common = _source(con, "Common Procedures", "https://wiki.ross-tech.com/wiki/index.php/Common_Procedures", "Proceduri comune Ross-Tech")
    src_tba = _source(con, "Throttle Body Alignment", "https://wiki.ross-tech.com/wiki/index.php/Throttle_Body_Alignment_(TBA)")
    src_epb = _source(con, "Electro-Mechanical Parking Brake", "https://wiki.ross-tech.com/wiki/index.php/Working_on_the_Electro-Mechanical_Parking_Brake_(EPB)")
    src_at = _source(con, "Automatic Transmission Basic Settings", "https://wiki.ross-tech.com/wiki/index.php/Automatic_Transmission_Basic_Settings")
    src_level = _source(con, "Suspension Level Control Calibration", "https://wiki.ross-tech.com/wiki/index.php/Suspension_Level_Control_Calibration_(non-UDS)")

    if scalar(con, "SELECT COUNT(*) FROM brands") == 0:
        for b in ["Volkswagen", "Audi", "Škoda", "SEAT / Cupra"]:
            con.execute("INSERT INTO brands(name) VALUES(?)", (b,))

    brand_ids = {r["name"]: r["id"] for r in con.execute("SELECT id,name FROM brands")}
    model_names = {
        "Volkswagen": ["Golf", "Passat", "Polo", "Tiguan", "Touran", "Caddy", "Touareg", "Transporter", "Sharan", "Phaeton", "Scirocco", "Eos"],
        "Audi": ["A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "Q3", "Q5", "Q7", "TT"],
        "Škoda": ["Fabia", "Octavia", "Superb", "Roomster"],
        "SEAT / Cupra": ["Ibiza", "Leon", "Altea", "Alhambra", "Toledo", "Exeo"]
    }
    for brand, names in model_names.items():
        for name in names:
            con.execute("INSERT OR IGNORE INTO models(brand_id,name) VALUES(?,?)", (brand_ids[brand], name))

    if scalar(con, "SELECT COUNT(*) FROM generations") == 0:
        G = [
        ("Volkswagen","Golf","IV 1J/9M",1998,2006,"1J/9M","PQ34","https://wiki.ross-tech.com/wiki/index.php/VW_Golf/Jetta/Bora_(1J/9M)"),
        ("Volkswagen","Golf","V 1K/5M",2004,2009,"1K/5M","PQ35","https://wiki.ross-tech.com/wiki/index.php/VW_Golf_(1K)"),
        ("Volkswagen","Golf","VI 5K/52/AJ",2009,2013,"5K/52/AJ","PQ35","https://wiki.ross-tech.com/wiki/index.php/VW_Golf_(5K)"),
        ("Volkswagen","Golf","VII 5G/AU",2013,2020,"5G/AU","MQB","https://wiki.ross-tech.com/wiki/index.php/VW_Golf_VII_(5G/AU)"),
        ("Volkswagen","Passat","B5 3B",1997,2005,"3B","PL45","https://wiki.ross-tech.com/wiki/index.php/VW_Passat_(3B)"),
        ("Volkswagen","Passat","B6 3C/AN",2006,2011,"3C/AN","PQ46","https://wiki.ross-tech.com/wiki/index.php/VW_Passat_(3C)"),
        ("Volkswagen","Passat","B7 36",2011,2015,"36","PQ46","https://wiki.ross-tech.com/wiki/index.php/Diagnostic_Procedures"),
        ("Volkswagen","Polo","6N",1994,2002,"6N","PQ24","https://wiki.ross-tech.com/wiki/index.php/VW_Polo_(6N)"),
        ("Volkswagen","Polo","9N",2002,2009,"9N","PQ24","https://wiki.ross-tech.com/wiki/index.php/VW_Polo_(9N)"),
        ("Volkswagen","Polo","6R",2009,2017,"6R","PQ25","https://wiki.ross-tech.com/wiki/index.php/Diagnostic_Procedures"),
        ("Volkswagen","Tiguan","5N/AX",2007,2016,"5N/AX","PQ35","https://wiki.ross-tech.com/wiki/index.php/VW_Tiguan_(5N)"),
        ("Volkswagen","Touran","1T",2003,2015,"1T","PQ35","https://wiki.ross-tech.com/wiki/index.php/VW_Touran_(1T)"),
        ("Volkswagen","Caddy","2K",2004,2020,"2K","PQ35","https://wiki.ross-tech.com/wiki/index.php/VW_Caddy_(2K)"),
        ("Volkswagen","Touareg","7L/A9",2003,2010,"7L/A9","PL71","https://wiki.ross-tech.com/wiki/index.php/VW_Touareg_(7L)"),
        ("Volkswagen","Touareg","7P/BP",2010,2018,"7P/BP","PL72","https://wiki.ross-tech.com/wiki/index.php/VW_Touareg_(7P)"),
        ("Volkswagen","Transporter","T5 7H/7J",2003,2009,"7H/7J","T5","https://wiki.ross-tech.com/wiki/index.php/VW_Transporter_(7H)"),
        ("Volkswagen","Transporter","T5 GP 7E/7F",2010,2015,"7E/7F","T5","https://wiki.ross-tech.com/wiki/index.php/VW_Transporter_(7E)"),
        ("Volkswagen","Phaeton","3D",2002,2016,"3D","D1","https://wiki.ross-tech.com/wiki/index.php/VW_Phaeton_(3D)"),
        ("Volkswagen","Scirocco","13",2008,2017,"13","PQ35","https://wiki.ross-tech.com/wiki/index.php/VW_Scirocco_(13)"),
        ("Audi","A3","8L",1997,2003,"8L","PQ34","https://wiki.ross-tech.com/wiki/index.php/Audi_A3_(8L)"),
        ("Audi","A3","8P/FM",2004,2013,"8P/FM","PQ35","https://wiki.ross-tech.com/wiki/index.php/Audi_A3_(8P)"),
        ("Audi","A3","8V/FF",2013,2020,"8V/FF","MQB","https://wiki.ross-tech.com/wiki/index.php/Audi_A3_(8V)"),
        ("Audi","A4","B5 8D",1995,2001,"8D","PL45","https://wiki.ross-tech.com/wiki/index.php/Audi_A4_(8D)"),
        ("Audi","A4","B6/B7 8E/8H",2001,2008,"8E/8H","PL46","https://wiki.ross-tech.com/wiki/index.php/Audi_A4_(8E)"),
        ("Audi","A4","B8 8K/FL",2008,2016,"8K/FL","MLB","https://wiki.ross-tech.com/wiki/index.php/Audi_A4_(8K)"),
        ("Audi","A6","C5 4B",1997,2006,"4B","PL45","https://wiki.ross-tech.com/wiki/index.php/Audi_A6_(4B)"),
        ("Audi","A6","C6 4F/FB",2005,2011,"4F/FB","PL47","https://wiki.ross-tech.com/wiki/index.php/Audi_A6_(4F)"),
        ("Audi","A6","C7 4G/FC",2011,2018,"4G/FC","MLB","https://wiki.ross-tech.com/wiki/index.php/Audi_A6_(4G)"),
        ("Audi","A8","4E",2003,2010,"4E","D3","https://wiki.ross-tech.com/wiki/index.php/Audi_A8_(4E)"),
        ("Audi","Q5","8R/FP",2008,2017,"8R/FP","MLB","https://wiki.ross-tech.com/wiki/index.php/Audi_Q5_(8R)"),
        ("Audi","Q7","4L/FE",2007,2015,"4L/FE","PL71","https://wiki.ross-tech.com/wiki/index.php/Audi_Q7_(4L)"),
        ("Škoda","Fabia","6Y",2000,2007,"6Y","PQ24","https://wiki.ross-tech.com/wiki/index.php/Skoda_Fabia_(6Y)"),
        ("Škoda","Fabia","5J",2007,2014,"5J","PQ25","https://wiki.ross-tech.com/wiki/index.php/Diagnostic_Procedures"),
        ("Škoda","Octavia","I 1U",1997,2010,"1U","PQ34","https://wiki.ross-tech.com/wiki/index.php/Skoda_Octavia_(1U)"),
        ("Škoda","Octavia","II 1Z",2005,2013,"1Z","PQ35","https://wiki.ross-tech.com/wiki/index.php/Skoda_Octavia_(1Z)"),
        ("Škoda","Superb","I 3U",2002,2008,"3U","PL45+","https://wiki.ross-tech.com/wiki/index.php/Diagnostic_Procedures"),
        ("Škoda","Superb","II 3T",2008,2015,"3T","PQ46","https://wiki.ross-tech.com/wiki/index.php/Diagnostic_Procedures"),
        ("SEAT / Cupra","Ibiza","6L",2002,2008,"6L","PQ24","https://wiki.ross-tech.com/wiki/index.php/Seat_Ibiza_(6L)"),
        ("SEAT / Cupra","Ibiza","6J",2008,2017,"6J","PQ25","https://wiki.ross-tech.com/wiki/index.php/Diagnostic_Procedures"),
        ("SEAT / Cupra","Leon","1M",2000,2006,"1M","PQ34","https://wiki.ross-tech.com/wiki/index.php/Diagnostic_Procedures"),
        ("SEAT / Cupra","Leon","1P",2006,2012,"1P","PQ35","https://wiki.ross-tech.com/wiki/index.php/Seat_Leon_(1P)"),
        ("SEAT / Cupra","Altea","5P",2004,2015,"5P","PQ35","https://wiki.ross-tech.com/wiki/index.php/Seat_Altea_(5P)"),
        ("SEAT / Cupra","Alhambra","7M",1996,2010,"7M","7M","https://wiki.ross-tech.com/wiki/index.php/Seat_Alhambra_(7M)"),
        ("SEAT / Cupra","Exeo","3R",2009,2013,"3R","PL46","https://wiki.ross-tech.com/wiki/index.php/Seat_Exeo_(3R)"),
        ]
        for brand, model, gen, yf, yt, chassis, platform, url in G:
            mid = scalar(con, "SELECT m.id FROM models m JOIN brands b ON b.id=m.brand_id WHERE b.name=? AND m.name=?", (brand, model))
            if mid:
                con.execute("INSERT INTO generations(model_id,name,year_from,year_to,chassis,platform,ross_tech_url) VALUES(?,?,?,?,?,?,?)", (mid,gen,yf,yt,chassis,platform,url))

    if scalar(con, "SELECT COUNT(*) FROM engines") == 0:
        engines = [
            ("1Z","Diesel",1.9,90,"EA180"),("AHU","Diesel",1.9,90,"EA180"),("AFN","Diesel",1.9,110,"EA180"),("ALH","Diesel",1.9,90,"EA180"),
            ("ASZ","Diesel",1.9,130,"EA188"),("ARL","Diesel",1.9,150,"EA188"),("BKC","Diesel",1.9,105,"EA188"),("BXE","Diesel",1.9,105,"EA188"),("BLS","Diesel",1.9,105,"EA188"),
            ("CAYC","Diesel",1.6,105,"EA189"),("CBAB","Diesel",2.0,140,"EA189"),("CFFB","Diesel",2.0,140,"EA189"),("CFHC","Diesel",2.0,140,"EA189"),("CAGA","Diesel",2.0,143,"EA189"),("CJCA","Diesel",2.0,143,"EA189"),
            ("BSE","Benzină",1.6,102,"EA113"),("AUM","Benzină",1.8,150,"EA113"),("AUQ","Benzină",1.8,180,"EA113"),("AXX","Benzină",2.0,200,"EA113"),("BWA","Benzină",2.0,200,"EA113"),
            ("CAXA","Benzină",1.4,122,"EA111"),("CAVD","Benzină",1.4,160,"EA111"),("CHPA","Benzină",1.4,140,"EA211"),("CJSA","Benzină",1.8,180,"EA888")
        ]
        con.executemany("INSERT INTO engines(code,fuel,displacement,power_hp,family) VALUES(?,?,?,?,?)", engines)

    if scalar(con, "SELECT COUNT(*) FROM modules") == 0:
        mods = [("01","Engine","Powertrain","KWP/CAN/UDS"),("02","Auto Trans","Powertrain","KWP/CAN/UDS"),("03","ABS Brakes","Chassis","KWP/CAN/UDS"),("08","HVAC","Body","KWP/CAN/UDS"),("09","Central Electrics","Body","KWP/CAN/UDS"),("15","Airbags","Safety","KWP/CAN/UDS"),("16","Steering Wheel","Body","KWP/CAN/UDS"),("17","Instruments","Body","KWP/CAN/UDS"),("19","CAN Gateway","Network","CAN/UDS"),("25","Immobilizer","Security","KWP/CAN"),("34","Level Control","Chassis","KWP/CAN/UDS"),("44","Steering Assist","Chassis","KWP/CAN/UDS"),("46","Comfort System","Body","KWP/CAN"),("53","Parking Brake","Chassis","CAN/UDS"),("55","Headlight Range","Body","KWP/CAN/UDS"),("5F","Information Electronics","Infotainment","UDS"),("61","Battery Regulation","Powertrain","CAN/UDS"),("65","Tire Pressure","Chassis","CAN/UDS"),("76","Parking Aid","Body","KWP/CAN/UDS")]
        con.executemany("INSERT INTO modules(address,name,family,protocol) VALUES(?,?,?,?)", mods)

    seed_procedure_library(con, src_main, src_common, src_tba, src_epb, src_at, src_level)
    map_procedures_to_vehicles(con)
    seed_dtcs(con, src_diag)
    con.commit()


def seed_procedure_library(con, src_main, src_common, src_tba, src_epb, src_at, src_level):
    if scalar(con, "SELECT COUNT(*) FROM procedure_library"):
        return
    P = [
    ("Auto-Scan complet","Diagnostic","","Auto-Scan","Identifică toate modulele și DTC-urile prezente.","Interfață conectată; contact pus.","Pornește VCDS > Auto-Scan > selectează platforma/chassis când este disponibil > Start. Salvează raportul înainte de orice ștergere.","Raport complet salvat.","Nu șterge erorile înainte de documentare.","General",1,src_main),
    ("Citire DTC modul","Diagnostic","","[Select] > [modul] > [Fault Codes - 02]","Citește erorile unui modul.","Contact pus și comunicație stabilă.","Intră în modulul dorit, deschide Fault Codes - 02 și notează codul, statusul și freeze-frame dacă există.","DTC afișate și documentate.","Nu interpreta un DTC fără contextul modulului.","General",1,src_main),
    ("Ștergere DTC controlată","Diagnostic","","[Select] > [modul] > [Fault Codes - 02] > [Clear Codes - 05]","Șterge erorile după reparație.","Salvează Auto-Scan înainte; repară cauza.","După reparație, șterge DTC și repetă scanarea/road-testul.","DTC nu revine.","Ștergerea erorii nu repară defectul.","General",1,src_main),
    ("Measuring Blocks","Live Data","","[Select] > [modul] > [Meas. Blocks - 08]","Vizualizează valori live la module non-UDS.","Modul compatibil cu Measuring Blocks.","Alege grupul documentat; compară valorile la condițiile specificate.","Valori coerente cu procedura.","Nu derula grupuri necunoscute în Basic Settings.","Condițional",1,src_main),
    ("Advanced Measuring Values","Live Data","","[Select] > [modul] > [Adv. Meas. Values]","Selectează parametri live după denumire.","Modul compatibil.","Bifează parametrii relevanți, urmărește simultan specified/actual și condițiile de test.","Date live stabile.","Interpretarea depinde de motor/ECU.","Condițional",1,src_main),
    ("Data Logging","Live Data","","[Select] > [modul] > valori > [Log]","Înregistrează valori pentru analiză.","Alege un set mic de parametri relevanți.","Pornește logul, execută testul în condiții sigure, oprește și salvează CSV.","Fișier de log creat.","Nu manipula laptopul în timp ce conduci.","General",1,src_main),
    ("Output Tests","Test actuatori","","[Select] > [modul] > [Output Tests - 03]","Testează ieșiri electrice și actuatori.","Vehicul securizat; modul compatibil.","Pornește Output Tests și avansează cu Start/Next; observă activarea componentelor.","Actuatorul reacționează conform așteptărilor.","Secvența este controlată de modul; unele teste rulează o singură dată pe sesiune.","Condițional",1,src_main),
    ("Basic Settings - flux general","Basic Settings","","[Select] > [modul] > [Basic Settings - 04]","Rulează o calibrare/învățare documentată.","Respectă condițiile procedurii specifice.","Selectează numai grupul sau funcția documentată și urmărește criteriul de finalizare.","Finished Correctly / ADP OK sau criteriul documentat.","Basic Settings poate comanda actuatori; nu experimenta cu grupuri necunoscute.","Condițional",1,src_main),
    ("Coding - backup și modificare","Coding","","[Select] > [modul] > [Coding - 07]","Modifică configurarea unui modul.","Auto-Scan și coding original salvate.","Salvează valoarea originală, modifică doar opțiunea documentată, aplică și verifică DTC.","Funcția lucrează și nu apar DTC noi.","Nu copia coding de pe alt vehicul fără verificarea hardware/software/PR-code.","Condițional",1,src_main),
    ("Long Coding Helper","Coding","","[Select] > [modul] > [Coding - 07] > Long Coding Helper","Editează byte/bit pe module compatibile.","Coding original salvat.","Modifică un singur bit/opțiune documentată, transferă coding-ul și testează.","Coding acceptat.","Etichetele depind de versiunea software a modulului.","Condițional",1,src_main),
    ("Adaptation - flux general","Adaptation","","[Select] > [modul] > [Adaptation - 10]","Schimbă o valoare de adaptare.","Salvează Auto-Scan și valoarea stocată.","Caută canalul documentat, citește Stored Value, introdu New Value, Test când este disponibil și Save.","Valoare acceptată și funcție verificată.","Păstrează obligatoriu valoarea originală.","Condițional",1,src_main),
    ("Long Adaptation / UDS","Adaptation","","[Select] > [modul] > [Adaptation]","Modifică adaptări denumite pe UDS.","Modul UDS și procedură documentată.","Selectează funcția după nume, citește valoarea originală, modifică și salvează.","Valoare acceptată.","Denumirile diferă între SW versions.","Condițional",1,src_main),
    ("Security Access","Security Access","","[Select] > [modul] > [Security Access - 16]","Deblochează temporar funcții protejate.","Cod documentat pentru modulul exact.","Introdu numai codul documentat pentru ECU/modul și funcția dorită.","Security Access accepted.","Nu ghici coduri; accesul greșit poate bloca temporar funcția.","Condițional",1,src_main),
    ("Login / Coding II","Security Access","","[Select] > [modul] > [Login-11 / Coding II-11]","Acces pe module mai vechi.","Procedură și cod documentate.","Introdu login-ul documentat, apoi continuă procedura necesară.","Login acceptat.","Valorile sunt specifice modulului.","Condițional",1,src_main),
    ("Readiness","Emisii","01","[Select] > [01-Engine] > [Readiness - 15]","Verifică monitoarele OBD de emisii.","Motor și ECU compatibile.","Citește starea readiness; dacă este necesar folosește procedura documentată pentru motor.","Monitoarele relevante sunt complete.","Nu forța teste fără condițiile corecte.","Condițional",1,src_main),
    ("Controller Channels Map","Documentare","","Applications > Controller Channels Map","Exportă canale/adaptări/valori suportate.","Modul comunicant.","Rulează Channel Map pentru modulul dorit și păstrează fișierul ca referință.","Fișier map creat.","Poate dura; menține tensiunea stabilă.","General",1,src_main),
    ("SRI Reset","Service","17","Applications > SRI Reset","Resetează intervalul de service unde este suportat.","Service efectuat; cluster compatibil.","Deschide SRI Reset, citește valorile, alege operația documentată și aplică.","Interval nou afișat corect.","Verifică tipul de service fixed/flexible.","Condițional",1,src_common),
    ("Throttle Body Alignment","Basic Settings","01","[Select] > [01-Engine] > [Basic Settings - 04]","Reînvață pozițiile clapetei pe motoare pe benzină compatibile.","Fără DTC relevante; tensiune suficientă; clapetă curată; accelerația neatinsă.","Folosește grupul/funcția potrivită protocolului ECU: pe multe DBW non-UDS este Group 060; pe UDS selectează funcția denumită throttle valve adaptation.","ADP OK / Finished Correctly.","Nu se aplică tuturor motoarelor; confirmă ECU/protocolul.","Condițional",1,src_tba),
    ("Automatic Transmission Basic Settings","Basic Settings","02","[Select] > [02-Auto Trans] > [Basic Settings - 04]","Reînvață semnale/adaptări suportate de TCM.","Fără DTC în motor/cutie; contact ON; procedura specifică transmisiei.","Rulează numai grupul documentat pentru transmisia exactă; unele TCM folosesc kick-down, altele nu îl suportă.","Criteriul documentat al TCM este îndeplinit.","Transmisiile diferă major: verifică tipul 01M/09G/DSG etc.","Condițional",1,src_at),
    ("EPB - mod service plăcuțe","Frâne","53","[Select] > [53-Parking Brake] sau [03-ABS] > [Basic Settings - 04]","Deschide/închide etrierele electrice pentru service.","Sistem EPB funcțional; frâna de parcare eliberată; tensiune stabilă.","Folosește funcția specifică chassis-ului pentru Open Rear Parking Brake, execută lucrarea, apoi Close și Function Test.","EPB fără DTC după function test.","Pe MQB procedura poate fi în 03-ABS; nu demonta etrierul înainte de service mode.","Condițional",1,src_epb),
    ("Suspension Level Calibration","Șasiu","34","[Select] > [34-Level Control] > Security/Login > Adaptation","Calibrează înălțimea suspensiei pneumatice compatibile.","Suprafață plană; uși închise; sistem fără defecțiuni; măsurători precise.","Măsoară înălțimile conform procedurii, introdu valorile în canalele documentate și finalizează calibrarea.","Fără DTC și nivel corect.","Se aplică doar sistemelor compatibile; UDS și non-UDS diferă.","Condițional",1,src_level),
    ("Cruise Control - verificare comenzi","Diagnostic","01","[01-Engine] > Measuring Values","Verifică stările manetei/pedalelor pentru CCS.","Motor compatibil și cruise instalat.","Urmărește measuring values pentru brake/clutch/switches și confirmă schimbarea bit-urilor la acționare.","Toate intrările comută corect.","Grupurile exacte depind de ECU.","Condițional",1,src_common),
    ("Fuel Trim Diagnosis","Diagnostic","01","[01-Engine] > Measuring Values","Analizează corecțiile de amestec pe benzină.","Motor la temperatură și fără probleme mecanice evidente.","Compară corecțiile idle/part load cu simptomele și caută fals aer, presiune combustibil sau MAF când valorile sunt anormale.","Cauza identificată și valorile revin normal.","Valorile exacte depind de ECU.","Condițional",1,src_common),
    ("Misfire Diagnosis","Diagnostic","01","[01-Engine] > Advanced Measuring Values","Localizează rateuri pe cilindri.","Motor pe benzină și ECU cu misfire counters.","Urmărește contoarele pe cilindri, condițiile de apariție și corelează cu aprindere/injecție/compresie.","Cilindrul/cauza identificată.","Nu înlocui piese doar dintr-un singur contor.","Condițional",1,src_common),
    ("DPF Emergency Regeneration","DPF","01","[01-Engine] > Basic Settings / Adaptation","Inițiază regenerarea doar când procedura motorului o permite.","Fără DTC blocante; încărcare și temperaturi în limite; nivel ulei verificat.","Folosește numai procedura specifică ECU și urmărește temperaturile/soot load pe toată durata.","Regenerare finalizată și soot load redus.","Risc de temperatură foarte mare; nu forța regenerarea unui DPF supraîncărcat.","Condițional",1,src_common),
    ("Fuel Pump Basic Settings TDI","Basic Settings","01","[01-Engine] > [Basic Settings - 04]","Comandă pompa de combustibil pentru amorsare/test unde este suportat.","Sistem asamblat; combustibil suficient; procedură pentru PD/PPD/CR.","Selectează funcția de fuel pump/basic setting documentată și execută ciclul necesar.","Circuit amorsat și fără scurgeri.","Funcția diferă după ECU.","Condițional",1,src_common),
    ("TDI Timing Checker VE","Diagnostic","01","[01-Engine] > [Meas. Blocks - 08] > TDI Timing","Verifică sincronizarea pompei pe VE TDI.","Numai motoare VE; motor la temperatură.","Folosește TDI Timing Checker și compară punctul cu graficul motorului.","Timing în zona specificată.","Nu se aplică PD/PPD/CR.","Condițional",1,src_common),
    ("Coding după PR-Codes","Coding","","[Select] > [modul] > [Coding - 07]","Reconstruiește coding-ul conform echipării când există procedură oficială.","PR-codes și modul exact identificate.","Folosește numai tabelul/procedura specifică modulului și păstrează coding-ul vechi.","Coding acceptat și funcții corecte.","Nu extrapola între module similare.","Condițional",1,src_common),
    ("Airbag Coding / Index","Coding","15","[15-Airbags] > [Coding - 07]","Codează unități airbag compatibile cu metoda index.","Numai generații/module suportate și identificare exactă.","Urmează procedura specifică chassis-ului; pe unele platforme noi metoda index nu se aplică.","Coding acceptat, fără DTC de configurare.","Sistem de siguranță: nu folosi valori presupuse.","Condițional",1,src_common),
    ("G85 Steering Angle Basic Setting","Basic Settings","03/44","[03-ABS] sau [44-Steering Assist] > [Basic Settings - 04]","Calibrează senzorul unghi volan când procedura chassis-ului o cere.","Geometrie corectă; volan/roți drepte; tensiune suficientă.","Rulează procedura specifică ABS/steering system; unele sisteme cer drive test înainte/după.","Basic setting acceptat și martorii se sting după test.","MK70/MK60/MK60EC1 etc. au proceduri diferite.","Condițional",1,src_common),
    ("Steering Limit Stop Adaptation","Basic Settings","44","[44-Steering Assist] > [Basic Settings/Adaptation]","Reînvață capetele de cursă după lucrări relevante.","G85 calibrat unde este necesar; sistem fără defect mecanic.","Urmează procedura steering assist specifică generației și finalizează road-testul.","DTC limit stop dispare.","Procedura diferă între generații de casetă.","Condițional",1,src_common),
    ("Battery / Quiescent Current Analysis","Diagnostic","61","[61-Battery Regulation] > Measuring Values","Ajută la localizarea consumului de repaus pe sisteme cu battery management.","Vehicul echipat cu modul relevant.","Urmărește istoricul/valorile battery management și corelează cu măsurarea fizică a curentului.","Consumatorul anormal identificat.","Disponibil doar pe anumite platforme.","Condițional",1,src_common),
    ("TPMS - diagnostic și reset","Șasiu","65/03","[65-Tire Pressure] sau [03-ABS]","Verifică sistem direct/indirect TPMS.","Identifică tipul de sistem.","Citește DTC și measuring values; pentru indirect folosește procedura de reset/learn a platformei.","Sistem fără DTC și presiuni memorate.","Nu confunda TPMS direct cu indirect.","Condițional",1,src_diag),
    ("Headlight Range Basic Setting","Iluminare","55","[55-Headlight Range] > [Basic Settings - 04]","Inițializează poziția de bază la sisteme compatibile.","Vehicul pe plan drept; suspensie și senzori nivel funcționali.","Rulează basic setting-ul documentat pentru AFS/headlight range și reglează mecanic dacă procedura cere.","Basic setting acceptat și farurile poziționate corect.","Xenon/AFS/LED au proceduri diferite.","Condițional",1,src_diag),
    ("HVAC Flap Motor Basic Setting","Climatizare","08","[08-HVAC] > [Basic Settings - 04]","Reînvață pozițiile clapetelor HVAC.","Fără blocaje mecanice; tensiune stabilă.","Selectează basic setting-ul pentru flap motors/adaptation și așteaptă finalizarea.","Fără DTC de poziție clapetă.","Funcția exactă diferă după climatronic.","Condițional",1,src_main),
    ("Transport Mode","Service","19","Applications / [19-CAN Gateway]","Activează/dezactivează modul transport unde este suportat.","Procedură documentată pentru platformă.","Folosește funcția VCDS dedicată sau metoda specifică gateway-ului.","Starea transport mode se schimbă.","Poate dezactiva consumatori/confort; folosește doar când este necesar.","Condițional",1,src_main),
    ("Optical Bus Diagnostics","Infotainment","19/5F","Applications > Optical Bus Diagnostics","Diagnostichează inelul optic pe platformele MOST compatibile.","Vehicul cu MOST.","Rulează optical bus diagnostics și identifică modulul care întrerupe inelul.","Topologia/defectul identificat.","Nu se aplică platformelor fără MOST.","Condițional",1,src_main),
    ("Installation List Gateway","Rețea","19","[19-CAN Gateway] > Installation List","Verifică modulele declarate în gateway.","Gateway compatibil.","Compară lista cu echiparea reală; modifică doar conform retrofitului/documentației.","Fără DTC de modul lipsă/neînregistrat.","Bifarea greșită generează DTC de comunicație.","Condițional",1,src_main),
    ("Controller Identification","Documentare","","[Select] > [modul] > Advanced ID","Salvează part number, HW/SW și component info.","Comunicație cu modulul.","Citește Advanced ID și salvează datele înainte de coding/replacement.","Identificare completă salvată.","Folosește part number exact la alegerea procedurii.","General",1,src_main),
    ("OBD-II Generic Scan","Diagnostic","01","[OBD-II]","Verifică modurile OBD standard suportate de ECU.","Vehicul OBD-II/EOBD compatibil.","Deschide OBD-II și citește DTC/readiness/live data standard când este necesar.","Date OBD obținute.","Funcțiile VAG specifice se fac din control modules, nu din OBD generic.","General",1,src_main),
    ]
    con.executemany("""INSERT INTO procedure_library(title,category,module_address,vcds_path,purpose,prerequisites,steps,success_criteria,warnings,applicability_rule,verified,source_id)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""", P)


def map_procedures_to_vehicles(con):
    if scalar(con, "SELECT COUNT(*) FROM vehicle_procedures"):
        return
    proc_rows = list(con.execute("SELECT id,title,applicability_rule FROM procedure_library"))
    gen_rows = list(con.execute("SELECT id,platform,name FROM generations"))
    for g in gen_rows:
        for p in proc_rows:
            applicability = p["applicability_rule"]
            title = p["title"].lower()
            notes = "Verifică modulul/ECU exact înainte de executare."
            if title in ("auto-scan complet","citire dtc modul","ștergere dtc controlată","data logging","controller identification","obd-ii generic scan"):
                applicability = "General"
            if "epb" in title and g["platform"] in ("PQ34","PQ24"):
                applicability = "De regulă indisponibil"
            if "suspension level" in title and not any(x in g["name"] for x in ["Touareg","Phaeton","A6","A8","Q7"]):
                applicability = "Doar dacă este echipat"
            con.execute("INSERT INTO vehicle_procedures(generation_id,procedure_id,applicability,notes) VALUES(?,?,?,?)", (g["id"],p["id"],applicability,notes))


def seed_dtcs(con, source_id):
    if scalar(con, "SELECT COUNT(*) FROM dtcs"):
        return
    rows = [
    ("00778","Steering Angle Sensor G85","Eroare asociată senzorului de unghi volan.","Martori ABS/ESP/steering","Basic setting lipsă; configurație sau senzor/cablaj","Identifică sistemul ABS/steering exact și aplică procedura G85 specifică chassis-ului.","Calibrare sau reparație conform diagnosticului.","Ridicat",1,source_id),
    ("01087","Basic Setting Not Performed","Un basic setting necesar nu a fost finalizat.","Limitare funcție; coding imposibil în unele cazuri","Basic setting neefectuat","Identifică modulul care stochează DTC și procedura specifică.","Execută basic setting-ul corect.","Mediu",1,source_id),
    ("01826","G85 Supply Voltage Terminal 30","Problemă de alimentare/adaptare G85.","Martor activ","Întrerupere tensiune; G85/J527","Verifică alimentarea și procedura specifică chassis-ului.","Adaptare sau reparație componentă/cablaj.","Ridicat",1,source_id),
    ("02233","Left Headlight Power Output Stage","Problemă modul putere far stânga.","AFS/far nefuncțional","Siguranță; cablaj; J667 incompatibil/defect","Verifică siguranțele, cablajul și compatibilitatea modulului.","Repară cablaj sau înlocuiește modul compatibil.","Mediu",1,source_id),
    ("02234","Right Headlight Power Output Stage","Problemă modul putere far dreapta.","AFS/far nefuncțional","Siguranță; cablaj; J668 incompatibil/defect","Verifică siguranțele, cablajul și compatibilitatea modulului.","Repară cablaj sau înlocuiește modul compatibil.","Mediu",1,source_id),
    ("03803","Steering Angle Sensor for Steering Aid - Basic Setting","Basic setting/adaptation lipsă pentru steering aid.","Martor steering","Casetă înlocuită; G85 necalibrat","Verifică 00778 și procedura steering assist specifică.","Calibrează G85 / characteristic curve dacă procedura cere.","Ridicat",1,source_id),
    ("P0401","EGR insufficient flow","Debit EGR insuficient.","MIL; performanță redusă","EGR/admisie colmatate; comandă; cablaj","Compară specified/actual și testează sistemul specific motorului.","Curățare/reparație după confirmare.","Mediu",0,source_id),
    ("P0299","Turbocharger underboost","Presiune turbo sub cerut.","Limp mode; putere redusă","Pierdere boost; vacuum; actuator; geometrie; senzor","Log boost specified/actual și verifică charge-air/vacuum.","Repară cauza confirmată.","Ridicat",0,source_id),
    ("P2002","DPF efficiency below threshold","Eficiență DPF sub prag.","MIL/DPF; regenerări dese","DPF; senzori; cauze de funingine","Verifică differential pressure, soot load și temperaturi.","Remediază cauza înainte de regen/înlocuire.","Ridicat",0,source_id),
    ("P2463","DPF soot accumulation","Încărcare mare de funingine.","DPF; limitare putere","Regenerări întrerupte; senzori; ardere","Verifică dacă regenerarea este permisă și sigură.","Regen doar dacă procedura ECU o permite; altfel service DPF.","Critic",0,source_id),
    ]
    con.executemany("""INSERT INTO dtcs(code,title,description,symptoms,causes,diagnosis,repair,severity,verified,source_id)
                       VALUES(?,?,?,?,?,?,?,?,?,?)""", rows)


def brands(con):
    return con.execute("SELECT id,name FROM brands ORDER BY name").fetchall()


def models_for_brand(con, brand_id):
    return con.execute("SELECT id,name FROM models WHERE brand_id=? ORDER BY name", (brand_id,)).fetchall()


def generations_for_model(con, model_id):
    return con.execute("SELECT id,name,year_from,year_to,chassis,platform,ross_tech_url FROM generations WHERE model_id=? ORDER BY year_from", (model_id,)).fetchall()


def engines_for_generation(con, generation_id):
    rows = con.execute("""SELECT e.id,e.code,e.fuel,e.displacement,e.power_hp,e.family FROM vehicle_engines ve
                          JOIN engines e ON e.id=ve.engine_id WHERE ve.generation_id=? ORDER BY e.code""", (generation_id,)).fetchall()
    return rows


def vehicle_header(con, generation_id):
    return con.execute("""SELECT g.*,m.name model,b.name brand FROM generations g JOIN models m ON m.id=g.model_id
                          JOIN brands b ON b.id=m.brand_id WHERE g.id=?""", (generation_id,)).fetchone()


def procedures_for_vehicle(con, generation_id, category=""):
    sql = """SELECT p.id,p.title,p.category,p.module_address,p.vcds_path,p.purpose,p.prerequisites,p.steps,
                    p.success_criteria,p.warnings,p.verified,p.source_id,vp.applicability,vp.notes,s.url source_url,s.title source_title
             FROM vehicle_procedures vp JOIN procedure_library p ON p.id=vp.procedure_id
             LEFT JOIN sources s ON s.id=p.source_id WHERE vp.generation_id=?"""
    args = [generation_id]
    if category and category != "Toate":
        sql += " AND p.category=?"; args.append(category)
    sql += " ORDER BY p.category,p.title"
    return con.execute(sql, args).fetchall()


def modules_for_vehicle(con, generation_id):
    # Catalog de module posibile; exactitatea finală se confirmă prin Auto-Scan al vehiculului.
    return con.execute("SELECT address,name,family,protocol FROM modules ORDER BY address").fetchall()


def search_all(con, text, generation_id=None):
    q = f"%{text}%"
    out = []
    for r in con.execute("SELECT code,title,description,severity,verified FROM dtcs WHERE code LIKE ? OR title LIKE ? OR description LIKE ? LIMIT 200", (q,q,q)):
        out.append(("DTC",r["code"],r["title"],r["description"],"VERIFICAT" if r["verified"] else "DE VERIFICAT"))
    if generation_id:
        for r in procedures_for_vehicle(con, generation_id):
            if text.lower() in (r["title"]+" "+r["category"]+" "+r["vcds_path"]+" "+r["purpose"]).lower():
                out.append(("PROCEDURĂ",str(r["id"]),r["title"],r["vcds_path"],r["applicability"]))
    return out[:500]


def stats(con):
    return {
        "brands": scalar(con,"SELECT COUNT(*) FROM brands"),
        "models": scalar(con,"SELECT COUNT(*) FROM models"),
        "generations": scalar(con,"SELECT COUNT(*) FROM generations"),
        "procedures": scalar(con,"SELECT COUNT(*) FROM procedure_library"),
        "vehicle_procedures": scalar(con,"SELECT COUNT(*) FROM vehicle_procedures"),
        "dtcs": scalar(con,"SELECT COUNT(*) FROM dtcs"),
        "modules": scalar(con,"SELECT COUNT(*) FROM modules")
    }


def backup_database(destination):
    shutil.copy2(DB_PATH, Path(destination))


def export_json(con, destination):
    tables = ["brands","models","generations","engines","vehicle_engines","modules","sources","procedure_library","vehicle_procedures","dtcs","coding","adaptations","notes","favorites","activity_log"]
    data = {t:[dict(r) for r in con.execute(f"SELECT * FROM {t}")] for t in tables}
    Path(destination).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def export_vehicle_csv(con, generation_id, destination):
    rows = procedures_for_vehicle(con, generation_id)
    with open(destination,"w",newline="",encoding="utf-8-sig") as f:
        w=csv.writer(f); w.writerow(["Categorie","Procedură","Modul","Cale VCDS","Aplicabilitate","Scop","Sursă"])
        for r in rows:
            w.writerow([r["category"],r["title"],r["module_address"],r["vcds_path"],r["applicability"],r["purpose"],r["source_url"]])
