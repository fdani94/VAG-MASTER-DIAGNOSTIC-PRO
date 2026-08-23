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

    def _select_golf_vii(self):
        self.assertTrue(_choose_text(self.window.brand_combo, "Volkswagen"))
        self.app.processEvents()
        self.assertTrue(_choose_text(self.window.model_combo, "Golf"))
        self.app.processEvents()
        self.assertTrue(_choose_text(self.window.gen_combo, "VII 5G/AU"))
        self.app.processEvents()
        self.assertTrue(_choose_text(self.window.year_combo, "2015"))
        self.assertGreater(self.window.engine_combo.count(), 1)
        self.window.engine_combo.setCurrentIndex(1)  # index 0 = Nespecificat
        self.assertIsNotNone(self.window.engine_combo.currentData())
        self.window._select_vehicle()
        self.app.processEvents()

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
        self.assertEqual(page.table.columnCount(), 6)
        self.assertEqual(page.table.horizontalHeaderItem(0).text(), "Status pe mașină")
        self.assertEqual(page.table.horizontalHeaderItem(2).text(), "Codare / funcție")
        self.assertGreaterEqual(page.table.currentRow(), 0)
        detail = page.detail.toPlainText()
        self.assertIn("MAȘINA PE CARE LUCREZI", detail)
        self.assertIn("CALE EXACTĂ ÎN VCDS", detail)
        self.assertIn("PAȘI DOCUMENTAȚI", detail)
        self.assertIn("CUM ȘTII CĂ A REUȘIT", detail)
        self.assertIn("POTRIVIRE CU VEHICULUL SELECTAT", detail)
        self.assertIn("ATENȚIE", detail)

    def test_autoscan_promotes_confirmed_module_and_original_coding(self):
        self._select_golf_vii()
        page = self.window._workspace_pages[3]
        self.window._load_procedures(page)
        rows = page.table.property("rows") or []
        target = next((row for row in rows if str(row["module_address"] or "").strip()), None)
        self.assertIsNotNone(target)
        address = str(target["module_address"]).strip()
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
        self.window.refresh_vehicle_context_v220()
        self.window._load_procedures(page)
        self.app.processEvents()
        rows = page.table.property("rows") or []
        confirmed_index = None
        for index, row in enumerate(rows):
            if str(row["module_address"] or "").strip().upper() == address.upper():
                confirmed_index = index
                break
        self.assertIsNotNone(confirmed_index)
        page.table.selectRow(confirmed_index)
        self.window._show_procedure(page)
        self.app.processEvents()
        self.assertEqual(page.table.item(confirmed_index, 0).text(), "CONFIRMAT AUTOSCAN")
        detail = page.detail.toPlainText()
        self.assertIn("CODING ORIGINAL DIN AUTO-SCAN", detail)
        self.assertIn("001122334455", detail)
        self.assertIn("5Q0 937 084", detail)
        self.assertIn("BCM MQBAB", detail)


if __name__ == "__main__":
    unittest.main(verbosity=2)
