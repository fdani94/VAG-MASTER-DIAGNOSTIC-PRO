from __future__ import annotations

import csv
import gzip
import shutil
import sqlite3
import sys
import types
from pathlib import Path


V2_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = V2_ROOT.parent
OUTPUT = V2_ROOT / "assets" / "vag_master_v2.db"
BUILD_OUTPUT = OUTPUT.with_name("vag_master_v2.building.db")
PUBLISH_OUTPUT = OUTPUT.with_name("vag_master_v2.publish.db")
ARCHIVE_OUTPUT = OUTPUT.with_suffix(".db.gz")
ARCHIVE_BUILD_OUTPUT = OUTPUT.with_name("vag_master_v2.building.db.gz")
CSV_PATH = V2_ROOT / "assets" / "obd_trouble_codes.csv"
GENERIC_SOURCE_URL = "https://github.com/foerbsnavi/OBDex"
EXPECTED_GENERIC_TITLES = {
    "P0128": "Coolant Thermostat Below Regulating Temperature",
    "P0130": "O2 Sensor Circuit Malfunction (Bank 1, Sensor 1)",
    "P0131": "O2 Sensor Circuit Low Voltage (Bank 1, Sensor 1)",
    "P0132": "O2 Sensor Circuit High Voltage (Bank 1, Sensor 1)",
    "P0300": "Random/Multiple Cylinder Misfire Detected",
    "P0420": "Catalyst System Efficiency Below Threshold (Bank 1)",
    "U0100": 'Lost Communication with ECM/PCM "A"',
}
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(V2_ROOT))

from localization import romanianize


try:
    import PySide6.QtCore  # noqa: F401
except Exception:
    qtcore = types.ModuleType("PySide6.QtCore")

    class QStandardPaths:
        AppDataLocation = 0

        @staticmethod
        def writableLocation(_):
            return str(OUTPUT.parent)

    qtcore.QStandardPaths = QStandardPaths
    pyside = types.ModuleType("PySide6")
    pyside.QtCore = qtcore
    sys.modules["PySide6"] = pyside
    sys.modules["PySide6.QtCore"] = qtcore


import appdb
from airbag_instruments_immobilizer_expansion import install as install_airbag
from all_platforms_models_expansion import install as install_all_platforms
from autoscan_audi_b8_common_pack import install as install_audi_b8
from autoscan_bcu_dtc_pack import install as install_bcu
from autoscan_can_gateway_master import install as install_gateway
from autoscan_chassis_dtc_pack import install as install_chassis_dtc
from autoscan_dtc_expansion_2 import install as install_dtc_2
from autoscan_dtc_pack import install as install_dtc
from autoscan_mass_dtc_pack import install as install_mass_dtc
from autoscan_verified_dtc_pack_3 import install as install_verified_dtc
from battery_visibility_pack import install as install_battery_visibility
from brake_steering_procedures_expansion import install as install_brake_steering
from catalog_complete_1996_2024 import install as install_catalog
from coding_market_pack import install as install_coding_market
from comfort_gateway_multimedia_expansion import install as install_comfort
from community_coding_pack import install as install_community_coding
from coverage_gap_filler import install as install_gap_filler
from engine_battery_fix_pack import install as install_engine_battery
from engine_procedures_expansion import install as install_engine
from expert_data_pack import install as install_expert
from hvac_procedures_expansion import install as install_hvac
from legacy_schema_compat import ensure_legacy_schema, migrate_legacy_procedures
from lighting_headlight_procedures_expansion import install as install_lighting
from long_coding_master_pack import install as install_long_coding
from model_specific_pack import install as install_model_1
from model_specific_pack_2 import install as install_model_2
from replacement_calibration_pack import install as install_replacement
from service_powertrain_pack import install as install_service
from supermaster_expansion import install as install_supermaster
from transmission_procedures_expansion import install as install_transmission
from vag_1996_2024_coverage_expansion import install as install_coverage
from vag_1996_2024_pack import install as install_1996_2024
from vcds_workshop_pack import install as install_workshop


def _remove_database_family(path: Path) -> None:
    """Elimină numai fișierul SQLite indicat și fișierele sale tranzacționale."""
    for candidate in (
        path,
        Path(f"{path}-journal"),
        Path(f"{path}-wal"),
        Path(f"{path}-shm"),
    ):
        if candidate.exists():
            candidate.unlink()


def _remove_database_sidecars(path: Path) -> None:
    """Elimină jurnalele unei baze fără a atinge fișierul principal."""
    for candidate in (
        Path(f"{path}-journal"),
        Path(f"{path}-wal"),
        Path(f"{path}-shm"),
    ):
        if candidate.exists():
            candidate.unlink()


