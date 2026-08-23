from __future__ import annotations

from html import escape
import re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidgetItem,
    QVBoxLayout,
)

import appdb as db

VEHICLE_FIRST_VERSION = "2.2.0"


def _norm_addr(value):
    text = str(value or "").strip().upper()
    text = text.replace("ADDRESS", "").replace("ADDR", "").strip(" :-")
    m = re.search(r"\b([0-9A-F]{2})\b", text)
    return m.group(1) if m else text[:2]


def _scan_modules(scan):
    result = {}
    for module in list(getattr(scan, "modules", []) or []):
        address = _norm_addr(
            getattr(module, "address", "")
            or getattr(module, "module_address", "")
            or getattr(module, "addr", "")
        )
        if address:
            result[address] = module
    return result


def _module_coding(module):
    if module is None:
        return ""
    for name in ("coding", "coding_value", "long_coding", "coding_original"):
        value = str(getattr(module, name, "") or "").strip()
        if value:
            return value
    return ""


def _module_identity(module):
    if module is None:
        return ""
    parts = []
    for label, name in (
        ("SW", "part_no_sw"),
        ("HW", "part_no_hw"),
        ("Component", "component"),
        ("ASAM", "asam_dataset"),
    ):
        value = str(getattr(module, name, "") or "").strip()
        if value:
            parts.append(f"{label}: {value}")
    return " • ".join(parts)


def _engine_row(owner, engine_id):
    if not engine_id:
        return None
    return owner.con.execute(
        "SELECT id,code,fuel,displacement,power_hp,family FROM engines WHERE id=?",
        (engine_id,),
    ).fetchone()


def selected_vehicle_context(owner):
    gid = getattr(owner, "selected_generation_id", None)
    if not gid:
        return {}
    header = db.vehicle_header(owner.con, gid)
    engine_id = getattr(owner, "selected_engine_id", None)
    engine = _engine_row(owner, engine_id)
    return {
        "generation_id": gid,
        "brand": str(header["brand"] or ""),
        "model": str(header["model"] or ""),
        "generation": str(header["name"] or ""),
        "chassis": str(header["chassis"] or ""),
        "platform": str(header["platform"] or ""),
        "year": getattr(owner, "selected_year", None),
        "engine_id": engine_id,
        "engine_code": str(engine["code"] or "") if engine else "",
        "fuel": str(engine["fuel"] or "") if engine else "",
        "displacement": engine["displacement"] if engine else None,
        "power_hp": engine["power_hp"] if engine else None,
        "engine_family": str(engine["family"] or "") if engine else "",
    }


def _vehicle_text(ctx):
    if not ctx:
        return "Niciun vehicul selectat"
    engine = ctx.get("engine_code") or "motor neconfirmat"
    year = ctx.get("year") or "an neconfirmat"
    chassis = ctx.get("chassis") or ctx.get("platform") or ""
    return (
        f'{ctx.get("brand", "")} {ctx.get("model", "")} • '
        f'{ctx.get("generation", "")} {chassis} • {year} • {engine}'
    ).replace("  ", " ").strip(" •")


def _procedure_meta(owner, row):
    ctx = selected_vehicle_context(owner)
    module_address = _norm_addr(row["module_address"])
    scan_map = _scan_modules(getattr(owner, "current_autoscan", None))
    scan_module = scan_map.get(module_address)

    expected_module = False
    if module_address and ctx:
        expected_module = bool(
            owner.con.execute(
                """SELECT 1 FROM generation_modules gm
                   JOIN modules m ON m.id=gm.module_id
                   WHERE gm.generation_id=? AND UPPER(m.address)=? LIMIT 1""",
                (ctx["generation_id"], module_address),
            ).fetchone()
        )

    source_url = str(row["source_url"] or "")
    source_title = str(row["source_title"] or "")
    official = "ross-tech.com" in source_url.lower()
    verified = bool(row["verified"])

    hay = " ".join(
        str(row[key] or "")
        for key in ("title", "purpose", "prerequisites", "steps", "applicability", "notes")
    ).upper()
    engine_code = str(ctx.get("engine_code") or "").upper()
    engine_explicit = bool(engine_code and engine_code in hay)
    year = str(ctx.get("year") or "")
    year_explicit = bool(year and year in hay)

    if scan_module is not None:
        status = "CONFIRMAT AUTOSCAN"
    elif expected_module:
        status = "POTRIVIT GENERAȚIEI"
    elif not module_address:
        status = "PROCEDURĂ GENERALĂ"
    else:
        status = "CONFIRMĂ MODULUL"

    if official and verified:
        source_badge = "OFICIAL / VERIFICAT"
    elif verified:
        source_badge = "VERIFICAT LOCAL"
    elif official:
        source_badge = "SURSĂ OFICIALĂ"
    else:
        source_badge = "DE CONFIRMAT"

    return {
        "module_address": module_address,
        "scan_module": scan_module,
        "expected_module": expected_module,
        "official": official,
        "verified": verified,
        "source_badge": source_badge,
        "status": status,
        "engine_explicit": engine_explicit,
        "year_explicit": year_explicit,
        "coding_original": _module_coding(scan_module),
        "identity": _module_identity(scan_module),
        "source_title": source_title,
        "source_url": source_url,
    }


