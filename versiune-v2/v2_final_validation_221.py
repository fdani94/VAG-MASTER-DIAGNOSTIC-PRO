from __future__ import annotations

import os
import re
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
V2 = Path(__file__).resolve().parent
for path in (ROOT, V2):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import main_v2


SCAN = """VCDS -- Windows Based VAG/VAS Emulator
VCDS Version: 25.3.1.0
Data version: 20260301 DS365.0
VIN: WVWZZZAUZFW000001   License Plate:
Mileage: 151000km
Chassis Type: {chassis}

-------------------------------------------------------------------------------
Address 09: Cent. Elect. (J519)       Labels: None
   Part No SW: 5Q0 937 084 AA    HW: 5Q0 937 084
   Component: BCM MQBAB H25 0253
   Coding: 001122334455
   ASAM Dataset: EV_BCMMQB 015001
No fault code found.

-------------------------------------------------------------------------------
Address 01: Engine (J623)       Labels: None
   Part No SW: 04L 906 056 AB    HW: 04L 907 445
   Component: R4 2.0l TDI H25 9978
   Coding: 0119001203241D082000
   ASAM Dataset: EV_ECM20TDI03004L906056AB 004006
1 Fault Found:
000665 - Boost Pressure Regulation
          P0299 00 [101] - Control Range Not Reached - Intermittent
             Freeze Frame:
                    Fault Status: 00000001
                    Fault Frequency: 2
                    Mileage: 151000 km
"""


def choose(combo, needle):
    for i in range(combo.count()):
        if needle.lower() in combo.itemText(i).lower():
            combo.setCurrentIndex(i)
            return True
    return False