def _publish_compressed_snapshot(source: Path) -> Path:
    """Publică reproductibil și atomic snapshotul comprimat folosit de surse."""
    ARCHIVE_BUILD_OUTPUT.unlink(missing_ok=True)
    with source.open("rb") as input_stream, ARCHIVE_BUILD_OUTPUT.open("wb") as raw_output:
        with gzip.GzipFile(
            filename="",
            mode="wb",
            compresslevel=9,
            fileobj=raw_output,
            mtime=0,
        ) as compressed:
            shutil.copyfileobj(input_stream, compressed, length=1024 * 1024)
    ARCHIVE_BUILD_OUTPUT.replace(ARCHIVE_OUTPUT)
    return ARCHIVE_OUTPUT


def _generic_dtc_profile(code: str, title_ro: str) -> dict[str, str]:
    """Construiește o fișă de atelier în română pentru un cod OBD generic."""
    family = code[:1]
    family_name = {
        "P": "grup motopropulsor",
        "B": "caroserie, confort și siguranță pasivă",
        "C": "șasiu, frânare și direcție",
        "U": "comunicație și rețea de bord",
    }.get(family, "sistem electronic al vehiculului")
    module_hint = {
        "P": "Motor, transmisie sau modul de propulsie",
        "B": "Modul caroserie, confort, airbag sau echipare interioară",
        "C": "ABS/ESP, direcție, suspensie sau șasiu",
        "U": "Gateway sau modulul care a raportat pierderea comunicației",
    }.get(family, "Modulul care a memorat codul")
    location = {
        "P": "În compartimentul motor, transmisie ori sistemul de propulsie; poziția exactă se stabilește după cod motor și numărul piesei.",
        "B": "În habitaclu sau caroserie; poziția exactă depinde de echiparea și schema electrică a vehiculului.",
        "C": "La trenul de rulare, sistemul de frânare, direcție sau suspensie; confirmați după schema modelului.",
        "U": "În modulul raportor și pe traseul CAN/LIN/FlexRay/Ethernet corespunzător; folosiți topologia Gateway.",
    }.get(family, "Poziția exactă se confirmă din schema electrică a vehiculului.")

    symptoms = {
        "P": "Martor motor sau propulsie posibil aprins\nFuncționare neregulată, putere limitată, consum ori emisii modificate\nSimptomul exact depinde de condițiile memorate la apariția codului",
        "B": "Funcție de confort, iluminare sau siguranță indisponibilă ori intermitentă\nMesaj de avertizare posibil în panoul de instrumente\nSimptomul se confirmă prin test funcțional pe vehicul",
        "C": "Martor ABS/ESP/direcție/suspensie posibil aprins\nFuncția de asistență poate fi limitată sau dezactivată\nComportamentul dinamic se verifică numai în condiții sigure",
        "U": "Unul sau mai multe module pot lipsi din scanare\nFuncții dependente de rețea pot fi intermitente ori indisponibile\nPot apărea coduri secundare în mai multe unități",
    }.get(family, "Simptome dependente de modul și de condițiile memorate la apariția codului")
    causes = {
        "P": "Alimentare, masă, siguranță, cablaj sau conector\nSenzor ori actuator cu semnal în afara domeniului\nProblemă mecanică, pneumatică, hidraulică sau de etanșeitate\nDefect secundar produs de alt cod primar sau de tensiune joasă",
        "B": "Alimentare, masă, cablaj ori conector în zona caroseriei\nComutator, senzor, motor sau actuator blocat/uzat\nCodare, adaptare ori configurație incompatibilă\nDefect secundar după subtensiune sau intervenție",
        "C": "Alimentare, masă, cablaj sau senzor de șasiu\nJoc mecanic, geometrie, presiune ori calibrare necorespunzătoare\nActuator hidraulic/electric cu funcționare limitată\nDefect secundar de comunicație sau tensiune",
        "U": "Tensiune joasă, alimentare sau masă instabilă\nCircuit CAN/LIN întrerupt, scurtcircuitat ori terminat incorect\nModul nealimentat, necodificat sau incompatibil\nConector oxidat, apă ori intervenție anterioară pe instalație",
    }.get(family, "Alimentare, cablaj, conector, senzor, actuator sau configurație")
    checks = {
        "U": "Salvați Auto-Scan-ul complet și identificați modulul raportor și modulul absent\nVerificați tensiunea bateriei, alimentările, masele și siguranțele\nComparați lista de instalare Gateway cu echiparea reală\nVerificați rezistența și formele de undă ale magistralei conform schemei\nIzolați ramura defectă fără a înlocui module la întâmplare\nȘtergeți codurile și repetați Auto-Scan-ul după remediere",
    }.get(
        family,
        "Salvați Auto-Scan-ul original și datele memorate la apariția erorii\nVerificați buletinele și schema exactă pentru VIN, cod motor și număr de piesă\nInspectați alimentarea, masa, siguranțele, cablajul și conectorii\nComparați valorile solicitate cu cele reale în VCDS\nFolosiți testele de actuatori sau setările de bază numai dacă procedura le cere\nConfirmați electric și mecanic cauza înainte de înlocuirea piesei",
    )
    measurements = (
        "Stare comunicație; tensiune terminal 30; erori pe magistrală; lista de instalare Gateway"
        if family == "U"
        else "Valoare solicitată; valoare reală; tensiune alimentare; masă; semnal; condiții de activare"
    )
    severity = "Ridicat - verificați înainte de utilizare" if family == "C" else "Mediu - necesită confirmare"
    return {
        "description": (
            f"Cod OBD generic din familia {family_name}: {title_ro}. Codul indică o abatere detectată de unitatea de comandă; "
            "nu dovedește singur că piesa menționată este defectă. Textul exact VCDS și datele memorate au prioritate."
        ),
        "symptoms": symptoms,
        "causes": causes,
        "diagnosis": checks,
        "repair": (
            "Remediați cauza confirmată prin măsurători și inspecție\n"
            "Refaceți cablajul/conectorii sau mecanismul înainte de a considera modulul defect\n"
            "Efectuați codarea, adaptarea ori setarea de bază numai când documentația o cere\n"
            "Ștergeți erorile, faceți testul funcțional/rutier în siguranță și repetați Auto-Scan-ul"
        ),
        "severity": severity,
        "component": f"Sistem/componente indicate de definiție: {title_ro}",
        "component_location": location,
        "test_path": "[Modulul care a memorat DTC-ul] > Coduri de eroare > Date memorate > Valori de măsură avansate",
        "vcds_parameters": measurements,
        "expected_values": "Folosiți valorile-limită documentate pentru unitatea, software-ul și vehiculul identificat; nu există un prag universal.",
        "replacement_steps": (
            "Confirmați defectul prin măsurare și eliminați cauzele comune\n"
            "Notați codarea/adaptările și numărul exact al piesei\n"
            "Înlocuiți numai cu o componentă compatibilă\n"
            "Efectuați parametrizarea/codarea autorizată, verificarea funcțională și Auto-Scan-ul final"
        ),
        "confidence": "Definiție generică OBDex CC0; necesită confirmare pe vehicul",
        "module_hint": module_hint,
    }


