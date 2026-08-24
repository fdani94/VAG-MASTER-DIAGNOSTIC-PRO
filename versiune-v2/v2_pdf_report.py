"""Unicode-safe PDF report for KID Diagnostic V2.

The previous Qt QTextDocument/QPdfWriter path could generate square glyphs on
some Windows/font configurations. This renderer uses ReportLab with a real
TrueType Unicode font from the host OS and produces selectable/extractable
Romanian text.
"""
from __future__ import annotations

from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image, KeepTogether, Paragraph, Preformatted, SimpleDocTemplate, Spacer,
    Table, TableStyle,
)

import appdb as db
from autoscan_correlation import render_correlation
from autoscan_ro import ro_status, ro_module, ro_title, ro_confidence, ro_vcds_note

FONT_REGULAR = "KIDUnicode"
FONT_BOLD = "KIDUnicodeBold"


def _font_candidates():
    return [
        (Path("C:/Windows/Fonts/arial.ttf"), Path("C:/Windows/Fonts/arialbd.ttf")),
        (Path("C:/Windows/Fonts/segoeui.ttf"), Path("C:/Windows/Fonts/segoeuib.ttf")),
        (Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")),
        (Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"), Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf")),
    ]


def _register_fonts():
    if FONT_REGULAR in pdfmetrics.getRegisteredFontNames() and FONT_BOLD in pdfmetrics.getRegisteredFontNames():
        return
    for regular, bold in _font_candidates():
        if regular.exists() and bold.exists():
            pdfmetrics.registerFont(TTFont(FONT_REGULAR, str(regular)))
            pdfmetrics.registerFont(TTFont(FONT_BOLD, str(bold)))
            return
    raise RuntimeError("Nu s-a găsit un font TrueType Unicode (Arial/Segoe UI/DejaVu/Liberation Sans).")


def _safe(value, default="—"):
    text = str(value or default)
    return escape(text).replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br/>")


def _vehicle_text(owner):
    parts = []
    for name in ("brand_combo", "model_combo", "gen_combo", "generation_combo", "year_combo", "engine_combo"):
        widget = getattr(owner, name, None)
        if widget is None or not hasattr(widget, "currentText"):
            continue
        text = widget.currentText().strip()
        if not text or text in parts or text.lower().startswith("alege"):
            continue
        parts.append(text)
    return " • ".join(parts) or "Vehicul selectat în KID Diagnostic"


def _logo_flowable(max_w=35 * mm, max_h=11 * mm):
    path = Path(getattr(db, "LOGO_PATH", ""))
    if not path.exists() or path.stat().st_size <= 256:
        return None
    try:
        w, h = ImageReader(str(path)).getSize()
        scale = min(max_w / float(w), max_h / float(h))
        return Image(str(path), width=w * scale, height=h * scale)
    except Exception:
        return None


def _styles():
    base = getSampleStyleSheet()
    body = ParagraphStyle(
        "KIDBody", parent=base["BodyText"], fontName=FONT_REGULAR,
        fontSize=8.8, leading=11.2, textColor=colors.HexColor("#172331"),
        spaceAfter=3.5 * mm,
    )
    small = ParagraphStyle(
        "KIDSmall", parent=body, fontSize=7.5, leading=9.2,
        textColor=colors.HexColor("#607481"), spaceAfter=2 * mm,
    )
    h1 = ParagraphStyle(
        "KIDH1", parent=body, fontName=FONT_BOLD, fontSize=17, leading=19,
        textColor=colors.HexColor("#103D59"), spaceAfter=1 * mm,
    )
    h2 = ParagraphStyle(
        "KIDH2", parent=body, fontName=FONT_BOLD, fontSize=11.5, leading=14,
        textColor=colors.HexColor("#145F88"), spaceBefore=4 * mm, spaceAfter=2.5 * mm,
    )
    h3 = ParagraphStyle(
        "KIDH3", parent=body, fontName=FONT_BOLD, fontSize=10.2, leading=12.5,
        textColor=colors.HexColor("#173F58"), spaceAfter=1.5 * mm,
    )
    label = ParagraphStyle(
        "KIDLabel", parent=body, fontName=FONT_BOLD, fontSize=8.8, leading=11.2,
        textColor=colors.HexColor("#174C6B"), spaceAfter=0,
    )
    pre = ParagraphStyle(
        "KIDPre", parent=body, fontName=FONT_REGULAR, fontSize=7.5, leading=9.4,
        leftIndent=2 * mm, rightIndent=2 * mm, spaceAfter=2 * mm,
    )
    return {"body": body, "small": small, "h1": h1, "h2": h2, "h3": h3, "label": label, "pre": pre}


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setTitle("KID Diagnostic V2 - Raport Auto-Scan VCDS")
    canvas.setCreator("KID Diagnostic")
    canvas.setAuthor("KID Diagnostic")
    canvas.setStrokeColor(colors.HexColor("#D6E4ED"))
    canvas.setLineWidth(0.5)
    canvas.line(15 * mm, 12 * mm, A4[0] - 15 * mm, 12 * mm)
    canvas.setFont(FONT_REGULAR, 7)
    canvas.setFillColor(colors.HexColor("#667D8B"))
    canvas.drawString(15 * mm, 7.8 * mm, "KID Diagnostic V2 • Raport diagnostic VAG")
    canvas.drawRightString(A4[0] - 15 * mm, 7.8 * mm, f"Pagina {doc.page}")
    canvas.restoreState()


