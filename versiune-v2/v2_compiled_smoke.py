"""Smoke test executed from the packaged Windows EXE.

It targets the regression seen on a real Windows desktop: feature cards opened
secondary blank windows after PyInstaller widget reparenting. V2.2.0 also
requires a complete vehicle context (generation + year + engine) before any
vehicle-specific workspace can be trusted.
"""
from __future__ import annotations

from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton


def _select_real_vehicle(win, app):
    """Select the first catalog vehicle that has a real engine entry."""
    for brand_index in range(1, win.brand_combo.count()):
        win.brand_combo.setCurrentIndex(brand_index)
        app.processEvents()
        for model_index in range(1, win.model_combo.count()):
            win.model_combo.setCurrentIndex(model_index)
            app.processEvents()
            for generation_index in range(1, win.gen_combo.count()):
                win.gen_combo.setCurrentIndex(generation_index)
                app.processEvents()

                if win.year_combo.count() <= 0 or win.engine_combo.count() <= 1:
                    continue

                win.year_combo.setCurrentIndex(0)
                # Index 0 is deliberately "Nespecificat" in V2.2.0.
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

    assert "2.2.0" in win.windowTitle(), win.windowTitle()
    assert "AI Copilot" in win.windowTitle(), win.windowTitle()
    assert win.stack.count() == 9, f"Expected 9 integrated pages, got {win.stack.count()}"
    assert len(getattr(win, "_workspace_pages", {})) == 8
    assert not getattr(win, "_workspace_windows", {}), "Secondary workspace windows must be disabled"
    assert _select_real_vehicle(win, app), "Could not select a complete vehicle (year + engine)"

    assert getattr(win, "selected_year", None) is not None
    assert getattr(win, "selected_engine_id", None) is not None
    strips = getattr(win, "_vehicle_context_strips", {})
    assert len(strips) == 8, f"Expected 8 vehicle context strips, got {len(strips)}"
    assert all(strip._kid_vehicle_state.text() == "SELECTAT" for strip in strips.values())

    opened = []
    for index in range(1, 9):
        page = win._workspace_pages[index]
        win.open_page(index)
        app.processEvents()

        assert win._active_workspace_index == index
        assert win.stack.currentWidget() is page, f"Page {index} is not the current integrated page"
        assert page.isVisible(), f"Page {index} is not visible"
        assert len(page.findChildren(object)) > 5, f"Page {index} appears empty"
        assert strips[index]._kid_vehicle_state.text() == "SELECTAT"

        # Auto-Scan/DTC/procedure/live/module/report pages must expose their real
        # controls, not an empty top-level shell.
        if index == 1:
            assert any("Auto-Scan" in b.text() for b in page.findChildren(QPushButton))
        elif index == 2:
            assert getattr(win, "dtc_table", None) is not None
            assert win.dtc_table.rowCount() > 0
        elif index in (3, 4, 5):
            assert hasattr(page, "table") and hasattr(page, "detail")
            if index == 3:
                assert page.table.columnCount() == 6
                assert page.table.horizontalHeaderItem(0).text() == "Status pe mașină"
        elif index == 6:
            assert getattr(win, "live_table", None) is not None
        elif index == 7:
            assert getattr(win, "module_table", None) is not None
            assert win.module_table.rowCount() > 0
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

    visible_secondary = [
        w for w in QApplication.topLevelWidgets()
        if w is not win and w.isVisible() and w.windowTitle().startswith("KID Diagnostic V2 •")
    ]
    assert not visible_secondary, f"Unexpected secondary workspaces: {visible_secondary}"

    print(
        "COMPILED V2.2.0 VEHICLE-FIRST NAVIGATION OK",
        opened,
        "stack=", win.stack.count(),
        "year=", win.selected_year,
        "engine_id=", win.selected_engine_id,
        "vehicle_strips=", len(strips),
    )
    win.close()
    app.processEvents()
    return 0
