"""Export the interpreted Auto-Scan diagnosis to a user-selected PDF file."""
from html import escape
from pathlib import Path

from PySide6.QtCore import QMarginsF, Qt
from PySide6.QtGui import (
    QTextDocument, QPdfWriter, QPageLayout, QPageSize,
    QImage, QPainter, QColor, QPen, QFont
)
from PySide6.QtWidgets import QPushButton, QFileDialog, QMessageBox

from appdb import APP_DATA, LOGO_PATH
from autoscan_correlation import render_correlation
from autoscan_ro import ro_status, ro_module, ro_title, ro_confidence, ro_vcds_note


def _e(value):
    return escape(str(value or "—")).replace("\n", "<br>")


def _vehicle_text(self):
    parts = []
    for name in ("brand_combo", "model_combo", "generation_combo", "year_combo", "engine_combo"):
        w = getattr(self, name, None)
        if w is not None and hasattr(w, "currentText"):
            t = w.currentText().strip()
            if t and t not in parts and not t.lower().startswith("alege"):
                parts.append(t)
    return " • ".join(parts) or "Vehicul selectat în KID Diagnostic"


def _report_logo_uri():
    """Return the user's KID logo when available; otherwise create a compact fallback."""
    custom = Path(LOGO_PATH)
    if custom.exists() and custom.stat().st_size > 256:
        return custom.as_uri()

    logo = Path(APP_DATA) / "kid_diagnostic_report_logo_compact.png"
    if not logo.exists() or logo.stat().st_size < 700:
        img = QImage(620, 150, QImage.Format.Format_ARGB32)
        img.fill(QColor("#061423"))
        p = QPainter(img); p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.setPen(QPen(QColor("#27b7ff"), 6)); p.setBrush(QColor("#081d31")); p.drawEllipse(14, 14, 118, 118)
        p.setPen(QColor("#f3f8fb")); f = QFont("Arial", 39); f.setBold(True); p.setFont(f)
        p.drawText(154, 17, 210, 62, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "KID")
        p.setPen(QColor("#36bfff")); f2 = QFont("Arial", 20); f2.setBold(True); p.setFont(f2)
        p.drawText(157, 72, 320, 40, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "DIAGNOSTIC")
        p.setPen(QColor("#9cb8ca")); f3 = QFont("Arial", 9); p.setFont(f3)
        p.drawText(158, 111, 430, 24, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "VAG MASTER • AUTO-SCAN • RAPORT")
        p.end(); img.save(str(logo), "PNG")
    return logo.as_uri()


def _build_html(self):
    result = self.current_autoscan
    plans = list(self.autoscan_plans or [])
    corr = self.autoscan_correlation
    vin = getattr(result, "vin", "") or "—"
    src = Path(getattr(result, "source_path", "autoscan")).name
    logo_uri = _report_logo_uri()

    css = """
    <style>
      body { font-family: Arial, sans-serif; color:#172331; font-size:9.6pt; line-height:1.32; margin:0; }
      h1 { font-size:18pt; margin:0; color:#103d59; }
      h2 { font-size:13.5pt; margin:15px 0 6px 0; color:#145f88; border-bottom:1px solid #a9ccde; padding-bottom:3px; }
      h3 { font-size:11pt; margin:0 0 5px 0; color:#173f58; }
      p { margin:6px 0; }
      .header { width:100%; margin:0 0 8px 0; border-bottom:2px solid #1d88bd; padding:0 0 6px 0; }
      .logoCell { width:128px; vertical-align:middle; }
      .logo { width:112px; height:32px; }
      .headerTitle { font-size:17pt; font-weight:bold; color:#103d59; margin:0; }
      .headerSub { font-size:8.7pt; color:#627986; margin-top:2px; }
      .meta { background:#eef6fa; border:1px solid #acd1e2; padding:8px 10px; margin:7px 0 9px 0; }
      .summary { background:#152b3a; color:white; padding:9px 11px; margin:8px 0 11px 0; }
      .fault { border:1px solid #c8d8e1; background:#fbfdfe; padding:8px 10px; margin:7px 0 10px 0; page-break-inside:avoid; }
      .label { font-weight:bold; color:#174c6b; }
      .small { color:#5d6f7a; font-size:8.3pt; }
      .warning { background:#fff8e8; border:1px solid #ead39a; padding:7px 9px; }
      pre { white-space:pre-wrap; font-family:Arial, sans-serif; font-size:9pt; line-height:1.28; }
    </style>
    """

    secondary = len((corr or {}).get("secondary", []))
    primary = max(0, len(plans) - secondary)
    html = ["<html><head>", css, "</head><body>"]
    html.append(
        "<table class='header' cellspacing='0' cellpadding='0'><tr>"
        f"<td class='logoCell'><img class='logo' src='{logo_uri}' width='112' height='32'></td>"
        "<td valign='middle'><div class='headerTitle'>Raport Auto-Scan VCDS</div>"
        "<div class='headerSub'>KID Diagnostic • diagnostic ghidat • plan de verificare • date live</div></td>"
        "</tr></table>"
    )
    html.append(
        f"<div class='meta'><b>Vehicul:</b> {_e(_vehicle_text(self))}<br>"
        f"<b>VIN:</b> {_e(vin)} &nbsp;&nbsp; <b>Fișier:</b> {_e(src)}<br>"
        f"<b>Module:</b> {len(getattr(result, 'modules', []) or [])} &nbsp;&nbsp; "
        f"<b>Erori:</b> {len(plans)}</div>"
    )
    html.append(
        f"<div class='summary'><b>REZULTAT DIAGNOSTIC:</b> {len(plans)} erori detectate &nbsp;•&nbsp; "
        f"{primary} de analizat prioritar &nbsp;•&nbsp; {secondary} probabil secundare</div>"
    )

    if corr:
        html.append("<h2>Plan diagnostic automat</h2>")
        html.append(f"<pre>{_e(render_correlation(corr))}</pre>")

    html.append("<h2>Erori și proceduri recomandate</h2>")
    for fault, p in plans:
        code = fault.code or fault.vag_code or "DTC"
        title = ro_title(p.get("title") or fault.title)
        html.append("<div class='fault'>")
        html.append(f"<h3>{_e(code)} — {_e(title)}</h3>")
        html.append(f"<span class='label'>Modul:</span> {_e(fault.module_address)} {_e(ro_module(fault.module_name))}<br>")
        html.append(f"<span class='label'>Stare:</span> {_e(ro_status(p.get('status','')))} &nbsp; • &nbsp; ")
        html.append(f"<span class='label'>Nivel:</span> {_e(ro_confidence(p.get('found'), p.get('verified')))}")
        fields = [
            ("Ce înseamnă", p.get("description")),
            ("Simptome posibile", p.get("symptoms")),
            ("Cauze posibile", p.get("causes")),
            ("Piesa / sistemul implicat", p.get("component")),
            ("Unde se află", p.get("location")),
            ("Ce verifici în VCDS", p.get("parameters")),
            ("Valori / comportament așteptat", p.get("expected")),
            ("Traseu în VCDS", p.get("test_path")),
            ("Diagnostic pas cu pas", p.get("diagnosis")),
            ("Cum o repari", p.get("repair")),
            ("După înlocuirea piesei", p.get("replacement")),
            ("Freeze Frame / date din raport", p.get("freeze_frame")),
        ]
        for label, value in fields:
            if value:
                html.append(f"<p><span class='label'>{_e(label)}:</span><br>{_e(value)}</p>")
        html.append("</div>")

    html.append("<h2>Notă tehnică</h2>")
    html.append(f"<div class='warning'>{_e(ro_vcds_note())}</div>")
    html.append("<p class='small'>Raport generat de KID Diagnostic din Auto-Scan-ul încărcat și baza locală. Confirmați procedura pentru platforma și controllerul exact înainte de Coding, Adaptation sau Basic Settings.</p>")
    html.append("</body></html>")
    return "".join(html)


