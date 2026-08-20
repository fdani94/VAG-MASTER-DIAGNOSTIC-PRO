import unittest
from pathlib import Path

from analysis_engine import analyze_scan
from parser import parse_autoscan_text


FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "tests"
    / "fixtures"
    / "real_audi_b8_autoscan_anonymized.txt"
)


class AnalysisTests(unittest.TestCase):
    def test_correlates_real_scan_without_declaring_parts_defective(self):
        scan = parse_autoscan_text(
            FIXTURE.read_text(encoding="utf-8"), FIXTURE.name
        )
        analysis = analyze_scan(scan)
        titles = {finding.title for finding in analysis.common_findings}
        self.assertIn("Alimentare și stare baterie", titles)
        self.assertIn(
            "Defecțiuni grupate în sistemul de preîncălzire", titles
        )
        self.assertIn("Blocare și deblocare clapetă rezervor", titles)
        self.assertEqual(len(analysis.prioritized), 14)
        self.assertEqual(analysis.prioritized[0].fault.display_code, "P261A")
        self.assertIn("Prioritate", analysis.prioritized[0].level)


if __name__ == "__main__":
    unittest.main()
