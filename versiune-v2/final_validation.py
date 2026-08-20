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
    p1(); p2(); p3(); p4(); p5(); p6(); p7()


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
    rows = win.con.execute("SELECT DISTINCT generation_id FROM vehicle_procedures ORDER BY generation_id LIMIT 800").fetchall()
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


def main():
    main_v2.prepare_database()
    apply_all_patches()

    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton
    import ui_v2
    import v2_functional_windows_patch as fp
    from ui_v2 import MainWindowV2

    app = QApplication([])
    app.setFont(QFont("Arial", 10))
    QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
    QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
    QMessageBox.critical = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)

    win = MainWindowV2(); win.show(); app.processEvents()
    assert win.stack.count() == 1, f"dashboard stack={win.stack.count()}"
    assert len(win._workspace_pages) == 8
    assert win.minimumWidth() <= 800 and win.minimumHeight() <= 600

    sizes = [(800, 600, 2, 2), (1024, 700, 2, 2), (1366, 768, 3, 4), (1600, 900, 4, 4)]
    for width, height, card_cols, stat_cols in sizes:
        win.resize(width, height); app.processEvents()
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

    cards = win.findChildren(ui_v2.FeatureCard)
    assert len(cards) == 8
    opened = set()
    for card in cards:
        btn = next(b for b in card.findChildren(QPushButton) if b.objectName() == "cardButton")
        btn.click(); app.processEvents()
        visible = [i for i, w in win._workspace_windows.items() if w.isVisible()]
        assert visible, "Feature card did not open a workspace"
        idx = visible[-1]; opened.add(idx)
        assert win._workspace_windows[idx].centralWidget() is win._workspace_pages[idx]
        win.show_dashboard(); app.processEvents()
    assert opened == set(range(1, 9)), opened

    win.selected_generation_id = original_gid
    sample = ROOT / "sample_vcds_autoscan_final.txt"
    sample.write_text(
        "VIN: WVWZZZ1KZ6W000001\n"
        "Address 01: Engine\n"
        "1 Fault Found:\n"
        "000665 - Boost Pressure Regulation\n"
        "P0299 - 000 - Control Range Not Reached - Intermittent\n"
        "Fault Frequency: 3\n"
        "Mileage: 188000 km\n",
        encoding="utf-8",
    )
    pdf_path = ROOT / "KID_Diagnostic_FINAL_TEST.pdf"
    fp.QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: (str(sample), "Text (*.txt)"))
    fp.QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: (str(pdf_path), "PDF (*.pdf)"))

    win.open_page(1); app.processEvents()
    auto_page = win._workspace_pages[1]
    load_btn = next(b for b in auto_page.findChildren(QPushButton) if b.text().startswith("Încarcă Auto-Scan"))
    load_btn.click(); app.processEvents()
    assert win.current_autoscan is not None
    assert len(win.current_autoscan.faults) >= 1
    assert len(win.autoscan_plans) >= 1
    assert win.autoscan_table.rowCount() >= 1
    assert win.autoscan_detail.toPlainText().strip()
    plan_btn = next(b for b in auto_page.findChildren(QPushButton) if b.text().startswith("Plan diagnostic"))
    plan_btn.click(); app.processEvents()
    assert win.autoscan_detail.toPlainText().strip()
    pdf_btn = next(b for b in auto_page.findChildren(QPushButton) if "raport PDF" in b.text())
    pdf_btn.click(); app.processEvents()
    assert pdf_path.exists() and pdf_path.stat().st_size > 1500
    win.show_dashboard(); app.processEvents()

    win.open_page(2); app.processEvents()
    assert win.dtc_table.rowCount() > 0
    assert win.dtc_detail.toPlainText().strip()
    win.dtc_search.setText("P0299"); app.processEvents()
    assert win.dtc_table.rowCount() > 0
    assert "P0299" in win.dtc_table.item(0, 0).text().upper()
    win.show_dashboard(); app.processEvents()

    procedure_gids = {}
    for idx in (3, 4, 5):
        page = win._workspace_pages[idx]
        gid = find_generation_for_procedure(win, page, app)
        assert gid is not None, f"No data for procedure workspace {idx}"
        procedure_gids[idx] = gid
        win.selected_generation_id = gid
        win.open_page(idx); app.processEvents()
        assert page.table.rowCount() > 0
        assert page.detail.toPlainText().strip()
        win.show_dashboard(); app.processEvents()

    win.open_page(6); app.processEvents()
    assert win.live_table.rowCount() > 0
    win.live_search.setText("EGR"); app.processEvents()
    win.live_search.clear(); app.processEvents()
    assert win.live_table.rowCount() > 0
    win.show_dashboard(); app.processEvents()

    module_gid = find_generation_with_modules(win, app)
    assert module_gid is not None
    win.selected_generation_id = module_gid
    win.open_page(7); app.processEvents()
    assert win.module_table.rowCount() > 0
    assert "Auto-Scan" in win.module_table.toolTip()
    win.show_dashboard(); app.processEvents()

    win.selected_generation_id = original_gid
    win.open_page(8); app.processEvents()
    report_page = win._workspace_pages[8]
    report_btn = next(b for b in report_page.findChildren(QPushButton) if "Generează" in b.text())
    report_btn.click(); app.processEvents()
    assert pdf_path.exists() and pdf_path.stat().st_size > 1500
    win.show_dashboard(); app.processEvents()

    win.selected_generation_id = original_gid
    win.open_page(2); app.processEvents()
    back = next(b for b in win._workspace_windows[2].findChildren(QPushButton) if b.objectName() == "backButton")
    back.click(); app.processEvents()
    assert win.isVisible()

    print(
        "FINAL FUNCTIONAL VALIDATION OK",
        f"workspaces={sorted(opened)}",
        f"autoscan_faults={len(win.current_autoscan.faults)}",
        f"pdf_bytes={pdf_path.stat().st_size}",
        f"procedure_gids={procedure_gids}",
        f"module_gid={module_gid}",
    )

    for w in list(win._workspace_windows.values()):
        w.hide()
    win.close(); app.quit()


if __name__ == "__main__":
    main()
