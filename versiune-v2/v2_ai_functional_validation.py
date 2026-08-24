from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V2 = Path(__file__).resolve().parent
for path in (ROOT, V2):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import main_v2

UDS_SAMPLE = """VCDS -- Windows Based VAG/VAS Emulator
VCDS Version: 25.3.1.0
Data version: 20260301 DS365.0
VIN: WVWZZZ3CZME000001   License Plate:
Mileage: 180000km
Chassis Type: 3C

-------------------------------------------------------------------------------
Address 01: Engine (J623)       Labels: None
   Part No SW: 04L 906 056 AB    HW: 04L 907 445
   Component: R4 2.0l TDI   H25 9978
   Coding: 0119001203241D082000
   ASAM Dataset: EV_ECM20TDI03004L906056AB 004006
   ROD: EV_ECM20TDI03004L906056AB.rod
1 Fault Found:
5188 - Diesel Particle Filter
          P2463 00 [175] - Excessive Soot Accumulation - MIL ON
             Freeze Frame:
                    Fault Status: 00000001
                    Fault Priority: 2
                    Fault Frequency: 1
                    Mileage: 180000 km
Readiness: 0 0 0 0 1
"""


def choose_first_vehicle(win, app):
    """Choose a complete vehicle context: generation + year + a real year-valid engine."""
    for bi in range(1, win.brand_combo.count()):
        win.brand_combo.setCurrentIndex(bi)
        app.processEvents()
        for mi in range(1, win.model_combo.count()):
            win.model_combo.setCurrentIndex(mi)
            app.processEvents()
            for gi in range(1, win.gen_combo.count()):
                win.gen_combo.setCurrentIndex(gi)
                app.processEvents()
                if not win.year_combo.count():
                    continue
                win.year_combo.setCurrentIndex(0)
                app.processEvents()
                if win.engine_combo.count() <= 1:
                    continue
                win.engine_combo.setCurrentIndex(1)
                app.processEvents()
                if win.engine_combo.currentData() is None:
                    continue
                win._select_vehicle()
                app.processEvents()
                return (
                    win.selected_generation_id is not None
                    and getattr(win, "selected_engine_id", None) is not None
                )
    return False


