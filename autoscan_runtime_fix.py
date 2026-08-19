"""Runtime fixes for Auto-Scan.

1) pypdf normal extraction can flatten VCDS PDFs into one long line. We use
   extraction_mode='layout' so Address/DTC blocks remain on separate lines.
2) When the selected vehicle changes, the previous Auto-Scan is cleared.
3) Correlation also reads VCDS VBatt start/end and same-time glow plug clusters.
"""

from pathlib import Path
import re

import autoscan_parser
import autoscan_correlation
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


def correlate_with_scan_context(result, plans):
    corr = autoscan_correlation.correlate(result, plans)
    raw = getattr(result, "raw_text", "") or ""

    # VCDS ends many Auto-Scans with: VBatt start/end: 11.6V/11.6V
    vm = re.search(r"VBatt\s+start/end:\s*([0-9.]+)V\s*/\s*([0-9.]+)V", raw, re.I)
    if vm:
        start_v, end_v = float(vm.group(1)), float(vm.group(2))
        corr["scan_vbatt"] = (start_v, end_v)
        if min(start_v, end_v) < 12.0:
            item = (
                "Tensiune baterie scăzută în timpul Auto-Scan-ului",
                f"VCDS a raportat VBatt {start_v:.1f} V / {end_v:.1f} V. Verifică/încarcă bateria și sistemul de încărcare înainte de a interpreta erorile de management energie sau comunicație."
            )
            if item not in corr["common_causes"]:
                corr["common_causes"].insert(0, item)

    codes = {(getattr(f, "code", "") or getattr(f, "vag_code", "") or "").upper() for f, _ in plans}
    glow = sorted(c for c in codes if c in {"P0671", "P0672", "P0673", "P0674", "P0675", "P0676"})
    if len(glow) >= 3:
        corr["common_causes"].append((
            "Mai multe circuite bujii incandescente raportate împreună",
            "Când 3-4 cilindri raportează simultan defect electric, verifică înainte de a schimba toate bujiile alimentarea comună, modulul/releul de bujii, siguranțele și cablajul comun. Verifică apoi fiecare bujie individual."
        ))

    if "02615" in codes and "02616" in codes:
        corr["common_causes"].append((
            "Blocare + deblocare clapetă rezervor cu defect electric",
            "Ambele sensuri ale actuatorului sunt raportate. Prioritizează mufa, cablajul și actuatorul comun al clapetei rezervorului."
        ))

    return corr


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
    # UI functions resolve these globals at runtime.
    ui_autoscan_page.parse_autoscan_file = robust_parse_autoscan_file
    ui_autoscan_page.correlate = correlate_with_scan_context

    old_select_vehicle = MainWindow.select_vehicle

    def select_vehicle(self):
        old_select_vehicle(self)
        current = getattr(self, "selected_generation_id", None)
        # Always clear after opening/selecting a vehicle so a previous report can
        # never remain attached to a different car/session.
        if current:
            _reset_autoscan_ui(self)

    MainWindow.select_vehicle = select_vehicle
    MainWindow.reset_autoscan_ui = _reset_autoscan_ui
