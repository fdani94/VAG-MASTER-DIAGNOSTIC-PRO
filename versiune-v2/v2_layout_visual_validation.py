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
    for b in range(1, win.brand_combo.count()):
        win.brand_combo.setCurrentIndex(b); app.processEvents()
        for m in range(1, win.model_combo.count()):
            win.model_combo.setCurrentIndex(m); app.processEvents()
            for g in range(1, win.gen_combo.count()):
                win.gen_combo.setCurrentIndex(g); app.processEvents()
                for y in range(win.year_combo.count()):
                    win.year_combo.setCurrentIndex(y); app.processEvents()
                    if win.engine_combo.count() <= 1:
                        continue
                    win.engine_combo.setCurrentIndex(1); app.processEvents()
                    if win.engine_combo.currentData() is None:
                        continue
                    win._select_vehicle(); app.processEvents()
                    if win.selected_generation_id and win.selected_year and win.selected_engine_id:
                        return
    raise AssertionError("Could not select vehicle")


def _native_screen_capture(win, app, index, filename):
    win.show()
    app.processEvents()
    win.open_page(index)
    app.processEvents()
    pix = win.grab()
    assert not pix.isNull()
    assert pix.width() >= 900 and pix.height() >= 620, (pix.width(), pix.height())
    path = ROOT / filename
    assert pix.save(str(path), "PNG")
    return path, pix.width(), pix.height()


def _render_at(win, app, width, height, index, filename):
    # GitHub's hosted Windows desktop is around 1028px wide, so a shown
    # top-level window is clamped by the OS. To audit 1366/FHD layouts without
    # pretending the CI monitor is larger, first activate the requested page,
    # then hide the window, assign the exact logical size and render the Qt
    # widget tree into a pixmap while still using the native Windows QPA/fonts.
    win.show()
    app.processEvents()
    win.open_page(index)
    app.processEvents()
    win.hide()
    app.processEvents()
    win.resize(width, height)
    app.processEvents()

    import v2_layout_breathing_patch as breathing
    if index in range(1, 6):
        breathing._apply_splitter_orientation(win, index)
    app.processEvents()

    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtGui import QColor, QPainter, QPixmap

    assert win.width() == width and win.height() == height, (win.size(), width, height)
    pix = QPixmap(width, height)
    pix.fill(QColor("white"))
    painter = QPainter(pix)
    win.render(painter, QPoint(0, 0))
    painter.end()
    assert not pix.isNull()
    path = ROOT / filename
    assert pix.save(str(path), "PNG")

    splitter = win._workspace_pages[index].findChild(
        __import__("PySide6.QtWidgets", fromlist=["QSplitter"]).QSplitter,
        f"kidWorkspaceSplitter{index}",
    ) if index in range(1, 6) else None
    if splitter is not None:
        expected = Qt.Vertical if width < breathing.RESPONSIVE_BREAKPOINT else Qt.Horizontal
        assert splitter.orientation() == expected, (index, width, splitter.orientation(), expected)
    return path


def main() -> int:
    main_v2.prepare_database()
    main_v2.apply_v2_patches()

    from PySide6.QtCore import Qt
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtWidgets import QApplication, QMessageBox, QSplitter
    import ui_v2

    app = QApplication.instance() or QApplication([])
    assert QGuiApplication.platformName().lower() == "windows", QGuiApplication.platformName()
    QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
    QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
    QMessageBox.critical = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)

    win = ui_v2.MainWindowV2()
    win.show()
    app.processEvents()
    _select_vehicle(win, app)

    native, native_w, native_h = _native_screen_capture(
        win, app, 3, "v2_222_coding_native_screen.png"
    )
    native_split = win._workspace_pages[3].findChild(QSplitter, "kidWorkspaceSplitter3")
    assert native_split is not None
    assert win._workspace_pages[3].table.rowCount() > 0
    assert win._workspace_pages[3].detail.toPlainText().strip()

    small = _render_at(win, app, 1366, 768, 3, "v2_222_coding_1366x768.png")
    coding_split = win._workspace_pages[3].findChild(QSplitter, "kidWorkspaceSplitter3")
    assert coding_split.orientation() == Qt.Vertical
    assert coding_split.minimumHeight() >= 260

    _render_at(win, app, 1366, 768, 2, "v2_222_dtc_1366x768.png")
    _render_at(win, app, 1366, 768, 4, "v2_222_adapt_1366x768.png")
    _render_at(win, app, 1366, 768, 5, "v2_222_service_1366x768.png")

    large = _render_at(win, app, 1920, 1080, 3, "v2_222_coding_1920x1080.png")
    coding_split = win._workspace_pages[3].findChild(QSplitter, "kidWorkspaceSplitter3")
    assert coding_split.orientation() == Qt.Horizontal
    assert coding_split.width() > 1200

    print(
        "V2.2.2 NATIVE WINDOWS + CONTROLLED LAYOUT VISUAL AUDIT OK",
        f"platform={QGuiApplication.platformName()}",
        f"vehicle={win.vehicle_badge.text()}",
        f"native={native.name}:{native_w}x{native_h}",
        f"small={small.name}:1366x768",
        f"large={large.name}:1920x1080",
        f"coding_rows={win._workspace_pages[3].table.rowCount()}",
    )
    win.close(); app.processEvents(); app.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
