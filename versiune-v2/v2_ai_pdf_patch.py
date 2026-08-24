from __future__ import annotations

import os
import tempfile
from html import escape
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from v2_ai_copilot import audit_scan_result, build_verified_report

AI_PDF_VERSION = "2.1.0"


def _vehicle_text(owner):
    badge = getattr(owner, "vehicle_badge", None)
    if badge is not None and hasattr(badge, "text"):
        text = badge.text().strip()
        if text and "Niciun vehicul" not in text:
            return text
    return "Vehicul selectat în KID Diagnostic V2"


def _write_ai_appendix(owner, output_path):
    import v2_pdf_report as report

    report._register_fonts()
    styles = report._styles()
    result = owner.current_autoscan
    plans = list(getattr(owner, "autoscan_plans", []) or [])
    audit = getattr(result, "audit", None) or audit_scan_result(
        result, getattr(result, "extraction_warnings", [])
    )
    verified_text = build_verified_report(result, plans, _vehicle_text(owner), audit)
    owner.v2_verified_report_text = verified_text

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=17 * mm,
        title="KID Diagnostic V2 - Anexa Audit AI VCDS",
        author="KID Diagnostic",
        creator="KID Diagnostic V2 AI Copilot",
    )
    story = [
        Paragraph("Anexă AI Copilot — audit Auto-Scan VCDS", styles["h1"]),
        Paragraph(
            f"Scor citire: <b>{audit['score']}/100</b> • încredere <b>{escape(audit['confidence'])}</b> • "
            + ("<b>VERIFICAT</b>" if audit["verified"] else "<b>NECESITĂ ATENȚIE</b>"),
            styles["body"],
        ),
        Spacer(1, 2 * mm),
    ]

    story.append(Paragraph("Constatări audit", styles["h2"]))
    for item in audit.get("issues", []):
        story.append(
            Paragraph(
                f"<b>{escape(str(item.get('severity', '')).upper())}</b>: {escape(str(item.get('message', '')))}",
                styles["body"],
            )
        )

    story.append(Paragraph("Coding ORIGINAL — BEFORE", styles["h2"]))
    coded = False
    for module in getattr(result, "modules", []) or []:
        coding = str(getattr(module, "coding", "") or "").strip()
        if not coding:
            continue
        coded = True
        story.append(
            Paragraph(
                f"<b>Address {escape(str(module.address))} {escape(str(module.name))}</b><br/>"
                f"Coding ORIGINAL: {escape(coding)}",
                styles["body"],
            )
        )
    if not coded:
        story.append(
            Paragraph(
                "Coding ORIGINAL nu a fost extras din sursă; înainte de orice scriere trebuie salvată starea BEFORE.",
                styles["body"],
            )
        )

    story.append(Paragraph("Raport verificat AI", styles["h2"]))
    for line in verified_text.splitlines():
        text = line.strip()
        if not text:
            story.append(Spacer(1, 1.2 * mm))
            continue
        if text[:2].isdigit() and ". " in text[:4]:
            story.append(Paragraph(f"<b>{escape(text)}</b>", styles["h3"]))
        else:
            story.append(Paragraph(escape(text), styles["small"]))

    story.append(Paragraph("Regulă de siguranță", styles["h2"]))
    story.append(
        Paragraph(
            "AI Copilot oferă analiză și ghidaj. Nu inventează Long Coding, Security Access sau valori Adaptation "
            "și nu pretinde că a efectuat scrieri pe ECU. Pentru operații active se confirmă controllerul exact și procedura documentată.",
            styles["body"],
        )
    )
    doc.build(story, onFirstPage=report._footer, onLaterPages=report._footer)


def apply():
    import v2_pdf_fix_patch
    import v2_pdf_report

    if getattr(v2_pdf_fix_patch, "_kid_v2_ai_pdf_applied", False):
        return

    base_export = v2_pdf_report.export_pdf

    def export_with_ai(owner, output_path):
        output_path = Path(output_path)
        base_export(owner, output_path)

        fd, appendix_name = tempfile.mkstemp(prefix="kid_v2_ai_", suffix=".pdf")
        os.close(fd)
        merged_name = str(output_path) + ".merged.tmp"
        try:
            _write_ai_appendix(owner, appendix_name)
            writer = PdfWriter()
            for pdf_path in (output_path, Path(appendix_name)):
                reader = PdfReader(str(pdf_path))
                for page in reader.pages:
                    writer.add_page(page)
            with open(merged_name, "wb") as handle:
                writer.write(handle)
            os.replace(merged_name, output_path)
        finally:
            try:
                Path(appendix_name).unlink(missing_ok=True)
            except Exception:
                pass
            try:
                Path(merged_name).unlink(missing_ok=True)
            except Exception:
                pass
        return output_path

    v2_pdf_fix_patch.export_unicode_pdf = export_with_ai
    v2_pdf_fix_patch._kid_v2_ai_pdf_applied = True
