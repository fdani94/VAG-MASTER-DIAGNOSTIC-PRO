import tempfile
import unittest
from pathlib import Path

from reportlab.pdfgen import canvas

from data import default_scan, dtc_info
from parser import parse_autoscan_file, parse_autoscan_text


ROOT_FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures"
REAL_B8 = ROOT_FIXTURES / "real_audi_b8_autoscan_anonymized.txt"

SAMPLE = """
VCDS Self-Diagnosis Log
VIN: WAUZZZ8KX8A003479 License Plate: TEST
Mileage: 326200km-202691mi
Chassis Type: 8K-AU48
01-Engine -- Status: Malfunction 0010
03-ABS Brakes -- Status: OK 0000
19-CAN Gateway -- Status: Malfunction 0010
Address 01: Engine
1 Fault Found
P0401 00 - EGR Flow Insufficient
Address 19: CAN Gateway
1 Fault Found
U1121 00 - Missing Message
"""


def _write_text_pdf(path: Path, text: str) -> None:
    document = canvas.Canvas(str(path))
    document.setFont("Courier", 6.3)
    y = 812
    for line in text.splitlines():
        if y < 30:
            document.showPage()
            document.setFont("Courier", 6.3)
            y = 812
        document.drawString(22, y, line[:150])
        y -= 8
    document.save()


class AutoScanParserTests(unittest.TestCase):
    def test_extracts_vehicle_unique_modules_and_dtc(self):
        scan = parse_autoscan_text(SAMPLE, "unit-test.txt")
        self.assertEqual(scan.vehicle.vin, "WAUZZZ8KX8A003479")
        self.assertEqual(scan.vehicle.mileage_km, 326200)
        self.assertEqual(len(scan.modules), 3)
        self.assertEqual(scan.dtc_codes, ["P0401", "U1121"])
        self.assertEqual(scan.source_name, "unit-test.txt")
        self.assertTrue(scan.validation_ok, scan.validation_message)
        self.assertEqual(scan.declared_fault_count, 2)

    def test_empty_scan_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_autoscan_text("  ")

    def test_known_and_unknown_dtc(self):
        known = dtc_info("P261A")
        self.assertTrue(known.verified)
        self.assertIn("pompă", known.title.casefold())
        unknown = dtc_info("Z9999")
        self.assertEqual(unknown.code, "Z9999")
        self.assertIn("neindexat", unknown.title.casefold())

    def test_default_scan_is_empty(self):
        scan = default_scan()
        self.assertFalse(scan.modules)
        self.assertFalse(scan.faults)
        self.assertEqual(scan.total_dtc, 0)
        self.assertIn("Importați", scan.validation_message)

    def test_real_audi_b8_regression_is_14_of_14(self):
        text = REAL_B8.read_text(encoding="utf-8")
        scan = parse_autoscan_text(text, REAL_B8.name)
        self.assertEqual(len(scan.modules), 18)
        self.assertEqual(scan.declared_fault_count, 14)
        self.assertEqual(scan.parsed_fault_count, 14)
        self.assertEqual(scan.total_dtc, 14)
        self.assertTrue(scan.validation_ok, scan.validation_message)
        self.assertFalse(scan.validation_details)
        self.assertEqual(len({module.address for module in scan.modules}), 18)
        expected = {
            ("01", "P261A"),
            ("01", "P0671"),
            ("01", "P0672"),
            ("01", "P0673"),
            ("01", "P0674"),
            ("01", "P2196"),
            ("05", "00955"),
            ("19", "03041"),
            ("46", "02615"),
            ("46", "02616"),
            ("46", "01699"),
            ("52", "02115"),
            ("56", "02095"),
            ("72", "02115"),
        }
        self.assertEqual(
            {(fault.module_address, fault.display_code) for fault in scan.faults},
            expected,
        )
        self.assertEqual(scan.voltage_start, 11.6)
        self.assertEqual(scan.voltage_end, 11.6)
        glow = next(fault for fault in scan.faults if fault.display_code == "P0671")
        self.assertIn("Neconfirmat", glow.status)
        self.assertNotIn(", Confirmat", glow.status)

    def test_pdf_autoscan_roundtrip_preserves_all_faults(self):
        text = REAL_B8.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "autoscan-vcds.pdf"
            _write_text_pdf(path, text)
            scan = parse_autoscan_file(path)
        self.assertEqual(scan.source_name, "autoscan-vcds.pdf")
        self.assertEqual(scan.declared_fault_count, 14)
        self.assertEqual(scan.parsed_fault_count, 14)
        self.assertTrue(scan.validation_ok, scan.validation_message)
        self.assertEqual(len({module.address for module in scan.modules}), 18)


if __name__ == "__main__":
    unittest.main()
