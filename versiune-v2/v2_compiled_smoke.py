"""Smoke test executed from the packaged Windows EXE.

It targets packaged navigation plus the V2.2.2 precision and layout invariants:
a complete year-valid engine selection, explicit coding columns, responsive
splitters, focus controls, and modules that are never overclaimed.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton, QSplitter


def _select_real_vehicle(win, app):
    """Select the first catalog vehicle/year that has a real valid engine entry."""
    for brand_index in range(1, win.brand_combo.count()):
        win.brand_combo.setCurrentIndex(brand_index)
        app.processEvents()
        for model_index in range(1, win.model_combo.count()):
            win.model_combo.setCurrentIndex(model_index)
            app.processEvents()
            for generation_index in range(1, win.gen_combo.count()):
                win.gen_combo.setCurrentIndex(generation_index)
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

                    button = next(
                        (b for b in win.findChildren(QPushButton) if b.text() == "CONFIRMĂ VEHICULUL"),
                        None,
                    )
                    if button is None:
                        continue
                    button.click()
                    app.processEvents()
                    if (
                        win.selected_generation_id is not None
                        and getattr(win, "selected_year", None) is not None
                        and getattr(win, "selected_engine_id", None) is not None
                    ):
                        return True
    return False


def run_compiled_smoke() -> int:
    import ui_v2

    app = QApplication.instance() or QApplication([])
    QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
    QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
    QMessageBox.critical = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)

    win = ui_v2.MainWindowV2()
    win.resize(1200, 760)
    win.show()
    app.processEvents()

    assert "2.2.2" in win.windowTitle(), win.windowTitle()
    assert "AI Copilot" in win.windowTitle(), win.windowTitle()
    assert getattr(win, "_kid_layout_breathing_applied", False)
    assert win.stack.count() == 9, f"Expected 9 integrated pages, got {win.stack.count()}"
    assert len(getattr(win, "_workspace_pages", {})) == 8
    assert not getattr(win, "_workspace_windows", {}), "Secondary workspace windows must be disabled"
    assert _select_real_vehicle(win, app), "Could not select a complete vehicle (year + valid engine)"

    assert getattr(win, "selected_year", None) is not None
    assert getattr(win, "selected_engine_id", None) is not None
    valid = win.con.execute(
        """SELECT 1 FROM vehicle_engines WHERE generation_id=? AND engine_id=?
           AND (year_from IS NULL OR year_from<=?) AND (year_to IS NULL OR year_to>=?) LIMIT 1""",
        (win.selected_generation_id, win.selected_engine_id, win.selected_year, win.selected_year),
    ).fetchone()
    assert valid, "Selected engine is not valid for the selected year"

    strips = getattr(win, "_vehicle_context_strips", {})
    assert len(strips) == 8, f"Expected 8 vehicle context strips, got {len(strips)}"
    assert all(strip._kid_vehicle_state.text() == "SELECTAT" for strip in strips.values())
    assert all(strip.maximumHeight() == 0 for strip in strips.values())

    opened = []
    for index in range(1, 9):
        page = win._workspace_pages[index]
        win.open_page(index)
        app.processEvents()

        assert win._active_workspace_index == index
        assert win.stack.currentWidget() is page, f"Page {index} is not the current integrated page"
        assert page.isVisible(), f"Page {index} is not visible"
        assert page.property("kidBreathingLayout") == "2.2.2"
        assert len(page.findChildren(object)) > 5, f"Page {index} appears empty"
        assert strips[index]._kid_vehicle_state.text() == "SELECTAT"

        if index in range(1, 6):
            splitter = page.findChild(QSplitter, f"kidWorkspaceSplitter{index}")
            assert splitter is not None
            assert splitter.orientation() == Qt.Vertical, (index, splitter.orientation())
            assert splitter.minimumHeight() >= 260
            assert page.findChild(QPushButton, f"kidViewDetail{index}") is not None
            assert page.findChild(QPushButton, f"kidViewBoth{index}") is not None

        if index == 1:
            assert any("Auto-Scan" in b.text() for b in page.findChildren(QPushButton))
        elif index == 2:
            assert getattr(win, "dtc_table", None) is not None
            assert win.dtc_table.rowCount() > 0
            assert win.dtc_table.verticalHeader().defaultSectionSize() >= 36
        elif index in (3, 4, 5):
            assert hasattr(page, "table") and hasattr(page, "detail")
            assert page.table.verticalHeader().defaultSectionSize() >= 36
            if index == 3:
                assert page.table.columnCount() == 7
                assert page.table.horizontalHeaderItem(0).text() == "Status"
                assert page.table.horizontalHeaderItem(4).text() == "Motor / an"
        elif index == 6:
            assert getattr(win, "live_table", None) is not None
        elif index == 7:
            assert getattr(win, "module_table", None) is not None
            assert win.module_table.columnCount() == 6
            if win.module_table.rowCount():
                allowed = {"MAPAT GENERAȚIE", "CONFIRMAT PE MAȘINĂ", "CITIT AUTOSCAN • NEMAPAT LOCAL"}
                statuses = {win.module_table.item(i, 0).text() for i in range(win.module_table.rowCount())}
                assert statuses.issubset(allowed), statuses
            else:
                assert "Auto-Scan" in win.module_table.toolTip()
        elif index == 8:
            assert any("Generează" in b.text() for b in page.findChildren(QPushButton))

        back = next(
            (b for b in page.findChildren(QPushButton)
             if b.objectName() == "backButton" or "Dashboard" in b.text()),
            None,
        )
        assert back is not None, f"Page {index} has no Back button"
        assert "Înapoi" in back.text(), f"Page {index} Back label is not explicit"
        back.click()
        app.processEvents()
        assert win.stack.currentIndex() == 0
        assert win._active_workspace_index == 0
        opened.append(index)

    win.resize(1600, 900)
    app.processEvents()
    win.open_page(3)
    app.processEvents()
    coding_split = win._workspace_pages[3].findChild(QSplitter, "kidWorkspaceSplitter3")
    assert coding_split.orientation() == Qt.Horizontal

    visible_secondary = [
        w for w in QApplication.topLevelWidgets()
        if w is not win and w.isVisible() and w.windowTitle().startswith("KID Diagnostic V2 •")
    ]
    assert not visible_secondary, f"Unexpected secondary workspaces: {visible_secondary}"

    print(
        "COMPILED V2.2.2 LAYOUT + VEHICLE PRECISION NAVIGATION OK",
        opened,
        "stack=", win.stack.count(),
        "year=", win.selected_year,
        "engine_id=", win.selected_engine_id,
        "vehicle_strips=", len(strips),
        "small=vertical",
        "large=horizontal",
    )
    win.close()
    app.processEvents()
    return 0
