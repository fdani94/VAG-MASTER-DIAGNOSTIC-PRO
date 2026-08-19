import unittest
from autoscan_parser import parse_autoscan_text


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
        self.assertEqual(r.declared_faults, 2)
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
        self.assertEqual(r.declared_faults, 2)
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
        self.assertEqual(r.declared_faults, 2)
        self.assertEqual(len(r.faults), 2)
        self.assertTrue(r.validation_ok)

    def test_validator_detects_missing_parse(self):
        text = '''Address 01: Engine
3 Faults Found:
16683 - Boost Pressure Regulation
            P0299 - 35-10 - Intermittent
'''
        r = parse_autoscan_text(text)
        self.assertEqual(r.declared_faults, 3)
        self.assertEqual(len(r.faults), 1)
        self.assertFalse(r.validation_ok)
        self.assertEqual(r.validation_missing, 2)
        self.assertTrue(r.validation_issues)

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


if __name__ == '__main__':
    unittest.main()
