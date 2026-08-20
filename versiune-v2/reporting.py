from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    CondPageBreak,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from analysis_engine import PrioritizedFault, ScanAnalysis, analyze_scan
from data import ScanFault, ScanResult
from localization import romanianize


NAVY = colors.HexColor("#07131E")
PANEL = colors.HexColor("#10283A")
BLUE = colors.HexColor("#087CAD")
CYAN = colors.HexColor("#18AEEA")
MUTED = colors.HexColor("#627A8D")
TEXT = colors.HexColor("#213441")
LIGHT = colors.HexColor("#EDF6FC")
PALE = colors.HexColor("#F3F8FB")
AMBER = colors.HexColor("#E9981D")
AMBER_PALE = colors.HexColor("#FFF6E5")
GREEN = colors.HexColor("#168E5D")
GREEN_PALE = colors.HexColor("#EAF8F1")
RED = colors.HexColor("#C74444")
RED_PALE = colors.HexColor("#FDEEEE")
GRID = colors.HexColor("#CEDDE7")


def _register_font() -> tuple[str, str, str]:
    candidates = (
        (
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/segoeuib.ttf",
            "C:/Windows/Fonts/consola.ttf",
        ),
        (
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        ),
        (
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/System/Library/Fonts/Supplemental/Courier New.ttf",
        ),
    )
    for regular_path, bold_path, mono_path in candidates:
        if not Path(regular_path).exists() or not Path(bold_path).exists():
            continue
        try:
            pdfmetrics.registerFont(TTFont("KIDRegular", regular_path))
            pdfmetrics.registerFont(TTFont("KIDBold", bold_path))
            mono = "Courier"
            if Path(mono_path).exists():
                pdfmetrics.registerFont(TTFont("KIDMono", mono_path))
                mono = "KIDMono"
            return "KIDRegular", "KIDBold", mono
        except Exception:  # noqa: BLE001 - încercăm următorul font disponibil.
            continue
    return "Helvetica", "Helvetica-Bold", "Courier"


def _styles(regular: str, bold: str, mono: str) -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "KIDTitle",
            parent=base["Title"],
            fontName=bold,
            fontSize=24,
            leading=28,
            textColor=NAVY,
            alignment=TA_LEFT,
            spaceAfter=2 * mm,
        ),
        "subtitle": ParagraphStyle(
            "KIDSubtitle",
            parent=base["Normal"],
            fontName=regular,
            fontSize=9,
            leading=13,
            textColor=MUTED,
            spaceAfter=4 * mm,
        ),
        "h1": ParagraphStyle(
            "KIDH1",
            parent=base["Heading1"],
            fontName=bold,
            fontSize=16,
            leading=20,
            textColor=PANEL,
            spaceBefore=4 * mm,
            spaceAfter=3 * mm,
            keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "KIDH2",
            parent=base["Heading2"],
            fontName=bold,
            fontSize=11.5,
            leading=15,
            textColor=BLUE,
            spaceBefore=3 * mm,
            spaceAfter=1.5 * mm,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "KIDBody",
            parent=base["BodyText"],
            fontName=regular,
            fontSize=8.6,
            leading=12.2,
            textColor=TEXT,
            spaceAfter=1.5 * mm,
        ),
        "small": ParagraphStyle(
            "KIDSmall",
            parent=base["BodyText"],
            fontName=regular,
            fontSize=7.4,
            leading=10,
            textColor=TEXT,
        ),
        "tiny": ParagraphStyle(
            "KIDTiny",
            parent=base["BodyText"],
            fontName=regular,
            fontSize=6.5,
            leading=8.3,
            textColor=TEXT,
        ),
        "mono": ParagraphStyle(
            "KIDMonoText",
            parent=base["BodyText"],
            fontName=mono,
            fontSize=6.5,
            leading=8.2,
            textColor=colors.HexColor("#304655"),
            wordWrap="CJK",
        ),
        "white": ParagraphStyle(
            "KIDWhite",
            parent=base["BodyText"],
            fontName=bold,
            fontSize=8.4,
            leading=11,
            textColor=colors.white,
        ),
        "white_center": ParagraphStyle(
            "KIDWhiteCenter",
            parent=base["BodyText"],
            fontName=bold,
            fontSize=8.4,
            leading=11,
            textColor=colors.white,
            alignment=TA_CENTER,
        ),
        "metric": ParagraphStyle(
            "KIDMetric",
            parent=base["BodyText"],
            fontName=bold,
            fontSize=17,
            leading=20,
            textColor=BLUE,
            alignment=TA_CENTER,
        ),
    }


