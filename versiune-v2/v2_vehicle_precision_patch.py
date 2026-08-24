from __future__ import annotations

import re

from PySide6.QtWidgets import QHeaderView, QMessageBox, QTableWidgetItem

import appdb as db
from autoscan_correlation import correlate
from autoscan_parser import diagnostic_plan
from autoscan_ro import ro_confidence, ro_module, ro_status, ro_title
import v2_vehicle_first_patch as vf
from v2_ai_copilot import build_verified_report

PRECISION_VERSION = "2.2.1"


def _selection_key(owner):
    return (
        getattr(owner, "selected_generation_id", None),
        getattr(owner, "selected_year", None),
        getattr(owner, "selected_engine_id", None),
    )


def _engine_rows(owner, generation_id, year):
    if not generation_id:
        return []
    return owner.con.execute(
        """SELECT e.id,e.code,e.fuel,e.displacement,e.power_hp,e.family,
                  ve.year_from,ve.year_to
           FROM vehicle_engines ve
           JOIN engines e ON e.id=ve.engine_id
           WHERE ve.generation_id=?
             AND (? IS NULL OR ve.year_from IS NULL OR ve.year_from<=?)
             AND (? IS NULL OR ve.year_to IS NULL OR ve.year_to>=?)
           ORDER BY e.code""",
        (generation_id, year, year, year, year),
    ).fetchall()


def _known_engine_codes(owner):
    gid = getattr(owner, "selected_generation_id", None)
    if not gid:
        return []
    return [
        str(r["code"] or "").strip().upper()
        for r in owner.con.execute(
            """SELECT DISTINCT e.code FROM vehicle_engines ve
               JOIN engines e ON e.id=ve.engine_id
               WHERE ve.generation_id=? ORDER BY e.code""",
            (gid,),
        ).fetchall()
        if str(r["code"] or "").strip()
    ]


def _procedure_text(row):
    return " ".join(
        str(row.get(key, "") if isinstance(row, dict) else row[key] or "")
        for key in ("title", "purpose", "applicability", "notes")
    )


def _engine_match(owner, row):
    selected = str(vf.selected_vehicle_context(owner).get("engine_code") or "").upper()
    if not selected:
        return "mismatch", "Motorul nu este selectat"
    text = _procedure_text(row).upper()
    mentioned = []
    for code in _known_engine_codes(owner):
        if re.search(rf"(?<![A-Z0-9]){re.escape(code)}(?![A-Z0-9])", text):
            mentioned.append(code)
    if mentioned and selected not in mentioned:
        return "mismatch", f"Procedura menționează alt motor: {', '.join(mentioned)}"
    if selected in mentioned:
        return "exact", f"Motor {selected} menționat explicit"
    return "generic", f"Motor {selected}: procedură nespecifică motorului"


def _year_match(owner, row):
    year = vf.selected_vehicle_context(owner).get("year")
    if not year:
        return "mismatch", "Anul nu este selectat"
    text = _procedure_text(row)
    ranges = [
        (int(a), int(b))
        for a, b in re.findall(r"\b((?:19|20)\d{2})\s*[-–—]\s*((?:19|20)\d{2})\b", text)
    ]
    if ranges:
        if not any(min(a, b) <= int(year) <= max(a, b) for a, b in ranges):
            readable = ", ".join(f"{a}-{b}" for a, b in ranges)
            return "mismatch", f"Anul {year} este în afara intervalului documentat {readable}"
        return "exact", f"An {year} în intervalul documentat"
    return "generic", f"An {year}: procedura este legată de generație, fără interval anual explicit"


def _norm_identity(value):
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


def _controller_match(row, module):
    if module is None:
        return False, "Controllerul nu este citit din Auto-Scan"
    text = _norm_identity(_procedure_text(row) + " " + str(row.get("source_title", "") if isinstance(row, dict) else row["source_title"] or ""))
    candidates = []
    for attr in ("part_no_sw", "part_no_hw", "asam_dataset"):
        raw = str(getattr(module, attr, "") or "").strip()
        token = _norm_identity(raw)
        if raw and len(token) >= 6:
            candidates.append((attr, raw, token))
    for attr, raw, token in candidates:
        if token in text:
            return True, f"Identitatea {attr} ({raw}) apare în procedură/sursă"
    return False, "Adresa modulului este prezentă, dar SW/HW/ASAM nu este confirmat de procedură"


def _chassis_codes(value):
    parts = re.findall(r"[A-Z0-9]{2,5}", str(value or "").upper())
    ignored = {"TYPE", "CHASSIS", "VCDS", "AUTO", "SCAN"}
    return [p for p in parts if p not in ignored]