def main():
    main_v2.prepare_database()
    main_v2.apply_v2_patches()

    from PySide6.QtWidgets import QApplication, QMessageBox
    import ui_v2
    import v2_functional_windows_patch as functional
    import v2_pdf_fix_patch as pdf_fix
    from v2_vehicle_first_patch import selected_vehicle_context
    from v2_vehicle_precision_patch import PRECISION_VERSION
    from pypdf import PdfReader

    app = QApplication.instance() or QApplication([])
    QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
    QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
    QMessageBox.critical = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)

    win = ui_v2.MainWindowV2()
    win.resize(1280, 800)
    win.show()
    app.processEvents()

    assert PRECISION_VERSION == "2.2.1"
    assert "2.2.1" in win.windowTitle(), win.windowTitle()
    assert "AI Copilot" in win.windowTitle(), win.windowTitle()
    assert win.stack.count() == 9
    assert len(getattr(win, "_workspace_pages", {})) == 8
    assert not getattr(win, "_workspace_windows", {})
    assert getattr(win.__class__, "_kid_vehicle_precision_applied", False)
    assert getattr(win.__class__, "_kid_vehicle_scan_sync_applied", False)
    assert getattr(win.__class__, "_kid_v2_ai_hardening_applied", False)

    assert choose(win.brand_combo, "Volkswagen")
    app.processEvents()
    assert choose(win.model_combo, "Golf")
    app.processEvents()
    assert choose(win.gen_combo, "VII 5G/AU")
    app.processEvents()
    assert choose(win.year_combo, "2015")
    app.processEvents()
    assert win.engine_combo.count() > 1
    win.engine_combo.setCurrentIndex(1)
    app.processEvents()
    assert win.engine_combo.currentData() is not None
    win._select_vehicle()
    app.processEvents()

    ctx = selected_vehicle_context(win)
    assert ctx["generation_id"]
    assert ctx["year"] == 2015
    assert ctx["engine_id"]
    valid_engine = win.con.execute(
        """SELECT 1 FROM vehicle_engines WHERE generation_id=? AND engine_id=?
           AND (year_from IS NULL OR year_from<=?) AND (year_to IS NULL OR year_to>=?) LIMIT 1""",
        (ctx["generation_id"], ctx["engine_id"], ctx["year"], ctx["year"]),
    ).fetchone()
    assert valid_engine
    assert len(win._vehicle_context_strips) == 8

    coding = win._workspace_pages[3]
    win.open_page(3)
    app.processEvents()
    assert coding.table.columnCount() == 7
    assert coding.table.horizontalHeaderItem(0).text() == "Status"
    assert coding.table.horizontalHeaderItem(4).text() == "Motor / an"
    assert coding.table.rowCount() > 0
    assert "PRECIZIE PENTRU SELECȚIA ACTUALĂ" in coding.detail.toPlainText()

    win.open_page(2)
    app.processEvents()
    win.dtc_search.setText("P0299")
    app.processEvents()
    assert win.dtc_table.rowCount() > 0

    for index in (4, 5):
        win.open_page(index)
        app.processEvents()
        page = win._workspace_pages[index]
        assert hasattr(page, "table") and hasattr(page, "detail")

    win.open_page(6)
    app.processEvents()
    assert win.live_table.rowCount() > 0

    win.open_page(7)
    app.processEvents()
    assert win.module_table.columnCount() == 6
    if win.module_table.rowCount():
        allowed = {"MAPAT GENERAȚIE", "CONFIRMAT PE MAȘINĂ", "CITIT AUTOSCAN • NEMAPAT LOCAL"}
        statuses = {win.module_table.item(i, 0).text() for i in range(win.module_table.rowCount())}
        assert statuses.issubset(allowed), statuses
    else:
        assert "Auto-Scan" in win.module_table.toolTip()

    codes = re.findall(r"[A-Z0-9]{2,5}", str(ctx.get("chassis") or "").upper())
    assert codes, ctx
    sample = ROOT / "sample_v2_221_full_stack.txt"
    sample.write_text(SCAN.format(chassis=codes[0]), encoding="utf-8")
    output_pdf = ROOT / "KID_Diagnostic_V2_221_FINAL_TEST.pdf"

    functional.QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: (str(sample), "Text (*.txt)"))
    pdf_fix.QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (str(output_pdf), "PDF (*.pdf)"))

    win.open_page(1)
    app.processEvents()
    win._load_autoscan()
    app.processEvents()
    assert win.current_autoscan is not None
    assert win.autoscan_vehicle_binding_ok, win.autoscan_vehicle_match
    assert win.autoscan_vehicle_match["status"] == "matched"
    assert any((f.code or f.vag_code or "").upper() == "P0299" for f in win.current_autoscan.faults)
    assert "VEHICUL CONFIRMAT CHASSIS" in win.autoscan_summary.text()

    win.open_page(3)
    app.processEvents()
    statuses = [coding.table.item(i, 0).text() for i in range(coding.table.rowCount())]
    assert any(s in ("MODUL GĂSIT AUTOSCAN", "CONTROLLER CONFIRMAT") for s in statuses), statuses
    confirmed_index = next(i for i, s in enumerate(statuses) if s in ("MODUL GĂSIT AUTOSCAN", "CONTROLLER CONFIRMAT"))
    coding.table.selectRow(confirmed_index)
    win._show_procedure(coding)
    app.processEvents()
    detail = coding.detail.toPlainText()
    assert "CODING ORIGINAL DIN AUTO-SCAN" in detail
    assert "PRECIZIE PENTRU SELECȚIA ACTUALĂ" in detail

    win.open_page(7)
    app.processEvents()
    module_statuses = [win.module_table.item(i, 0).text() for i in range(win.module_table.rowCount())]
    assert any(s in ("CONFIRMAT PE MAȘINĂ", "CITIT AUTOSCAN • NEMAPAT LOCAL") for s in module_statuses)

    win.open_page(1)
    app.processEvents()
    win._export_pdf()
    app.processEvents()
    assert output_pdf.exists() and output_pdf.stat().st_size > 5000
    reader = PdfReader(str(output_pdf))
    pdf_text = "\n".join((page.extract_text() or "") for page in reader.pages)
    for token in ("P0299", "Coding ORIGINAL", "AI Copilot"):
        assert token in pdf_text, token

    for width, height in ((800, 600), (1600, 900)):
        win.resize(width, height)
        win.show_dashboard()
        app.processEvents()
        assert win.grab().save(str(ROOT / f"v2_221_final_{width}x{height}.png"), "PNG")

    counts = {
        "dtcs": win.con.execute("SELECT COUNT(*) FROM dtcs").fetchone()[0],
        "procedures": win.con.execute("SELECT COUNT(*) FROM vehicle_procedures").fetchone()[0],
        "modules": win.con.execute("SELECT COUNT(*) FROM modules").fetchone()[0],
    }
    assert counts["dtcs"] >= 50000
    assert counts["procedures"] > 0
    assert counts["modules"] > 0

    print(
        "V2.2.1 AUTHORITATIVE FULL STACK AUDIT OK",
        f"vehicle={ctx['brand']} {ctx['model']} {ctx['generation']} {ctx['year']} {ctx['engine_code']}",
        f"coding_rows={coding.table.rowCount()}",
        f"module_rows={win.module_table.rowCount()}",
        f"faults={len(win.current_autoscan.faults)}",
        f"pdf_pages={len(reader.pages)}",
        f"pdf_bytes={output_pdf.stat().st_size}",
        f"counts={counts}",
    )

    win.close()
    app.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