def build() -> Path:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    # Construim separat și înlocuim baza publicată numai după verificarea
    # integrală. Astfel, un build întrerupt nu poate lăsa aplicația fără bază.
    _remove_database_family(BUILD_OUTPUT)
    _remove_database_family(PUBLISH_OUTPUT)
    appdb.APP_DATA = OUTPUT.parent
    appdb.DB_PATH = BUILD_OUTPUT
    appdb.LOGO_PATH = OUTPUT.parent / "custom_logo.png"
    appdb.src_diag = None

    con = appdb.connect_db()
    for installer in (
        install_supermaster,
        install_1996_2024,
        install_catalog,
        install_coverage,
        install_all_platforms,
        install_transmission,
        install_engine,
        install_brake_steering,
    ):
        installer(con)
    ensure_legacy_schema(con)
    for installer in (install_lighting, install_hvac, install_airbag, install_comfort):
        installer(con)
    migrate_legacy_procedures(con)
    for installer in (
        install_supermaster,
        install_expert,
        install_replacement,
        install_service,
        install_coding_market,
        install_community_coding,
        install_workshop,
        install_model_1,
        install_model_2,
        install_battery_visibility,
        install_engine_battery,
        install_long_coding,
        install_dtc,
        install_dtc_2,
        install_chassis_dtc,
        install_mass_dtc,
        install_verified_dtc,
        install_bcu,
        install_gateway,
        install_audi_b8,
        install_gap_filler,
    ):
        installer(con)

    source = con.execute(
        "SELECT id FROM sources WHERE url=?",
        (GENERIC_SOURCE_URL,),
    ).fetchone()
    if source:
        source_id = source[0]
    else:
        source_id = con.execute(
            """INSERT INTO sources(title,publisher,url,accessed,source_type,notes)
               VALUES(?,?,?,?,?,?)""",
            (
                "OBDex - catalog generic OBD-II",
                "Comunitatea OBDex",
                GENERIC_SOURCE_URL,
                "2026-08-20",
                "Date deschise CC0-1.0",
                "Definiții independente pentru codurile generice. Textul exact VCDS și documentația vehiculului au prioritate.",
            ),
        ).lastrowid

    catalog: dict[str, str] = {}
    with CSV_PATH.open(encoding="utf-8", newline="") as stream:
        for row in csv.reader(stream):
            if len(row) < 2:
                continue
            code, title = row[0].strip().upper(), row[1].strip()
            if not code or not title:
                continue
            if code in catalog:
                raise RuntimeError(f"Cod OBD duplicat în catalog: {code}")
            catalog[code] = title

    mismatches = {
        code: (catalog.get(code), expected)
        for code, expected in EXPECTED_GENERIC_TITLES.items()
        if catalog.get(code) != expected
    }
    if len(catalog) != 9533 or mismatches:
        raise RuntimeError(
            f"Catalog OBDex invalid: count={len(catalog)}, definiții_neconforme={mismatches}"
        )

    for code, title in catalog.items():
        title_ro = romanianize(title)
        profile = _generic_dtc_profile(code, title_ro)
        con.execute(
            """INSERT OR IGNORE INTO dtcs
               (code,title,description,symptoms,causes,diagnosis,repair,severity,verified,source_id,
                component,component_location,test_path,vcds_parameters,expected_values,
                replacement_steps,confidence,module_hint)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                code,
                title,
                profile["description"],
                profile["symptoms"],
                profile["causes"],
                profile["diagnosis"],
                profile["repair"],
                profile["severity"],
                0,
                source_id,
                profile["component"],
                profile["component_location"],
                profile["test_path"],
                profile["vcds_parameters"],
                profile["expected_values"],
                profile["replacement_steps"],
                profile["confidence"],
                profile["module_hint"],
            ),
        )

    columns = {row[1] for row in con.execute("PRAGMA table_info(dtcs)")}
    if "title_ro" not in columns:
        con.execute("ALTER TABLE dtcs ADD COLUMN title_ro TEXT DEFAULT ''")
    titles = list(con.execute("SELECT id,title FROM dtcs"))
    con.executemany(
        "UPDATE dtcs SET title_ro=? WHERE id=?",
        [(romanianize(str(row[1])), row[0]) for row in titles],
    )

    con.executescript(
        """CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
           INSERT OR REPLACE INTO metadata(key,value) VALUES('database_version','2.2-profesional');
           INSERT OR REPLACE INTO metadata(key,value) VALUES('language','ro');
           INSERT OR REPLACE INTO metadata(key,value) VALUES('synthetic_data','false');
           CREATE INDEX IF NOT EXISTS idx_dtcs_title ON dtcs(title);
           CREATE INDEX IF NOT EXISTS idx_dtcs_title_ro ON dtcs(title_ro);
           ANALYZE;
           PRAGMA optimize;"""
    )
    con.commit()
    con.close()

    # Publicăm un snapshot SQLite nou, nu fișierul de lucru. Astfel, niciun
    # jurnal tranzacțional al instalatoarelor V1 nu poate însoți baza V2.
    source = sqlite3.connect(BUILD_OUTPUT)
    published = sqlite3.connect(PUBLISH_OUTPUT)
    try:
        source.backup(published)
        published.commit()
    finally:
        published.close()
        source.close()
    _remove_database_family(BUILD_OUTPUT)

    check = sqlite3.connect(PUBLISH_OUTPUT)
    counts = {
        table: check.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in ("dtcs", "procedure_library", "vehicle_procedures", "generations", "engines")
    }
    integrity = check.execute("PRAGMA integrity_check").fetchone()[0]
    check.close()
    if integrity != "ok" or counts["dtcs"] < 9500 or counts["procedure_library"] < 200:
        _remove_database_family(PUBLISH_OUTPUT)
        raise RuntimeError(f"Bază incompletă: integrity={integrity}, counts={counts}")
    _remove_database_sidecars(OUTPUT)
    PUBLISH_OUTPUT.replace(OUTPUT)
    _remove_database_family(PUBLISH_OUTPUT)
    archive = _publish_compressed_snapshot(OUTPUT)
    print(f"Bază creată: {OUTPUT}")
    print(f"Snapshot comprimat: {archive}")
    print(" | ".join(f"{name}={value}" for name, value in counts.items()))
    return OUTPUT


if __name__ == "__main__":
    build()
