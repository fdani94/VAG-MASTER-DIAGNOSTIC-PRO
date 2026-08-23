from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
V2 = Path(__file__).resolve().parent
for path in (ROOT, V2):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from PySide6.QtWidgets import QApplication

import main_v2


def choose(combo, needle):
    for i in range(combo.count()):
        if needle.lower() in combo.itemText(i).lower():
            combo.setCurrentIndex(i)
            return True
    return False


def run():
    main_v2.prepare_database()
    main_v2.apply_v2_patches()

    import ui_v2
    from v2_vehicle_first_patch import selected_vehicle_context

    app = QApplication.instance() or QApplication([])
    win = ui_v2.MainWindowV2()
    win.show()
    app.processEvents()

    assert choose(win.brand_combo, "Volkswagen")
    app.processEvents()
    assert choose(win.model_combo, "Golf")
    app.processEvents()
    assert choose(win.gen_combo, "VII 5G/AU")
    app.processEvents()
    assert choose(win.year_combo, "2015")
    assert win.engine_combo.count() > 1
    win.engine_combo.setCurrentIndex(1)  # index 0 = Nespecificat
    assert win.engine_combo.currentData() is not None
    win._select_vehicle()
    app.processEvents()

    ctx = selected_vehicle_context(win)
    assert ctx["brand"] == "Volkswagen"
    assert ctx["model"] == "Golf"
    assert ctx["year"] == 2015
    assert ctx["engine_code"]
    assert len(win._vehicle_context_strips) == 8

    win.grab().save("v2_220_dashboard_vehicle_selected.png")

    win.open_page(3)
    app.processEvents()
    page = win._workspace_pages[3]
    rows = page.table.property("rows") or []
    assert rows, "Coding list is empty for selected vehicle"
    assert page.table.columnCount() == 6
    assert "Volkswagen Golf" in win._vehicle_context_strips[3]._kid_vehicle_label.text()

    target = next((row for row in rows if str(row["module_address"] or "").strip()), None)
    assert target is not None
    addr = str(target["module_address"]).strip()
    win.current_autoscan = SimpleNamespace(
        modules=[
            SimpleNamespace(
                address=addr,
                coding="A1B2C3D4E5F6",
                part_no_sw="5Q0 937 084",
                part_no_hw="5Q0 937 084",
                component="BCM MQBAB",
                asam_dataset="EV_BCMCONTI",
            )
        ],
        faults=[],
    )
    win.refresh_vehicle_context_v220()
    win._load_procedures(page)
    app.processEvents()

    rows = page.table.property("rows") or []
    confirmed = [i for i, row in enumerate(rows) if str(row["module_address"] or "").strip().upper() == addr.upper()]
    assert confirmed
    page.table.selectRow(confirmed[0])
    win._show_procedure(page)
    app.processEvents()

    detail = page.detail.toPlainText()
    assert page.table.item(confirmed[0], 0).text() == "CONFIRMAT AUTOSCAN"
    assert "CODING ORIGINAL DIN AUTO-SCAN" in detail
    assert "A1B2C3D4E5F6" in detail
    assert "PAȘI DOCUMENTAȚI" in detail
    assert "CUM ȘTII CĂ A REUȘIT" in detail
    assert "SURSĂ" in detail

    win.grab().save("v2_220_coding_explicit.png")

    print(
        "V2.2.0 VEHICLE-FIRST AUDIT OK "
        f"vehicle={ctx['brand']} {ctx['model']} {ctx['generation']} {ctx['year']} {ctx['engine_code']} "
        f"coding_rows={len(rows)} confirmed_module={addr} context_strips={len(win._vehicle_context_strips)}"
    )
    win.close()
    app.processEvents()
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
