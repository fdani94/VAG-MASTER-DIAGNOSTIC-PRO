"""Smoke test executed from the packaged Windows EXE.

It targets the regression seen on a real Windows desktop: feature cards opened
secondary blank windows after PyInstaller widget reparenting. The final build
must keep all workspaces inside the main QStackedWidget and Back must return to
the dashboard.
"""
from __future__ import annotations

from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton


def _select_real_vehicle(win, app):
    for brand_index in range(1, win.brand_combo.count()):
        win.brand_combo.setCurrentIndex(brand_index)
        app.processEvents()
        for model_index in range(1, win.model_combo.count()):
            win.model_combo.setCurrentIndex(model_index)
            app.processEvents()
            if win.gen_combo.count() > 1:
                win.gen_combo.setCurrentIndex(1)
                app.processEvents()
                button = next(
                    (b for b in win.findChildren(QPushButton) if b.text() == "CONFIRMĂ VEHICULUL"),
                    None,
                )
                if button is not None:
                    button.click()
                    app.processEvents()
                    return win.selected_generation_id is not None
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

    assert win.stack.count() == 9, f"Expected 9 integrated pages, got {win.stack.count()}"
    assert len(getattr(win, "_workspace_pages", {})) == 8
    assert not getattr(win, "_workspace_windows", {}), "Secondary workspace windows must be disabled"
    assert _select_real_vehicle(win, app), "Could not select a vehicle"

    opened = []
    for index in range(1, 9):
        page = win._workspace_pages[index]
        win.open_page(index)
        app.processEvents()

        assert win._active_workspace_index == index
        assert win.stack.currentWidget() is page, f"Page {index} is not the current integrated page"
        assert page.isVisible(), f"Page {index} is not visible"
        assert len(page.findChildren(object)) > 5, f"Page {index} appears empty"

        # Auto-Scan/DTC/procedure/live/module/report pages must expose their real
        # controls, not an empty top-level shell.
        if index == 1:
            assert any("Auto-Scan" in b.text() for b in page.findChildren(QPushButton))
        elif index == 2:
            assert getattr(win, "dtc_table", None) is not None
            assert win.dtc_table.rowCount() > 0
        elif index in (3, 4, 5):
            assert hasattr(page, "table") and hasattr(page, "detail")
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

    print("COMPILED INTEGRATED NAVIGATION OK", opened, "stack=", win.stack.count())
    win.close()
    app.processEvents()
    return 0
