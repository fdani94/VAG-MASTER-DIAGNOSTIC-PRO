"""Runtime fixes for Auto-Scan.

1) pypdf normal extraction can flatten VCDS PDFs into one long line. We use
   extraction_mode='layout' so Address/DTC blocks remain on separate lines.
2) When the selected vehicle changes, the previous Auto-Scan must be cleared.
"""

from pathlib import Path

import autoscan_parser
import ui_autoscan_page


def robust_parse_autoscan_file(path):
    path = Path(path)
    if path.suffix.lower() != ".pdf":
        return autoscan_parser.parse_autoscan_file(path)

    try:
        from pypdf import PdfReader
    except Exception as exc:
        raise RuntimeError("Suportul PDF necesită pachetul pypdf. Folosește TXT/LOG sau instalează pypdf.") from exc

    reader = PdfReader(str(path))
    pages = []
    for page in reader.pages:
        try:
            txt = page.extract_text(extraction_mode="layout") or ""
        except TypeError:
            txt = page.extract_text() or ""
        pages.append(txt)
    text = "\n".join(pages)
    if not text.strip():
        raise ValueError("PDF-ul nu conține text extractibil. Exportă Auto-Scan-ul din VCDS ca TXT.")
    return autoscan_parser.parse_autoscan_text(text, str(path))


def _reset_autoscan_ui(self):
    if not hasattr(self, "autoscan_table"):
        return
    self.current_autoscan = None
    self.autoscan_plans = []
    self.autoscan_correlation = None
    self.autoscan_table.clearContents()
    self.autoscan_table.setRowCount(0)
    self.autoscan_table.setProperty("rows", [])
    self.autoscan_fault_title.setText("Încarcă Auto-Scan pentru mașina selectată")
    self.autoscan_detail.clear()
    self.autoscan_summary.setText(
        "Mașina a fost schimbată. Auto-Scan-ul anterior a fost șters din sesiune. "
        "Încarcă raportul VCDS pentru vehiculul selectat acum."
    )


def apply(MainWindow):
    # UI functions resolve this global at runtime, so replacing it here fixes PDF parsing
    # without duplicating the whole Auto-Scan page.
    ui_autoscan_page.parse_autoscan_file = robust_parse_autoscan_file

    old_select_vehicle = MainWindow.select_vehicle

    def select_vehicle(self):
        previous = getattr(self, "selected_generation_id", None)
        old_select_vehicle(self)
        current = getattr(self, "selected_generation_id", None)
        # Clear the scan after a successful vehicle selection. Even if the same
        # generation is reopened, this prevents a report from being mistaken for
        # a newly selected vehicle/session.
        if current:
            _reset_autoscan_ui(self)

    MainWindow.select_vehicle = select_vehicle
    MainWindow.reset_autoscan_ui = _reset_autoscan_ui