def scan_vehicle_match(owner, scan):
    ctx = vf.selected_vehicle_context(owner)
    selected_codes = _chassis_codes(ctx.get("chassis"))
    scan_codes = _chassis_codes(getattr(scan, "chassis_type", ""))
    if not selected_codes:
        return {
            "status": "unverified",
            "matched": False,
            "reason": "Catalogul local nu are un cod chassis utilizabil pentru generația selectată.",
        }
    if not scan_codes:
        return {
            "status": "unverified",
            "matched": False,
            "reason": "Auto-Scan-ul nu conține Chassis Type; nu este folosit pentru confirmarea codărilor.",
        }
    scan_primary = scan_codes[0]
    matched = any(
        scan_primary == selected
        or (len(scan_primary) >= 2 and scan_primary.startswith(selected))
        or (len(selected) >= 2 and selected.startswith(scan_primary))
        for selected in selected_codes
    )
    if matched:
        return {
            "status": "matched",
            "matched": True,
            "reason": f"Chassis Auto-Scan {scan_primary} corespunde selecției {ctx.get('chassis') or '—'}.",
        }
    return {
        "status": "mismatch",
        "matched": False,
        "reason": f"Chassis Auto-Scan {scan_primary} NU corespunde selecției {ctx.get('chassis') or '—'}.",
    }


def _mapped_modules(owner):
    gid = getattr(owner, "selected_generation_id", None)
    if not gid:
        return []
    return owner.con.execute(
        """SELECT m.address,m.name,m.family,m.protocol,gm.applicability
           FROM generation_modules gm
           JOIN modules m ON m.id=gm.module_id
           WHERE gm.generation_id=?
           ORDER BY m.address,m.name""",
        (gid,),
    ).fetchall()


def _scan_map(owner):
    if not getattr(owner, "autoscan_vehicle_binding_ok", False):
        return {}
    return vf._scan_modules(getattr(owner, "current_autoscan", None))