def apply(MainWindow):
    old_build_ui = MainWindow.build_ui
    old_reset = getattr(MainWindow, "reset_autoscan_ui", None)

    def build_ui(self):
        old_build_ui(self)
        page = self.stack.widget(self.autoscan_page_index)
        root = page.layout()
        self.autoscan_export_pdf_btn = QPushButton("Salvează raport analiză PDF")
        self.autoscan_export_pdf_btn.setObjectName("primary")
        self.autoscan_export_pdf_btn.setEnabled(False)
        self.autoscan_export_pdf_btn.clicked.connect(self.export_autoscan_pdf)
        root.insertWidget(3 if root.count() >= 3 else root.count(), self.autoscan_export_pdf_btn)

    def export_autoscan_pdf(self):
        if not getattr(self, "current_autoscan", None) or not getattr(self, "autoscan_plans", None):
            QMessageBox.warning(self, "Salvare PDF", "Încarcă și analizează mai întâi un Auto-Scan VCDS.")
            return
        source = Path(self.current_autoscan.source_path).stem or "autoscan"
        suggested = f"KID_Diagnostic_{source}_analiza.pdf"
        path, _ = QFileDialog.getSaveFileName(self, "Salvează raportul de diagnostic", suggested, "PDF (*.pdf)")
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        try:
            writer = QPdfWriter(path)
            writer.setTitle("KID Diagnostic - Raport Auto-Scan VCDS")
            writer.setCreator("KID Diagnostic")
            writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
            writer.setPageMargins(QMarginsF(13, 13, 13, 13), QPageLayout.Unit.Millimeter)
            writer.setResolution(120)
            doc = QTextDocument(); doc.setHtml(_build_html(self)); doc.print_(writer)
        except Exception as exc:
            QMessageBox.critical(self, "Salvare PDF", f"Raportul PDF nu a putut fi salvat:\n{exc}")
            return
        QMessageBox.information(self, "Salvare PDF", f"Raportul a fost salvat cu succes:\n{path}")

    old_populate = MainWindow.populate_autoscan
    def populate_autoscan(self, result):
        old_populate(self, result)
        if hasattr(self, "autoscan_export_pdf_btn"):
            self.autoscan_export_pdf_btn.setEnabled(bool(getattr(result, "faults", None)))

    def reset_autoscan_ui(self):
        if old_reset:
            old_reset(self)
        if hasattr(self, "autoscan_export_pdf_btn"):
            self.autoscan_export_pdf_btn.setEnabled(False)

    MainWindow.build_ui = build_ui
    MainWindow.populate_autoscan = populate_autoscan
    MainWindow.export_autoscan_pdf = export_autoscan_pdf
    MainWindow.reset_autoscan_ui = reset_autoscan_ui
