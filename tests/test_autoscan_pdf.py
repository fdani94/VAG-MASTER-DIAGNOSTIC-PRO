import tempfile
import unittest
from pathlib import Path

from autoscan_parser import parse_autoscan_file

FIXTURES = Path(__file__).parent / "fixtures"


def _text_to_pdf(text, out_path):
    """Create a simple text PDF preserving VCDS line structure for parser regression tests."""
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4

    c = canvas.Canvas(str(out_path), pagesize=A4)
    width, height = A4
    x = 28
    y = height - 28
    line_height = 9
    c.setFont("Courier", 7)
    for raw in text.splitlines():
        line = raw.replace("\t", "    ")
        # keep long VCDS lines readable by splitting them conservatively
        chunks = [line[i:i + 115] for i in range(0, len(line), 115)] or [""]
        for chunk in chunks:
            if y < 28:
                c.showPage()
                c.setFont("Courier", 7)
                y = height - 28
            c.drawString(x, y, chunk)
            y -= line_height
    c.save()


class AutoScanPdfRegressionTests(unittest.TestCase):
    MATRIX = [
        ("PQ24/PQ25", "representative_pq24_pq25.txt"),
        ("PQ34", "representative_kline_pq34.txt"),
        ("PQ35/PQ46", "representative_pq35_pq46.txt"),
        ("MLB", "representative_mlb.txt"),
        ("MLB Evo", "representative_mlb_evo.txt"),
        ("MQB", "representative_mqb_uds.txt"),
        ("MQB Evo", "representative_mqb_evo.txt"),
        ("MEB", "representative_meb.txt"),
        ("Audi B8 real anonymized", "real_audi_b8_autoscan_anonymized.txt"),
    ]

    def test_pdf_matrix_matches_txt_fault_count(self):
        """Every supported platform fixture must survive TXT -> PDF -> parser without losing DTCs."""
        for platform, filename in self.MATRIX:
            with self.subTest(platform=platform):
                src = FIXTURES / filename
                text = src.read_text(encoding="utf-8")
                with tempfile.TemporaryDirectory() as tmp:
                    pdf_path = Path(tmp) / (src.stem + ".pdf")
                    _text_to_pdf(text, pdf_path)
                    result = parse_autoscan_file(pdf_path)
                    self.assertTrue(result.validation_ok, f"{platform}: {result.validation_message}")
                    self.assertEqual(result.declared_fault_count, result.parsed_fault_count)

    def test_pdf_real_audi_b8_keeps_all_14_faults(self):
        src = FIXTURES / "real_audi_b8_autoscan_anonymized.txt"
        text = src.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = Path(tmp) / "real_audi_b8_autoscan_anonymized.pdf"
            _text_to_pdf(text, pdf_path)
            result = parse_autoscan_file(pdf_path)
            self.assertEqual(result.declared_fault_count, 14)
            self.assertEqual(result.parsed_fault_count, 14)
            self.assertTrue(result.validation_ok, result.validation_message)

    def test_pdf_without_extractable_text_is_rejected(self):
        # A minimal image-only-like PDF would require image generation; here we verify the public API
        # rejects a PDF whose text extraction returns nothing by creating a blank page.
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = Path(tmp) / "blank.pdf"
            c = canvas.Canvas(str(pdf_path), pagesize=A4)
            c.showPage()
            c.save()
            with self.assertRaises(ValueError):
                parse_autoscan_file(pdf_path)


if __name__ == "__main__":
    unittest.main()
