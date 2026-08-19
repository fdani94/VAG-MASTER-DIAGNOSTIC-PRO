import csv
import json
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QStandardPaths

APP_NAME = "VAG MASTER Diagnostic PRO"
APP_VERSION = "4.0.0"


def app_data_dir():
    base = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
    path = Path(base) if base else Path.home() / ".vag_master_pro"
    path.mkdir(parents=True, exist_ok=True)
    return path


APP_DATA = app_data_dir()
DB_PATH = APP_DATA / "vag_master_super.db"
LOGO_PATH = APP_DATA / "custom_logo.png"

SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS brands(id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL);
CREATE TABLE IF NOT EXISTS models(id INTEGER PRIMARY KEY, brand_id INTEGER NOT NULL REFERENCES brands(id), name TEXT NOT NULL, platform TEXT DEFAULT '', UNIQUE(brand_id,name));
CREATE TABLE IF NOT EXISTS generations(id INTEGER PRIMARY KEY, model_id INTEGER NOT NULL REFERENCES models(id), name TEXT NOT NULL, year_from INTEGER, year_to INTEGER, platform TEXT DEFAULT '', notes TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS engines(id INTEGER PRIMARY KEY, code TEXT UNIQUE NOT NULL, fuel TEXT DEFAULT '', displacement REAL, power_hp INTEGER, power_kw INTEGER, family TEXT DEFAULT '', notes TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS vehicle_engines(generation_id INTEGER REFERENCES generations(id), engine_id INTEGER REFERENCES engines(id), year_from INTEGER, year_to INTEGER, PRIMARY KEY(generation_id,engine_id));
CREATE TABLE IF NOT EXISTS modules(id INTEGER PRIMARY KEY, address TEXT NOT NULL, name TEXT NOT NULL, family TEXT DEFAULT '', protocol TEXT DEFAULT '', description TEXT DEFAULT '', UNIQUE(address,name));
CREATE TABLE IF NOT EXISTS generation_modules(generation_id INTEGER REFERENCES generations(id), module_id INTEGER REFERENCES modules(id), notes TEXT DEFAULT '', PRIMARY KEY(generation_id,module_id));
CREATE TABLE IF NOT EXISTS dtcs(id INTEGER PRIMARY KEY, code TEXT UNIQUE NOT NULL, title TEXT NOT NULL, description TEXT DEFAULT '', severity TEXT DEFAULT 'Mediu', symptoms TEXT DEFAULT '', causes TEXT DEFAULT '', diagnosis TEXT DEFAULT '', repair TEXT DEFAULT '', verified INTEGER DEFAULT 0, source_id INTEGER REFERENCES sources(id));
CREATE TABLE IF NOT EXISTS coding(id INTEGER PRIMARY KEY, title TEXT NOT NULL, module_address TEXT DEFAULT '', coding_type TEXT DEFAULT '', byte_value TEXT DEFAULT '', bit_value TEXT DEFAULT '', original_value TEXT DEFAULT '', new_value TEXT DEFAULT '', effect TEXT DEFAULT '', prerequisites TEXT DEFAULT '', applicability TEXT DEFAULT '', restore_method TEXT DEFAULT '', warnings TEXT DEFAULT '', verified INTEGER DEFAULT 0, source_id INTEGER REFERENCES sources(id));
CREATE TABLE IF NOT EXISTS adaptations(id INTEGER PRIMARY KEY, title TEXT NOT NULL, module_address TEXT DEFAULT '', channel TEXT DEFAULT '', stored_value TEXT DEFAULT '', new_value TEXT DEFAULT '', effect TEXT DEFAULT '', prerequisites TEXT DEFAULT '', applicability TEXT DEFAULT '', restore_method TEXT DEFAULT '', warnings TEXT DEFAULT '', verified INTEGER DEFAULT 0, source_id INTEGER REFERENCES sources(id));
CREATE TABLE IF NOT EXISTS basic_settings(id INTEGER PRIMARY KEY, title TEXT NOT NULL, module_address TEXT DEFAULT '', group_name TEXT DEFAULT '', prerequisites TEXT DEFAULT '', steps TEXT DEFAULT '', success_criteria TEXT DEFAULT '', warnings TEXT DEFAULT '', applicability TEXT DEFAULT '', verified INTEGER DEFAULT 0, source_id INTEGER REFERENCES sources(id));
CREATE TABLE IF NOT EXISTS output_tests(id INTEGER PRIMARY KEY, title TEXT NOT NULL, module_address TEXT DEFAULT '', prerequisites TEXT DEFAULT '', steps TEXT DEFAULT '', expected_result TEXT DEFAULT '', warnings TEXT DEFAULT '', applicability TEXT DEFAULT '', verified INTEGER DEFAULT 0, source_id INTEGER REFERENCES sources(id));
CREATE TABLE IF NOT EXISTS security_access(id INTEGER PRIMARY KEY, title TEXT NOT NULL, module_address TEXT DEFAULT '', access_method TEXT DEFAULT '', purpose TEXT DEFAULT '', prerequisites TEXT DEFAULT '', notes TEXT DEFAULT '', applicability TEXT DEFAULT '', verified INTEGER DEFAULT 0, source_id INTEGER REFERENCES sources(id));
CREATE TABLE IF NOT EXISTS measuring_values(id INTEGER PRIMARY KEY, title TEXT NOT NULL, module_address TEXT DEFAULT '', parameter TEXT DEFAULT '', expected_value TEXT DEFAULT '', units TEXT DEFAULT '', conditions TEXT DEFAULT '', interpretation TEXT DEFAULT '', applicability TEXT DEFAULT '', verified INTEGER DEFAULT 0, source_id INTEGER REFERENCES sources(id));
CREATE TABLE IF NOT EXISTS resets(id INTEGER PRIMARY KEY, title TEXT NOT NULL, module_address TEXT DEFAULT '', prerequisites TEXT DEFAULT '', steps TEXT DEFAULT '', warnings TEXT DEFAULT '', applicability TEXT DEFAULT '', verified INTEGER DEFAULT 0, source_id INTEGER REFERENCES sources(id));
CREATE TABLE IF NOT EXISTS procedures(id INTEGER PRIMARY KEY, title TEXT NOT NULL, category TEXT DEFAULT '', prerequisites TEXT DEFAULT '', steps TEXT DEFAULT '', warnings TEXT DEFAULT '', difficulty TEXT DEFAULT 'Intermediar', verified INTEGER DEFAULT 0, source_id INTEGER REFERENCES sources(id));
CREATE TABLE IF NOT EXISTS components(id INTEGER PRIMARY KEY, name TEXT NOT NULL, family TEXT DEFAULT '', function TEXT DEFAULT '', location TEXT DEFAULT '', inspection TEXT DEFAULT '', replacement_notes TEXT DEFAULT '', verified INTEGER DEFAULT 0, source_id INTEGER REFERENCES sources(id));
CREATE TABLE IF NOT EXISTS sources(id INTEGER PRIMARY KEY, title TEXT NOT NULL, publisher TEXT DEFAULT '', url TEXT DEFAULT '', accessed TEXT DEFAULT '', notes TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS favorites(id INTEGER PRIMARY KEY, entity_type TEXT NOT NULL, entity_key TEXT NOT NULL, label TEXT DEFAULT '', created_at TEXT NOT NULL, UNIQUE(entity_type,entity_key));
CREATE TABLE IF NOT EXISTS notes(id INTEGER PRIMARY KEY, entity_type TEXT NOT NULL, entity_key TEXT NOT NULL, note TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS activity_log(id INTEGER PRIMARY KEY, action TEXT NOT NULL, entity_type TEXT DEFAULT '', entity_key TEXT DEFAULT '', details TEXT DEFAULT '', created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT DEFAULT '');
CREATE INDEX IF NOT EXISTS idx_dtc_code ON dtcs(code);
CREATE INDEX IF NOT EXISTS idx_model_name ON models(name);
CREATE INDEX IF NOT EXISTS idx_engine_code ON engines(code);
CREATE INDEX IF NOT EXISTS idx_module_address ON modules(address);
CREATE INDEX IF NOT EXISTS idx_activity_date ON activity_log(created_at);
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


def seed(con):
    if scalar(con, "SELECT COUNT(*) FROM sources") == 0:
        sources = [
            ("VCDS Main Screen / Function Index", "Ross-Tech", "https://www.ross-tech.com/vcds/tour/main_screen.php", "Official VCDS function overview"),
            ("VCDS Adaptation", "Ross-Tech", "https://www.ross-tech.com/vcds/tour/adaptation_screen.php", "Official Adaptation behavior and warnings"),
            ("VCDS Basic Settings", "Ross-Tech", "https://www.ross-tech.com/vcds/tour/b-settings.php", "Official Basic Settings behavior and warnings"),
            ("VCDS Output Tests", "Ross-Tech", "https://www.ross-tech.com/vcds/tour/out_test.php", "Official Output Tests behavior and warnings"),
            ("VCDS Security Access", "Ross-Tech", "https://www.ross-tech.com/vcds/tour/securityaccess.php", "Official Security Access behavior"),
        ]
        con.executemany("INSERT INTO sources(title,publisher,url,accessed,notes) VALUES(?,?,?,?,?)",
                        [(a,b,c,datetime.now().date().isoformat(),d) for a,b,c,d in sources])

    if scalar(con, "SELECT COUNT(*) FROM brands") == 0:
        for name in ["Volkswagen", "Audi", "Škoda", "SEAT / Cupra"]:
            con.execute("INSERT INTO brands(name) VALUES(?)", (name,))
        con.commit()

    brand_ids = {r["name"]: r["id"] for r in con.execute("SELECT id,name FROM brands")}
    if scalar(con, "SELECT COUNT(*) FROM models") == 0:
        model_rows = [
            ("Volkswagen","Golf","PQ/MQB"),("Volkswagen","Passat","PQ/MLB/MQB"),("Volkswagen","Polo","PQ/MQB-A0"),("Volkswagen","Tiguan","PQ/MQB"),("Volkswagen","Touran","PQ/MQB"),("Volkswagen","Caddy","PQ/MQB"),("Volkswagen","Touareg","PL/MLB"),("Volkswagen","Transporter","T-platform"),
            ("Audi","A1","PQ/MQB-A0"),("Audi","A3","PQ/MQB"),("Audi","A4","B/MLB"),("Audi","A5","MLB"),("Audi","A6","C/MLB"),("Audi","A7","MLB"),("Audi","A8","D/MLB"),("Audi","Q3","PQ/MQB"),("Audi","Q5","MLB"),("Audi","Q7","PL/MLB"),
            ("Škoda","Fabia","PQ/MQB-A0"),("Škoda","Octavia","PQ/MQB"),("Škoda","Superb","PQ/MQB"),("Škoda","Rapid","PQ"),("Škoda","Scala","MQB-A0"),("Škoda","Karoq","MQB"),("Škoda","Kodiaq","MQB"),
            ("SEAT / Cupra","Ibiza","PQ/MQB-A0"),("SEAT / Cupra","Leon","PQ/MQB"),("SEAT / Cupra","Toledo","PQ"),("SEAT / Cupra","Ateca","MQB"),("SEAT / Cupra","Tarraco","MQB"),
        ]
        con.executemany("INSERT INTO models(brand_id,name,platform) VALUES(?,?,?)", [(brand_ids[b],n,p) for b,n,p in model_rows])
        con.commit()

    if scalar(con, "SELECT COUNT(*) FROM generations") == 0:
        gens = [
            ("Golf","IV 1J",1997,2006,"PQ34"),("Golf","V 1K",2003,2009,"PQ35"),("Golf","VI 5K",2008,2013,"PQ35"),("Golf","VII 5G",2012,2020,"MQB"),("Golf","VIII CD",2019,2024,"MQB Evo"),
            ("Passat","B5/B5.5",1996,2005,"PL45"),("Passat","B6",2005,2010,"PQ46"),("Passat","B7",2010,2014,"PQ46"),("Passat","B8",2014,2024,"MQB"),
            ("Polo","9N/9N3",2001,2009,"PQ24"),("Polo","6R/6C",2009,2017,"PQ25"),("Polo","AW",2017,2024,"MQB-A0"),
            ("Tiguan","5N",2007,2016,"PQ35"),("Tiguan","AD/BW",2016,2024,"MQB"),("Touran","1T",2003,2015,"PQ35"),("Touran","5T",2015,2024,"MQB"),
            ("A3","8L",1996,2003,"PQ34"),("A3","8P",2003,2013,"PQ35"),("A3","8V",2012,2020,"MQB"),("A3","8Y",2020,2024,"MQB Evo"),
            ("A4","B5 8D",1995,2001,"PL45"),("A4","B6 8E",2000,2004,"PL46"),("A4","B7 8E",2004,2008,"PL46"),("A4","B8 8K",2007,2016,"MLB"),("A4","B9 8W",2015,2024,"MLB Evo"),
            ("A6","C5 4B",1997,2005,"PL45"),("A6","C6 4F",2004,2011,"PL47"),("A6","C7 4G",2011,2018,"MLB"),("A6","C8 4K",2018,2024,"MLB Evo"),
            ("Q5","8R",2008,2017,"MLB"),("Q5","FY",2017,2024,"MLB Evo"),("Q7","4L",2005,2015,"PL71"),("Q7","4M",2015,2024,"MLB Evo"),
            ("Fabia","6Y",1999,2007,"PQ24"),("Fabia","5J",2007,2014,"PQ25"),("Fabia","NJ",2014,2021,"PQ26"),("Fabia","PJ",2021,2024,"MQB-A0"),
            ("Octavia","1U",1996,2010,"PQ34"),("Octavia","1Z",2004,2013,"PQ35"),("Octavia","5E",2013,2020,"MQB"),("Octavia","NX",2019,2024,"MQB Evo"),
            ("Superb","3U",2001,2008,"PL45+"),("Superb","3T",2008,2015,"PQ46"),("Superb","3V",2015,2024,"MQB"),
            ("Ibiza","6L",2002,2008,"PQ24"),("Ibiza","6J",2008,2017,"PQ25"),("Ibiza","KJ",2017,2024,"MQB-A0"),
            ("Leon","1M",1999,2006,"PQ34"),("Leon","1P",2005,2012,"PQ35"),("Leon","5F",2012,2020,"MQB"),("Leon","KL",2020,2024,"MQB Evo"),
        ]
        for model, name, yf, yt, platform in gens:
            mid = scalar(con, "SELECT id FROM models WHERE name=?", (model,))
            if mid:
                con.execute("INSERT INTO generations(model_id,name,year_from,year_to,platform) VALUES(?,?,?,?,?)", (mid,name,yf,yt,platform))
        con.commit()

    if scalar(con, "SELECT COUNT(*) FROM engines") == 0:
        engines = [
            ("1Z","Diesel",1.9,90,66,"EA180"),("AHU","Diesel",1.9,90,66,"EA180"),("AFN","Diesel",1.9,110,81,"EA180"),("ALH","Diesel",1.9,90,66,"EA180"),
            ("BKC","Diesel",1.9,105,77,"EA188"),("BXE","Diesel",1.9,105,77,"EA188"),("BLS","Diesel",1.9,105,77,"EA188"),("CAYC","Diesel",1.6,105,77,"EA189"),
            ("CFFB","Diesel",2.0,140,103,"EA189"),("CFHC","Diesel",2.0,140,103,"EA189"),("CUNA","Diesel",2.0,184,135,"EA288"),("CRBC","Diesel",2.0,150,110,"EA288"),
            ("CBAB","Diesel",2.0,140,103,"EA189"),("CJCA","Diesel",2.0,143,105,"EA189"),("CAGA","Diesel",2.0,143,105,"EA189"),
            ("BSE","Petrol",1.6,102,75,"EA113"),("BAG","Petrol",1.6,115,85,"FSI"),("CAXA","Petrol",1.4,122,90,"EA111"),("CAVD","Petrol",1.4,160,118,"EA111"),
            ("CHPA","Petrol",1.4,140,103,"EA211"),("CZEA","Petrol",1.4,150,110,"EA211"),("DADA","Petrol",1.5,150,110,"EA211 Evo"),("CJSA","Petrol",1.8,180,132,"EA888"),
            ("CCZA","Petrol",2.0,200,147,"EA888"),("CHHB","Petrol",2.0,220,162,"EA888"),("CJXC","Petrol",2.0,300,221,"EA888")
        ]
        con.executemany("INSERT INTO engines(code,fuel,displacement,power_hp,power_kw,family) VALUES(?,?,?,?,?,?)", engines)
        con.commit()

    if scalar(con, "SELECT COUNT(*) FROM modules") == 0:
        modules = [
            ("01","Engine","Powertrain","KWP/CAN/UDS"),("02","Auto Trans","Powertrain","KWP/CAN/UDS"),("03","ABS Brakes","Chassis","KWP/CAN/UDS"),("05","Acc/Start Auth","Security","CAN/UDS"),
            ("08","Auto HVAC","Body","KWP/CAN/UDS"),("09","Central Electrics","Body","KWP/CAN/UDS"),("10","Park/Steer Assist","Chassis","CAN/UDS"),("13","Auto Dist. Reg","ADAS","CAN/UDS"),
            ("15","Airbags","Safety","KWP/CAN/UDS"),("16","Steering Wheel","Body","KWP/CAN/UDS"),("17","Instruments","Body","KWP/CAN/UDS"),("19","CAN Gateway","Network","CAN/UDS"),
            ("25","Immobilizer","Security","KWP/CAN"),("42","Door Elect. Driver","Body","CAN/UDS"),("44","Steering Assist","Chassis","CAN/UDS"),("46","Comfort System","Body","KWP/CAN"),
            ("52","Door Elect. Pass.","Body","CAN/UDS"),("53","Parking Brake","Chassis","CAN/UDS"),("55","Headlight Range","Body","CAN/UDS"),("5F","Information Electronics","Infotainment","UDS"),
            ("61","Battery Regulation","Powertrain","CAN/UDS"),("69","Trailer","Body","CAN/UDS"),("6C","Back-up Cam","Infotainment","UDS"),("75","Telematics","Infotainment","UDS")
        ]
        con.executemany("INSERT INTO modules(address,name,family,protocol) VALUES(?,?,?,?)", modules)
        con.commit()

    src_main = scalar(con, "SELECT id FROM sources WHERE title LIKE 'VCDS Main%' LIMIT 1")
    src_adapt = scalar(con, "SELECT id FROM sources WHERE title='VCDS Adaptation' LIMIT 1")
    src_basic = scalar(con, "SELECT id FROM sources WHERE title='VCDS Basic Settings' LIMIT 1")
    src_output = scalar(con, "SELECT id FROM sources WHERE title='VCDS Output Tests' LIMIT 1")
    src_security = scalar(con, "SELECT id FROM sources WHERE title='VCDS Security Access' LIMIT 1")

    if scalar(con, "SELECT COUNT(*) FROM dtcs") == 0:
        dtcs = [
            ("P0101","Mass Air Flow range/performance","MAF outside expected range","Mediu","Reduced power; higher consumption","MAF; intake leak; EGR; air filter","Compare specified/actual air mass; inspect intake","Repair root cause, clear DTC, road test",0),
            ("P0299","Turbocharger underboost","Boost pressure below requested","Ridicat","Low power; limp mode","Charge leak; vacuum; actuator; turbo geometry; MAP","Compare requested/actual boost; smoke/pressure test; inspect actuator","Repair leak/control fault and verify boost",0),
            ("P0401","EGR insufficient flow","EGR flow below expected","Mediu","MIL; poor response; smoke possible","Carbon; intake restriction; actuator/vacuum; wiring","Check EGR command/feedback and intake path","Clean/repair as appropriate; perform applicable basic setting",0),
            ("P2002","DPF efficiency below threshold","DPF efficiency below calibrated threshold","Ridicat","DPF/MIL; frequent regenerations","DPF loading; pressure/temp sensors; combustion issue","Check soot/ash estimates and differential pressure","Correct cause before regeneration/replacement",0),
            ("P2463","DPF soot accumulation","High calculated soot load","Critic","DPF lamp; power limitation","Interrupted regens; pressure sensor; EGR/injection issue","Confirm soot load, pressure, temperature plausibility","Do not force regen until prerequisites are safe",0),
            ("P0562","System voltage low","Supply voltage below threshold","Mediu","Multiple electrical DTCs; slow crank","Battery; alternator; grounds; supply wiring","Battery/charging voltage test and voltage-drop test","Repair supply fault then rescan",0),
            ("P0300","Random/multiple cylinder misfire","Misfire detected on multiple cylinders","Ridicat","Rough running; MIL flashing possible","Ignition; injectors; compression; air/fuel issue","Check counters, plugs/coils, fuel and compression","Repair cause and verify counters",0),
            ("P0171","System too lean bank 1","Fuel trim indicates lean condition","Mediu","Idle issues; MIL","Vacuum leak; MAF; fuel pressure; injector","Inspect trims and intake leaks; verify fuel pressure","Repair leak/fueling cause",0)
        ]
        con.executemany("INSERT INTO dtcs(code,title,description,severity,symptoms,causes,diagnosis,repair,verified,source_id) VALUES(?,?,?,?,?,?,?,?,?,?)", [x+(src_main,) for x in dtcs])
        con.commit()

    if scalar(con, "SELECT COUNT(*) FROM coding") == 0:
        rows = [
            ("Coming / Leaving Home","09","Long Coding / Adaptation","","","","","Comfort exterior lighting","Stable voltage; save Auto-Scan/coding first","BCM/software/equipment dependent","Restore original coding/adaptation","Never copy coding blindly between cars",0,src_main),
            ("Auto Lock","09/46","Coding / Adaptation","","","","","Automatic door locking while driving","Backup original values","Generation/module dependent","Restore original value","Confirm unlock behavior",0,src_main),
            ("Needle Sweep","17","Coding / Adaptation","","","","","Gauge sweep on ignition","Cluster must support function","Cluster/software dependent","Disable same option","Not available on all clusters",0,src_main),
        ]
        con.executemany("INSERT INTO coding(title,module_address,coding_type,byte_value,bit_value,original_value,new_value,effect,prerequisites,applicability,restore_method,warnings,verified,source_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
        con.commit()

    if scalar(con, "SELECT COUNT(*) FROM adaptations") == 0:
        rows = [
            ("Adaptation workflow","various","Channel / UDS item","Original","New","Change supported controller parameter","Save Auto-Scan and original value before change","Controller-specific; UDS uses named items rather than classic channels","Restore recorded original value","Some controllers require Security Access; undocumented channels exist",1,src_adapt),
            ("Channel 00 factory adaptation reset (where supported)","various","00","Current adaptations","Factory defaults","Reset supported adaptation values","Confirm controller documentation first","Only controllers that explicitly support it","Restore from recorded values where possible","Can change many values at once",1,src_adapt),
        ]
        con.executemany("INSERT INTO adaptations(title,module_address,channel,stored_value,new_value,effect,prerequisites,applicability,restore_method,warnings,verified,source_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", rows)
        con.commit()

    if scalar(con, "SELECT COUNT(*) FROM basic_settings") == 0:
        rows = [
            ("Throttle body / actuator basic setting","01","Controller-specific","Correct battery voltage; engine conditions per repair procedure","Select documented Basic Setting and follow displayed instructions","Controller reports successful completion","Incorrect procedure can cause drivability issues","Only where supported by ECU",0,src_basic),
            ("ABS hydraulic unit bleeding","03","Controller-specific","Vehicle safely supported; correct brake fluid level; repair procedure available","Run documented bleeding Basic Setting and follow sequence","Procedure completes without fault","Brake system safety critical","Only ABS modules with documented procedure",0,src_basic),
        ]
        con.executemany("INSERT INTO basic_settings(title,module_address,group_name,prerequisites,steps,success_criteria,warnings,applicability,verified,source_id) VALUES(?,?,?,?,?,?,?,?,?,?)", rows)
        con.commit()

    if scalar(con, "SELECT COUNT(*) FROM output_tests") == 0:
        rows = [
            ("Sequential Output Test","various","Stationary vehicle; documented expected outputs","Start/Next through controller-defined sequence","Each commanded output responds as expected","Never run unsafe chassis/brake output tests while moving","Controller controls available sequence",1,src_output),
            ("Selective Output Test","various","Module must support selective testing","Choose supported output and activate","Selected actuator/output responds","Know expected behavior before activation","Availability depends on controller/supporting data",1,src_output),
        ]
        con.executemany("INSERT INTO output_tests(title,module_address,prerequisites,steps,expected_result,warnings,applicability,verified,source_id) VALUES(?,?,?,?,?,?,?,?,?)", rows)
        con.commit()

    if scalar(con, "SELECT COUNT(*) FROM security_access") == 0:
        rows = [
            ("Security Access before Coding/Adaptation","various","Controller-specific access key","Unlock protected functions","Correct module/session; documented key","Valid keys are vehicle/controller specific","KWP-2000/CAN/UDS modules where required",1,src_security),
        ]
        con.executemany("INSERT INTO security_access(title,module_address,access_method,purpose,prerequisites,notes,applicability,verified,source_id) VALUES(?,?,?,?,?,?,?,?,?)", rows)
        con.commit()

    if scalar(con, "SELECT COUNT(*) FROM measuring_values") == 0:
        rows = [
            ("Battery / system voltage","various","Supply voltage","Vehicle-dependent","V","Ignition state documented","Low voltage can create misleading DTCs","Most modules",0,src_main),
            ("Requested vs actual boost","01","Boost pressure","Engine/load dependent","mbar/kPa","Road test/load conditions","Large sustained deviation supports boost-control diagnosis","Turbocharged engines",0,src_main),
            ("DPF differential pressure","01","Differential pressure","Engine/rpm dependent","hPa/mbar","Known rpm/load","Use with soot/ash estimates and sensor plausibility","DPF-equipped diesels",0,src_main),
        ]
        con.executemany("INSERT INTO measuring_values(title,module_address,parameter,expected_value,units,conditions,interpretation,applicability,verified,source_id) VALUES(?,?,?,?,?,?,?,?,?,?)", rows)
        con.commit()

    if scalar(con, "SELECT COUNT(*) FROM resets") == 0:
        rows = [
            ("Service Reminder / SRI","17","Correct service performed; cluster supports reset","Use SRI Reset or documented adaptation channels","Do not reset service indicators without completing required service","Cluster/generation dependent",0,src_main),
            ("Clear DTC after repair","various","Save original scan first; fault repaired","Clear DTC, cycle ignition if required, rescan and road-test","Clearing a DTC does not repair the cause","All supported modules",1,src_main),
        ]
        con.executemany("INSERT INTO resets(title,module_address,prerequisites,steps,warnings,applicability,verified,source_id) VALUES(?,?,?,?,?,?,?,?)", rows)
        con.commit()

    if scalar(con, "SELECT COUNT(*) FROM procedures") == 0:
        rows = [
            ("Auto-Scan complet înainte de lucru","Diagnostic","Interfață conectată; baterie stabilă","1. Contact ON.\n2. Auto-Scan.\n3. Salvează raportul.\n4. Notează DTC și freeze-frame unde există.\n5. Abia apoi șterge sau modifică.","Nu pierde codurile inițiale înainte de documentare","Începător",1,src_main),
            ("Backup înainte de Coding/Adaptation","Coding","Auto-Scan salvat","1. Salvează coding/adaptation original.\n2. Fă o singură modificare.\n3. Testează.\n4. Notează rezultatul.\n5. Revino la original dacă apar probleme.","Nu copia valori de pe alt vehicul fără verificare","Intermediar",1,src_main),
            ("Flux diagnostic DTC","Diagnostic","Scan inițial salvat","1. Confirmă simptomul.\n2. Verifică DTC asociate.\n3. Verifică tensiunea.\n4. Consultă measuring values.\n5. Testează electric/mecanic.\n6. Repară cauza.\n7. Șterge DTC și verifică din nou.","Nu înlocui piese doar pe baza numelui DTC","Intermediar",1,src_main),
        ]
        con.executemany("INSERT INTO procedures(title,category,prerequisites,steps,warnings,difficulty,verified,source_id) VALUES(?,?,?,?,?,?,?,?)", rows)
        con.commit()

    if scalar(con, "SELECT COUNT(*) FROM components") == 0:
        rows = [
            ("MAF sensor","Engine management","Measures intake air mass","Intake tract after air filter on many engines","Inspect contamination, wiring, plausibility against requested/expected airflow","Use engine-specific service information",0,src_main),
            ("MAP / boost pressure sensor","Engine management","Measures manifold/charge pressure","Charge-air/manifold location varies by engine","Compare reading with barometric pressure key-on and under load","Confirm exact location by engine code",0,src_main),
            ("DPF differential pressure sensor","Emissions","Measures pressure difference across DPF","Engine bay; hoses connect before/after DPF","Inspect hoses for blockage/leaks and reading plausibility","Hose routing and adaptation can be engine-specific",0,src_main),
        ]
        con.executemany("INSERT INTO components(name,family,function,location,inspection,replacement_notes,verified,source_id) VALUES(?,?,?,?,?,?,?,?)", rows)
        con.commit()

    log(con, "Database ready", "system", APP_VERSION, "Super Master schema initialized")


def counts(con):
    tables = ["brands","models","generations","engines","modules","dtcs","coding","adaptations","basic_settings","output_tests","security_access","measuring_values","resets","procedures","components","sources","favorites","notes"]
    return {t: scalar(con, f"SELECT COUNT(*) FROM {t}") for t in tables}


def global_search(con, text):
    q = f"%{text.strip()}%"
    return con.execute("""
        SELECT 'DTC' type, code key, title, description details FROM dtcs WHERE code LIKE ? OR title LIKE ? OR description LIKE ?
        UNION ALL SELECT 'VEHICUL', b.name || ' ' || m.name, g.name, g.year_from || '–' || g.year_to FROM generations g JOIN models m ON m.id=g.model_id JOIN brands b ON b.id=m.brand_id WHERE b.name LIKE ? OR m.name LIKE ? OR g.name LIKE ?
        UNION ALL SELECT 'MOTOR', code, family, fuel || ' ' || displacement || 'L' FROM engines WHERE code LIKE ? OR family LIKE ?
        UNION ALL SELECT 'MODUL', address, name, protocol FROM modules WHERE address LIKE ? OR name LIKE ?
        UNION ALL SELECT 'CODING', CAST(id AS TEXT), title, effect FROM coding WHERE title LIKE ? OR effect LIKE ?
        UNION ALL SELECT 'ADAPTATION', CAST(id AS TEXT), title, effect FROM adaptations WHERE title LIKE ? OR effect LIKE ?
        UNION ALL SELECT 'BASIC SETTINGS', CAST(id AS TEXT), title, applicability FROM basic_settings WHERE title LIKE ? OR applicability LIKE ?
        UNION ALL SELECT 'PROCEDURĂ', CAST(id AS TEXT), title, category FROM procedures WHERE title LIKE ? OR steps LIKE ?
        ORDER BY type,key LIMIT 500
    """, (q,q,q,q,q,q,q,q,q,q,q,q,q,q,q,q,q,q)).fetchall()


def add_favorite(con, entity_type, entity_key, label):
    con.execute("INSERT OR IGNORE INTO favorites(entity_type,entity_key,label,created_at) VALUES(?,?,?,?)",
                (entity_type, str(entity_key), label, datetime.now().isoformat(timespec="seconds")))
    con.commit(); log(con, "Favorite added", entity_type, entity_key, label)


def add_note(con, entity_type, entity_key, note):
    con.execute("INSERT INTO notes(entity_type,entity_key,note,created_at) VALUES(?,?,?,?)",
                (entity_type, str(entity_key), note, datetime.now().isoformat(timespec="seconds")))
    con.commit(); log(con, "Note added", entity_type, entity_key, note[:120])


def backup_database(con, destination):
    con.commit(); shutil.copy2(DB_PATH, destination); log(con, "Database backup", "system", destination, "")


def export_json(con, destination):
    tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    payload = {t: [dict(r) for r in con.execute(f"SELECT * FROM {t}")] for t in tables}
    Path(destination).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    log(con, "JSON export", "system", destination, "")


def export_table_csv(con, table, destination):
    rows = con.execute(f"SELECT * FROM {table}").fetchall()
    if not rows: return
    with open(destination, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f); w.writerow(rows[0].keys()); w.writerows([tuple(r) for r in rows])
    log(con, "CSV export", table, destination, "")
