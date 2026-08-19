import unittest
from pathlib import Path

from autoscan_parser import parse_autoscan_text


FIXTURES = Path(__file__).parent / "fixtures"


class AutoScanPlatformMatrixTests(unittest.TestCase):
    def test_platform_matrix(self):
        cases = {
            "PQ24/PQ25": ("representative_pq24_pq25.txt", 3, {"01", "03", "09", "17"}),
            "PQ34": ("representative_kline_pq34.txt", 4, {"01", "03", "17", "46"}),
            "PQ35/PQ46": ("representative_pq35_pq46.txt", 4, {"01", "03", "09", "19", "53"}),
            "MLB": ("representative_mlb.txt", 3, {"01", "05", "19", "46"}),
            "MLB Evo": ("representative_mlb_evo.txt", 3, {"01", "03", "19", "5F"}),
            "MQB": ("representative_mqb_uds.txt", 4, {"01", "03", "09", "19"}),
            "MQB Evo": ("representative_mqb_evo.txt", 3, {"01", "03", "09", "19"}),
            "MEB": ("representative_meb.txt", 3, {"01", "03", "19", "51", "5F"}),
        }
        for platform, (filename, expected_faults, expected_modules) in cases.items():
            with self.subTest(platform=platform):
                text = (FIXTURES / filename).read_text(encoding="utf-8")
                result = parse_autoscan_text(text, filename)
                self.assertEqual(result.declared_fault_count, expected_faults)
                self.assertEqual(result.parsed_fault_count, expected_faults)
                self.assertTrue(result.validation_ok, result.validation_message)
                self.assertEqual({m.address for m in result.modules}, expected_modules)


if __name__ == "__main__":
    unittest.main()