def _make_context_strip(owner, page_index):
    frame = QFrame()
    frame.setObjectName("vehicleFirstContext")
    layout = QHBoxLayout(frame)
    layout.setContentsMargins(14, 10, 14, 10)
    layout.setSpacing(10)

    left = QVBoxLayout()
    kicker = QLabel("VEHICUL ACTIV")
    kicker.setObjectName("vehicleFirstKicker")
    label = QLabel("Selectează vehiculul din Dashboard")
    label.setObjectName("vehicleFirstLabel")
    label.setWordWrap(True)
    left.addWidget(kicker)
    left.addWidget(label)
    layout.addLayout(left, 1)

    state = QLabel("NESELECTAT")
    state.setObjectName("vehicleFirstState")
    state.setAlignment(Qt.AlignCenter)
    layout.addWidget(state)

    change = QPushButton("SCHIMBĂ VEHICULUL")
    change.setObjectName("secondaryButton")
    change.clicked.connect(owner.show_dashboard)
    layout.addWidget(change)

    frame._kid_vehicle_label = label
    frame._kid_vehicle_state = state
    frame._kid_page_index = page_index
    return frame


def _make_coding_overview(owner):
    frame = QFrame()
    frame.setObjectName("codingOverview")
    layout = QHBoxLayout(frame)
    layout.setContentsMargins(14, 12, 14, 12)
    layout.setSpacing(14)

    title_box = QVBoxLayout()
    title = QLabel("CODĂRI DISPONIBILE PENTRU MAȘINA SELECTATĂ")
    title.setObjectName("codingOverviewTitle")
    subtitle = QLabel(
        "Lista este filtrată pe generația aleasă. Auto-Scan confirmă ce module sunt montate efectiv și afișează Coding ORIGINAL înainte de orice modificare."
    )
    subtitle.setObjectName("codingOverviewSub")
    subtitle.setWordWrap(True)
    title_box.addWidget(title)
    title_box.addWidget(subtitle)
    layout.addLayout(title_box, 1)

    count = QLabel("0 CODĂRI")
    count.setObjectName("codingCount")
    count.setAlignment(Qt.AlignCenter)
    layout.addWidget(count)

    scan_state = QLabel("AUTO-SCAN: NEÎNCĂRCAT")
    scan_state.setObjectName("codingScanState")
    scan_state.setAlignment(Qt.AlignCenter)
    layout.addWidget(scan_state)

    frame._kid_count = count
    frame._kid_scan_state = scan_state
    return frame


