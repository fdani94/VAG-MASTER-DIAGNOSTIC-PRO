from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V2 = Path(__file__).resolve().parent
for p in (ROOT, V2):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import main_v2


def apply_all_patches():
    from v2_diagnostic_patch import apply as p1
    from v2_ui_runtime_patch import apply as p2
    from v2_master_ui_patch import apply as p3
    from v2_visual_fix import apply as p4
    from v2_redesign_patch import apply as p5
    from v2_responsive_windows_patch import apply as p6
    from v2_functional_windows_patch import apply as p7
    from v2_pdf_fix_patch import apply as p8
    from v2_integrated_navigation_patch import apply as p9
    p1(); p2(); p3(); p4(); p5(); p6(); p7(); p8(); p9()


def find_first_vehicle(win, app):
    for bi in range(1, win.brand_combo.count()):
        win.brand_combo.setCurrentIndex(bi); app.processEvents()
        for mi in range(1, win.model_combo.count()):
            win.model_combo.setCurrentIndex(mi); app.processEvents()
            if win.gen_combo.count() > 1:
                win.gen_combo.setCurrentIndex(1); app.processEvents()
                return True
    return False


def find_generation_for_procedure(win, page, app):
    rows = win.con.execute("SELECT DISTINCT generation_id FROM vehicle_procedures ORDER BY generation_id LIMIT 1200").fetchall()
    for row in rows:
        gid = row["generation_id"]
        win.selected_generation_id = gid
        page.search.clear()
        win._load_procedures(page); app.processEvents()
        if page.table.rowCount() > 0 and page.detail.toPlainText().strip():
            return gid
    return None


def find_generation_with_modules(win, app):
    rows = win.con.execute("SELECT DISTINCT generation_id FROM generation_modules ORDER BY generation_id LIMIT 800").fetchall()
    if not rows:
        rows = win.con.execute("SELECT id AS generation_id FROM generations ORDER BY id LIMIT 800").fetchall()
    for row in rows:
        gid = row["generation_id"]
        win.selected_generation_id = gid
        win._load_modules(); app.processEvents()
        if win.module_table.rowCount() > 0:
            return gid
    return None


def create_sample_autoscans():
    text = (
        "VIN: WVWZZZ1KZ6W000001\n"
        "Address 01: Engine\n"
        "1 Fault Found:\n"
        "000665 - Boost Pressure Regulation\n"
        "P0299 - 000 - Control Range Not Reached - Intermittent\n"
        "Fault Frequency: 3\n"
        "Mileage: 188000 km\n"
    )
    txt_path = ROOT / "sample_vcds_autoscan_final.txt"
    log_path = ROOT / "sample_vcds_autoscan_final.log"
    input_pdf = ROOT / "sample_vcds_autoscan_final.pdf"
    txt_path.write_text(text, encoding="utf-8")
    log_path.write_text(text, encoding="utf-8")

    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    c = canvas.Canvas(str(input_pdf), pagesize=A4)
    c.setFont("Helvetica", 10)
    y = A4[1] - 45
    for line in text.splitlines():
        c.drawString(45, y, line)
        y -= 15
    c.save()
    return txt_path, log_path, input_pdf


def validate_output_pdf(pdf_path):
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    assert len(reader.pages) >= 1
    extracted = "\n".join((page.extract_text() or "") for page in reader.pages)
    for token in ("Raport Auto-Scan VCDS", "P0299", "Vehicul", "Diagnostic", "Notă tehnică"):
        assert token in extracted, f"PDF text missing token: {token}"
    assert "□" not in extracted, "PDF contains replacement-square characters"
    assert len(extracted) > 500, "PDF text extraction unexpectedly short"

    font_ok = False
    for page in reader.pages:
        resources = page.get("/Resources") or {}
        fonts = resources.get("/Font") or {}
        try:
            font_items = fonts.get_object().items()
        except Exception:
            font_items = []
        for _, ref in font_items:
            try:
                font = ref.get_object()
                subtype = str(font.get("/Subtype") or "")
                if subtype in ("/TrueType", "/Type0"):
                    font_ok = True
                    break
            except Exception:
                pass
        if font_ok:
            break
    assert font_ok, "PDF has no TrueType/Type0 Unicode font resource"
    return len(reader.pages), len(extracted)


