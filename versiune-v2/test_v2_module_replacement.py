from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V2 = Path(__file__).resolve().parent
for path in (ROOT, V2):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from autoscan_parser import parse_autoscan_text
from v2_module_replacement import analyze_replacement_coding, render_recovery_text


HEADER = """VCDS Auto-Scan synthetic replacement test
VIN: TESTVIN1234567890
"""


def scan_with(block):
    return parse_autoscan_text(HEADER + "\n" + block)


class ModuleReplacementAnalyzerV230Tests(unittest.TestCase):
    def test_01042_is_explicit_not_coded(self):
        scan = scan_with("""
Address 55: Headlight Range
Part No SW: 5M0 907 357 C
Part No HW: 5M0 907 357 C
Component: AFS-Steuergeraet
Coding: 0000000
Shop #: WSC 00000 000 00000
1 Fault Found:
01042 - Control Module; Not Coded
            000 - -
""")
        analysis = analyze_replacement_coding(scan)
        self.assertEqual(len(analysis.findings), 1)
        item = analysis.findings[0]
        self.assertEqual(item.kind, "NOT_CODED")
        self.assertEqual(item.severity, "CRITIC")
        self.assertEqual(item.address, "55")
        self.assertEqual(item.coding, "0000000")
        self.assertIn("01042", item.source_title)
        self.assertFalse(item.requires_online)

    def test_u1013_is_explicit_not_coded(self):
        scan = scan_with("""
Address 5F: Information Electr.
Part No SW: 3Q0 035 846
Component: MU-S-N-ER
1 Fault Found:
29709 - Control Module Not Coded
            U1013 - 00 [009] - -
            Confirmed
""")
        item = analyze_replacement_coding(scan).findings[0]
        self.assertEqual(item.kind, "NOT_CODED")
        self.assertTrue("U1013" in item.source_title or "01042" in item.source_title)

    def test_01044_is_incorrect_coding_and_preserves_current_value_as_evidence(self):
        scan = scan_with("""
Address 03: ABS Brakes
Part No SW: 5Q0 614 517
Part No HW: 5Q0 614 517
Component: ESC
Coding: 01FA6A124924096D007D060841C9298056249000608294F300285078C002
1 Fault Found:
01044 - Control Module Incorrectly Coded
            000 - -
""")
        item = analyze_replacement_coding(scan).findings[0]
        self.assertEqual(item.kind, "INCORRECT_CODING")
        self.assertEqual(item.dtc_code, "01044")
        self.assertTrue(item.coding.startswith("01FA6A"))
        self.assertTrue(any("NU valoare confirmată" in line for line in item.evidence))

    def test_component_protection_is_online_blocker_not_simple_coding(self):
        scan = scan_with("""
Address 56: Radio
Part No SW: 4F0 035 056
Component: Radio U S Premium
1 Fault Found:
02095 - Component Protection Active
            000 - -
""")
        item = analyze_replacement_coding(scan).findings[0]
        self.assertEqual(item.kind, "COMPONENT_PROTECTION")
        self.assertEqual(item.severity, "BLOCAJ")
        self.assertTrue(item.requires_online)
        self.assertIn("Component Protection", item.source_title)

    def test_missing_coding_line_without_coding_dtc_is_not_declared_not_coded(self):
        scan = scan_with("""
Address 09: Cent. Elect.
Part No SW: 5Q0 937 084
Component: BCM MQBAB
No fault code found.
""")
        analysis = analyze_replacement_coding(scan)
        self.assertEqual(analysis.findings, [])
        self.assertIn("09", analysis.modules_without_coding_line)
        self.assertIn("fără DTC explicit", analysis.summary())

    def test_basic_setting_is_separate_from_coding_fault(self):
        scan = scan_with("""
Address 44: Steering Assist
Part No SW: 5Q0 909 144
Component: EPS_MQB_ZFLS
1 Fault Found:
00778 - Steering Angle Sensor (G85)
            005 - No or Incorrect Basic Setting / Adaptation
""")
        item = analyze_replacement_coding(scan).findings[0]
        self.assertEqual(item.kind, "BASIC_SETTING")
        self.assertEqual(item.severity, "ATENȚIE")
        self.assertFalse(item.requires_online)

    def test_report_explicitly_preserves_uncertainty(self):
        scan = scan_with("""
Address 09: Cent. Elect.
Part No SW: 5Q0 937 084
Component: BCM MQBAB
No fault code found.
""")
        text = render_recovery_text(analyze_replacement_coding(scan))
        self.assertIn("nu sunt declarate automat necodate", text)


class ModuleReplacementUiV230Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import main_v2
        main_v2.prepare_database()
        main_v2.apply_v2_patches()

    def setUp(self):
        from PySide6.QtWidgets import QApplication, QMessageBox
        import ui_v2

        self.app = QApplication.instance() or QApplication([])
        QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
        QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
        QMessageBox.critical = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
        self.win = ui_v2.MainWindowV2()
        self.win.show()
        self.app.processEvents()

    def tearDown(self):
        self.win.close()
        self.app.processEvents()

    def test_v230_panel_exists_and_scan_analysis_is_visible(self):
        self.assertIn("2.3.0", self.win.windowTitle())
        panel = getattr(self.win, "kid_coding_recovery_panel", None)
        self.assertIsNotNone(panel)
        self.assertFalse(panel._kid_button.isEnabled())

        self.win.current_autoscan = scan_with("""
Address 03: ABS Brakes
Part No SW: 5Q0 614 517
Component: ESC
Coding: 0000000000000000
1 Fault Found:
01044 - Control Module Incorrectly Coded
            000 - -
""")
        analysis = self.win.refresh_module_replacement_v230()
        self.app.processEvents()
        self.assertEqual(analysis.coding_fault_count, 1)
        self.assertTrue(panel._kid_button.isEnabled())
        self.assertEqual(panel._kid_badge.text(), "CODING NECESAR")
        self.assertIn("01044", self.win.v2_verified_report_text)

    def test_component_protection_panel_is_blocking(self):
        self.win.current_autoscan = scan_with("""
Address 56: Radio
1 Fault Found:
02095 - Component Protection Active
            000 - -
""")
        self.win.refresh_module_replacement_v230()
        self.assertEqual(self.win.kid_coding_recovery_panel._kid_badge.text(), "BLOCAJ ONLINE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
