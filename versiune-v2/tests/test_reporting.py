import tempfile
import unittest
from pathlib import Path

from data import default_scan
from reporting import create_diagnostic_pdf


class ReportingTests(unittest.TestCase):
    def test_creates_non_empty_pdf(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.pdf"
            result = create_diagnostic_pdf(path, default_scan())
            self.assertEqual(result, path)
            self.assertTrue(path.exists())
            self.assertGreater(path.stat().st_size, 1500)
            self.assertEqual(path.read_bytes()[:4], b"%PDF")


if __name__ == "__main__":
    unittest.main()
