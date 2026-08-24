from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
V2 = Path(__file__).resolve().parent
for path in (ROOT, V2):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from PySide6.QtWidgets import QApplication, QMessageBox

import main_v2

main_v2.prepare_database()
main_v2.apply_v2_patches()

import ui_v2
import v2_functional_windows_patch as functional
import v2_vehicle_first_patch as vf
from v2_vehicle_precision_patch import PRECISION_VERSION


SCAN_TEMPLATE = """VCDS -- Windows Based VAG/VAS Emulator
VCDS Version: 25.3.1.0
Data version: 20260301 DS365.0
VIN: WVWZZZAUZFW000001   License Plate:
Mileage: 123456km
{chassis_line}

-------------------------------------------------------------------------------
Address 09: Cent. Elect. (J519)       Labels: None
   Part No SW: 5Q0 937 084 AA    HW: 5Q0 937 084
   Component: BCM MQBAB H25 0253
   Coding: 001122334455
   ASAM Dataset: EV_BCMMQB 015001
No fault code found.
"""


def _choose_text(combo, text):
    for index in range(combo.count()):
        if text.lower() in combo.itemText(index).lower():
            combo.setCurrentIndex(index)
            return True
    return False


class VehiclePrecisionV221Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
        QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
        QMessageBox.critical = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)

    def setUp(self):
        self.window = ui_v2.MainWindowV2()
        self.window.show()
        self.app.processEvents()

    def tearDown(self):
        self.window.close()
        self.app.processEvents()

    def _select_golf_vii(self, year=2015):
        self.assertTrue(_choose_text(self.window.brand_combo, "Volkswagen"))
        self.app.processEvents()
        self.assertTrue(_choose_text(self.window.model_combo, "Golf"))
        self.app.processEvents()
        self.assertTrue(_choose_text(self.window.gen_combo, "VII 5G/AU"))
        self.app.processEvents()
        self.assertTrue(_choose_text(self.window.year_combo, str(year)))
        self.app.processEvents()
        self.assertGreater(self.window.engine_combo.count(), 1)
        self.window.engine_combo.setCurrentIndex(1)
        self.assertIsNotNone(self.window.engine_combo.currentData())
        self.window._select_vehicle()
        self.app.processEvents()
        return vf.selected_vehicle_context(self.window)

    def _load_scan(self, chassis_type: str | None):
        chassis_line = f"Chassis Type: {chassis_type}" if chassis_type else ""
        sample = ROOT / f"_v221_precision_{chassis_type or 'none'}.txt"
        sample.write_text(SCAN_TEMPLATE.format(chassis_line=chassis_line), encoding="utf-8")
        original = functional.QFileDialog.getOpenFileName
        try:
            functional.QFileDialog.getOpenFileName = staticmethod(
                lambda *a, **k: (str(sample), "Text (*.txt)")
            )
            self.window._load_autoscan()
            self.app.processEvents()
        finally:
            functional.QFileDialog.getOpenFileName = original
        return sample

    def test_release_and_title_are_221(self):
        self.assertEqual(PRECISION_VERSION, "2.2.1")
        self.assertIn("2.3.0", self.window.windowTitle())
        self.assertIn("Coding Recovery", self.window.windowTitle())

    def test_engine_dropdown_obeys_vehicle_engine_year_ranges(self):
        self._select_golf_vii(2015)
        gid = self.window.gen_combo.currentData()
        year = self.window.year_combo.currentData()
        expected = {
            row["id"]
            for row in self.window.con.execute(
                """SELECT e.id FROM vehicle_engines ve JOIN engines e ON e.id=ve.engine_id
                   WHERE ve.generation_id=?
                     AND (ve.year_from IS NULL OR ve.year_from<=?)
                     AND (ve.year_to IS NULL OR ve.year_to>=?)""",
                (gid, year, year),
            ).fetchall()
        }
        displayed = {
            self.window.engine_combo.itemData(i)
            for i in range(1, self.window.engine_combo.count())
        }
        self.assertEqual(displayed, expected)
        all_for_generation = {
            row["id"]
            for row in self.window.con.execute(
                "SELECT engine_id id FROM vehicle_engines WHERE generation_id=?",
                (gid,),
            ).fetchall()
        }
        self.assertTrue(displayed.issubset(all_for_generation))

    def test_modules_page_never_falls_back_to_entire_catalog(self):
        total = self.window.con.execute("SELECT COUNT(*) FROM modules").fetchone()[0]
        mapped = self.window.con.execute(
            """SELECT generation_id,COUNT(*) c FROM generation_modules
               GROUP BY generation_id HAVING COUNT(*)>0 ORDER BY COUNT(*) DESC LIMIT 1"""
        ).fetchone()

        if mapped is not None:
            self.window.selected_generation_id = mapped["generation_id"]
            expected_count = mapped["c"]
        else:
            generation = self.window.con.execute("SELECT id FROM generations ORDER BY id LIMIT 1").fetchone()
            self.assertIsNotNone(generation)
            self.window.selected_generation_id = generation["id"]
            expected_count = 0

        self.window.autoscan_vehicle_binding_ok = False
        self.window.current_autoscan = None
        self.window._load_modules()
        self.app.processEvents()
        self.assertEqual(self.window.module_table.rowCount(), expected_count)
        self.assertLess(self.window.module_table.rowCount(), total)

        if expected_count:
            statuses = [
                self.window.module_table.item(i, 0).text()
                for i in range(self.window.module_table.rowCount())
            ]
            self.assertTrue(all(status == "MAPAT GENERAȚIE" for status in statuses))
        else:
            self.assertIn("Auto-Scan", self.window.module_table.toolTip())
            self.assertIn("hartă locală", self.window.module_table.toolTip())

    def test_mismatched_chassis_scan_is_rejected_for_selected_vehicle(self):
        self._select_golf_vii(2015)
        self._load_scan("3C")
        self.assertIsNone(self.window.current_autoscan)
        self.assertFalse(self.window.autoscan_vehicle_binding_ok)
        self.assertIn("RESPINS", self.window.autoscan_summary.text())
        page = self.window._workspace_pages[3]
        self.window._load_procedures(page)
        statuses = [page.table.item(i, 0).text() for i in range(page.table.rowCount())]
        self.assertNotIn("CONTROLLER CONFIRMAT", statuses)
        self.assertNotIn("MODUL GĂSIT AUTOSCAN", statuses)

    def test_scan_without_chassis_can_be_read_but_cannot_confirm_coding(self):
        self._select_golf_vii(2015)
        self._load_scan(None)
        self.assertIsNotNone(self.window.current_autoscan)
        self.assertFalse(self.window.autoscan_vehicle_binding_ok)
        self.assertEqual(self.window.autoscan_vehicle_match["status"], "unverified")
        self.assertIn("NECONFIRMAT", self.window.autoscan_summary.text())
        page = self.window._workspace_pages[3]
        self.window._load_procedures(page)
        statuses = [page.table.item(i, 0).text() for i in range(page.table.rowCount())]
        self.assertNotIn("CONTROLLER CONFIRMAT", statuses)
        self.assertNotIn("MODUL GĂSIT AUTOSCAN", statuses)

    def test_matching_chassis_binds_scan_but_address_alone_does_not_confirm_procedure(self):
        self._select_golf_vii(2015)
        self._load_scan("5G")
        self.assertIsNotNone(self.window.current_autoscan)
        self.assertTrue(self.window.autoscan_vehicle_binding_ok)
        self.assertEqual(self.window.autoscan_vehicle_match["status"], "matched")

        base = {
            "module_address": "09",
            "source_url": "https://wiki.ross-tech.com/wiki/index.php/Test",
            "source_title": "Test procedure",
            "verified": 1,
            "title": "Precision controller test",
            "purpose": "Generic BCM coding",
            "prerequisites": "Auto-Scan BEFORE",
            "steps": "Documented steps only",
            "applicability": "Golf VII 5G/AU",
            "notes": "",
            "vcds_path": "09-Cent. Elect. > Coding - 07",
            "success_criteria": "No DTC",
            "warnings": "Keep original coding",
            "category": "Coding",
        }
        generic = vf._procedure_meta(self.window, dict(base))
        self.assertEqual(generic["status"], "MODUL GĂSIT AUTOSCAN")
        self.assertFalse(generic["controller_match"])

        exact_row = dict(base)
        exact_row["notes"] = "Controller 5Q0 937 084 AA only"
        exact = vf._procedure_meta(self.window, exact_row)
        self.assertEqual(exact["status"], "CONTROLLER CONFIRMAT")
        self.assertTrue(exact["controller_match"])
        self.assertEqual(exact["coding_original"], "001122334455")

    def test_coding_filters_procedure_for_other_engine(self):
        ctx = self._select_golf_vii(2015)
        gid = ctx["generation_id"]
        selected = ctx["engine_code"].upper()
        other = next(
            (code for code in [r["code"].upper() for r in self.window.con.execute(
                """SELECT e.code FROM vehicle_engines ve JOIN engines e ON e.id=ve.engine_id
                   WHERE ve.generation_id=? ORDER BY e.code""", (gid,)).fetchall()]
             if code != selected),
            None,
        )
        if other is None:
            self.skipTest("Generația de test nu are al doilea cod motor")

        ids = []
        try:
            for marker, engine_code in (("KEEP", selected), ("DROP", other)):
                cur = self.window.con.execute(
                    """INSERT INTO procedure_library(
                       title,category,module_address,vcds_path,purpose,prerequisites,steps,
                       success_criteria,warnings,applicability_rule,verified,source_id
                       ) VALUES(?,?,?,?,?,?,?,?,?,?,?,NULL)""",
                    (
                        f"PRECISION-ENGINE-TEST-{marker}", "Coding", "09",
                        "09-Cent. Elect. > Coding - 07",
                        f"Only engine {engine_code}", "Auto-Scan BEFORE", "Test step",
                        "Success", "Warning", "Condițional", 1,
                    ),
                )
                pid = cur.lastrowid
                ids.append(pid)
                self.window.con.execute(
                    "INSERT INTO vehicle_procedures(generation_id,procedure_id,applicability,notes) VALUES(?,?,?,?)",
                    (gid, pid, f"Engine {engine_code}", f"Engine {engine_code}"),
                )
            self.window.con.commit()

            page = self.window._workspace_pages[3]
            page.search.setText("PRECISION-ENGINE-TEST")
            self.window._load_procedures(page)
            rows = page.table.property("rows") or []
            titles = [row["title"] for row in rows]
            self.assertIn("PRECISION-ENGINE-TEST-KEEP", titles)
            self.assertNotIn("PRECISION-ENGINE-TEST-DROP", titles)
        finally:
            for pid in ids:
                self.window.con.execute("DELETE FROM vehicle_procedures WHERE procedure_id=?", (pid,))
                self.window.con.execute("DELETE FROM procedure_library WHERE id=?", (pid,))
            self.window.con.commit()


if __name__ == "__main__":
    unittest.main(verbosity=2)
