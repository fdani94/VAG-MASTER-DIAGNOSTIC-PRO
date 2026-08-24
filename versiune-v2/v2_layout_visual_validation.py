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


def _save(win, app, width, height, index, filename):
    win.resize(width, height)
    app.processEvents()
    win.open_page(index)
    app.processEvents()
    pix = win.grab()
    assert not pix.isNull()
    assert pix.width() >= width - 40 and pix.height() >= height - 80
    path = ROOT / filename
    assert pix.save(str(path), "PNG")
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

    small = _save(win, app, 1366, 768, 3, "v2_222_coding_1366x768.png")
    coding_split = win._workspace_pages[3].findChild(QSplitter, "kidWorkspaceSplitter3")
    assert coding_split is not None and coding_split.orientation() == Qt.Vertical
    assert coding_split.height() >= 260
    assert win._workspace_pages[3].table.rowCount() > 0
    assert win._workspace_pages[3].detail.toPlainText().strip()

    _save(win, app, 1366, 768, 2, "v2_222_dtc_1366x768.png")
    _save(win, app, 1366, 768, 4, "v2_222_adapt_1366x768.png")
    _save(win, app, 1366, 768, 5, "v2_222_service_1366x768.png")

    large = _save(win, app, 1920, 1080, 3, "v2_222_coding_1920x1080.png")
    coding_split = win._workspace_pages[3].findChild(QSplitter, "kidWorkspaceSplitter3")
    assert coding_split.orientation() == Qt.Horizontal
    assert coding_split.width() > 1200

    print(
        "V2.2.2 NATIVE LAYOUT VISUAL AUDIT OK",
        f"platform={QGuiApplication.platformName()}",
        f"vehicle={win.vehicle_badge.text()}",
        f"small={small.name}",
        f"large={large.name}",
        f"coding_rows={win._workspace_pages[3].table.rowCount()}",
        f"splitter_height={coding_split.height()}",
    )
    win.close(); app.processEvents(); app.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
