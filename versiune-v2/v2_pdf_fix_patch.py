"""Final V2 PDF export override.

Applied after all UI/functional patches so every report button uses the
Unicode-safe ReportLab renderer instead of Qt QTextDocument/QPdfWriter.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QMessageBox

from v2_pdf_report import export_pdf as export_unicode_pdf

PDF_EXPORT_VERSION = "3.0-unicode-reportlab"


def _active_parent(owner):
    index = int(getattr(owner, "_active_workspace_index", 0) or 0)
    win = getattr(owner, "_workspace_windows", {}).get(index)
    if win is not None and win.isVisible():
        return win
    return owner


def apply():
    import ui_v2

    cls = ui_v2.MainWindowV2
    if getattr(cls, "_kid_v2_pdf_fix_applied", False):
        return

    def _export_pdf(self):
        parent = _active_parent(self)
        if not getattr(self, "current_autoscan", None) or not getattr(self, "autoscan_plans", None):
            QMessageBox.warning(parent, "Raport PDF", "Încarcă mai întâi un Auto-Scan VCDS cu erori.")
            self.open_page(1)
            return

        source_path = Path(getattr(self.current_autoscan, "source_path", "autoscan"))
        suggested = f"KID_Diagnostic_{source_path.stem}_V2.pdf"
        path, _ = QFileDialog.getSaveFileName(
            parent,
            "Salvează raportul KID Diagnostic",
            suggested,
            "PDF (*.pdf)",
        )
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        try:
            export_unicode_pdf(self, path)
        except Exception as exc:
            QMessageBox.critical(parent, "Raport PDF", f"Raportul nu a putut fi salvat:\n{exc}")
            return
        QMessageBox.information(parent, "Raport PDF", f"Raport salvat:\n{path}")

    cls._export_pdf = _export_pdf
    cls._kid_v2_pdf_fix_applied = True