def _render_coding_detail(owner, row):
    ctx = selected_vehicle_context(owner)
    meta = _procedure_meta(owner, row)

    def e(value):
        return escape(str(value or "")).replace("\n", "<br>")

    coding_original = meta["coding_original"]
    if coding_original:
        original_html = (
            '<div class="before"><b>CODING ORIGINAL DIN AUTO-SCAN — PĂSTREAZĂ-L</b><br>'
            f'<span class="code">{e(coding_original)}</span></div>'
        )
    else:
        original_html = (
            '<div class="need"><b>CODING ORIGINAL: NEÎNCĂRCAT</b><br>'
            "Încarcă Auto-Scan-ul mașinii înainte de o modificare. Aplicația nu va inventa valoarea originală.</div>"
        )

    match_bits = ["Generație: exactă prin catalogul V2"]
    if meta["engine_explicit"]:
        match_bits.append(f'Motor {ctx.get("engine_code")}: menționat explicit')
    else:
        match_bits.append(f'Motor {ctx.get("engine_code") or "—"}: context selectat, confirmă în controller')
    if meta["year_explicit"]:
        match_bits.append(f'An {ctx.get("year")}: menționat explicit')
    else:
        match_bits.append(f'An {ctx.get("year") or "—"}: în intervalul generației')

    identity = meta["identity"] or "Identificarea exactă SW/HW se completează din Auto-Scan."
    source = meta["source_title"] or "Sursă locală V2"
    source_url = meta["source_url"] or "—"

    return f"""
    <html><head><style>
      body {{ font-family:'Segoe UI',Arial; color:#182536; font-size:13px; line-height:1.45; }}
      h2 {{ margin:0 0 6px 0; font-size:21px; color:#132b43; }}
      .chips {{ margin:7px 0 12px 0; }}
      .chip {{ display:inline-block; padding:5px 9px; margin:0 6px 6px 0; border-radius:9px; background:#eaf3fb; color:#1b5e91; font-weight:700; }}
      .ok {{ background:#e6f7ee; color:#167342; }}
      .warn {{ background:#fff4dc; color:#8c5a00; }}
      .section {{ margin-top:12px; padding:11px 12px; border:1px solid #dbe5ed; border-radius:10px; background:#fbfdff; }}
      .section b.h {{ color:#315a78; font-size:11px; letter-spacing:.5px; }}
      .before {{ margin:10px 0; padding:12px; border:2px solid #37a66b; border-radius:10px; background:#effaf4; color:#145d37; }}
      .need {{ margin:10px 0; padding:12px; border:2px solid #e0a33d; border-radius:10px; background:#fff8e8; color:#744a00; }}
      .danger {{ margin-top:12px; padding:12px; border:1px solid #e4a3a3; border-radius:10px; background:#fff2f2; color:#8b2929; }}
      .code {{ font-family:Consolas,monospace; font-size:15px; font-weight:700; }}
      ul {{ margin-top:5px; }}
    </style></head><body>
      <h2>{e(row['title'])}</h2>
      <div class="chips">
        <span class="chip ok">{e(meta['status'])}</span>
        <span class="chip">MODUL {e(meta['module_address'] or 'GENERAL')}</span>
        <span class="chip">{e(meta['source_badge'])}</span>
      </div>
      <div class="section"><b class="h">MAȘINA PE CARE LUCREZI</b><br>{e(_vehicle_text(ctx))}</div>
      <div class="section"><b class="h">IDENTIFICARE CONTROLLER</b><br>{e(identity)}</div>
      {original_html}
      <div class="section"><b class="h">CE FACE ACEASTĂ CODARE</b><br>{e(row['purpose'])}</div>
      <div class="section"><b class="h">CALE EXACTĂ ÎN VCDS</b><br><span class="code">{e(row['vcds_path'])}</span></div>
      <div class="section"><b class="h">ÎNAINTE SĂ ÎNCEPI</b><br>{e(row['prerequisites'])}</div>
      <div class="section"><b class="h">PAȘI DOCUMENTAȚI</b><br>{e(row['steps'])}</div>
      <div class="section"><b class="h">CUM ȘTII CĂ A REUȘIT</b><br>{e(row['success_criteria'])}</div>
      <div class="section"><b class="h">POTRIVIRE CU VEHICULUL SELECTAT</b><ul>{''.join(f'<li>{e(x)}</li>' for x in match_bits)}</ul><br><b>Aplicabilitate:</b> {e(row['applicability'])}<br><b>Note:</b> {e(row['notes'])}</div>
      <div class="danger"><b>ATENȚIE</b><br>{e(row['warnings'])}<br><br>
        KID Diagnostic nu inventează Long Coding, Byte/Bit, Security Access sau canale de Adaptation. Dacă valoarea exactă nu este documentată și confirmată pentru controllerul citit, aplicația o lasă neconfirmată.</div>
      <div class="section"><b class="h">SURSĂ</b><br>{e(source)}<br>{e(source_url)}</div>
    </body></html>
    """


