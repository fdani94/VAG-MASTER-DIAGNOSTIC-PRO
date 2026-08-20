import sqlite3
import tempfile
import unittest
from pathlib import Path

from data import load_procedures
from database import get_database, materialize_database_archive


class DatabaseTests(unittest.TestCase):
    def test_compressed_snapshot_materializes_as_complete_sqlite(self):
        archive = Path(__file__).resolve().parents[1] / "assets" / "vag_master_v2.db.gz"
        self.assertTrue(archive.is_file())
        self.assertLess(archive.stat().st_size, 10_000_000)
        with tempfile.TemporaryDirectory() as temporary:
            database_path = materialize_database_archive(archive, Path(temporary))
            self.assertTrue(database_path.is_file())
            connection = sqlite3.connect(database_path)
            try:
                self.assertEqual(
                    connection.execute("PRAGMA quick_check").fetchone()[0], "ok"
                )
                self.assertGreaterEqual(
                    connection.execute("SELECT COUNT(*) FROM dtcs").fetchone()[0],
                    9500,
                )
            finally:
                connection.close()

    def test_database_is_large_localized_and_integral(self):
        database = get_database()
        stats = database.stats()
        self.assertGreaterEqual(stats["DTC"], 9500)
        self.assertGreaterEqual(stats["proceduri"], 200)
        self.assertGreaterEqual(stats["aplicabilități"], 10000)
        self.assertGreaterEqual(stats["generații"], 100)
        self.assertGreaterEqual(stats["surse"], 100)

        verification = sqlite3.connect(database.path)
        self.assertEqual(
            verification.execute("PRAGMA integrity_check").fetchone()[0], "ok"
        )
        metadata = dict(verification.execute("SELECT key,value FROM metadata"))
        verification.close()
        self.assertEqual(metadata["language"], "ro")
        self.assertEqual(metadata["synthetic_data"], "false")
        self.assertEqual(metadata["database_version"], "2.2-profesional")
        self.assertNotIn("demo_mode", metadata)

    def test_detailed_entries_override_generic_catalog(self):
        database = get_database()
        detailed = database.lookup_dtc("P261A")
        generic = database.lookup_dtc("P0105")
        self.assertIsNotNone(detailed)
        self.assertIsNotNone(generic)
        self.assertEqual(int(detailed["verified"]), 1)
        self.assertEqual(int(generic["verified"]), 0)
        self.assertIn("pompă", detailed["title_ro"].casefold())

    def test_generic_catalog_is_aligned_localized_and_traceable(self):
        database = get_database()
        thermostat = database.lookup_dtc("P0128")
        oxygen = database.lookup_dtc("P0132")
        network = database.lookup_dtc("U0100")
        pedestrian = database.lookup_dtc("B0122")

        self.assertEqual(
            thermostat["title"], "Coolant Thermostat Below Regulating Temperature"
        )
        self.assertEqual(
            oxygen["title"], "O2 Sensor Circuit High Voltage (Bank 1, Sensor 1)"
        )
        self.assertIn("tensiune", oxygen["title_ro"].casefold())
        self.assertEqual(network["title"], 'Lost Communication with ECM/PCM "A"')
        self.assertIn("comunicație pierdută", network["title_ro"].casefold())
        self.assertEqual(pedestrian["title_ro"], "Difuzor avertizare pietoni A")
        self.assertIn("OBDex", oxygen["source_title"])
        self.assertEqual(oxygen["source_url"], "https://github.com/foerbsnavi/OBDex")
        self.assertIn("CC0", oxygen["confidence"])
        self.assertGreaterEqual(len(oxygen["diagnosis"].splitlines()), 6)

    def test_guided_libraries_are_populated(self):
        self.assertGreaterEqual(len(load_procedures("coding")), 50)
        self.assertGreaterEqual(len(load_procedures("adaptation")), 100)
        self.assertGreaterEqual(len(load_procedures("service")), 40)


if __name__ == "__main__":
    unittest.main()
