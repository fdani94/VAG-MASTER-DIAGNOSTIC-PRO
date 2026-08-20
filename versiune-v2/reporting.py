from __future__ import annotations

from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from data import ScanResult, dtc_info

NAVY = colors.HexColor("#09131d")
PANEL = colors.HexColor("#102233")
CYAN = colors.HexColor("#20b7f6")
MUTED = colors.HexColor("#6f8599")
LIGHT = colors.HexColor("#edf6fc")
AMBER = colors.HexColor("#f3a936")
GREEN = colors.HexColor("#29b879")
GRID = colors.HexColor("#d3e0e9")


def _register_font() -> tuple[str, str]:
    candidates = (
        ("C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/segoeuib.ttf"),
        ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ("/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
    )
    for regular_path, bold_path in candidates:
        if Path(regular_path).exists() and Path(bold_path).exists():
            try:
                pdfmetrics.registerFont(TTFont("V2Regular", regular_path))
                pdfmetrics.registerFont(TTFont("V2Bold", bold_path))
                return "V2Regular", "V2Bold"
            except Exception:  # noqa: BLE001, S112 - try the next installed font.
                continue
    return "Helvetica", "Helvetica-Bold"


def _footer(canvas, document, regular_font: str) -> None:
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#d9e5ed"))
    canvas.line(18 * mm, 15 * mm, 192 * mm, 15 * mm)
    canvas.setFont(regular_font, 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 10 * mm, "KID VAG MASTER — Diagnostic PRO V2")
    canvas.drawRightString(192 * mm, 10 * mm, f"Pagina {document.page}")
    canvas.restoreState()


def create_diagnostic_pdf(path: str | Path, scan: ScanResult) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    regular_font, bold_font = _register_font()

    document = SimpleDocTemplate(
        str(destination),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=17 * mm,
        bottomMargin=21 * mm,
        title=f"Raport diagnostic {scan.vehicle.vin}",
        author="KID VAG MASTER Diagnostic PRO V2",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "V2Title",
        parent=styles["Title"],
        fontName=bold_font,
        fontSize=22,
        leading=26,
        textColor=NAVY,
        alignment=TA_LEFT,
        spaceAfter=4 * mm,
    )
    subtitle_style = ParagraphStyle(
        "V2Subtitle",
        parent=styles["Normal"],
        fontName=regular_font,
        fontSize=9,
        leading=12,
        textColor=MUTED,
        spaceAfter=6 * mm,
    )
    heading_style = ParagraphStyle(
        "V2Heading",
        parent=styles["Heading2"],
        fontName=bold_font,
        fontSize=14,
        leading=18,
        textColor=PANEL,
        spaceBefore=5 * mm,
        spaceAfter=3 * mm,
    )
    body_style = ParagraphStyle(
        "V2Body",
        parent=styles["BodyText"],
        fontName=regular_font,
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#273746"),
        spaceAfter=2 * mm,
    )
    small_style = ParagraphStyle(
        "V2Small",
        parent=body_style,
        fontSize=8,
        leading=11,
    )
    white_bold = ParagraphStyle(
        "V2WhiteBold",
        parent=body_style,
        fontName=bold_font,
        textColor=LIGHT,
        alignment=TA_CENTER,
    )

    story: list = []
    story.append(Paragraph("RAPORT DIAGNOSTIC PROFESIONAL", title_style))
    story.append(
        Paragraph(
            f"Generat la {datetime.now().astimezone().strftime('%d.%m.%Y %H:%M')} • Sursă: {scan.source_name}",
            subtitle_style,
        )
    )

    vehicle = scan.vehicle
    vehicle_data = [
        [Paragraph("VEHICUL", white_bold), "", Paragraph("REZULTAT SCANARE", white_bold), ""],
        ["Marcă / model", vehicle.display_name, "Module detectate", str(len(scan.modules))],
        ["An / motor", vehicle.subtitle if vehicle.year else vehicle.engine, "Module cu erori", str(scan.fault_modules)],
        ["VIN", vehicle.vin, "DTC identificate", str(scan.total_dtc)],
        ["Kilometraj", f"{vehicle.mileage_km:,} km".replace(",", ".") if vehicle.mileage_km else "Nedetectat", "Stare raport", "Finalizat"],
    ]
    vehicle_table = Table(vehicle_data, colWidths=[31 * mm, 55 * mm, 34 * mm, 54 * mm])
    vehicle_table.setStyle(
        TableStyle(
            [
                ("SPAN", (0, 0), (1, 0)),
                ("SPAN", (2, 0), (3, 0)),
                ("BACKGROUND", (0, 0), (1, 0), PANEL),
                ("BACKGROUND", (2, 0), (3, 0), colors.HexColor("#0a668f")),
                ("FONTNAME", (0, 1), (-1, -1), regular_font),
                ("FONTNAME", (0, 1), (0, -1), bold_font),
                ("FONTNAME", (2, 1), (2, -1), bold_font),
                ("FONTSIZE", (0, 1), (-1, -1), 8.5),
                ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#263746")),
                ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                ("GRID", (0, 1), (-1, -1), 0.35, GRID),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.append(vehicle_table)

    story.append(Paragraph("Module scanate", heading_style))
    module_data = [["Adresă", "Modul", "Stare", "DTC"]]
    for module in scan.modules:
        module_data.append([module.address, module.name, module.status, str(module.dtc_count)])
    if not scan.modules:
        module_data.append(["—", "Nu au fost detectate module", "—", "0"])
    module_table = Table(module_data, colWidths=[20 * mm, 92 * mm, 42 * mm, 20 * mm], repeatRows=1)
    module_style = [
        ("BACKGROUND", (0, 0), (-1, 0), PANEL),
        ("TEXTCOLOR", (0, 0), (-1, 0), LIGHT),
        ("FONTNAME", (0, 0), (-1, 0), bold_font),
        ("FONTNAME", (0, 1), (-1, -1), regular_font),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.35, GRID),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f7fa")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]
    for row, module in enumerate(scan.modules, start=1):
        if module.dtc_count:
            module_style.extend(
                [
                    ("TEXTCOLOR", (2, row), (3, row), AMBER),
                    ("FONTNAME", (2, row), (3, row), bold_font),
                ]
            )
        elif module.status.upper() == "OK":
            module_style.extend(
                [
                    ("TEXTCOLOR", (2, row), (3, row), GREEN),
                    ("FONTNAME", (2, row), (2, row), bold_font),
                ]
            )
    module_table.setStyle(TableStyle(module_style))
    story.append(module_table)

    story.append(Paragraph("Erori și recomandări", heading_style))
    codes = scan.dtc_codes or []
    if not codes:
        story.append(
            Table(
                [[Paragraph("Nu au fost identificate coduri DTC în fișierul importat.", body_style)]],
                colWidths=[174 * mm],
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#e8f7f0")),
                        ("BOX", (0, 0), (-1, -1), 0.8, GREEN),
                        ("LEFTPADDING", (0, 0), (-1, -1), 10),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                        ("TOPPADDING", (0, 0), (-1, -1), 10),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                    ]
                ),
            )
        )
    for index, code in enumerate(codes):
        info = dtc_info(code)
        block: list = [
            Table(
                [[Paragraph(info.code, ParagraphStyle("Code", parent=body_style, fontName=bold_font, fontSize=17, textColor=AMBER)), Paragraph(f"<b>{info.title}</b><br/>{info.system} • Severitate: {info.severity}", body_style)]],
                colWidths=[28 * mm, 146 * mm],
                style=TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f9fbfd")),
                        ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#c9d9e4")),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                        ("TOPPADDING", (0, 0), (-1, -1), 8),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ]
                ),
            ),
            Spacer(1, 2 * mm),
            Paragraph(info.summary, body_style),
            Paragraph("<b>Cauze posibile</b>", body_style),
            Paragraph("<br/>".join(f"• {line}" for line in info.causes), small_style),
            Paragraph("<b>Verificări recomandate</b>", body_style),
            Paragraph("<br/>".join(f"• {line}" for line in info.checks), small_style),
            Paragraph("<b>Direcție de reparație</b>", body_style),
            Paragraph("<br/>".join(f"• {line}" for line in info.repairs), small_style),
            Paragraph(f"<b>Localizare orientativă:</b> {info.location}", small_style),
            Spacer(1, 4 * mm),
        ]
        story.append(KeepTogether(block))
        if index and index % 2 == 0 and index != len(codes) - 1:
            story.append(PageBreak())

    story.append(Spacer(1, 4 * mm))
    disclaimer = Table(
        [[Paragraph("IMPORTANT", ParagraphStyle("Important", parent=body_style, fontName=bold_font, textColor=AMBER)), Paragraph("Raportul asistă diagnosticul și nu înlocuiește măsurătorile, documentația tehnică aferentă codului motor sau confirmarea mecanică. Nu înlocuiți componente doar pe baza unui DTC.", small_style)]],
        colWidths=[27 * mm, 147 * mm],
        style=TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fff7e8")),
                ("BOX", (0, 0), (-1, -1), 0.8, AMBER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        ),
    )
    story.append(disclaimer)

    document.build(
        story,
        onFirstPage=lambda canvas, doc: _footer(canvas, doc, regular_font),
        onLaterPages=lambda canvas, doc: _footer(canvas, doc, regular_font),
    )
    return destination