def main():
    main_v2.prepare_database()
    apply_all_patches()

    from PySide6.QtGui import QFont, QFontDatabase
    from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton
    import ui_v2
    import v2_pdf_fix_patch as pdf_patch
    import v2_functional_windows_patch as fp
    from autoscan_parser import parse_autoscan_file
    from ui_v2 import MainWindowV2

    app = QApplication([])
    for font_path in (Path("C:/Windows/Fonts/segoeui.ttf"), Path("C:/Windows/Fonts/arial.ttf")):
        if font_path.exists():
            QFontDatabase.addApplicationFont(str(font_path))
            break
    app.setFont(QFont("Segoe UI", 10))
    QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
    QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
    QMessageBox.critical = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)

    win = MainWindowV2(); win.show(); app.processEvents()

    # Critical regression test: dashboard + eight functions must be integrated
    # in ONE QStackedWidget. No secondary workspace QMainWindow is allowed.
    assert win.stack.count() == 9, f"integrated stack={win.stack.count()}, expected 9"
    assert len(win._workspace_pages) == 8
    assert not win._workspace_windows, "Separate workspace windows still exist"
    assert win.minimumWidth() <= 800 and win.minimumHeight() <= 600

    counts = {
        "dtcs": win.con.execute("SELECT COUNT(*) FROM dtcs").fetchone()[0],
        "procedures": win.con.execute("SELECT COUNT(*) FROM vehicle_procedures").fetchone()[0],
        "modules": win.con.execute("SELECT COUNT(*) FROM modules").fetchone()[0],
        "brands": win.con.execute("SELECT COUNT(*) FROM brands").fetchone()[0],
        "models": win.con.execute("SELECT COUNT(*) FROM models").fetchone()[0],
    }
    assert counts["dtcs"] >= 50000, counts
    assert counts["procedures"] > 0 and counts["modules"] > 0 and counts["brands"] > 0 and counts["models"] > 0, counts

    sizes = [(800, 600, 2, 2), (1024, 700, 2, 2), (1366, 768, 3, 4), (1600, 900, 4, 4)]
    for width, height, card_cols, stat_cols in sizes:
        win.resize(width, height); app.processEvents()
        win.show_dashboard(); app.processEvents()
        win._responsive_dashboard.reflow(width - 44); app.processEvents()
        assert int(win._responsive_dashboard.property("responsiveColumns")) == card_cols
        assert int(win._responsive_dashboard.property("responsiveStatColumns")) == stat_cols
        shot = win.grab()
        assert shot.width() > 0 and shot.height() > 0
        assert shot.save(str(ROOT / f"v2_final_{width}x{height}.png"), "PNG")

    assert find_first_vehicle(win, app), "No selectable vehicle"
    confirm = next(b for b in win.findChildren(QPushButton) if b.text() == "CONFIRMĂ VEHICULUL")
    confirm.click(); app.processEvents()
    assert win.selected_generation_id is not None
    original_gid = win.selected_generation_id

    # Click every real dashboard card. Each must change the current widget in
    # the main stack, expose Back, and never open another KID workspace window.
    cards = win.findChildren(ui_v2.FeatureCard)
    assert len(cards) == 8
    opened = set()
    for card in cards:
        win.show_dashboard(); app.processEvents()
        btn = next(b for b in card.findChildren(QPushButton) if b.objectName() == "cardButton")
        btn.click(); app.processEvents()
        idx = win._active_workspace_index
        assert idx in range(1, 9), f"Card did not navigate in-app: {idx}"
        page = win._workspace_pages[idx]
        assert win.stack.currentWidget() is page
        assert page.isVisible()
        assert not win._workspace_windows
        visible_secondary = [
            w for w in QApplication.topLevelWidgets()
            if w is not win and w.isVisible() and w.windowTitle().startswith("KID Diagnostic V2 •")
        ]
        assert not visible_secondary, f"Secondary blank window regression: {visible_secondary}"

        # Save visual evidence of the actual integrated workspace.
        shot = win.grab()
        assert shot.save(str(ROOT / f"v2_final_workspace_{idx}.png"), "PNG")

        back = next(
            (b for b in page.findChildren(QPushButton)
             if b.objectName() == "backButton" or "Dashboard" in b.text()),
            None,
        )
        assert back is not None, f"Workspace {idx} missing Back"
        assert "Înapoi" in back.text(), f"Workspace {idx} Back label={back.text()}"
        back.click(); app.processEvents()
        assert win.stack.currentIndex() == 0
        assert win._active_workspace_index == 0
        opened.add(idx)
    assert opened == set(range(1, 9)), opened

    txt_path, log_path, input_pdf = create_sample_autoscans()
    for sample in (txt_path, log_path, input_pdf):
        parsed = parse_autoscan_file(sample)
        codes = {(f.code or f.vag_code or "").upper() for f in parsed.faults}
        assert "P0299" in codes, f"P0299 missing when parsing {sample.name}: {codes}"

    win.selected_generation_id = original_gid
    output_pdf = ROOT / "KID_Diagnostic_FINAL_TEST.pdf"
    fp.QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: (str(input_pdf), "PDF (*.pdf)"))
    pdf_patch.QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (str(output_pdf), "PDF (*.pdf)"))

    win.open_page(1); app.processEvents()
    auto_page = win._workspace_pages[1]
    assert win.stack.currentWidget() is auto_page
    load_btn = next(b for b in auto_page.findChildren(QPushButton) if b.text().startswith("Încarcă Auto-Scan"))
    load_btn.click(); app.processEvents()
    assert win.current_autoscan is not None
    assert len(win.current_autoscan.faults) >= 1
    assert any((f.code or f.vag_code or "").upper() == "P0299" for f in win.current_autoscan.faults)
    assert len(win.autoscan_plans) >= 1
    assert win.autoscan_table.rowCount() >= 1
    assert win.autoscan_detail.toPlainText().strip()
    plan_btn = next(b for b in auto_page.findChildren(QPushButton) if b.text().startswith("Plan diagnostic"))
    plan_btn.click(); app.processEvents()
    assert win.autoscan_detail.toPlainText().strip()
    pdf_btn = next(b for b in auto_page.findChildren(QPushButton) if "raport PDF" in b.text())
    pdf_btn.click(); app.processEvents()
    assert output_pdf.exists() and output_pdf.stat().st_size > 5000
    pdf_pages, pdf_text_chars = validate_output_pdf(output_pdf)
    assert win.grab().save(str(ROOT / "v2_final_workspace_1_loaded.png"), "PNG")
    win.show_dashboard(); app.processEvents()

    win.open_page(2); app.processEvents()
    assert win.stack.currentWidget() is win._workspace_pages[2]
    assert win.dtc_table.rowCount() > 0
    assert win.dtc_detail.toPlainText().strip()
    win.dtc_search.setText("P0299"); app.processEvents()
    assert win.dtc_table.rowCount() > 0
    assert "P0299" in win.dtc_table.item(0, 0).text().upper()
    assert len(win.dtc_detail.toPlainText().strip()) > 40
    win.show_dashboard(); app.processEvents()

    procedure_gids = {}
    for idx in (3, 4, 5):
        page = win._workspace_pages[idx]
        gid = find_generation_for_procedure(win, page, app)
        assert gid is not None, f"No data for procedure workspace {idx}"
        procedure_gids[idx] = gid
        win.selected_generation_id = gid
        win.open_page(idx); app.processEvents()
        assert win.stack.currentWidget() is page
        assert page.table.rowCount() > 0
        assert page.detail.toPlainText().strip()
        win.show_dashboard(); app.processEvents()

    win.open_page(6); app.processEvents()
    assert win.stack.currentWidget() is win._workspace_pages[6]
    assert win.live_table.rowCount() > 0
    win.live_search.setText("EGR"); app.processEvents()
    win.live_search.clear(); app.processEvents()
    assert win.live_table.rowCount() > 0
    win.show_dashboard(); app.processEvents()

    module_gid = find_generation_with_modules(win, app)
    assert module_gid is not None
    win.selected_generation_id = module_gid
    win.open_page(7); app.processEvents()
    assert win.stack.currentWidget() is win._workspace_pages[7]
    assert win.module_table.rowCount() > 0
    assert "Auto-Scan" in win.module_table.toolTip()
    win.show_dashboard(); app.processEvents()

    win.selected_generation_id = original_gid
    win.open_page(8); app.processEvents()
    report_page = win._workspace_pages[8]
    assert win.stack.currentWidget() is report_page
    report_btn = next(b for b in report_page.findChildren(QPushButton) if "Generează" in b.text())
    report_btn.click(); app.processEvents()
    assert output_pdf.exists() and output_pdf.stat().st_size > 5000
    validate_output_pdf(output_pdf)
    win.show_dashboard(); app.processEvents()

    # Final Back verification from a real populated DTC page.
    win.selected_generation_id = original_gid
    win.open_page(2); app.processEvents()
    page = win._workspace_pages[2]
    back = next(b for b in page.findChildren(QPushButton) if b.objectName() == "backButton")
    back.click(); app.processEvents()
    assert win.stack.currentIndex() == 0 and win._active_workspace_index == 0

    print(
        "FINAL INTEGRATED AUDIT OK",
        f"workspaces={sorted(opened)}",
        f"stack={win.stack.count()}",
        f"secondary_windows={len(win._workspace_windows)}",
        f"counts={counts}",
        f"autoscan_faults={len(win.current_autoscan.faults)}",
        f"pdf_bytes={output_pdf.stat().st_size}",
        f"pdf_pages={pdf_pages}",
        f"pdf_text_chars={pdf_text_chars}",
        f"procedure_gids={procedure_gids}",
        f"module_gid={module_gid}",
    )

    win.close(); app.quit()


if __name__ == "__main__":
    main()