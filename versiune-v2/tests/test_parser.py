import unittest

from data import default_scan, dtc_info
from parser import parse_autoscan_text

SAMPLE = """
VCDS Self-Diagnosis Log
VIN: WAUZZZ8KX8A003479 License Plate: TEST
Mileage: 326200km-202691mi
Chassis Type: 8K-AU48
01-Engine -- Status: Malfunction 0010
03-ABS Brakes -- Status: OK 0000
19-CAN Gateway -- Status: Malfunction 0010
Address 01: Engine
P0401 00 - EGR Flow Insufficient
Address 19: CAN Gateway
U1121 00 - Missing Message
"""


class AutoScanParserTests(unittest.TestCase):
    def test_extracts_vehicle_modules_and_dtc(self):
        scan = parse_autoscan_text(SAMPLE, "unit-test.txt")
        self.assertEqual(scan.vehicle.vin, "WAUZZZ8KX8A003479")
        self.assertEqual(scan.vehicle.mileage_km, 326200)
        self.assertEqual(len(scan.modules), 3)
        self.assertEqual(scan.dtc_codes, ["P0401", "U1121"])
        self.assertEqual(scan.source_name, "unit-test.txt")

    def test_empty_scan_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_autoscan_text("  ")

    def test_known_and_unknown_dtc(self):
        self.assertIn("EGR", dtc_info("p0401").title)
        unknown = dtc_info("P1234")
        self.assertEqual(unknown.code, "P1234")
        self.assertIn("nerecunoscut", unknown.title.lower())

    def test_default_scan_is_ready_for_demo(self):
        scan = default_scan()
        self.assertGreater(len(scan.modules), 8)
        self.assertIn("P0401", scan.dtc_codes)


if __name__ == "__main__":
    unittest.main()