def _safe(value: object, fallback: str = "-") -> str:
    text = str(value).strip() if value not in (None, "") else fallback
    return escape(text).replace("\n", "<br/>")


def _p(value: object, style: ParagraphStyle, fallback: str = "-") -> Paragraph:
    return Paragraph(_safe(value, fallback), style)


def _label_value(label: str, value: object, style: ParagraphStyle) -> Paragraph:
    return Paragraph(f"<b>{escape(label)}:</b> {_safe(value)}", style)


def _bullet_paragraphs(
    values: tuple[str, ...] | list[str], style: ParagraphStyle
) -> list[Paragraph]:
    rows = [
        re.sub(r"^\s*\d+[.)]\s*", "", str(value)).strip()
        for value in values
        if str(value).strip()
    ] or ["Nu există informații suplimentare în fișa locală."]
    return [
        Paragraph(f"<b>{index}.</b> {_safe(value)}", style)
        for index, value in enumerate(rows, 1)
    ]


def _section_title(text: str, styles: dict[str, ParagraphStyle]) -> Paragraph:
    return Paragraph(escape(text), styles["h2"])


def _page_decoration(report_id: str, regular: str, bold: str):
    def draw(canvas, document) -> None:
        canvas.saveState()
        width, height = A4
        if document.page > 1:
            canvas.setFillColor(NAVY)
            canvas.rect(0, height - 14 * mm, width, 14 * mm, fill=1, stroke=0)
            canvas.setFont(bold, 7.5)
            canvas.setFillColor(colors.white)
            canvas.drawString(
                18 * mm, height - 9 * mm, "KID VAG MASTER - RAPORT DIAGNOSTIC"
            )
            canvas.setFont(regular, 7.2)
            canvas.drawRightString(192 * mm, height - 9 * mm, report_id)
        canvas.setStrokeColor(GRID)
        canvas.line(18 * mm, 14.5 * mm, 192 * mm, 14.5 * mm)
        canvas.setFont(regular, 7.2)
        canvas.setFillColor(MUTED)
        canvas.drawString(
            18 * mm, 9.5 * mm, "KID VAG MASTER - Diagnostic PRO V2"
        )
        canvas.drawCentredString(105 * mm, 9.5 * mm, report_id)
        canvas.drawRightString(192 * mm, 9.5 * mm, f"Pagina {document.page}")
        canvas.restoreState()

    return draw


def _base_table_style(
    regular: str, bold: str, header: bool = True
) -> TableStyle:
    rules: list[tuple] = [
        ("FONTNAME", (0, 0), (-1, -1), regular),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("TEXTCOLOR", (0, 0), (-1, -1), TEXT),
        ("GRID", (0, 0), (-1, -1), 0.35, GRID),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        (
            "ROWBACKGROUNDS",
            (0, 1 if header else 0),
            (-1, -1),
            [colors.white, PALE],
        ),
    ]
    if header:
        rules.extend(
            [
                ("BACKGROUND", (0, 0), (-1, 0), PANEL),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), bold),
                ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
            ]
        )
    return TableStyle(rules)


def _freeze_frame_rows(fault: ScanFault) -> list[tuple[str, str]]:
    translations = {
        "fault priority": "Prioritate eroare",
        "fault frequency": "Frecvență eroare",
        "reset counter": "Contor resetări",
        "mileage": "Kilometraj",
        "date": "Dată",
        "time": "Oră",
        "engine speed": "Turație motor",
        "vehicle speed": "Viteză vehicul",
        "voltage terminal 30": "Tensiune Terminal 30",
        "coolant temperature": "Temperatură lichid de răcire",
    }
    result: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for line in (fault.freeze_frame or "").splitlines():
        match = re.match(r"\s*([^:]{2,100}):\s*(.+?)\s*$", line)
        if not match:
            continue
        original, value = match.group(1).strip(), match.group(2).strip()
        if original.casefold() == "freeze frame":
            continue
        label = translations.get(original.casefold(), romanianize(original))
        value = romanianize(value)
        key = (label.casefold(), value)
        if key not in seen:
            seen.add(key)
            result.append((label, value))
    return result