def main():
    main_v2.prepare_database()
    main_v2.apply_v2_patches()

    from PySide6.QtWidgets import QApplication, QMessageBox, QToolBar
    import ui_v2
    import v2_functional_windows_patch as functional
    import v2_pdf_fix_patch as pdf_fix
    from v2_vehicle_first_patch import VEHICLE_FIRST_VERSION, selected_vehicle_context
    from v2_vehicle_precision_patch import PRECISION_VERSION
    from v2_ai_hardening_patch import HARDENING_VERSION
    from pypdf import PdfReader

    db_path = Path(main_v2.appdb.DB_PATH)
    assert db_path.name == "kid_diagnostic_v2.db", db_path
    assert "KID Diagnostic V2" in str(db_path.parent), db_path

    app = QApplication.instance() or QApplication([])
    QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
    QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
    QMessageBox.critical = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)

    win = ui_v2.MainWindowV2()
    win.show()
    app.processEvents()

    main_v2.prepare_database()

    assert hasattr(win, "v2_ai_copilot")
    assert "AI Copilot" in win.windowTitle()
    assert VEHICLE_FIRST_VERSION == "2.2.0"  # vehicle-first component revision
    assert PRECISION_VERSION == "2.2.1"      # application precision release
    assert "2.2.1" in win.windowTitle()
    assert HARDENING_VERSION == "2.1.2"
    toolbar = win.findChild(QToolBar, "kidV2AiToolbar")
    assert toolbar is not None, "AI toolbar missing"

    ai_strips = getattr(win, "v2_ai_strips", {})
    assert set(ai_strips) == set(range(9)), f"AI strips missing: {sorted(set(range(9)) - set(ai_strips))}"
    assert ai_strips[0].isVisible(), "Dashboard AI strip is not visible"

    assert choose_first_vehicle(win, app), "No complete selectable vehicle for AI validation"
    assert getattr(win, "selected_engine_id", None) is not None
    assert len(getattr(win, "_vehicle_context_strips", {})) == 8

    ctx = selected_vehicle_context(win)
    chassis_codes = re.findall(r"[A-Z0-9]{2,5}", str(ctx.get("chassis") or "").upper())
    assert chassis_codes, ctx
    selected_chassis = chassis_codes[0]

    sample = ROOT / "sample_v2_ai_uds.txt"
    sample.write_text(
        UDS_SAMPLE.replace("Chassis Type: 3C", f"Chassis Type: {selected_chassis}"),
        encoding="utf-8",
    )
    output_pdf = ROOT / "KID_Diagnostic_V2_AI_TEST.pdf"

    functional.QFileDialog.getOpenFileName = staticmethod(
        lambda *a, **k: (str(sample), "Text (*.txt)")
    )
    pdf_fix.QFileDialog.getSaveFileName = staticmethod(
        lambda *a, **k: (str(output_pdf), "PDF (*.pdf)")
    )

    win.open_page(1)
    app.processEvents()
    assert ai_strips[1].isVisible(), "Auto-Scan AI strip is not visible"
    assert "AI Copilot" in win.windowTitle()
    win._load_autoscan()
    app.processEvents()

    scan = win.current_autoscan
    assert scan is not None
    assert win.autoscan_vehicle_binding_ok, win.autoscan_vehicle_match
    assert win.autoscan_vehicle_match["status"] == "matched"
    assert getattr(scan, "audit", None), "AI audit missing from loaded scan"
    assert scan.audit["score"] >= 90, scan.audit
    assert scan.audit["verified"], scan.audit
    assert len(scan.faults) == 1
    fault = scan.faults[0]
    assert fault.code == "P2463"
    assert fault.vag_code == "5188"
    assert getattr(fault, "uds_status_byte", "") == "00"
    assert getattr(fault, "uds_bracket", "") == "175"

    module = scan.modules[0]
    assert getattr(module, "part_no_sw", "") == "04L 906 056 AB"
    assert getattr(module, "part_no_hw", "") == "04L 907 445"
    assert module.coding == "0119001203241D082000"
    assert "Audit AI" in win.autoscan_summary.text()
    assert "VEHICUL CONFIRMAT CHASSIS" in win.autoscan_summary.text()
    assert "RAPORT VCDS VERIFICAT AI" in win.v2_verified_report_text
    assert "Coding ORIGINAL: 0119001203241D082000" in win.v2_verified_report_text

    for index in range(2, 9):
        win.open_page(index)
        app.processEvents()
        assert ai_strips[index].isVisible(), f"AI strip not visible on page {index}"
        vehicle_strip = win._vehicle_context_strips[index]
        assert vehicle_strip._kid_vehicle_state.text() == "SELECTAT"
        assert win.vehicle_badge.text() in vehicle_strip._kid_vehicle_label.text()

    win.open_page(1)
    app.processEvents()

    security = win.v2_ai_copilot.ask(
        "Security Access pentru coding Address 01",
        selected_vehicle=win.vehicle_badge.text(),
        scan=scan,
        plans=win.autoscan_plans,
        report_text=win.v2_verified_report_text,
    )
    assert "Security Access - 16" in security
    assert "Nu inventez" in security

    rebuilt = win.v2_ai_copilot.ask(
        "Refă raportul automat și verifică-l",
        selected_vehicle=win.vehicle_badge.text(),
        scan=scan,
        plans=win.autoscan_plans,
        report_text=win.v2_verified_report_text,
    )
    assert "Am refăcut raportul" in rebuilt
    assert "Coding ORIGINAL" in rebuilt

    win.open_v2_ai_copilot()
    app.processEvents()
    assert win.v2_ai_dialog is not None and win.v2_ai_dialog.isVisible()
    assert HARDENING_VERSION in win.v2_ai_dialog.windowTitle()
    win.v2_ai_dialog.close()
    app.processEvents()

    win._export_pdf()
    app.processEvents()
    assert output_pdf.exists() and output_pdf.stat().st_size > 5000

    reader = PdfReader(str(output_pdf))
    text = "\n".join((page.extract_text() or "") for page in reader.pages)
    for token in ("AI Copilot", "Scor citire", "Coding ORIGINAL", "P2463"):
        assert token in text, f"AI PDF missing token: {token}"

    print(
        "V2 AI FUNCTIONAL AUDIT OK",
        f"app_version={PRECISION_VERSION}",
        f"vehicle_first={VEHICLE_FIRST_VERSION}",
        f"ai_hardening={HARDENING_VERSION}",
        f"db={db_path}",
        f"ai_strips={len(ai_strips)}",
        f"vehicle_strips={len(win._vehicle_context_strips)}",
        f"score={scan.audit['score']}",
        f"modules={len(scan.modules)}",
        f"faults={len(scan.faults)}",
        f"pdf_pages={len(reader.pages)}",
        f"pdf_bytes={output_pdf.stat().st_size}",
    )

    win.close()
    app.quit()


if __name__ == "__main__":
    main()
