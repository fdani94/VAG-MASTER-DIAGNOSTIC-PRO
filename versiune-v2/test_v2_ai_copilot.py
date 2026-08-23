from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
V2_DIR = Path(__file__).resolve().parent
for path in (ROOT, V2_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from v2_ai_copilot import (
    V2AICopilot,
    VCDS_FUNCTIONS,
    audit_scan_result,
    build_verified_report,
    parse_autoscan_file_audited,
)

UDS_SAMPLE = """VCDS -- Windows Based VAG/VAS Emulator
VCDS Version: 25.3.1.0
Data version: 20260301 DS365.0
VIN: WVWZZZ3CZME000001   License Plate:
Mileage: 180000km
Chassis Type: 3C

-------------------------------------------------------------------------------
Address 01: Engine (J623)       Labels: None
   Part No SW: 04L 906 056 AB    HW: 04L 907 445
   Component: R4 2.0l TDI   H25 9978
   Coding: 0119001203241D082000
   ASAM Dataset: EV_ECM20TDI03004L906056AB 004006
   ROD: EV_ECM20TDI03004L906056AB.rod
1 Fault Found:
5188 - Diesel Particle Filter
          P2463 00 [175] - Excessive Soot Accumulation - MIL ON
             Freeze Frame:
                    Fault Status: 00000001
                    Fault Priority: 2
                    Fault Frequency: 1
                    Mileage: 180000 km
Readiness: 0 0 0 0 1
"""

MISMATCH_SAMPLE = UDS_SAMPLE.replace("1 Fault Found:", "2 Faults Found:")


def parse_text(text):
    handle = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8")
    try:
        handle.write(text)
        handle.close()
        return parse_autoscan_file_audited(handle.name)
    finally:
        try:
            os.unlink(handle.name)
        except OSError:
            pass


class V2AiCopilotTests(unittest.TestCase):
    def test_modern_uds_dtc_status_byte_and_four_digit_vag_code(self):
        scan = parse_text(UDS_SAMPLE)
        self.assertEqual(len(scan.faults), 1)
        fault = scan.faults[0]
        self.assertEqual(fault.code, "P2463")
        self.assertEqual(fault.vag_code, "5188")
        self.assertEqual(fault.uds_status_byte, "00")
        self.assertEqual(fault.uds_bracket, "175")
        self.assertIn("Mil On", fault.status)
        self.assertTrue(scan.validation_ok)

    def test_module_identification_and_original_coding_are_preserved(self):
        scan = parse_text(UDS_SAMPLE)
        module = scan.modules[0]
        self.assertEqual(module.address, "01")
        self.assertEqual(module.part_no_sw, "04L 906 056 AB")
        self.assertEqual(module.part_no_hw, "04L 907 445")
        self.assertIn("EV_ECM20TDI", module.asam_dataset)
        self.assertEqual(module.coding, "0119001203241D082000")
        report = build_verified_report(scan, selected_vehicle="VW Passat")
        self.assertIn("Coding ORIGINAL: 0119001203241D082000", report)
        self.assertIn("SNAPSHOT CODING — BEFORE", report)

    def test_consistent_scan_receives_high_audit_score(self):
        scan = parse_text(UDS_SAMPLE)
        audit = scan.audit
        self.assertGreaterEqual(audit["score"], 90)
        self.assertTrue(audit["verified"])
        self.assertEqual(audit["faultCount"], 1)

    def test_declared_fault_mismatch_is_detected(self):
        scan = parse_text(MISMATCH_SAMPLE)
        audit = scan.audit
        self.assertFalse(scan.validation_ok)
        self.assertFalse(audit["verified"])
        self.assertTrue(any(item["severity"] == "error" for item in audit["issues"]))

    def test_pdf_extraction_warning_persists_in_audit_and_report(self):
        scan = parse_text(UDS_SAMPLE)
        warning = "Pagina 2 nu conține text extractibil."
        scan.extraction_warnings = [warning]
        audit = audit_scan_result(scan, scan.extraction_warnings)
        report = build_verified_report(scan, audit=audit)
        self.assertFalse(audit["verified"])
        self.assertIn(warning, report)

    def test_rebuild_report_intent_rebuilds_not_only_audits(self):
        scan = parse_text(UDS_SAMPLE)
        answer = V2AICopilot().ask("Refă raportul automat și verifică-l", scan=scan)
        self.assertIn("Am refăcut raportul", answer)
        self.assertIn("RAPORT VCDS VERIFICAT AI", answer)
        self.assertIn("Coding ORIGINAL", answer)

    def test_security_access_intent_has_priority_over_generic_coding(self):
        scan = parse_text(UDS_SAMPLE)
        answer = V2AICopilot().ask("Security Access pentru coding Address 01", scan=scan)
        self.assertIn("Security Access - 16", answer)
        self.assertIn("Nu inventez", answer)
        self.assertIn("Address 01", answer)

    def test_coding_help_does_not_invent_exact_value(self):
        scan = parse_text(UDS_SAMPLE)
        answer = V2AICopilot().ask("Ce Long Coding pun pentru activare?", scan=scan)
        self.assertIn("Coding ORIGINAL", answer)
        self.assertIn("Nu dau o valoare exactă", answer)

    def test_remote_plain_http_ai_is_rejected(self):
        env = {
            "KID_V2_AI_BASE_URL": "http://example.com/v1",
            "KID_V2_AI_MODEL": "test",
            "KID_V2_AI_API_KEY": "secret",
        }
        with patch.dict(os.environ, env, clear=False):
            self.assertFalse(V2AICopilot().external_model_ready)

    def test_https_and_localhost_http_ai_are_allowed(self):
        with patch.dict(
            os.environ,
            {"KID_V2_AI_BASE_URL": "https://example.com/v1", "KID_V2_AI_MODEL": "test"},
            clear=False,
        ):
            self.assertTrue(V2AICopilot().external_model_ready)
        with patch.dict(
            os.environ,
            {"KID_V2_AI_BASE_URL": "http://127.0.0.1:11434/v1", "KID_V2_AI_MODEL": "local"},
            clear=False,
        ):
            self.assertTrue(V2AICopilot().external_model_ready)

    def test_official_vcds_function_names_are_exposed(self):
        self.assertEqual(VCDS_FUNCTIONS["coding"]["name"], "Coding - 07 / Long Coding")
        self.assertEqual(VCDS_FUNCTIONS["adaptation"]["name"], "Adaptation - 10")
        self.assertIn("Security Access - 16", VCDS_FUNCTIONS["security_access"]["name"])
        self.assertIn("Basic Settings - 04", VCDS_FUNCTIONS["basic_settings"]["name"])
        self.assertIn("Output Tests - 03", VCDS_FUNCTIONS["output_tests"]["name"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