def _field_block(label, value, styles):
    if not value:
        return []
    return [
        Paragraph(_safe(label) + ":", styles["label"]),
        Paragraph(_safe(value), styles["body"]),
    ]


def export_pdf(owner, output_path: str | Path):
    _register_fonts()
    output_path = str(output_path)
    result = owner.current_autoscan
    plans = list(owner.autoscan_plans or [])
    corr = owner.autoscan_correlation
    styles = _styles()

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=13 * mm,
        bottomMargin=17 * mm,
        title="KID Diagnostic V2 - Raport Auto-Scan VCDS",
        author="KID Diagnostic",
        creator="KID Diagnostic",
    )

    story = []
    logo = _logo_flowable()
    title_cell = [
        Paragraph("Raport Auto-Scan VCDS", styles["h1"]),
        Paragraph("KID Diagnostic • diagnostic ghidat • plan de verificare • date live", styles["small"]),
    ]
    header_data = [[logo if logo is not None else Paragraph("<b>KID</b><br/>DIAGNOSTIC", styles["h3"]), title_cell]]
    header = Table(header_data, colWidths=[37 * mm, doc.width - 37 * mm], hAlign="LEFT")
    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LINEBELOW", (0, 0), (-1, -1), 1.3, colors.HexColor("#1D88BD")),
    ]))
    story.extend([header, Spacer(1, 3 * mm)])

    vin = getattr(result, "vin", "") or "—"
    source = Path(getattr(result, "source_path", "autoscan")).name
    meta_rows = [
        [Paragraph("<b>Vehicul</b>", styles["body"]), Paragraph(_safe(_vehicle_text(owner)), styles["body"])],
        [Paragraph("<b>VIN</b>", styles["body"]), Paragraph(_safe(vin), styles["body"])],
        [Paragraph("<b>Fișier</b>", styles["body"]), Paragraph(_safe(source), styles["body"])],
        [Paragraph("<b>Module / erori</b>", styles["body"]), Paragraph(f"{len(getattr(result, 'modules', []) or [])} module • {len(plans)} erori", styles["body"])],
    ]
    meta = Table(meta_rows, colWidths=[32 * mm, doc.width - 32 * mm])
    meta.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EEF6FA")),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#ACD1E2")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D5E4EC")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.extend([meta, Spacer(1, 3 * mm)])

    secondary = len((corr or {}).get("secondary", []))
    primary = max(0, len(plans) - secondary)
    summary_text = f"REZULTAT DIAGNOSTIC: {len(plans)} erori detectate • {primary} de analizat prioritar • {secondary} probabil secundare"
    summary = Table([[Paragraph(_safe(summary_text), ParagraphStyle(
        "KIDSummary", parent=styles["body"], fontName=FONT_BOLD, fontSize=9,
        leading=11.5, textColor=colors.white, spaceAfter=0,
    ))]], colWidths=[doc.width])
    summary.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#152B3A")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.extend([summary, Spacer(1, 2 * mm)])

    if corr:
        story.append(Paragraph("Plan diagnostic automat", styles["h2"]))
        story.append(Preformatted(render_correlation(corr), styles["pre"], maxLineLength=105))

    story.append(Paragraph("Erori și proceduri recomandate", styles["h2"]))
    for fault, plan in plans:
        code = fault.code or fault.vag_code or "DTC"
        title = ro_title(plan.get("title") or fault.title)
        head = Table([[Paragraph(f"{_safe(code)} — {_safe(title)}", styles["h3"]) ]], colWidths=[doc.width])
        head.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EAF4F9")),
            ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#B9D7E6")),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.extend([Spacer(1, 1.5 * mm), head, Spacer(1, 1.5 * mm)])
        story.append(Paragraph(
            f"<b>Modul:</b> {_safe(fault.module_address)} {_safe(ro_module(fault.module_name))}<br/>"
            f"<b>Stare:</b> {_safe(ro_status(plan.get('status', '')))} &nbsp;&nbsp; "
            f"<b>Nivel:</b> {_safe(ro_confidence(plan.get('found'), plan.get('verified')))}",
            styles["body"],
        ))
        for label, value in [
            ("Ce înseamnă", plan.get("description")),
            ("Simptome posibile", plan.get("symptoms")),
            ("Cauze posibile", plan.get("causes")),
            ("Piesa / sistemul implicat", plan.get("component")),
            ("Unde se află", plan.get("location")),
            ("Ce verifici în VCDS", plan.get("parameters")),
            ("Valori / comportament așteptat", plan.get("expected")),
            ("Traseu în VCDS", plan.get("test_path")),
            ("Diagnostic pas cu pas", plan.get("diagnosis")),
            ("Cum o repari", plan.get("repair")),
            ("După înlocuirea piesei", plan.get("replacement")),
            ("Freeze Frame / date din raport", plan.get("freeze_frame")),
        ]:
            story.extend(_field_block(label, value, styles))

    story.append(Paragraph("Notă tehnică", styles["h2"]))
    note = Table([[Paragraph(_safe(ro_vcds_note()), styles["body"]) ]], colWidths=[doc.width])
    note.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF8E8")),
        ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#EAD39A")),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.extend([
        note,
        Spacer(1, 2 * mm),
        Paragraph(
            "Raport generat de KID Diagnostic din Auto-Scan-ul încărcat și baza locală. "
            "Confirmați procedura pentru platforma și controllerul exact înainte de Coding, Adaptation sau Basic Settings.",
            styles["small"],
        ),
    ])

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return Path(output_path)