def _validation_box(
    scan: ScanResult, styles: dict[str, ParagraphStyle], regular: str
) -> Table:
    if scan.validation_ok is True:
        background, border, marker = GREEN_PALE, GREEN, "VALIDARE REUȘITĂ"
    elif scan.validation_ok is False:
        background, border, marker = RED_PALE, RED, "VERIFICARE NECESARĂ"
    else:
        background, border, marker = AMBER_PALE, AMBER, "VALIDARE PARȚIALĂ"
    content = Paragraph(
        f"<b>{marker}</b><br/>{_safe(scan.validation_message)}",
        styles["body"],
    )
    table = Table([[content]], colWidths=[174 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), background),
                ("BOX", (0, 0), (-1, -1), 0.8, border),
                ("FONTNAME", (0, 0), (-1, -1), regular),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return table


def _fault_header(
    index: int,
    total: int,
    item: PrioritizedFault,
    styles: dict[str, ParagraphStyle],
) -> Table:
    fault, info = item.fault, item.info
    left = Paragraph(
        f"<font size='17'><b>{_safe(fault.display_code)}</b></font><br/>"
        f"<font size='7'>FIȘA {index} DIN {total}</font>",
        styles["white_center"],
    )
    right = Paragraph(
        f"<b>{_safe(info.title)}</b><br/>"
        f"{_safe(fault.module_address)} - {_safe(fault.module_name)} | {_safe(item.level)}",
        styles["white"],
    )
    table = Table([[left, right]], colWidths=[34 * mm, 140 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), AMBER),
                ("BACKGROUND", (1, 0), (1, 0), PANEL),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ]
        )
    )
    return table


def _append_fault_detail(
    story: list,
    item: PrioritizedFault,
    index: int,
    total: int,
    styles: dict[str, ParagraphStyle],
    regular: str,
    bold: str,
) -> None:
    fault, info = item.fault, item.info
    story.append(_fault_header(index, total, item, styles))
    story.append(Spacer(1, 3 * mm))

    original_title = info.original_title or fault.title or "Nespecificat în raport"
    metadata = [
        [
            _label_value("Adresă", fault.module_address, styles["small"]),
            _label_value(
                "Stare", fault.status or "Nespecificată", styles["small"]
            ),
        ],
        [
            _label_value("Text original VCDS", original_title, styles["small"]),
            _label_value(
                "Prioritate VCDS",
                fault.priority or "Nespecificată",
                styles["small"],
            ),
        ],
        [
            _label_value(
                "Frecvență",
                fault.frequency or "Nespecificată",
                styles["small"],
            ),
            _label_value(
                "Kilometraj memorare",
                fault.mileage or "Nespecificat",
                styles["small"],
            ),
        ],
    ]
    meta_table = Table(metadata, colWidths=[87 * mm, 87 * mm])
    meta_table.setStyle(_base_table_style(regular, bold, header=False))
    story.append(meta_table)

    story.append(_section_title("Interpretare și precauție", styles))
    story.append(_p(info.summary, styles["body"]))
    caution = info.warning
    if item.secondary_reason:
        caution = f"{item.secondary_reason} {caution}"
    caution_table = Table(
        [
            [
                Paragraph(
                    f"<b>ATENȚIE:</b> {_safe(caution)}", styles["small"]
                )
            ]
        ],
        colWidths=[174 * mm],
    )
    caution_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), AMBER_PALE),
                ("BOX", (0, 0), (-1, -1), 0.7, AMBER),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.append(caution_table)

    story.append(_section_title("Componentă, sistem și localizare", styles))
    component_rows = [
        [
            _p("Componentă / circuit", styles["small"]),
            _p(info.component, styles["small"]),
        ],
        [
            _p("Sistem / modul", styles["small"]),
            _p(info.system, styles["small"]),
        ],
        [
            _p("Localizare orientativă", styles["small"]),
            _p(info.location, styles["small"]),
        ],
    ]
    component_table = Table(
        component_rows, colWidths=[38 * mm, 136 * mm]
    )
    component_table.setStyle(
        _base_table_style(regular, bold, header=False)
    )
    component_table.setStyle(
        TableStyle([("FONTNAME", (0, 0), (0, -1), bold)])
    )
    story.append(component_table)

    story.append(_section_title("Simptome posibile", styles))
    story.extend(_bullet_paragraphs(info.symptoms, styles["body"]))
    story.append(
        _section_title("Cauze posibile - în ordinea confirmării", styles)
    )
    story.extend(_bullet_paragraphs(info.causes, styles["body"]))

    story.append(CondPageBreak(48 * mm))
    story.append(
        _section_title("Traseu de diagnostic în VCDS și măsurători", styles)
    )
    measurement_rows = [
        [
            _p("Cale VCDS", styles["small"]),
            _p(info.test_path, styles["small"]),
        ],
        [
            _p("Parametri de urmărit", styles["small"]),
            _p(info.parameters, styles["small"]),
        ],
        [
            _p("Criteriu / valori așteptate", styles["small"]),
            _p(info.expected, styles["small"]),
        ],
    ]
    measurement_table = Table(
        measurement_rows, colWidths=[42 * mm, 132 * mm]
    )
    measurement_table.setStyle(
        _base_table_style(regular, bold, header=False)
    )
    measurement_table.setStyle(
        TableStyle([("FONTNAME", (0, 0), (0, -1), bold)])
    )
    story.append(measurement_table)
    story.append(Spacer(1, 1.5 * mm))
    story.extend(_bullet_paragraphs(info.checks, styles["body"]))

    story.append(
        _section_title("Reparație și verificare după intervenție", styles)
    )
    story.extend(_bullet_paragraphs(info.repairs, styles["body"]))
    if info.replacement:
        story.append(_p("Pași suplimentari la înlocuire:", styles["body"]))
        story.extend(_bullet_paragraphs(info.replacement, styles["body"]))

    freeze_rows = _freeze_frame_rows(fault)
    story.append(
        _section_title("Date memorate la apariția erorii", styles)
    )
    if freeze_rows:
        table_rows = [
            [
                _p("Parametru", styles["white"]),
                _p("Valoare memorată", styles["white"]),
            ]
        ]
        table_rows.extend(
            [
                [_p(label, styles["small"]), _p(value, styles["small"])]
                for label, value in freeze_rows
            ]
        )
        freeze_table = Table(
            table_rows, colWidths=[78 * mm, 96 * mm], repeatRows=1
        )
        freeze_table.setStyle(_base_table_style(regular, bold))
        story.append(freeze_table)
    else:
        story.append(
            _p(
                "Raportul importat nu conține valori memorate pentru această eroare.",
                styles["body"],
            )
        )

    story.append(_section_title("Trasabilitate și sursă", styles))
    source_level = (
        "Fișă VAG detaliată"
        if info.verified
        else "Definiție de catalog - necesită confirmare pe vehicul"
    )
    source_rows = [
        [
            _p("Nivel informație", styles["small"]),
            _p(source_level, styles["small"]),
        ],
        [
            _p("Sursă", styles["small"]),
            _p(
                info.source_title or "Catalog local KID Diagnostic",
                styles["small"],
            ),
        ],
        [
            _p("Referință", styles["small"]),
            _p(info.source_url or "Înregistrare locală", styles["tiny"]),
        ],
    ]
    source_table = Table(source_rows, colWidths=[38 * mm, 136 * mm])
    source_table.setStyle(_base_table_style(regular, bold, header=False))
    source_table.setStyle(
        TableStyle([("FONTNAME", (0, 0), (0, -1), bold)])
    )
    story.append(source_table)


