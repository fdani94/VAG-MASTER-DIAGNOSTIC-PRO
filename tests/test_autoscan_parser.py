import unittest
from pathlib import Path

from autoscan_parser import parse_autoscan_text


FIXTURES = Path(__file__).parent / "fixtures"


class AutoScanParserTests(unittest.TestCase):
    def test_kline_vag_and_pcode(self):
        text = '''VIN: WVWZZZ1JZ3W000001
Address 01: Engine
Part No: 038 906 019
Component: 1,9l R4 EDC
2 Faults Found:
16683 - Boost Pressure Regulation
            P0299 - 35-10 - Control Range Not Reached - Intermittent
17964 - Charge Pressure Control
            P1556 - 35-10 - Negative Deviation - Intermittent
'''
        r = parse_autoscan_text(text)
        self.assertEqual(r.vin, 'WVWZZZ1JZ3W000001')
        self.assertEqual(len(r.modules), 1)
        self.assertEqual(len(r.faults), 2)
        self.assertEqual(r.declared_fault_count, 2)
        self.assertTrue(r.validation_ok)
        self.assertEqual({f.vag_code for f in r.faults}, {'16683', '17964'})

    def test_can_multiple_modules_and_zero_faults(self):
        text = '''Address 01: Engine
1 Fault Found:
000665 - Boost Pressure Regulation
            P0299 - 000 - Control Range Not Reached
Address 03: ABS Brakes
No fault code found.
Address 19: CAN Gateway
1 Fault Found:
01312 - Powertrain Data Bus
            004 - No Signal/Communication - Intermittent
'''
        r = parse_autoscan_text(text)
        self.assertEqual(len(r.modules), 3)
        self.assertEqual(len(r.faults), 2)
        self.assertEqual(r.declared_fault_count, 2)
        self.assertTrue(r.validation_ok)

    def test_uds_fault_code_format(self):
        text = '''Address 09: Cent. Elect.
2 Faults Found:
Fault Code: U112100
Databus missing message
Fault Priority: 6
Fault Frequency: 2
Fault Code: B12E512
Terminal 30 open circuit
Fault Priority: 4
Fault Frequency: 1
'''
        r = parse_autoscan_text(text)
        self.assertEqual(r.declared_fault_count, 2)
        self.assertEqual(len(r.faults), 2)
        self.assertTrue(r.validation_ok)

    def test_validator_detects_missing_parse(self):
        text = '''Address 01: Engine
3 Faults Found:
16683 - Boost Pressure Regulation
            P0299 - 35-10 - Intermittent
'''
        r = parse_autoscan_text(text)
        self.assertEqual(r.declared_fault_count, 3)
        self.assertEqual(len(r.faults), 1)
        self.assertFalse(r.validation_ok)
        self.assertIn('2 erori', r.validation_message)
        self.assertTrue(r.validation_details)

    def test_static_and_intermittent_status(self):
        text = '''Address 08: Auto HVAC
2 Faults Found:
00898 - Control Circuit A/C compressor
            010 - Open or Short to Plus - Intermittent
01274 - Air Flow Flap Positioning Motor
            000 - Static
'''
        r = parse_autoscan_text(text)
        self.assertEqual(len(r.faults), 2)
        self.assertIn('Intermittent', r.faults[0].status)
        self.assertIn('Static', r.faults[1].status)
        self.assertTrue(r.validation_ok)

    def test_real_audi_b8_anonymized_regression(self):
        """Regression fixture derived from a real VCDS 25.3 Auto-Scan; personal data is removed."""
        text = (FIXTURES / 'real_audi_b8_autoscan_anonymized.txt').read_text(encoding='utf-8')
        r = parse_autoscan_text(text, 'real_audi_b8_autoscan_anonymized.txt')

        self.assertEqual(r.declared_fault_count, 14)
        self.assertEqual(r.parsed_fault_count, 14)
        self.assertEqual(len(r.faults), 14)
        self.assertTrue(r.validation_ok, r.validation_message)
        self.assertFalse(r.validation_details)

        codes = {(f.module_address, f.code or f.vag_code) for f in r.faults}
        expected = {
            ('01', 'P261A'), ('01', 'P0671'), ('01', 'P0672'), ('01', 'P0673'),
            ('01', 'P0674'), ('01', 'P2196'), ('05', '00955'), ('19', '03041'),
            ('46', '02615'), ('46', '02616'), ('46', '01699'), ('52', '02115'),
            ('56', '02095'), ('72', '02115'),
        }
        self.assertEqual(codes, expected)
        self.assertEqual(next(f for f in r.faults if f.code == 'P261A').frequency, '1')
        self.assertIn('Intermittent', next(f for f in r.faults if f.vag_code == '00955').status)


if __name__ == '__main__':
    unittest.main()
