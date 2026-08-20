import tempfile
import unittest
from pathlib import Path

from pypdf import PdfReader

from parser import parse_autoscan_text
from reporting import create_diagnostic_pdf


FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "tests"
    / "fixtures"
    / "real_audi_b8_autoscan_anonymized.txt"
)


class ReportingTests(unittest.TestCase):
    def test_creates_detailed_professional_pdf(self):
        scan = parse_autoscan_text(
            FIXTURE.read_text(encoding="utf-8"), FIXTURE.name
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "raport-profesional.pdf"
            result = create_diagnostic_pdf(path, scan)
            self.assertEqual(result, path)
            self.assertTrue(path.exists())
            self.assertGreater(path.stat().st_size, 50000)
            self.assertEqual(path.read_bytes()[:4], b"%PDF")
            reader = PdfReader(path)
            self.assertGreaterEqual(len(reader.pages), 12)
            text = "\n".join(page.extract_text() or "" for page in reader.pages)

        self.assertIn("RAPORT DIAGNOSTIC", text)
        self.assertIn("VALIDARE REUȘITĂ", text)
        self.assertIn("Inventarul modulelor VCDS", text)
        self.assertIn("Ordinea recomandată a verificărilor", text)
        self.assertIn("Anexa A", text)
        self.assertIn("P261A", text)
        self.assertIn("03041", text)
        self.assertIn("Plan final de atelier", text)


if __name__ == "__main__":
    unittest.main()
