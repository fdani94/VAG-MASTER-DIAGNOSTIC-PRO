from __future__ import annotations

import hashlib
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


def _render_signature(text, font, QColor, QImage, QPainter, Qt):
    image = QImage(160, 100, QImage.Format_ARGB32)
    white = QColor("white")
    image.fill(white)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.TextAntialiasing, True)
    painter.setPen(QColor("black"))
    painter.setFont(font)
    painter.drawText(image.rect(), Qt.AlignCenter, text)
    painter.end()

    changed = 0
    payload = bytearray()
    for y in range(image.height()):
        for x in range(image.width()):
            color = image.pixelColor(x, y)
            if color != white:
                changed += 1
                payload.extend((x & 0xFF, y & 0xFF, color.red(), color.green(), color.blue(), color.alpha()))
    return hashlib.sha256(payload).hexdigest(), changed


def main() -> int:
    # This validator must use the native Windows QPA plugin. Functional tests use
    # offscreen for determinism, but offscreen screenshots are not accepted as
    # visual proof because hosted runners can render system text as tofu boxes.
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

    font = QFont(preferred, 18)
    resolved = QFontInfo(font).family()
    metrics = QFontMetrics(font)
    assert metrics.horizontalAdvance("WWWW") != metrics.horizontalAdvance("IIII"), "Native font metrics look invalid"

    # Keep this source ASCII-only. The characters are constructed at runtime so
    # Git/GitHub/console encoding cannot silently replace Romanian diacritics.
    chars = {
        "a_breve": chr(0x0103),
        "a_circ": chr(0x00E2),
        "i_circ": chr(0x00EE),
        "s_comma": chr(0x0219),
        "t_comma": chr(0x021B),
        "A_breve": chr(0x0102),
        "A_circ": chr(0x00C2),
        "I_circ": chr(0x00CE),
        "S_comma": chr(0x0218),
        "T_comma": chr(0x021A),
        "emdash": chr(0x2014),
        "bullet": chr(0x2022),
    }
    probe = (
        "KID Diagnostic V2.2.1 " + chars["emdash"] + " Cod" + chars["a_breve"] + "ri "
        + chars["bullet"] + " " + chars["S_comma"] + "tergere erori " + chars["bullet"] + " "
        + chars["a_breve"] + chars["a_circ"] + chars["i_circ"] + chars["s_comma"] + chars["t_comma"] + " "
        + chars["A_breve"] + chars["A_circ"] + chars["I_circ"] + chars["S_comma"] + chars["T_comma"]
    )
    assert chr(0xFFFD) not in probe, "Probe contains Unicode replacement characters"

    # QRawFont checks only one physical face and can produce false negatives when
    # Qt legitimately uses font fallback. Test what Qt actually paints instead.
    tofu_signatures = set()
    for tofu in (chr(0xFFFD), chr(0x25A1), chr(0x25A0)):
        signature, pixels = _render_signature(tofu, font, QColor, QImage, QPainter, Qt)
        if pixels:
            tofu_signatures.add(signature)

    base_pairs = {
        "a_breve": "a",
        "a_circ": "a",
        "i_circ": "i",
        "s_comma": "s",
        "t_comma": "t",
        "A_breve": "A",
        "A_circ": "A",
        "I_circ": "I",
        "S_comma": "S",
        "T_comma": "T",
    }
    glyph_results = {}
    for name, char in chars.items():
        signature, pixels = _render_signature(char, font, QColor, QImage, QPainter, Qt)
        assert pixels > 20, f"Native Windows rendered no usable glyph for {name} U+{ord(char):04X}"
        assert signature not in tofu_signatures, f"Native Windows rendered tofu/replacement for {name} U+{ord(char):04X}"
        if name in base_pairs:
            base_signature, base_pixels = _render_signature(base_pairs[name], font, QColor, QImage, QPainter, Qt)
            assert base_pixels > 20
            assert signature != base_signature, f"Diacritic {name} rendered identically to base letter"
        glyph_results[name] = pixels

    image = QImage(1400, 120, QImage.Format_ARGB32)
    white = QColor("white")
    image.fill(white)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.TextAntialiasing, True)
    painter.setPen(QColor("black"))
    painter.setFont(font)
    painter.drawText(image.rect().adjusted(18, 8, -18, -8), Qt.AlignLeft | Qt.AlignVCenter, probe)
    painter.end()
    assert image.save(str(ROOT / "v2_221_native_font_probe.png"), "PNG")

    changed = 0
    for y in range(image.height()):
        for x in range(image.width()):
            if image.pixelColor(x, y) != white:
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
    detail = coding_page.detail.toPlainText()
    assert detail.strip()
    assert chr(0xFFFD) not in detail, "Coding detail contains Unicode replacement characters"
    coding = win.grab()
    assert not coding.isNull()
    assert coding.save(str(ROOT / "v2_221_native_coding.png"), "PNG")

    print(
        "V2.2.1 NATIVE WINDOWS VISUAL AUDIT OK",
        f"platform={platform}",
        f"font={resolved}",
        f"families={len(families)}",
        f"probe_pixels={changed}",
        f"glyphs={len(glyph_results)}",
        f"dashboard={dashboard.width()}x{dashboard.height()}",
        f"coding_rows={coding_page.table.rowCount()}",
    )

    win.close()
    app.processEvents()
    app.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