def _append_raw_appendix(
    story: list,
    analysis: ScanAnalysis,
    styles: dict[str, ParagraphStyle],
) -> None:
    story.append(PageBreak())
    story.append(
        Paragraph(
            "Anexa A - blocurile originale extrase din VCDS", styles["h1"]
        )
    )
    story.append(
        _p(
            "Această anexă păstrează trasabilitatea față de fișierul importat. "
            "Textul este redat în forma originală VCDS și nu este tradus sau reinterpretat.",
            styles["body"],
        )
    )
    for index, item in enumerate(analysis.prioritized, 1):
        fault = item.fault
        if not fault.raw_block:
            continue
        story.append(CondPageBreak(38 * mm))
        story.append(
            Paragraph(
                f"<b>{index}. {_safe(fault.display_code)}</b> | "
                f"{_safe(fault.module_address)} - {_safe(fault.module_name)}",
                styles["h2"],
            )
        )
        raw_table = Table(
            [[_p(fault.raw_block, styles["mono"])]], colWidths=[174 * mm]
        )
        raw_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), PALE),
                    ("BOX", (0, 0), (-1, -1), 0.4, GRID),
                    ("LEFTPADDING", (0, 0), (-1, -1), 7),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(raw_table)


def _summary_metrics(
    scan: ScanResult,
    analysis: ScanAnalysis,
    styles: dict[str, ParagraphStyle],
) -> Table:
    metrics = (
        (len(scan.modules), "MODULE IDENTIFICATE"),
        (scan.fault_modules, "MODULE CU ERORI"),
        (scan.total_dtc, "DTC EXTRASE"),
        (analysis.verified_count, "FIȘE VAG DETALIATE"),
    )
    cells = [
        Paragraph(
            f"<font size='17'><b>{value}</b></font><br/>"
            f"<font size='7'>{escape(label)}</font>",
            styles["metric"],
        )
        for value, label in metrics
    ]
    table = Table([cells], colWidths=[43.5 * mm] * 4)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PALE),
                ("BOX", (0, 0), (-1, -1), 0.5, GRID),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, GRID),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    return table


