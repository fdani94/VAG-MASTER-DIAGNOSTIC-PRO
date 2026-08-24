from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V2 = Path(__file__).resolve().parent
for path in (ROOT, V2):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import main_v2


def _select_vehicle(win, app):
    for brand_index in range(1, win.brand_combo.count()):
        win.brand_combo.setCurrentIndex(brand_index)
        app.processEvents()
        for model_index in range(1, win.model_combo.count()):
            win.model_combo.setCurrentIndex(model_index)
            app.processEvents()
            for gen_index in range(1, win.gen_combo.count()):
                win.gen_combo.setCurrentIndex(gen_index)
                app.processEvents()
                for year_index in range(win.year_combo.count()):
                    win.year_combo.setCurrentIndex(year_index)
                    app.processEvents()
                    if win.engine_combo.count() <= 1:
                        continue
                    win.engine_combo.setCurrentIndex(1)
                    app.processEvents()
                    if win.engine_combo.currentData() is None:
                        continue
                    win._select_vehicle()
                    app.processEvents()
                    if win.selected_generation_id and win.selected_year and win.selected_engine_id:
                        return
    raise AssertionError("No complete vehicle selection found")


def main() -> int:
    main_v2.prepare_database()
    main_v2.apply_v2_patches()

    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QFrame, QMessageBox, QPushButton, QSplitter
    import ui_v2

    app = QApplication.instance() or QApplication([])
    QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
    QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
    QMessageBox.critical = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)

    win = ui_v2.MainWindowV2()
    win.resize(1366, 768)
    win.show()
    app.processEvents()
    _select_vehicle(win, app)

    assert "2.2.2" in win.windowTitle(), win.windowTitle()
    assert getattr(win, "_kid_layout_breathing_applied", False)

    strips = getattr(win, "_vehicle_context_strips", {})
    assert len(strips) == 8
    assert all(strip.maximumHeight() == 0 for strip in strips.values())
    assert "Volkswagen" in win.vehicle_badge.text() or win.vehicle_badge.text().strip()

    for index in range(1, 9):
        win.open_page(index)
        app.processEvents()
        page = win._workspace_pages[index]
        assert page.property("kidBreathingLayout") == "2.2.2"
        margins = page.layout().contentsMargins()
        assert margins.left() >= 18 and margins.right() >= 18

        if index <= 7:
            table = None
            if index == 1:
                table = win.autoscan_table
            elif index == 2:
                table = win.dtc_table
            elif index in (3, 4, 5):
                table = page.table
            elif index == 6:
                table = win.live_table
            elif index == 7:
                table = win.module_table
            if table is not None:
                assert table.verticalHeader().defaultSectionSize() >= 36
                assert table.horizontalHeader().minimumHeight() >= 38

        if index in range(1, 6):
            splitter = page.findChild(QSplitter, f"kidWorkspaceSplitter{index}")
            assert splitter is not None
            assert splitter.orientation() == Qt.Vertical, (index, splitter.orientation())
            assert splitter.property("kidResponsiveOrientation") == "vertical"
            assert splitter.minimumHeight() >= 260
            controls = page.findChild(QFrame, f"kidViewControls{index}")
            assert controls is not None
            detail_button = page.findChild(QPushButton, f"kidViewDetail{index}")
            both_button = page.findChild(QPushButton, f"kidViewBoth{index}")
            assert detail_button is not None and both_button is not None
            detail_button.click(); app.processEvents()
            assert not splitter.widget(0).isVisible()
            assert splitter.widget(1).isVisible()
            both_button.click(); app.processEvents()
            assert splitter.widget(0).isVisible() and splitter.widget(1).isVisible()

    win.resize(1600, 900)
    app.processEvents()
    for index in range(1, 6):
        win.open_page(index)
        app.processEvents()
        splitter = win._workspace_pages[index].findChild(QSplitter, f"kidWorkspaceSplitter{index}")
        assert splitter.orientation() == Qt.Horizontal, (index, splitter.orientation())
        assert splitter.property("kidResponsiveOrientation") == "horizontal"

    win.open_page(3)
    app.processEvents()
    coding = win._workspace_pages[3]
    assert coding.table.rowCount() > 0
    assert coding.detail.toPlainText().strip()
    assert coding.detail.font().pointSize() >= 9 or coding.detail.document().documentMargin() >= 12

    print(
        "V2.2.2 LAYOUT BREATHING AUDIT OK",
        f"vehicle={win.vehicle_badge.text()}",
        f"coding_rows={coding.table.rowCount()}",
        "small=vertical",
        "large=horizontal",
        "focus_modes=ok",
        "row_height=36",
    )
    win.close()
    app.processEvents()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
