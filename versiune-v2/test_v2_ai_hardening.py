from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
V2 = Path(__file__).resolve().parent
for path in (ROOT, V2):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import main_v2

# Install the same patch stack used by the packaged application.
main_v2.apply_v2_patches()

from v2_ai_copilot import V2AICopilot
from v2_ai_hardening_patch import HARDENING_VERSION
from v2_ai_language_safety_patch import _fold_upper


class V2AiHardeningTests(unittest.TestCase):
    def test_version_is_212(self):
        self.assertEqual(HARDENING_VERSION, "2.1.2")

    def test_external_model_is_never_used_for_write_sensitive_guidance(self):
        env = {
            "KID_V2_AI_BASE_URL": "https://example.com/v1",
            "KID_V2_AI_MODEL": "test-model",
        }
        with patch.dict(os.environ, env, clear=False):
            copilot = V2AICopilot()
            self.assertTrue(copilot.external_model_ready)
            with patch.object(
                copilot,
                "_external_answer",
                side_effect=AssertionError("external model must not be called for coding"),
            ):
                answer = copilot.ask(
                    "Ce Long Coding pun?",
                    ui_context="Funcție activă: Codări\nProcedură selectată: Address 09",
                )
        self.assertIn("Coding - 07 / Long Coding", answer)
        self.assertIn("Nu dau o valoare exactă", answer)
        self.assertNotIn("AI extern", answer)

    def test_romanian_coding_words_cannot_bypass_external_ai_guard(self):
        env = {
            "KID_V2_AI_BASE_URL": "https://example.com/v1",
            "KID_V2_AI_MODEL": "test-model",
        }
        variants = (
            "Ce înseamnă codări?",
            "Ce inseamna codari?",
            "Ajută-mă cu codificări la modulul 09",
            "Ajuta-ma cu codificare la modulul 09",
        )
        with patch.dict(os.environ, env, clear=False):
            for question in variants:
                with self.subTest(question=question):
                    copilot = V2AICopilot()
                    with patch.object(
                        copilot,
                        "_external_answer",
                        side_effect=AssertionError("Romanian coding wording reached external AI"),
                    ):
                        answer = copilot.ask(question)
                    self.assertIn("Coding - 07 / Long Coding", answer)
                    self.assertNotIn("AI extern", answer)

    def test_diacritic_normalizer_is_stable(self):
        self.assertEqual(_fold_upper("Codări și funcții"), "CODARI SI FUNCTII")
        self.assertEqual(_fold_upper("adaptări"), "ADAPTARI")

    def test_external_read_only_answer_is_supplemental_not_replacement(self):
        env = {
            "KID_V2_AI_BASE_URL": "https://example.com/v1",
            "KID_V2_AI_MODEL": "test-model",
        }
        with patch.dict(os.environ, env, clear=False):
            copilot = V2AICopilot()
            with patch.object(copilot, "_external_answer", return_value="EXPLICAȚIE EXTERNĂ"):
                answer = copilot.ask("Ce poți face?")
        self.assertIn("Pot verifica Auto-Scan-ul", answer)
        self.assertIn("AI extern", answer)
        self.assertIn("EXPLICAȚIE EXTERNĂ", answer)

    def test_generic_question_uses_active_coding_context(self):
        answer = V2AICopilot().ask(
            "Ce fac aici?",
            ui_context=(
                "Funcție activă: Codări\n"
                "Vehicul V2: Volkswagen Golf VII\n"
                "Procedură selectată: Categorie: Coding | Modul: 09"
            ),
        )
        self.assertIn("Coding - 07 / Long Coding", answer)
        self.assertIn("Context selectat în KID Diagnostic V2", answer)
        self.assertIn("Modul: 09", answer)


if __name__ == "__main__":
    unittest.main(verbosity=2)
