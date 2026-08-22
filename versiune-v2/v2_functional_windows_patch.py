"""Functional wiring for the separate KID Diagnostic V2 workspace windows.

Applied after the responsive/windows patch. The visual workspace windows keep
using the real MainWindowV2 diagnostic engine, but all modal dialogs are
parented to the active workspace and every data page refreshes visibly when it
opens.
"""
from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtCore import Qt, QMarginsF
from PySide6.QtGui import QTextDocument, QPdfWriter, QPageLayout, QPageSize
from PySide6.QtWidgets import QFileDialog, QMessageBox, QHeaderView

import appdb as db
from autoscan_parser import parse_autoscan_file, diagnostic_plan
from autoscan_correlation import correlate, render_correlation
from autoscan_ro import ro_status, ro_module, ro_title, ro_confidence, ro_vcds_note

FUNCTIONAL_WIRING_VERSION = "2.2-module-fallback"


def _active_parent(owner):
    index = int(getattr(owner, "_active_workspace_index", 0) or 0)
    win = getattr(owner, "_workspace_windows", {}).get(index)
    if win is not None and win.isVisible():
        return win
    return owner


def apply():
    import ui_v2
    from v2_responsive_windows_patch import WorkspaceWindow

    cls = ui_v2.MainWindowV2
    if getattr(cls, "_kid_v2_functional_windows_applied", False):
        return

    base_load_dtcs = cls._load_dtcs
    base_load_live = cls._load_live
    base_load_modules = cls._load_modules
    base_load_procedures = cls._load_procedures

    def _select_vehicle(self):
        gid = self.gen_combo.currentData()
        parent = _active_parent(self)
        if not gid:
            QMessageBox.warning(parent, "Vehicul", "Selectează marca, modelul și generația.")
            return
        self.selected_generation_id = gid
        self.selected_year = self.year_combo.currentData()
        h = db.vehicle_header(self.con, gid)
        engine_text = self.engine_combo.currentText().strip()
        text = f'{h["brand"]} {h["model"]} • {h["name"]} • {self.selected_year or ""}'
        if engine_text and engine_text.lower() != "nespecificat":
            text += f" • {engine_text}"
        self.vehicle_badge.setText(text)
        db.log(self.con, "select_vehicle_v2", "generation", gid, text)

    def _load_dtcs(self):
        base_load_dtcs(self)
        if self.dtc_table.rowCount() > 0:
            self.dtc_table.selectRow(0)
            self._show_dtc()
        else:
            self.dtc_detail.setPlainText("Nu s-au găsit coduri DTC pentru filtrul introdus.")

    def _load_live(self):
        base_load_live(self)
        if self.live_table.rowCount() == 0:
            self.live_search.setToolTip("Nu există rezultate pentru filtrul actual. Șterge filtrul pentru toate valorile disponibile.")

    def _load_modules(self):
        base_load_modules(self)
        if self.module_table.rowCount() > 0:
            self.module_table.setToolTip(
                "Module mapate pentru generația selectată. Confirmă echiparea reală prin Auto-Scan VCDS."
            )
            return

        # Unele generații din baza extinsă nu au încă legături explicite în
        # generation_modules. O fereastră goală pare nefuncțională și nu ajută
        # în atelier, așa că afișăm catalogul general de controlere VAG ca
        # fallback, fără să pretindem că toate sunt instalate pe mașina aleasă.
        rows = self.con.execute(
            "SELECT address,name,family,protocol FROM modules ORDER BY address,name LIMIT 500"
        ).fetchall()
        self.module_table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, key in enumerate(("address", "name", "family", "protocol")):
                self.module_table.setItem(i, j, ui_v2.QTableWidgetItem(str(row[key] or "—")))
        self.module_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.module_table.setToolTip(
            "Catalog general de module VAG — prezența pe vehicul se confirmă prin Auto-Scan VCDS."
        )

    def _load_procedures(self, page):
        base_load_procedures(self, page)
        if page.table.rowCount() > 0:
            page.table.selectRow(0)
            self._show_procedure(page)
        else:
            page.detail.setPlainText(
                "Nu există o procedură locală potrivită pentru filtrul și vehiculul curent.\n\n"
                "Schimbă filtrul sau confirmă exact generația, anul și motorul. Aplicația nu inventează valori de Coding/Adaptation."
            )

    def _load_autoscan(self):
        parent = _active_parent(self)
        path, _ = QFileDialog.getOpenFileName(
            parent,
            "Încarcă Auto-Scan VCDS",
            "",
            "Auto-Scan VCDS (*.txt *.log *.pdf);;Text (*.txt *.log);;PDF (*.pdf);;Toate fișierele (*.*)",
        )
        if not path:
            return
        try:
            result = parse_autoscan_file(path)
        except Exception as exc:
            QMessageBox.critical(parent, "Auto-Scan", f"Raportul nu a putut fi citit:\n{exc}")
            return

        self.current_autoscan = result
        engine_id = self.engine_combo.currentData() if hasattr(self, "engine_combo") else None
        self.autoscan_plans = [
            (fault, diagnostic_plan(self.con, fault, self.selected_generation_id, engine_id))
            for fault in result.faults
        ]
        self.autoscan_correlation = correlate(result, self.autoscan_plans)
        self.autoscan_table.setRowCount(len(self.autoscan_plans))
        self.autoscan_table.setProperty("rows", self.autoscan_plans)

        for i, (fault, plan) in enumerate(self.autoscan_plans):
            values = [
                f"{fault.module_address} {ro_module(fault.module_name)}".strip(),
                fault.code or fault.vag_code,
                ro_title(plan.get("title") or fault.title),
                ro_status(fault.status),
                ro_confidence(plan.get("found"), plan.get("verified")),
            ]
            for j, value in enumerate(values):
                self.autoscan_table.setItem(i, j, ui_v2.QTableWidgetItem(str(value)))
        self.autoscan_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)

        validation = getattr(result, "validation_message", "") or ""
        self.autoscan_summary.setText(
            f"{Path(path).name} • {len(result.modules)} module • {len(result.faults)} erori • "
            f"{sum(1 for _, p in self.autoscan_plans if p.get('found'))} fișe locale"
            + (f" • {validation}" if validation else "")
        )
        if self.autoscan_plans:
            self.autoscan_table.selectRow(0)
            self._show_autoscan_fault()
        else:
            self.autoscan_detail.setPlainText(
                "Raportul a fost citit, dar nu au fost detectate erori DTC.\n\n"
                + (validation or "Verifică formatul Auto-Scan-ului și modulele raportate.")
            )

    def _show_correlation(self):
        parent = _active_parent(self)
        if not self.autoscan_correlation:
            QMessageBox.warning(parent, "Plan diagnostic", "Încarcă mai întâi un Auto-Scan VCDS cu erori.")
            return
        self.autoscan_detail.setPlainText(render_correlation(self.autoscan_correlation) + "\n\n" + ro_vcds_note())

    def _export_pdf(self):
        parent = _active_parent(self)
        if not self.current_autoscan or not self.autoscan_plans:
            QMessageBox.warning(parent, "Raport PDF", "Încarcă mai întâi un Auto-Scan VCDS cu erori.")
            self.open_page(1)
            return

        suggested = f"KID_Diagnostic_{Path(self.current_autoscan.source_path).stem}_V2.pdf"
        path, _ = QFileDialog.getSaveFileName(parent, "Salvează raportul KID Diagnostic", suggested, "PDF (*.pdf)")
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        try:
            html = ui_v2._build_html(self)
            custom_logo = Path(db.LOGO_PATH)
            if custom_logo.exists():
                uri = custom_logo.resolve().as_uri()
                html = re.sub(
                    r"(<img class='logo' src=')[^']+(')",
                    lambda m: m.group(1) + uri + m.group(2),
                    html,
                    count=1,
                )
            writer = QPdfWriter(path)
            writer.setTitle("KID Diagnostic V2 - Raport Auto-Scan VCDS")
            writer.setCreator("KID Diagnostic")
            writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
            writer.setPageMargins(QMarginsF(14, 14, 14, 14), QPageLayout.Unit.Millimeter)
            writer.setResolution(120)
            doc = QTextDocument()
            doc.setHtml(html)
            doc.print_(writer)
        except Exception as exc:
            QMessageBox.critical(parent, "Raport PDF", f"Raportul nu a putut fi salvat:\n{exc}")
            return
        QMessageBox.information(parent, "Raport PDF", f"Raport salvat:\n{path}")

    def _open_page(self, index):
        if index == 0:
            self.show_dashboard()
            return
        if not self.selected_generation_id:
            QMessageBox.warning(self, "Vehicul", "Selectează mai întâi vehiculul.")
            self.show_dashboard()
            return

        page = self._workspace_pages.get(index)
        if page is None:
            QMessageBox.critical(self, "Interfață", f"Workspace-ul {index} nu a putut fi inițializat.")
            return

        win = self._workspace_windows.get(index)
        if win is None:
            title = ui_v2.CARDS[index - 1][0]
            win = WorkspaceWindow(self, index, title, page)
            self._workspace_windows[index] = win

        self._active_workspace_index = index

        # Keep the dashboard alive behind the workspace. File/message dialogs
        # owned by the diagnostic engine can therefore never be orphaned behind
        # a hidden main window.
        if not self.isVisible():
            self.show()

        if index == 2:
            self._load_dtcs()
        elif index in (3, 4, 5):
            self._load_procedures(page)
        elif index == 6:
            self._load_live()
        elif index == 7:
            self._load_modules()

        win.show_for_owner_screen()

    cls._select_vehicle = _select_vehicle
    cls._load_dtcs = _load_dtcs
    cls._load_live = _load_live
    cls._load_modules = _load_modules
    cls._load_procedures = _load_procedures
    cls._load_autoscan = _load_autoscan
    cls._show_correlation = _show_correlation
    cls._export_pdf = _export_pdf
    cls.open_page = _open_page
    cls._kid_v2_functional_windows_applied = True