def apply():
    import ui_v2

    cls = ui_v2.MainWindowV2
    if getattr(cls, "_kid_vehicle_precision_applied", False):
        return

    previous_init = cls.__init__
    previous_select_vehicle = cls._select_vehicle
    previous_load_autoscan = cls._load_autoscan
    previous_open_page = cls.open_page
    previous_show_dashboard = cls.show_dashboard
    original_meta = vf._procedure_meta

    def precise_meta(owner, row):
        scan = getattr(owner, "current_autoscan", None)
        binding = bool(getattr(owner, "autoscan_vehicle_binding_ok", False))
        if scan is not None and not binding:
            owner.current_autoscan = None
            try:
                meta = original_meta(owner, row)
            finally:
                owner.current_autoscan = scan
        else:
            meta = original_meta(owner, row)

        module = meta.get("scan_module")
        if module is not None and binding:
            exact, reason = _controller_match(row, module)
            meta["controller_match"] = exact
            meta["controller_reason"] = reason
            meta["status"] = "CONTROLLER CONFIRMAT" if exact else "MODUL GĂSIT AUTOSCAN"
        else:
            meta["controller_match"] = False
            meta["controller_reason"] = "Auto-Scan-ul nu este legat confirmat de vehiculul selectat."
        return meta

    vf._procedure_meta = precise_meta

    def reload_engines_for_year(self, *_args):
        gid = self.gen_combo.currentData()
        year = self.year_combo.currentData()
        old_engine = self.engine_combo.currentData()
        rows = _engine_rows(self, gid, year)
        self.engine_combo.blockSignals(True)
        self.engine_combo.clear()
        self.engine_combo.addItem("Alege motorul", None)
        selected_index = 0
        for row in rows:
            label = f'{row["code"]} • {row["fuel"]} {row["displacement"] or ""}L {row["power_hp"] or ""}CP'
            self.engine_combo.addItem(label, row["id"])
            if row["id"] == old_engine:
                selected_index = self.engine_combo.count() - 1
        self.engine_combo.setCurrentIndex(selected_index)
        self.engine_combo.blockSignals(False)
        self.engine_combo.setToolTip(
            f"Motoare mapate pentru anul {year}. Un motor din alt interval de producție nu este afișat."
            if year else "Alege anul pentru filtrarea motoarelor."
        )

    def load_years_engines_precise(self):
        gid = self.gen_combo.currentData()
        self.year_combo.blockSignals(True)
        self.year_combo.clear()
        if gid:
            header = db.vehicle_header(self.con, gid)
            for year in range(int(header["year_from"]), int(header["year_to"]) + 1):
                self.year_combo.addItem(str(year), year)
        self.year_combo.blockSignals(False)
        reload_engines_for_year(self)

    def init_precision(self, *args, **kwargs):
        previous_init(self, *args, **kwargs)
        self.autoscan_vehicle_binding_ok = False
        self.autoscan_vehicle_match = None
        self.year_combo.currentIndexChanged.connect(self._reload_engines_for_year_v221)
        self.setWindowTitle("KID Diagnostic V2 • Vehicle First • AI Copilot • v2.2.1")

    def select_vehicle_precision(self):
        before = _selection_key(self)
        previous_select_vehicle(self)
        after = _selection_key(self)
        if before != after:
            self.autoscan_vehicle_binding_ok = False
            self.autoscan_vehicle_match = None
        if all(after):
            self.setWindowTitle("KID Diagnostic V2 • Vehicle First • AI Copilot • v2.2.1")

    def _refresh_autoscan_rows(self):
        rows = list(getattr(self, "autoscan_plans", []) or [])
        self.autoscan_table.setRowCount(len(rows))
        self.autoscan_table.setProperty("rows", rows)
        for i, (fault, plan) in enumerate(rows):
            values = [
                f"{fault.module_address} {ro_module(fault.module_name)}".strip(),
                fault.code or fault.vag_code,
                ro_title(plan.get("title") or fault.title),
                ro_status(fault.status),
                ro_confidence(plan.get("found"), plan.get("verified")),
            ]
            for j, value in enumerate(values):
                self.autoscan_table.setItem(i, j, QTableWidgetItem(str(value)))
        self.autoscan_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        if rows:
            self.autoscan_table.selectRow(0)
            self._show_autoscan_fault()

    def _refresh_coding(self):
        refresh = getattr(self, "refresh_vehicle_context_v220", None)
        if callable(refresh):
            refresh()
        page = (getattr(self, "_workspace_pages", {}) or {}).get(3)
        if page is not None and getattr(self, "selected_generation_id", None):
            self._load_procedures(page)

    def load_autoscan_precision(self):
        self.autoscan_vehicle_binding_ok = False
        self.autoscan_vehicle_match = None
        previous_load_autoscan(self)
        scan = getattr(self, "current_autoscan", None)
        if scan is None:
            return

        match = scan_vehicle_match(self, scan)
        self.autoscan_vehicle_match = match
        setattr(scan, "vehicle_match", match)

        if match["status"] == "mismatch":
            self.current_autoscan = None
            self.autoscan_plans = []
            self.autoscan_correlation = None
            self.v2_verified_report_text = ""
            self.autoscan_table.setRowCount(0)
            self.autoscan_table.setProperty("rows", [])
            self.autoscan_summary.setText(f"AUTO-SCAN RESPINS PENTRU VEHICULUL ACTIV • {match['reason']}")
            self.autoscan_detail.setPlainText(
                "Scanarea a fost citită, dar nu este legată de vehiculul selectat. "
                "Selectează mașina corectă și încarcă din nou Auto-Scan-ul. Nicio codare nu este confirmată din acest fișier."
            )
            _refresh_coding(self)
            QMessageBox.warning(self, "Auto-Scan / vehicul", match["reason"])
            return

        if match["status"] == "matched":
            self.autoscan_vehicle_binding_ok = True
            audit = getattr(scan, "audit", None) or {}
            evidence = audit.setdefault("evidence", [])
            evidence.append(match["reason"])
            self.autoscan_summary.setText(self.autoscan_summary.text() + " • VEHICUL CONFIRMAT CHASSIS")
        else:
            self.autoscan_vehicle_binding_ok = False
            # Keep DTC reading, but remove vehicle-specific correlation because
            # the scan cannot safely prove it belongs to the selected car.
            self.autoscan_plans = [
                (fault, diagnostic_plan(self.con, fault, None, None))
                for fault in list(getattr(scan, "faults", []) or [])
            ]
            self.autoscan_correlation = correlate(scan, self.autoscan_plans)
            _refresh_autoscan_rows(self)
            audit = getattr(scan, "audit", None) or {}
            audit["verified"] = False
            audit["score"] = max(0, int(audit.get("score", 100)) - 10)
            audit.setdefault("issues", []).append({"severity": "warning", "message": match["reason"]})
            self.autoscan_summary.setText(self.autoscan_summary.text() + " • VEHICUL NECONFIRMAT")
            self.v2_verified_report_text = build_verified_report(
                scan,
                self.autoscan_plans,
                selected_vehicle=f"NECONFIRMAT față de selecția UI: {self.vehicle_badge.text()}",
                audit=audit,
            )
        _refresh_coding(self)

    def load_modules_precision(self):
        mapped = list(_mapped_modules(self))
        scan_map = _scan_map(self)
        rows = []
        mapped_addresses = set()
        for row in mapped:
            address = vf._norm_addr(row["address"])
            mapped_addresses.add(address)
            scan_module = scan_map.get(address)
            identity = vf._module_identity(scan_module) if scan_module else ""
            rows.append({
                "status": "CONFIRMAT PE MAȘINĂ" if scan_module else "MAPAT GENERAȚIE",
                "address": row["address"],
                "name": row["name"],
                "family": identity or row["family"],
                "protocol": row["protocol"],
                "applicability": row["applicability"],
            })
        for address, module in scan_map.items():
            if address in mapped_addresses:
                continue
            rows.append({
                "status": "CITIT AUTOSCAN • NEMAPAT LOCAL",
                "address": address,
                "name": getattr(module, "name", "") or "Controller",
                "family": vf._module_identity(module) or getattr(module, "component", "") or "—",
                "protocol": "Auto-Scan",
                "applicability": "Prezent fizic; lipsește din harta locală a generației",
            })

        self.module_table.setColumnCount(6)
        self.module_table.setHorizontalHeaderLabels(
            ["Status", "Adresă", "Modul", "Familie / identificare", "Protocol", "Aplicabilitate"]
        )
        self.module_table.setRowCount(len(rows))
        self.module_table.setProperty("rows", rows)
        for i, row in enumerate(rows):
            for j, key in enumerate(("status", "address", "name", "family", "protocol", "applicability")):
                self.module_table.setItem(i, j, QTableWidgetItem(str(row[key] or "—")))
        self.module_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.module_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        if not rows:
            self.module_table.setToolTip(
                "Nu există o hartă locală explicită de module pentru această generație. Încarcă Auto-Scan-ul aceleiași mașini pentru lista reală."
            )
        else:
            self.module_table.setToolTip(
                "MAPAT GENERAȚIE = catalog local; CONFIRMAT PE MAȘINĂ = controller citit într-un Auto-Scan cu chassis potrivit."
            )

    def load_procedures_precision(self, page):
        coding_page = (getattr(self, "_workspace_pages", {}) or {}).get(3)
        if page is not coding_page:
            # Keep the existing V2 flow for Adaptations and Service.
            return self._kid_previous_load_procedures_v221(page)
        if not getattr(self, "selected_generation_id", None):
            page.table.setRowCount(0)
            page.table.setProperty("rows", [])
            page.detail.setPlainText("Selectează vehiculul complet: generație, an și motor.")
            return

        search = page.search.text().lower().strip()
        rows = []
        for raw in db.procedures_for_vehicle(self.con, self.selected_generation_id):
            row = dict(raw)
            hay = f'{row["category"]} {row["title"]} {row["vcds_path"]} {row["purpose"]}'.lower()
            if not any(keyword in hay for keyword in page.keywords):
                continue
            if search and search not in hay:
                continue
            engine_state, engine_reason = _engine_match(self, row)
            year_state, year_reason = _year_match(self, row)
            if engine_state == "mismatch" or year_state == "mismatch":
                continue
            row["_engine_state"] = engine_state
            row["_engine_reason"] = engine_reason
            row["_year_state"] = year_state
            row["_year_reason"] = year_reason
            rows.append(row)

        rank = {
            "CONTROLLER CONFIRMAT": 0,
            "MODUL GĂSIT AUTOSCAN": 1,
            "POTRIVIT GENERAȚIEI": 2,
            "PROCEDURĂ GENERALĂ": 3,
            "CONFIRMĂ MODULUL": 4,
        }
        rows.sort(
            key=lambda row: (
                rank.get(vf._procedure_meta(self, row)["status"], 9),
                0 if row["_engine_state"] == "exact" else 1,
                0 if row["_year_state"] == "exact" else 1,
                str(row["title"]),
            )
        )

        page.table.setColumnCount(7)
        page.table.setHorizontalHeaderLabels(
            ["Status", "Modul", "Codare / funcție", "Cale VCDS", "Motor / an", "Aplicabilitate", "Sursă"]
        )
        page.table.setRowCount(len(rows))
        page.table.setProperty("rows", rows)
        for i, row in enumerate(rows):
            meta = vf._procedure_meta(self, row)
            match_text = (
                ("MOTOR EXACT" if row["_engine_state"] == "exact" else "MOTOR GENERIC")
                + " • "
                + ("AN EXACT" if row["_year_state"] == "exact" else "AN GENERAȚIE")
            )
            values = [
                meta["status"],
                meta["module_address"] or "GENERAL",
                row["title"],
                row["vcds_path"],
                match_text,
                row["applicability"],
                meta["source_badge"],
            ]
            for j, value in enumerate(values):
                item = QTableWidgetItem(str(value or ""))
                if j == 0:
                    item.setToolTip(meta.get("controller_reason", ""))
                if j == 4:
                    item.setToolTip(row["_engine_reason"] + "\n" + row["_year_reason"])
                page.table.setItem(i, j, item)
        header = page.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)

        overview = getattr(self, "_coding_overview", None)
        if overview is not None:
            strong = sum(1 for row in rows if vf._procedure_meta(self, row)["status"] == "CONTROLLER CONFIRMAT")
            module_only = sum(1 for row in rows if vf._procedure_meta(self, row)["status"] == "MODUL GĂSIT AUTOSCAN")
            overview._kid_count.setText(f"{len(rows)} CODĂRI COMPATIBILE")
            if getattr(self, "current_autoscan", None) and not getattr(self, "autoscan_vehicle_binding_ok", False):
                overview._kid_scan_state.setText("AUTO-SCAN: VEHICUL NECONFIRMAT")
            elif getattr(self, "autoscan_vehicle_binding_ok", False):
                overview._kid_scan_state.setText(f"AUTO-SCAN: {strong} CONTROLLER • {module_only} MODUL")
            else:
                overview._kid_scan_state.setText("AUTO-SCAN: NEÎNCĂRCAT")

        if rows:
            page.table.selectRow(0)
            self._show_procedure(page)
        else:
            page.detail.setPlainText(
                "Nu există codări locale compatibile cu filtrul generație + an + motor. "
                "Aplicația nu extinde automat o procedură de la alt motor sau alt interval de ani."
            )

    def show_procedure_precision(self, page):
        coding_page = (getattr(self, "_workspace_pages", {}) or {}).get(3)
        if page is not coding_page:
            return self._kid_previous_show_procedure_v221(page)
        index = page.table.currentRow()
        rows = page.table.property("rows") or []
        if index < 0 or index >= len(rows):
            return
        row = rows[index]
        meta = vf._procedure_meta(self, row)
        precision = (
            '<div class="section"><b class="h">PRECIZIE PENTRU SELECȚIA ACTUALĂ</b><br>'
            + vf.escape(row.get("_engine_reason", ""))
            + '<br>'
            + vf.escape(row.get("_year_reason", ""))
            + '<br><b>Auto-Scan:</b> '
            + vf.escape(meta.get("controller_reason", ""))
            + '</div>'
        )
        html = vf._render_coding_detail(self, row)
        html = html.replace('<div class="danger">', precision + '<div class="danger">', 1)
        page.detail.setHtml(html)

    def open_page_precision(self, index):
        previous_open_page(self, index)
        if int(index) == 3 and getattr(self, "selected_generation_id", None):
            self.setWindowTitle(
                f"KID Diagnostic V2 • Codări precise • {vf._vehicle_text(vf.selected_vehicle_context(self))} • v2.2.1"
            )
        elif int(index) != 0:
            self.setWindowTitle("KID Diagnostic V2 • Vehicle First • AI Copilot • v2.2.1")

    def show_dashboard_precision(self):
        previous_show_dashboard(self)
        self.setWindowTitle("KID Diagnostic V2 • Dashboard • Vehicle First • AI Copilot • v2.2.1")

    cls._kid_previous_load_procedures_v221 = cls._load_procedures
    cls._kid_previous_show_procedure_v221 = cls._show_procedure
    cls.__init__ = init_precision
    cls._select_vehicle = select_vehicle_precision
    cls._load_years_engines = load_years_engines_precise
    cls._reload_engines_for_year_v221 = reload_engines_for_year
    cls._load_autoscan = load_autoscan_precision
    cls._load_modules = load_modules_precision
    cls._load_procedures = load_procedures_precision
    cls._show_procedure = show_procedure_precision
    cls.open_page = open_page_precision
    cls.show_dashboard = show_dashboard_precision
    cls._kid_vehicle_precision_applied = True


__all__ = ["PRECISION_VERSION", "scan_vehicle_match", "apply"]
