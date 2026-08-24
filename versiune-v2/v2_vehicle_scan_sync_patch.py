from __future__ import annotations

from v2_vehicle_precision_patch import apply as apply_precision

SYNC_VERSION = "2.2.1"


def _selection_key(owner):
    return (
        getattr(owner, "selected_generation_id", None),
        getattr(owner, "selected_year", None),
        getattr(owner, "selected_engine_id", None),
    )


def _requested_key(owner):
    return (
        owner.gen_combo.currentData() if hasattr(owner, "gen_combo") else None,
        owner.year_combo.currentData() if hasattr(owner, "year_combo") else None,
        owner.engine_combo.currentData() if hasattr(owner, "engine_combo") else None,
    )


def _clear_scan_state(owner):
    """Drop all evidence that belongs to the previously selected vehicle."""
    owner.current_autoscan = None
    owner.autoscan_plans = []
    owner.autoscan_correlation = None
    owner.v2_verified_report_text = ""
    owner.autoscan_vehicle_binding_ok = False
    owner.autoscan_vehicle_match = None

    table = getattr(owner, "autoscan_table", None)
    if table is not None:
        table.setRowCount(0)
        table.setProperty("rows", [])
    summary = getattr(owner, "autoscan_summary", None)
    if summary is not None:
        summary.setText("Auto-Scan: neîncărcat pentru vehiculul activ")
    detail = getattr(owner, "autoscan_detail", None)
    if detail is not None:
        detail.setPlainText(
            "Vehiculul a fost schimbat. Încarcă Auto-Scan-ul acestei mașini pentru confirmarea modulelor și Coding ORIGINAL."
        )


def _refresh_coding(owner):
    refresh = getattr(owner, "refresh_vehicle_context_v220", None)
    if callable(refresh):
        refresh()
    page = (getattr(owner, "_workspace_pages", {}) or {}).get(3)
    if page is not None and getattr(owner, "selected_generation_id", None):
        owner._load_procedures(page)


def apply():
    import ui_v2

    cls = ui_v2.MainWindowV2
    if getattr(cls, "_kid_vehicle_scan_sync_applied", False):
        apply_precision()
        return

    previous_select_vehicle = cls._select_vehicle
    previous_load_autoscan = cls._load_autoscan

    def select_vehicle_synced(self):
        old_key = _selection_key(self)
        requested = _requested_key(self)
        previous_select_vehicle(self)
        new_key = _selection_key(self)

        # If validation rejected the request, selected state did not become the
        # requested complete vehicle and no existing scan should be touched.
        if not all(requested) or new_key != requested:
            return

        if old_key != new_key:
            _clear_scan_state(self)
            _refresh_coding(self)

    def load_autoscan_synced(self):
        before = getattr(self, "current_autoscan", None)
        previous_load_autoscan(self)
        after = getattr(self, "current_autoscan", None)
        if after is None or after is before:
            return

        # A newly imported scan immediately changes the coding evidence. Refresh
        # the coding table even when the user imported it from another workspace.
        _refresh_coding(self)

    cls._select_vehicle = select_vehicle_synced
    cls._load_autoscan = load_autoscan_synced
    cls._kid_vehicle_scan_sync_applied = True
    apply_precision()


__all__ = ["SYNC_VERSION", "apply"]
