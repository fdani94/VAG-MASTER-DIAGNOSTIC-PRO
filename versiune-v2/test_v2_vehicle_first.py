from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
V2 = Path(__file__).resolve().parent
for path in (ROOT, V2):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from PySide6.QtWidgets import QApplication

import main_v2

main_v2.prepare_database()
main_v2.apply_v2_patches()

import ui_v2
import v2_functional_windows_patch as functional
from v2_ai_functional_validation import UDS_SAMPLE
from v2_vehicle_first_patch import VEHICLE_FIRST_VERSION, selected_vehicle_context


def _choose_text(combo, text):
    for index in range(combo.count()):
        if text.lower() in combo.itemText(index).lower():
            combo.setCurrentIndex(index)
            return True
    return False


class VehicleFirstV220Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.window = ui_v2.MainWindowV2()
        self.window.show()
        self.app.processEvents()

    def tearDown(self):
        self.window.close()
        self.app.processEvents()
        temp = ROOT / "_v220_autoscan_refresh_test.txt"
        if temp.exists():
            temp.unlink()

    def _select_golf_vii(self):
        self.assertTrue(_choose_text(self.window.brand_combo, "Volkswagen"))
        self.app.processEvents()
        self.assertTrue(_choose_text(self.window.model_combo, "Golf"))
        self.app.processEvents()
        self.assertTrue(_choose_text(self.window.gen_combo, "VII 5G/AU"))
        self.app.processEvents()
        self.assertTrue(_choose_text(self.window.year_combo, "2015"))
        self.app.processEvents()
        self.assertGreater(self.window.engine_combo.count(), 1)
        self.window.engine_combo.setCurrentIndex(1)
        self.assertIsNotNone(self.window.engine_combo.currentData())
        self.window._select_vehicle()
        self.app.processEvents()

    def _coding_target(self):
        page = self.window._workspace_pages[3]
        self.window._load_procedures(page)
        rows = page.table.property("rows") or []
        target = next((row for row in rows if str(row["module_address"] or "").strip()), None)
        self.assertIsNotNone(target)
        return page, rows, target, str(target["module_address"]).strip()

    def test_version_and_full_vehicle_context(self):
        self.assertEqual(VEHICLE_FIRST_VERSION, "2.2.0")
        self._select_golf_vii()
        ctx = selected_vehicle_context(self.window)
        self.assertEqual(ctx["brand"], "Volkswagen")
        self.assertEqual(ctx["model"], "Golf")
        self.assertIn("VII", ctx["generation"])
        self.assertEqual(ctx["year"], 2015)
        self.assertTrue(ctx["engine_id"])
        self.assertTrue(ctx["engine_code"])
        self.assertIn(ctx["engine_code"], self.window.vehicle_badge.text())
        self.assertIn("2.3.0", self.window.windowTitle())
        self.assertIn("Coding Recovery", self.window.windowTitle())

    def test_all_workspaces_receive_same_vehicle_context(self):
        self._select_golf_vii()
        ctx = selected_vehicle_context(self.window)
        for index in range(1, 9):
            strip = self.window._vehicle_context_strips[index]
            text = strip._kid_vehicle_label.text()
            self.assertIn("Volkswagen Golf", text)
            self.assertIn(str(ctx["year"]), text)
            self.assertIn(ctx["engine_code"], text)
            self.assertEqual(strip._kid_vehicle_state.text(), "SELECTAT")

    def test_coding_is_vehicle_filtered_and_explicit(self):
        self._select_golf_vii()
        self.window.open_page(3)
        self.app.processEvents()
        page = self.window._workspace_pages[3]
        rows = page.table.property("rows") or []
        self.assertGreater(len(rows), 0)
        self.assertEqual(page.table.columnCount(), 7)
        self.assertEqual(page.table.horizontalHeaderItem(0).text(), "Status")
        self.assertEqual(page.table.horizontalHeaderItem(2).text(), "Codare / funcție")
        self.assertEqual(page.table.horizontalHeaderItem(4).text(), "Motor / an")
        self.assertGreaterEqual(page.table.currentRow(), 0)
        detail = page.detail.toPlainText()
        self.assertIn("MAȘINA PE CARE LUCREZI", detail)
        self.assertIn("PRECIZIE PENTRU SELECȚIA ACTUALĂ", detail)
        self.assertIn("CALE EXACTĂ ÎN VCDS", detail)
        self.assertIn("PAȘI DOCUMENTAȚI", detail)
        self.assertIn("CUM ȘTII CĂ A REUȘIT", detail)
        self.assertIn("POTRIVIRE CU VEHICULUL SELECTAT", detail)
        self.assertIn("ATENȚIE", detail)

    def test_autoscan_promotes_module_but_does_not_overclaim_controller(self):
        self._select_golf_vii()
        page, _rows, _target, address = self._coding_target()
        self.window.current_autoscan = SimpleNamespace(
            modules=[
                SimpleNamespace(
                    address=address,
                    coding="001122334455",
                    part_no_sw="5Q0 937 084",
                    part_no_hw="5Q0 937 084",
                    component="BCM MQBAB",
                    asam_dataset="EV_BCMCONTI",
                )
            ]
        )
        self.window.autoscan_vehicle_binding_ok = True
        self.window.refresh_vehicle_context_v220()
        self.window._load_procedures(page)
        self.app.processEvents()
        rows = page.table.property("rows") or []
        confirmed_index = next(
            (i for i, row in enumerate(rows) if str(row["module_address"] or "").strip().upper() == address.upper()),
            None,
        )
        self.assertIsNotNone(confirmed_index)
        page.table.selectRow(confirmed_index)
        self.window._show_procedure(page)
        self.app.processEvents()
        self.assertIn(
            page.table.item(confirmed_index, 0).text(),
            ("MODUL GĂSIT AUTOSCAN", "CONTROLLER CONFIRMAT"),
        )
        detail = page.detail.toPlainText()
        self.assertIn("CODING ORIGINAL DIN AUTO-SCAN", detail)
        self.assertIn("001122334455", detail)
        self.assertIn("5Q0 937 084", detail)
        self.assertIn("BCM MQBAB", detail)

    def test_vehicle_change_clears_previous_autoscan_evidence(self):
        self._select_golf_vii()
        page, _rows, _target, address = self._coding_target()
        self.window.current_autoscan = SimpleNamespace(
            modules=[SimpleNamespace(address=address, coding="OLD-CAR-CODING")],
            faults=[],
        )
        self.window.autoscan_vehicle_binding_ok = True
        self.window.autoscan_plans = [("old", "plan")]
        self.window.autoscan_correlation = {"old": True}
        self.window.v2_verified_report_text = "OLD VEHICLE REPORT"
        self.window._load_procedures(page)
        before_statuses = [page.table.item(i, 0).text() for i in range(page.table.rowCount())]
        self.assertTrue(any(s in ("MODUL GĂSIT AUTOSCAN", "CONTROLLER CONFIRMAT") for s in before_statuses))

        new_year_index = next(
            (i for i in range(self.window.year_combo.count()) if self.window.year_combo.itemData(i) == 2016),
            None,
        )
        self.assertIsNotNone(new_year_index)
        self.window.year_combo.setCurrentIndex(new_year_index)
        self.app.processEvents()
        self.assertGreater(self.window.engine_combo.count(), 1)
        self.window.engine_combo.setCurrentIndex(1)
        self.window._select_vehicle()
        self.app.processEvents()

        self.assertIsNone(self.window.current_autoscan)
        self.assertFalse(self.window.autoscan_vehicle_binding_ok)
        self.assertEqual(self.window.autoscan_plans, [])
        self.assertIsNone(self.window.autoscan_correlation)
        self.assertEqual(self.window.v2_verified_report_text, "")
        self.assertIn("neîncărcat", self.window.autoscan_summary.text().lower())
        statuses = [page.table.item(i, 0).text() for i in range(page.table.rowCount())]
        self.assertNotIn("MODUL GĂSIT AUTOSCAN", statuses)
        self.assertNotIn("CONTROLLER CONFIRMAT", statuses)
        self.assertNotIn("OLD-CAR-CODING", page.detail.toPlainText())

    def test_importing_matching_autoscan_refreshes_already_open_coding_page(self):
        self._select_golf_vii()
        self.window.open_page(3)
        self.app.processEvents()
        page, _rows, _target, address = self._coding_target()
        before = [page.table.item(i, 0).text() for i in range(page.table.rowCount())]
        self.assertNotIn("MODUL GĂSIT AUTOSCAN", before)
        self.assertNotIn("CONTROLLER CONFIRMAT", before)

        sample = ROOT / "_v220_autoscan_refresh_test.txt"
        matched_sample = UDS_SAMPLE.replace("Chassis Type: 3C", "Chassis Type: 5G").replace(
            "Address 01:", f"Address {address}:"
        )
        sample.write_text(matched_sample, encoding="utf-8")
        original_dialog = functional.QFileDialog.getOpenFileName
        try:
            functional.QFileDialog.getOpenFileName = staticmethod(
                lambda *a, **k: (str(sample), "Text (*.txt)")
            )
            self.window._load_autoscan()
            self.app.processEvents()
        finally:
            functional.QFileDialog.getOpenFileName = original_dialog

        self.assertIsNotNone(self.window.current_autoscan)
        self.assertTrue(self.window.autoscan_vehicle_binding_ok)
        statuses = [page.table.item(i, 0).text() for i in range(page.table.rowCount())]
        self.assertTrue(any(s in ("MODUL GĂSIT AUTOSCAN", "CONTROLLER CONFIRMAT") for s in statuses))
        confirmed_index = next(i for i, s in enumerate(statuses) if s in ("MODUL GĂSIT AUTOSCAN", "CONTROLLER CONFIRMAT"))
        page.table.selectRow(confirmed_index)
        self.window._show_procedure(page)
        detail = page.detail.toPlainText()
        self.assertIn("CODING ORIGINAL DIN AUTO-SCAN", detail)
        self.assertIn("0119001203241D082000", detail)
        self.assertIn("AUTO-SCAN:", self.window._coding_overview._kid_scan_state.text())


if __name__ == "__main__":
    unittest.main(verbosity=2)
