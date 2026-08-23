from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V2 = Path(__file__).resolve().parent
for path in (ROOT, V2):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import main_v2


def _choose_text(combo, text: str) -> bool:
    for index in range(combo.count()):
        if text.lower() in combo.itemText(index).lower():
            combo.setCurrentIndex(index)
            return True
    return False


def _select_vehicle(win, app) -> None:
    assert _choose_text(win.brand_combo, "Volkswagen")
    app.processEvents()
    assert _choose_text(win.model_combo, "Golf")
    app.processEvents()
    assert _choose_text(win.gen_combo, "VII 5G/AU")
    app.processEvents()
    assert _choose_text(win.year_combo, "2015")
    app.processEvents()
    assert win.engine_combo.count() > 1
    win.engine_combo.setCurrentIndex(1)
    assert win.engine_combo.currentData() is not None
    win._select_vehicle()
    app.processEvents()
    assert win.selected_generation_id is not None
    assert getattr(win, "selected_engine_id", None) is not None


def main() -> int:
    # This validator must use the native Windows QPA plugin. It deliberately
    # refuses offscreen/minimal because those plugins can render system text as
    # tofu squares on hosted runners, making screenshots useless as visual proof.
    main_v2.prepare_database()
    main_v2.apply_v2_patches()

    from PySide6.QtCore import Qt
    from PySide6.QtGui import (
        QColor,
        QFont,
        QFontDatabase,
        QFontInfo,
        QFontMetrics,
        QGuiApplication,
        QImage,
        QPainter,
        QRawFont,
    )
    from PySide6.QtWidgets import QApplication, QMessageBox
    import ui_v2

    app = QApplication.instance() or QApplication([])
    platform = QGuiApplication.platformName().lower()
    assert platform == "windows", f"Native visual audit requires windows QPA, got {platform!r}"

    QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
    QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
    QMessageBox.critical = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)

    families = set(QFontDatabase.families())
    preferred = "Segoe UI" if "Segoe UI" in families else "Arial" if "Arial" in families else ""
    assert preferred, "Neither Segoe UI nor Arial is available on the Windows runner"

    font = QFont(preferred, 14)
    resolved = QFontInfo(font).family()
    metrics = QFontMetrics(font)
    raw = QRawFont.fromFont(font)
    assert raw.isValid(), f"Resolved font is invalid: {resolved}"

    probe = "KID Diagnostic V2.2.1 — Codări • Ștergere erori • ăâîșț ĂÂÎȘȚ"
    required = "KIDDiagnosticV221CodăriȘtergereeroriăâîșțĂÂÎȘȚ—•"
    unsupported = [char for char in dict.fromkeys(required) if not raw.supportsCharacter(char)]
    assert not unsupported, f"Font {resolved!r} lacks required glyphs: {unsupported!r}"
    glyphs = raw.glyphIndexesForString(probe)
    missing_glyphs = [probe[i] for i, glyph in enumerate(glyphs) if probe[i] != " " and glyph == 0]
    assert not missing_glyphs, f"Native text resolves to .notdef glyphs: {missing_glyphs!r}"
    assert metrics.horizontalAdvance("WWWW") != metrics.horizontalAdvance("IIII"), "Font metrics look like uniform tofu glyphs"

    image = QImage(1400, 120, QImage.Format_ARGB32)
    image.fill(QColor("white"))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.TextAntialiasing, True)
    painter.setPen(QColor("black"))
    painter.setFont(font)
    painter.drawText(image.rect().adjusted(18, 8, -18, -8), Qt.AlignLeft | Qt.AlignVCenter, probe)
    painter.end()
    assert image.save(str(ROOT / "v2_221_native_font_probe.png"), "PNG")

    # Ensure text rendering actually changed a meaningful number of pixels from
    # the white background. Font coverage checks above protect against .notdef.
    changed = 0
    for y in range(image.height()):
        for x in range(image.width()):
            if image.pixelColor(x, y) != QColor("white"):
                changed += 1
    assert changed > 1000, f"Native font probe rendered too little text: {changed} pixels"

    win = ui_v2.MainWindowV2()
    win.resize(1600, 900)
    win.show()
    app.processEvents()
    assert "2.2.1" in win.windowTitle()
    _select_vehicle(win, app)

    dashboard = win.grab()
    assert not dashboard.isNull()
    assert dashboard.save(str(ROOT / "v2_221_native_dashboard.png"), "PNG")

    win.open_page(3)
    app.processEvents()
    coding_page = win._workspace_pages[3]
    assert coding_page.table.rowCount() > 0
    assert coding_page.detail.toPlainText().strip()
    coding = win.grab()
    assert not coding.isNull()
    assert coding.save(str(ROOT / "v2_221_native_coding.png"), "PNG")

    print(
        "V2.2.1 NATIVE WINDOWS VISUAL AUDIT OK",
        f"platform={platform}",
        f"font={resolved}",
        f"families={len(families)}",
        f"probe_pixels={changed}",
        f"dashboard={dashboard.width()}x{dashboard.height()}",
        f"coding_rows={coding_page.table.rowCount()}",
    )

    win.close()
    app.processEvents()
    app.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
