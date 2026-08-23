from __future__ import annotations

import unicodedata

import v2_ai_hardening_patch as hardening

LANGUAGE_SAFETY_VERSION = "2.1.2"

# Keep this list deliberately broad for controller-changing coding language.
_EXTRA_WRITE_TERMS = (
    "CODARI",
    "CODIFICARE",
    "CODIFICARI",
)


def _fold_upper(value: object) -> str:
    """Upper-case text and remove diacritics for safety classification."""
    text = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(ch for ch in text if not unicodedata.combining(ch)).upper()


def _normalized_terms(values) -> tuple[str, ...]:
    return tuple(dict.fromkeys(_fold_upper(value) for value in values if str(value or "").strip()))


def _is_write_sensitive(question, ui_context="") -> bool:
    haystack = _fold_upper(f"{question}\n{ui_context}")
    terms = _normalized_terms(hardening.WRITE_SENSITIVE_TERMS + _EXTRA_WRITE_TERMS)
    return any(term in haystack for term in terms)


def _route_generic_question(question, ui_context):
    q = str(question or "").strip()
    folded = _fold_upper(q)

    # Romanian coding wording must be treated as coding even without page context.
    if any(term in folded for term in ("CODARI", "CODIFICARE", "CODIFICARI")):
        return (
            "Ajută-mă la Coding / Long Coding folosind numai valorile originale și documentate. "
            + q
        )

    intent_terms = _normalized_terms(hardening.INTENT_TERMS + _EXTRA_WRITE_TERMS)
    if any(term in folded for term in intent_terms):
        return q

    ctx = str(ui_context or "")
    if "Funcție activă: Coduri DTC" in ctx:
        return "Explică DTC-ul selectat și spune ce verific mai întâi. " + q
    if "Funcție activă: Codări" in ctx:
        return "Ajută-mă la Coding / Long Coding folosind numai valorile originale și documentate. " + q
    if "Funcție activă: Adaptări" in ctx:
        return "Ajută-mă la Adaptation / Basic Settings fără valori inventate. " + q
    if "Funcție activă: Service & Resetări" in ctx:
        return "Ajută-mă cu procedura de service selectată și condițiile ei. " + q
    if "Funcție activă: Date Live" in ctx:
        return "Ajută-mă să interpretez Live Data selectat. " + q
    if "Funcție activă: Auto-Scan VCDS" in ctx:
        return "Verifică Auto-Scan-ul și DTC-ul selectat. " + q
    return q


def apply():
    if getattr(hardening, "_kid_v2_language_safety_applied", False):
        return
    hardening._is_write_sensitive = _is_write_sensitive
    hardening._route_generic_question = _route_generic_question
    hardening._kid_v2_language_safety_applied = True


__all__ = [
    "LANGUAGE_SAFETY_VERSION",
    "_fold_upper",
    "_is_write_sensitive",
    "_route_generic_question",
    "apply",
]