def apply():
    import ui_v2

    cls = ui_v2.MainWindowV2
    if getattr(cls, "_kid_vehicle_first_applied", False):
        return

    previous_init = cls.__init__
    previous_select_vehicle = cls._select_vehicle
    previous_open_page = cls.open_page
    previous_load_procedures = cls._load_procedures
    previous_show_procedure = cls._show_procedure

    def refresh_context(self):
        ctx = selected_vehicle_context(self)
        self.selected_vehicle_context = ctx
        text = _vehicle_text(ctx)
        if getattr(self, "vehicle_badge", None) is not None:
            self.vehicle_badge.setText(text)
            self.vehicle_badge.setToolTip(
                f"Vehicul activ în toate funcțiile V2.2.0\n{text}\n"
                f"Platformă: {ctx.get('platform') or '—'}\nMotor: {ctx.get('engine_code') or '—'}"
            )
        for strip in getattr(self, "_vehicle_context_strips", {}).values():
            strip._kid_vehicle_label.setText(text)
            strip._kid_vehicle_state.setText("SELECTAT" if ctx else "NESELECTAT")
        coding_overview = getattr(self, "_coding_overview", None)
        if coding_overview is not None:
            coding_overview._kid_scan_state.setText(
                "AUTO-SCAN: ÎNCĂRCAT" if getattr(self, "current_autoscan", None) else "AUTO-SCAN: NEÎNCĂRCAT"
            )

    def init_vehicle_first(self, *args, **kwargs):
        previous_init(self, *args, **kwargs)
        self.selected_engine_id = getattr(self, "selected_engine_id", None)
        self.selected_vehicle_context = {}
        self._vehicle_context_strips = {}

        pages = getattr(self, "_workspace_pages", {}) or {}
        for index in range(1, 9):
            page = pages.get(index)
            if page is None or page.layout() is None:
                continue
            strip = _make_context_strip(self, index)
            page.layout().insertWidget(1, strip)
            self._vehicle_context_strips[index] = strip

        coding_page = pages.get(3)
        if coding_page is not None and coding_page.layout() is not None:
            coding_page.setProperty("kidVehicleFirstKind", "coding")
            coding_page.search.setPlaceholderText(
                "Filtrat deja pe mașina selectată. Caută: coming home, DRL, needle sweep, confort, lumini..."
            )
            overview = _make_coding_overview(self)
            coding_page.layout().insertWidget(2, overview)
            self._coding_overview = overview
            coding_page.table.setSelectionBehavior(QAbstractItemView.SelectRows)
            coding_page.table.setSelectionMode(QAbstractItemView.SingleSelection)

        self.setWindowTitle("KID Diagnostic V2 • Vehicle First • v2.2.0")
        refresh_context(self)

        extra_qss = """
        #vehicleFirstContext { background:#f8fbfe; border:1px solid #d2e2ee; border-radius:10px; }
        #vehicleFirstKicker { color:#5d7b91; font-size:10px; font-weight:800; letter-spacing:.7px; }
        #vehicleFirstLabel { color:#18364f; font-size:13px; font-weight:700; }
        #vehicleFirstState { background:#e8f6ee; color:#167342; border:1px solid #bfe1ce; border-radius:8px; padding:6px 10px; font-weight:800; }
        #codingOverview { background:#eef6ff; border:1px solid #c9def1; border-radius:12px; }
        #codingOverviewTitle { color:#173d5e; font-size:14px; font-weight:850; }
        #codingOverviewSub { color:#547086; font-size:11px; }
        #codingCount, #codingScanState { background:#ffffff; color:#245f8d; border:1px solid #cadce9; border-radius:9px; padding:8px 11px; font-weight:800; }
        """
        self.setStyleSheet(self.styleSheet() + extra_qss)

    def select_vehicle_precise(self):
        gid = self.gen_combo.currentData()
        year = self.year_combo.currentData()
        engine_id = self.engine_combo.currentData()
        if not gid:
            QMessageBox.warning(self, "Vehicul", "Selectează marca, modelul și generația.")
            return
        if not year:
            QMessageBox.warning(self, "Vehicul", "Selectează anul mașinii. V2.2.0 folosește anul ca parte din contextul global.")
            return
        if not engine_id:
            QMessageBox.warning(self, "Vehicul", "Selectează motorul. V2.2.0 nu pornește codările pe un motor neprecizat.")
            return

        self.selected_engine_id = engine_id
        previous_select_vehicle(self)
        self.selected_engine_id = engine_id
        refresh_context(self)

        # Refresh every data page so no result from the previous vehicle remains visible.
        pages = getattr(self, "_workspace_pages", {}) or {}
        for index in (3, 4, 5):
            page = pages.get(index)
            if page is not None:
                self._load_procedures(page)
        if getattr(self, "_active_workspace_index", 0) == 2:
            self._load_dtcs()
        elif getattr(self, "_active_workspace_index", 0) == 6:
            self._load_live()
        elif getattr(self, "_active_workspace_index", 0) == 7:
            self._load_modules()

    def load_procedures_vehicle_first(self, page):
        if page is not (getattr(self, "_workspace_pages", {}) or {}).get(3):
            return previous_load_procedures(self, page)

        if not self.selected_generation_id:
            page.table.setRowCount(0)
            page.table.setProperty("rows", [])
            page.detail.setPlainText("Selectează mai întâi vehiculul complet: generație, an și motor.")
            return

        search = page.search.text().lower().strip()
        rows = []
        for row in db.procedures_for_vehicle(self.con, self.selected_generation_id):
            hay = f'{row["category"]} {row["title"]} {row["vcds_path"]} {row["purpose"]}'.lower()
            if not any(keyword in hay for keyword in page.keywords):
                continue
            if search and search not in hay:
                continue
            rows.append(row)

        def sort_key(row):
            meta = _procedure_meta(self, row)
            status_rank = {
                "CONFIRMAT AUTOSCAN": 0,
                "POTRIVIT GENERAȚIEI": 1,
                "PROCEDURĂ GENERALĂ": 2,
                "CONFIRMĂ MODULUL": 3,
            }.get(meta["status"], 9)
            return (
                status_rank,
                0 if meta["official"] and meta["verified"] else 1,
                meta["module_address"],
                str(row["title"]),
            )

        rows.sort(key=sort_key)
        page.table.setColumnCount(6)
        page.table.setHorizontalHeaderLabels(
            ["Status pe mașină", "Modul", "Codare / funcție", "Cale VCDS", "Aplicabilitate", "Sursă"]
        )
        page.table.setRowCount(len(rows))
        page.table.setProperty("rows", rows)

        for i, row in enumerate(rows):
            meta = _procedure_meta(self, row)
            values = [
                meta["status"],
                meta["module_address"] or "GENERAL",
                row["title"],
                row["vcds_path"],
                row["applicability"],
                meta["source_badge"],
            ]
            for j, value in enumerate(values):
                item = QTableWidgetItem(str(value or ""))
                if j == 0:
                    item.setToolTip(
                        "Confirmat Auto-Scan = modul găsit în scanarea mașinii. Potrivit generației = catalog V2; confirmă controllerul înainte de scriere."
                    )
                page.table.setItem(i, j, item)

        header = page.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)

        overview = getattr(self, "_coding_overview", None)
        if overview is not None:
            confirmed = sum(1 for row in rows if _procedure_meta(self, row)["status"] == "CONFIRMAT AUTOSCAN")
            overview._kid_count.setText(f"{len(rows)} CODĂRI")
            overview._kid_scan_state.setText(
                f"AUTO-SCAN: {confirmed} CONFIRMATE" if getattr(self, "current_autoscan", None) else "AUTO-SCAN: NEÎNCĂRCAT"
            )

        if rows:
            page.table.selectRow(0)
            self._show_procedure(page)
        else:
            ctx = selected_vehicle_context(self)
            page.detail.setHtml(
                "<h3>Nicio codare documentată nu corespunde filtrului.</h3>"
                f"<p>Vehicul activ: <b>{escape(_vehicle_text(ctx))}</b></p>"
                "<p>Șterge textul de căutare sau încarcă Auto-Scan-ul pentru confirmarea modulelor. Nu vor fi inventate valori de coding.</p>"
            )

    def show_procedure_vehicle_first(self, page):
        if page is not (getattr(self, "_workspace_pages", {}) or {}).get(3):
            return previous_show_procedure(self, page)
        row_index = page.table.currentRow()
        rows = page.table.property("rows") or []
        if row_index < 0 or row_index >= len(rows):
            return
        page.detail.setHtml(_render_coding_detail(self, rows[row_index]))

    def open_page_vehicle_first(self, index):
        previous_open_page(self, index)
        refresh_context(self)
        if int(index) == 3 and self.selected_generation_id:
            page = (getattr(self, "_workspace_pages", {}) or {}).get(3)
            if page is not None:
                self._load_procedures(page)
                self.setWindowTitle(f"KID Diagnostic V2 • Codări • {_vehicle_text(selected_vehicle_context(self))} • v2.2.0")

    cls.__init__ = init_vehicle_first
    cls._select_vehicle = select_vehicle_precise
    cls._load_procedures = load_procedures_vehicle_first
    cls._show_procedure = show_procedure_vehicle_first
    cls.open_page = open_page_vehicle_first
    cls.refresh_vehicle_context_v220 = refresh_context
    cls._kid_vehicle_first_applied = True


__all__ = [
    "VEHICLE_FIRST_VERSION",
    "selected_vehicle_context",
    "apply",
]
