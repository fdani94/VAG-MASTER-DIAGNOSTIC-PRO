"""Hotfix for Auto-Scan PDF export.

Ensures the button is enabled after scan parsing and after diagnostic-plan rendering,
and exports through QtPrintSupport for reliable Unicode PDF output in the Windows build.
"""
from pathlib import Path

from PySide6.QtGui import QTextDocument
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtWidgets import QFileDialog, QMessageBox


def apply(MainWindow):
    old_populate = MainWindow.populate_autoscan
    old_show_corr = MainWindow.show_autoscan_correlation
    old_reset = getattr(MainWindow, "reset_autoscan_ui", None)

    def _set_pdf_ready(self):
        btn = getattr(self, "autoscan_export_pdf_btn", None)
        ready = bool(getattr(self, "current_autoscan", None) and getattr(self, "autoscan_plans", None))
        if btn is not None:
            btn.setEnabled(ready)
            btn.setToolTip("Salvează analiza completă, planul diagnostic și valorile Live Data într-un PDF." if ready else "Încarcă mai întâi un Auto-Scan cu erori.")
        return ready

    def populate_autoscan(self, result):
        old_populate(self, result)
        _set_pdf_ready(self)

    def show_autoscan_correlation(self):
        old_show_corr(self)
        _set_pdf_ready(self)

    def export_autoscan_pdf(self):
        if not _set_pdf_ready(self):
            QMessageBox.warning(self, "Salvare PDF", "Încarcă mai întâi un Auto-Scan VCDS cu erori și generează analiza.")
            return

        # Import here so this patch can be loaded independently of the export UI module.
        try:
            from ui_autoscan_pdf_export import _build_html
        except Exception as exc:
            QMessageBox.critical(self, "Salvare PDF", f"Modulul de raport PDF nu poate fi încărcat:\n{exc}")
            return

        source = Path(getattr(self.current_autoscan, "source_path", "autoscan")).stem or "autoscan"
        suggested = f"KID_Diagnostic_{source}_analiza.pdf"
        path, _ = QFileDialog.getSaveFileName(self, "Salvează raportul de diagnostic", suggested, "PDF (*.pdf)")
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"

        try:
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(path)
            printer.setDocName("KID Diagnostic - Raport Auto-Scan VCDS")
            doc = QTextDocument()
            doc.setDocumentMargin(28)
            doc.setHtml(_build_html(self))
            doc.print_(printer)
            if not Path(path).exists() or Path(path).stat().st_size < 500:
                raise RuntimeError("Fișierul PDF nu a fost creat corect sau este gol.")
        except Exception as exc:
            QMessageBox.critical(self, "Salvare PDF", f"Raportul PDF nu a putut fi salvat:\n{exc}")
            return

        QMessageBox.information(self, "Salvare PDF", f"Raportul a fost salvat cu succes:\n{path}")

    def reset_autoscan_ui(self):
        if old_reset:
            old_reset(self)
        btn = getattr(self, "autoscan_export_pdf_btn", None)
        if btn is not None:
            btn.setEnabled(False)

    MainWindow.populate_autoscan = populate_autoscan
    MainWindow.show_autoscan_correlation = show_autoscan_correlation
    MainWindow.export_autoscan_pdf = export_autoscan_pdf
    MainWindow.reset_autoscan_ui = reset_autoscan_ui
