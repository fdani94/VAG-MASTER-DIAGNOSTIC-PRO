"""Export the interpreted Auto-Scan diagnosis to a user-selected PDF file."""
from html import escape
from pathlib import Path

from PySide6.QtCore import QMarginsF
from PySide6.QtGui import QTextDocument, QPdfWriter, QPageLayout, QPageSize
from PySide6.QtWidgets import QPushButton, QFileDialog, QMessageBox

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
            if t and t not in parts:
                parts.append(t)
    return " • ".join(parts) or "Vehicul selectat în KID Diagnostic"


def _build_html(self):
    result = self.current_autoscan
    plans = list(self.autoscan_plans or [])
    corr = self.autoscan_correlation
    vin = getattr(result, "vin", "") or "—"
    src = Path(getattr(result, "source_path", "autoscan")).name

    css = """
    <style>
      body { font-family: Arial, sans-serif; color:#172331; font-size:10.5pt; }
      h1 { font-size:22pt; margin:0 0 4px 0; color:#0f3752; }
      h2 { font-size:15pt; margin:18px 0 7px 0; color:#145f88; border-bottom:1px solid #9bc6de; padding-bottom:3px; }
      h3 { font-size:12pt; margin:14px 0 4px 0; color:#173f58; }
      .meta { background:#eef6fa; border:1px solid #a9d1e5; padding:9px; margin:8px 0 12px 0; }
      .summary { background:#172331; color:white; padding:12px; margin:10px 0 14px 0; }
      .fault { border:1px solid #c9d7df; padding:9px; margin:9px 0 12px 0; }
      .label { font-weight:bold; color:#174c6b; }
      .small { color:#556772; font-size:9pt; }
      pre { white-space:pre-wrap; font-family:Arial, sans-serif; }
    </style>
    """

    secondary = len((corr or {}).get("secondary", []))
    primary = max(0, len(plans) - secondary)
    html = ["<html><head>", css, "</head><body>"]
    html.append("<h1>KID Diagnostic - Raport Auto-Scan VCDS</h1>")
    html.append(
        f"<div class='meta'><b>Vehicul:</b> {_e(_vehicle_text(self))}<br>"
        f"<b>VIN:</b> {_e(vin)}<br><b>Fișier analizat:</b> {_e(src)}<br>"
        f"<b>Module detectate:</b> {len(getattr(result, 'modules', []) or [])} &nbsp; "
        f"<b>Erori detectate:</b> {len(plans)}</div>"
    )
    html.append(
        f"<div class='summary'><b>REZULTAT:</b> {len(plans)} erori detectate • "
        f"{primary} de analizat prioritar • {secondary} probabil secundare</div>"
    )

    if corr:
        html.append("<h2>Plan diagnostic automat</h2>")
        html.append(f"<pre>{_e(render_correlation(corr))}</pre>")

    html.append("<h2>Erori și proceduri recomandate</h2>")
    for fault, p in plans:
        code = fault.code or fault.vag_code or "DTC"
        title = ro_title(p.get("title") or fault.title)
        html.append("<div class='fault'>")
        html.append(f"<h3>{_e(code)} - {_e(title)}</h3>")
        html.append(f"<span class='label'>Modul:</span> {_e(fault.module_address)} {_e(ro_module(fault.module_name))}<br>")
        html.append(f"<span class='label'>Stare:</span> {_e(ro_status(p.get('status','')))}<br>")
        html.append(f"<span class='label'>Nivel informație:</span> {_e(ro_confidence(p.get('found'), p.get('verified')))}<br><br>")
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

    html.append("<h2>Notă VCDS</h2>")
    html.append(f"<p>{_e(ro_vcds_note())}</p>")
    html.append("<p class='small'>Raport generat de KID Diagnostic pe baza Auto-Scan-ului încărcat și a bazei locale de diagnostic. Confirmați procedurile specifice platformei înainte de Coding / Adaptation / Basic Settings.</p>")
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
        # Keep it visible just below the large result area / scan controls.
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
            writer.setPageMargins(QMarginsF(14, 14, 14, 14), QPageLayout.Unit.Millimeter)
            writer.setResolution(120)
            doc = QTextDocument()
            doc.setHtml(_build_html(self))
            doc.print_(writer)
        except Exception as exc:
            QMessageBox.critical(self, "Salvare PDF", f"Raportul PDF nu a putut fi salvat:\n{exc}")
            return
        QMessageBox.information(self, "Salvare PDF", f"Raportul a fost salvat cu succes:\n{path}")

    # Enable export when a parsed scan is populated.
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
