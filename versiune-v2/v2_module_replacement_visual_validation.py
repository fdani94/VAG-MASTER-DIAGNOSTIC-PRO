from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V2 = Path(__file__).resolve().parent
for path in (ROOT, V2):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import main_v2
from autoscan_parser import parse_autoscan_text


def main() -> int:
    main_v2.prepare_database()
    main_v2.apply_v2_patches()

    from PySide6.QtGui import QGuiApplication
    from PySide6.QtWidgets import QApplication, QMessageBox, QTableWidget
    import ui_v2

    app = QApplication.instance() or QApplication([])
    assert QGuiApplication.platformName().lower() == "windows", QGuiApplication.platformName()
    QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
    QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
    QMessageBox.critical = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)

    win = ui_v2.MainWindowV2()
    win.show()
    app.processEvents()
    assert "2.3.0" in win.windowTitle(), win.windowTitle()

    win.current_autoscan = parse_autoscan_text("""
VCDS Auto-Scan Coding Recovery visual fixture
Address 03: ABS Brakes
Part No SW: 5Q0 614 517
Part No HW: 5Q0 614 517
Component: ESC
Coding: 01FA6A124924096D
1 Fault Found:
01044 - Control Module Incorrectly Coded
            000 - -

Address 55: Headlight Range
Part No SW: 5M0 907 357 C
Component: AFS-Steuergeraet
1 Fault Found:
01042 - Control Module; Not Coded
            000 - -

Address 56: Radio
Part No SW: 4F0 035 056
Component: Radio U S Premium
1 Fault Found:
02095 - Component Protection Active
            000 - -
""")
    analysis = win.refresh_module_replacement_v230()
    assert len(analysis.findings) == 3
    assert analysis.coding_fault_count == 2
    assert analysis.blocking_count == 1
    assert win.kid_coding_recovery_panel._kid_badge.text() == "BLOCAJ ONLINE"

    win.open_page(1)
    app.processEvents()
    pix = win.grab()
    assert not pix.isNull() and pix.width() >= 900 and pix.height() >= 620
    path = ROOT / "v2_230_coding_recovery_native.png"
    assert pix.save(str(path), "PNG")

    win.open_module_replacement_assistant_v230()
    app.processEvents()
    dialog = win._coding_recovery_dialog
    assert dialog is not None and dialog.isVisible()
    table = dialog.findChild(QTableWidget)
    assert table is not None and table.rowCount() == 3
    assert table.item(0, 0).text() in {"BLOCAJ", "CRITIC"}
    dpix = dialog.grab()
    assert not dpix.isNull() and dpix.width() >= 900 and dpix.height() >= 600
    dpath = ROOT / "v2_230_coding_recovery_dialog.png"
    assert dpix.save(str(dpath), "PNG")

    print(
        "V2.3.0 NATIVE CODING RECOVERY VISUAL AUDIT OK",
        f"platform={QGuiApplication.platformName()}",
        f"findings={len(analysis.findings)}",
        f"coding={analysis.coding_fault_count}",
        f"online={analysis.blocking_count}",
        f"panel={path.name}",
        f"dialog={dpath.name}",
    )
    dialog.close()
    win.close()
    app.processEvents()
    app.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