def create_diagnostic_pdf(path: str | Path, scan: ScanResult) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    regular, bold, mono = _register_font()
    styles = _styles(regular, bold, mono)
    generated = datetime.now().astimezone()
    vin_value = scan.vehicle.vin.upper().strip()
    vin_token = (
        re.sub(r"[^A-Z0-9]", "", vin_value)[-8:]
        if re.fullmatch(r"[A-HJ-NPR-Z0-9]{17}", vin_value)
        else "NEIDENT"
    )
    report_id = (
        f"KID-{generated.strftime('%Y%m%d-%H%M')}-{vin_token}"
    )
    analysis = analyze_scan(scan)

    document = SimpleDocTemplate(
        str(destination),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=19 * mm,
        bottomMargin=20 * mm,
        title=f"Raport diagnostic profesional {scan.vehicle.vin}",
        author="KID VAG MASTER Diagnostic PRO V2",
        subject="Analiză Auto-Scan VCDS",
        creator="KID VAG MASTER Diagnostic PRO V2",
    )

    story: list = []
    brand = Table(
        [
            [
                Paragraph("KID VAG MASTER", styles["white"]),
                Paragraph("DIAGNOSTIC PRO V2", styles["white_center"]),
            ]
        ],
        colWidths=[118 * mm, 56 * mm],
    )
    brand.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), NAVY),
                ("BACKGROUND", (1, 0), (1, 0), BLUE),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(brand)
    story.append(Spacer(1, 7 * mm))
    story.append(
        Paragraph("RAPORT DIAGNOSTIC PROFESIONAL", styles["title"])
    )
    story.append(
        Paragraph(
            "Analiză tehnică a unui Auto-Scan VCDS importat din TXT, LOG "
            "sau PDF. Toate valorile vehiculului provin din fișierul indicat "
            "mai jos.",
            styles["subtitle"],
        )
    )

    report_data = [
        [
            _p("ID raport", styles["small"]),
            _p(report_id, styles["small"]),
            _p("Generat", styles["small"]),
            _p(
                generated.strftime("%d.%m.%Y, %H:%M %Z"),
                styles["small"],
            ),
        ],
        [
            _p("Fișier sursă", styles["small"]),
            _p(scan.source_name, styles["small"]),
            _p("Aplicație", styles["small"]),
            _p(
                "KID VAG MASTER Diagnostic PRO V2", styles["small"]
            ),
        ],
    ]
    report_table = Table(
        report_data, colWidths=[27 * mm, 60 * mm, 25 * mm, 62 * mm]
    )
    report_table.setStyle(
        _base_table_style(regular, bold, header=False)
    )
    report_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), bold),
                ("FONTNAME", (2, 0), (2, -1), bold),
            ]
        )
    )
    story.append(report_table)
    story.append(Spacer(1, 5 * mm))

    vehicle = scan.vehicle
    vehicle_title = vehicle.display_name
    vehicle_subtitle = " | ".join(
        value
        for value in (
            str(vehicle.year) if vehicle.year else "",
            vehicle.engine,
            vehicle.chassis,
        )
        if value
    )
    mileage_text = (
        f"{vehicle.mileage_km:,} km".replace(",", ".")
        if vehicle.mileage_km
        else "Nedetectat"
    )
    vehicle_panel = Table(
        [
            [
                Paragraph(
                    f"<font size='16'><b>{_safe(vehicle_title)}</b></font>"
                    f"<br/>{_safe(vehicle_subtitle or 'Identificare parțială din Auto-Scan')}",
                    styles["white"],
                ),
                Paragraph(
                    f"<b>VIN</b><br/>{_safe(vehicle.vin)}<br/><br/>"
                    f"<b>KILOMETRAJ</b><br/>{_safe(mileage_text)}",
                    styles["white_center"],
                ),
            ]
        ],
        colWidths=[112 * mm, 62 * mm],
    )
    vehicle_panel.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, 0), PANEL),
                ("BACKGROUND", (1, 0), (1, 0), BLUE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 11),
                ("RIGHTPADDING", (0, 0), (-1, -1), 11),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
            ]
        )
    )
    story.append(vehicle_panel)
    story.append(Spacer(1, 4 * mm))
    story.append(_validation_box(scan, styles, regular))
    story.append(Spacer(1, 4 * mm))
    story.append(_summary_metrics(scan, analysis, styles))

    story.append(Paragraph("Rezumat executiv", styles["h1"]))
    if scan.total_dtc:
        story.append(
            _p(
                f"Scanarea conține {scan.total_dtc} erori în "
                f"{scan.fault_modules} module. {analysis.confirmed_count} "
                "sunt marcate confirmat, iar "
                f"{analysis.intermittent_count} sunt intermitente. "
                "Prioritizarea de mai jos combină statusul VCDS, prioritatea "
                "datele memorate, sistemul implicat și nivelul fișei tehnice; "
                "nu reprezintă un verdict automat asupra piesei.",
                styles["body"],
            )
        )
    else:
        story.append(
            _p(
                "Nu au fost extrase coduri DTC. Verificați totuși starea "
                "modulelor și confirmați că scanarea s-a încheiat complet.",
                styles["body"],
            )
        )

    if analysis.common_findings:
        story.append(
            _section_title("Corelări și cauze comune de verificat", styles)
        )
        rows = [
            [
                _p("Corelare", styles["white"]),
                _p("Dovezi și prima acțiune", styles["white"]),
                _p("Încredere", styles["white_center"]),
            ]
        ]
        for finding in analysis.common_findings:
            rows.append(
                [
                    _p(finding.title, styles["small"]),
                    Paragraph(
                        f"{_safe(finding.evidence)}<br/>"
                        f"<b>Prima acțiune:</b> {_safe(finding.first_action)}",
                        styles["small"],
                    ),
                    _p(finding.confidence, styles["small"]),
                ]
            )
        correlation_table = Table(
            rows,
            colWidths=[39 * mm, 113 * mm, 22 * mm],
            repeatRows=1,
        )
        correlation_table.setStyle(_base_table_style(regular, bold))
        correlation_table.setStyle(
            TableStyle([("FONTNAME", (0, 1), (0, -1), bold)])
        )
        story.append(correlation_table)

    if analysis.prioritized:
        story.append(
            _section_title("Ordinea recomandată a verificărilor", styles)
        )
        rows = [
            [
                _p("#", styles["white_center"]),
                _p("DTC și modul", styles["white"]),
                _p("Interpretare", styles["white"]),
                _p("Prioritate", styles["white_center"]),
            ]
        ]
        for index, item in enumerate(analysis.prioritized, 1):
            rows.append(
                [
                    _p(index, styles["small"]),
                    Paragraph(
                        f"<b>{_safe(item.fault.display_code)}</b><br/>"
                        f"{_safe(item.fault.module_address)} - "
                        f"{_safe(item.fault.module_name)}",
                        styles["small"],
                    ),
                    _p(item.info.title, styles["small"]),
                    _p(item.level, styles["small"]),
                ]
            )
        priority_table = Table(
            rows,
            colWidths=[9 * mm, 52 * mm, 76 * mm, 37 * mm],
            repeatRows=1,
        )
        priority_table.setStyle(_base_table_style(regular, bold))
        priority_table.setStyle(
            TableStyle(
                [
                    ("TEXTCOLOR", (1, 1), (1, -1), AMBER),
                    ("FONTNAME", (1, 1), (1, -1), bold),
                ]
            )
        )
        story.append(priority_table)

    story.append(PageBreak())
    story.append(
        Paragraph(
            "Identificarea vehiculului și integritatea importului",
            styles["h1"],
        )
    )
    identification_rows = [
        [
            _p("Marcă", styles["small"]),
            _p(vehicle.brand, styles["small"]),
            _p("Model", styles["small"]),
            _p(vehicle.model, styles["small"]),
        ],
        [
            _p("An model", styles["small"]),
            _p(vehicle.year or "Nedetectat", styles["small"]),
            _p("Platformă", styles["small"]),
            _p(vehicle.platform, styles["small"]),
        ],
        [
            _p("Cod motor", styles["small"]),
            _p(vehicle.engine_code or "Nedetectat", styles["small"]),
            _p("Motor / componentă", styles["small"]),
            _p(vehicle.engine, styles["small"]),
        ],
        [
            _p("VIN", styles["small"]),
            _p(vehicle.vin, styles["small"]),
            _p("Șasiu VCDS", styles["small"]),
            _p(vehicle.chassis, styles["small"]),
        ],
        [
            _p("Număr înmatriculare", styles["small"]),
            _p(
                vehicle.license_plate or "Nedetectat", styles["small"]
            ),
            _p("Kilometraj", styles["small"]),
            _p(mileage_text, styles["small"]),
        ],
    ]
    identification_table = Table(
        identification_rows,
        colWidths=[31 * mm, 56 * mm, 31 * mm, 56 * mm],
    )
    identification_table.setStyle(
        _base_table_style(regular, bold, header=False)
    )
    identification_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), bold),
                ("FONTNAME", (2, 0), (2, -1), bold),
            ]
        )
    )
    story.append(identification_table)

    story.append(_section_title("Control automat al importului", styles))
    voltage_text = (
        f"{scan.voltage_start:.1f} V / {scan.voltage_end:.1f} V"
        if scan.voltage_start is not None and scan.voltage_end is not None
        else "Nedetectată"
    )
    integrity_rows = [
        [
            _p("Fișier", styles["small"]),
            _p(scan.source_name, styles["small"]),
        ],
        [
            _p("Erori declarate de VCDS", styles["small"]),
            _p(
                scan.declared_fault_count
                if scan.declared_fault_count is not None
                else "Raportul nu oferă totaluri pe module",
                styles["small"],
            ),
        ],
        [
            _p("Erori extrase", styles["small"]),
            _p(scan.parsed_fault_count, styles["small"]),
        ],
        [
            _p("Rezultat validare", styles["small"]),
            _p(scan.validation_message, styles["small"]),
        ],
        [
            _p("Tensiune început / final", styles["small"]),
            _p(voltage_text, styles["small"]),
        ],
    ]
    for detail in scan.validation_details:
        integrity_rows.append(
            [_p("Diferență", styles["small"]), _p(detail, styles["small"])]
        )
    integrity_table = Table(
        integrity_rows, colWidths=[50 * mm, 124 * mm]
    )
    integrity_table.setStyle(
        _base_table_style(regular, bold, header=False)
    )
    integrity_table.setStyle(
        TableStyle([("FONTNAME", (0, 0), (0, -1), bold)])
    )
    story.append(integrity_table)

    try:
        from database import get_database

        stats = get_database().stats()
        coverage_text = (
            f"Baza locală include {stats['DTC']:,} DTC, "
            f"{stats['proceduri']} proceduri, "
            f"{stats['aplicabilități']:,} asocieri de aplicabilitate, "
            f"{stats['generații']} generații și {stats['surse']} surse. "
            "Acoperirea de catalog nu înlocuiește identificarea exactă a "
            "modulului."
        ).replace(",", ".")
        story.append(
            _section_title("Acoperirea bazei tehnice locale", styles)
        )
        story.append(_p(coverage_text, styles["body"]))
    except Exception:  # noqa: BLE001 - raportul rămâne exportabil.
        pass

    story.append(Paragraph("Inventarul modulelor VCDS", styles["h1"]))
    module_rows = [
        [
            _p("Adr.", styles["white_center"]),
            _p("Modul", styles["white"]),
            _p("Identificare unitate", styles["white"]),
            _p("Stare", styles["white_center"]),
            _p("DTC", styles["white_center"]),
        ]
    ]
    for module in scan.modules:
        identification = [
            f"Număr piesă: {module.part_no or 'Nedetectat'}",
            f"Componentă: {module.component or 'Nedetectată'}",
        ]
        if module.coding:
            identification.append(f"Codare: {module.coding}")
        module_rows.append(
            [
                _p(module.address, styles["small"]),
                _p(module.name, styles["small"]),
                _p("\n".join(identification), styles["tiny"]),
                _p(module.status, styles["small"]),
                _p(module.dtc_count, styles["small"]),
            ]
        )
    if not scan.modules:
        module_rows.append(
            [
                _p("-", styles["small"]),
                _p("Niciun modul identificat", styles["small"]),
                _p("-", styles["small"]),
                _p("-", styles["small"]),
                _p("0", styles["small"]),
            ]
        )
    module_table = Table(
        module_rows,
        colWidths=[13 * mm, 42 * mm, 80 * mm, 25 * mm, 14 * mm],
        repeatRows=1,
    )
    module_table.setStyle(_base_table_style(regular, bold))
    for row_index, module in enumerate(scan.modules, 1):
        if module.dtc_count:
            module_table.setStyle(
                TableStyle(
                    [
                        (
                            "TEXTCOLOR",
                            (3, row_index),
                            (4, row_index),
                            AMBER,
                        ),
                        (
                            "FONTNAME",
                            (3, row_index),
                            (4, row_index),
                            bold,
                        ),
                    ]
                )
            )
        elif module.status.upper() == "OK":
            module_table.setStyle(
                TableStyle(
                    [
                        (
                            "TEXTCOLOR",
                            (3, row_index),
                            (4, row_index),
                            GREEN,
                        )
                    ]
                )
            )
    story.append(module_table)

    if analysis.prioritized:
        for index, item in enumerate(analysis.prioritized, 1):
            story.append(PageBreak())
            _append_fault_detail(
                story,
                item,
                index,
                len(analysis.prioritized),
                styles,
                regular,
                bold,
            )

        _append_raw_appendix(story, analysis, styles)

    story.append(PageBreak())
    story.append(
        Paragraph(
            "Plan final de atelier și închiderea lucrării", styles["h1"]
        )
    )
    workflow = (
        "Salvați Auto-Scan-ul inițial și notați reclamația clientului.",
        "Confirmați identitatea vehiculului, codul motor, numerele de piesă și nivelurile software.",
        "Verificați mai întâi bateria, alimentările, masele și comunicația atunci când raportul oferă indicii comune.",
        "Abordați DTC-urile în ordinea prioritizată, începând cu cele de siguranță, motor/transmisie și cele statice sau confirmate.",
        "Măsurați și comparați valorile solicitate cu cele reale; folosiți datele memorate pentru a reproduce condițiile.",
        "Reparați numai cauza confirmată. Salvați codările originale înainte de orice adaptare sau codare.",
        "Ștergeți erorile numai după intervenție, executați ciclul funcțional/testul rutier cerut și repetați Auto-Scan-ul complet.",
        "Atașați scanarea finală și valorile măsurate la fișa lucrării.",
    )
    story.extend(_bullet_paragraphs(workflow, styles["body"]))

    story.append(
        _section_title("Fișă de confirmare după reparație", styles)
    )
    checklist_rows = [
        [
            _p("Control", styles["white"]),
            _p("Rezultat / observații atelier", styles["white"]),
        ]
    ]
    for label in (
        "Tensiune baterie și încărcare",
        "DTC-uri care reapar după ștergere",
        "Valori solicitate versus reale",
        "Teste de actuatori / setări de bază",
        "Test rutier și simptome",
        "Auto-Scan final atașat",
    ):
        checklist_rows.append(
            [
                _p(label, styles["small"]),
                _p(
                    "________________________________________________________",
                    styles["small"],
                ),
            ]
        )
    checklist = Table(
        checklist_rows, colWidths=[62 * mm, 112 * mm], repeatRows=1
    )
    checklist.setStyle(_base_table_style(regular, bold))
    story.append(checklist)

    story.append(_section_title("Notă profesională și limite", styles))
    disclaimer = (
        "Acest raport organizează datele găsite în Auto-Scan și informațiile "
        "din baza locală. Un cod DTC indică sistemul care a detectat abaterea, "
        "nu dovedește singur că piesa denumită este defectă. Textul original "
        "VCDS, numărul exact al unității, schema electrică, buletinele tehnice "
        "și măsurătorile pe vehicul au prioritate. Codarea, adaptarea, setările "
        "de bază, protecția componentelor și operațiile asupra sistemelor de "
        "siguranță trebuie executate numai de personal calificat, cu sursă de "
        "tensiune stabilă și procedura specifică vehiculului."
    )
    disclaimer_table = Table(
        [
            [
                Paragraph(
                    f"<b>IMPORTANT:</b> {_safe(disclaimer)}",
                    styles["body"],
                )
            ]
        ],
        colWidths=[174 * mm],
    )
    disclaimer_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), AMBER_PALE),
                ("BOX", (0, 0), (-1, -1), 0.9, AMBER),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ]
        )
    )
    story.append(disclaimer_table)
    story.append(Spacer(1, 7 * mm))
    story.append(_p(f"Sfârșit raport - {report_id}", styles["subtitle"]))

    decorator = _page_decoration(report_id, regular, bold)
    document.build(
        story, onFirstPage=decorator, onLaterPages=decorator
    )
    return destination
