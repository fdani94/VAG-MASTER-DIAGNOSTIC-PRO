"""Master UI/data integration patch for KID Diagnostic V2.

Keeps the modern shell small while wiring the large local database into:
- DTC search and full workshop detail
- live-data reference search
- model/platform module filtering
- coding/adaptation/service catalog entries
- custom KID logo in the app and PDF
- distinct dashboard illustrations
"""

from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtCore import Qt, QMarginsF
from PySide6.QtGui import (
    QColor, QFont, QPainter, QPen, QPixmap, QTextDocument,
    QPdfWriter, QPageLayout, QPageSize,
)
from PySide6.QtWidgets import QLabel, QMessageBox, QFileDialog, QHeaderView

import appdb as db


def _table_columns(con, table: str) -> set[str]:
    try:
        return {r[1] for r in con.execute(f"PRAGMA table_info({table})")}
    except Exception:
        return set()


def _row_get(row, key: str, default=""):
    try:
        value = row[key]
    except Exception:
        return default
    return default if value is None else value


def _fmt_int(value) -> str:
    return f"{int(value or 0):,}".replace(",", ".")


def _vehicle_context(window) -> str:
    if not window.selected_generation_id:
        return ""
    h = db.vehicle_header(window.con, window.selected_generation_id)
    engine = window.engine_combo.currentText() if hasattr(window, "engine_combo") else ""
    parts = [
        _row_get(h, "brand"), _row_get(h, "model"), _row_get(h, "name"),
        _row_get(h, "chassis"), _row_get(h, "platform"),
        str(window.selected_year or ""), engine,
    ]
    return " ".join(str(x) for x in parts if x).lower()


def _is_catalog_applicable(applicability: str, context: str) -> bool:
    text = (applicability or "").strip().lower()
    if not text:
        return True
    generic = ("vag", "generic", "universal", "toate", "all models", "mai multe", "platform")
    if any(token in text for token in generic):
        return True
    if not context:
        return True
    tokens = {
        token.strip("()[]/,-.")
        for token in context.replace("•", " ").split()
        if len(token.strip("()[]/,-.")) >= 2
    }
    return any(token and token in text for token in tokens)


def _paint_card_art(self, _event):
    p = QPainter(self)
    p.setRenderHint(QPainter.Antialiasing)
    r = self.rect().adjusted(3, 3, -3, -3)
    from PySide6.QtGui import QLinearGradient
    g = QLinearGradient(r.topLeft(), r.bottomRight())
    g.setColorAt(0, QColor("#123b67"))
    g.setColorAt(0.55, QColor("#0b2744"))
    g.setColorAt(1, QColor("#06131f"))
    p.setBrush(g)
    p.setPen(QPen(QColor("#1b557d"), 1))
    p.drawRoundedRect(r, 18, 18)

    x, y, w, h = r.x(), r.y(), r.width(), r.height()
    cyan = QColor("#36c0ff")
    pale = QColor("#dff4ff")
    dim = QColor("#4f7592")
    code = str(getattr(self, "code", "")).upper()

    p.setPen(QPen(cyan, 4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)

    if code == "SCAN":
        p.drawLine(x+w*.18, y+h*.62, x+w*.80, y+h*.62)
        p.drawLine(x+w*.29, y+h*.62, x+w*.39, y+h*.39)
        p.drawLine(x+w*.39, y+h*.39, x+w*.62, y+h*.39)
        p.drawLine(x+w*.62, y+h*.39, x+w*.73, y+h*.62)
        p.drawEllipse(int(x+w*.28), int(y+h*.55), 18, 18)
        p.drawEllipse(int(x+w*.65), int(y+h*.55), 18, 18)
        p.setPen(QPen(pale, 2))
        for k in range(3):
            yy = int(y + h*(.22 + k*.11))
            p.drawLine(int(x+w*.13), yy, int(x+w*.28), yy)

    elif code == "DTC":
        pts = [
            (int(x+w*.50), int(y+h*.20)),
            (int(x+w*.27), int(y+h*.72)),
            (int(x+w*.73), int(y+h*.72)),
        ]
        from PySide6.QtGui import QPolygon
        from PySide6.QtCore import QPoint
        p.drawPolygon(QPolygon([QPoint(a,b) for a,b in pts]))
        p.setPen(QPen(pale, 5, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(int(x+w*.50), int(y+h*.37), int(x+w*.50), int(y+h*.53))
        p.drawPoint(int(x+w*.50), int(y+h*.62))

    elif code == "CODE":
        p.drawLine(int(x+w*.31), int(y+h*.28), int(x+w*.20), int(y+h*.46))
        p.drawLine(int(x+w*.20), int(y+h*.46), int(x+w*.31), int(y+h*.64))
        p.drawLine(int(x+w*.69), int(y+h*.28), int(x+w*.80), int(y+h*.46))
        p.drawLine(int(x+w*.80), int(y+h*.46), int(x+w*.69), int(y+h*.64))
        p.setPen(QPen(pale, 3))
        for frac in (.39,.47,.55,.63):
            xx = int(x+w*frac)
            p.drawLine(xx, int(y+h*.34), xx, int(y+h*.58))

    elif code == "ADAPT":
        for frac, knob in ((.30,.40),(.48,.63),(.66,.48)):
            yy = int(y+h*frac)
            p.drawLine(int(x+w*.24), yy, int(x+w*.76), yy)
            p.setBrush(QColor("#0c2740"))
            p.drawEllipse(int(x+w*knob)-7, yy-7, 14, 14)
            p.setBrush(Qt.NoBrush)

    elif code == "SERV":
        p.drawArc(int(x+w*.27), int(y+h*.21), int(w*.28), int(h*.32), 35*16, 270*16)
        p.drawLine(int(x+w*.46), int(y+h*.45), int(x+w*.70), int(y+h*.69))
        p.drawEllipse(int(x+w*.66), int(y+h*.64), 12, 12)

    elif code == "LIVE":
        p.setPen(QPen(dim, 2))
        p.drawLine(int(x+w*.20), int(y+h*.70), int(x+w*.80), int(y+h*.70))
        p.drawLine(int(x+w*.20), int(y+h*.25), int(x+w*.20), int(y+h*.70))
        p.setPen(QPen(cyan, 4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        points = [(0.24,.60),(0.34,.49),(0.43,.56),(0.53,.32),(0.64,.43),(0.76,.25)]
        for a,b in zip(points, points[1:]):
            p.drawLine(int(x+w*a[0]), int(y+h*a[1]), int(x+w*b[0]), int(y+h*b[1]))

    elif code == "MOD":
        nodes = [(0.30,.35),(0.66,.30),(0.50,.66),(0.75,.67)]
        p.setPen(QPen(dim, 2))
        for a,b in ((0,2),(1,2),(2,3),(1,3)):
            p.drawLine(int(x+w*nodes[a][0]), int(y+h*nodes[a][1]),
                       int(x+w*nodes[b][0]), int(y+h*nodes[b][1]))
        p.setPen(QPen(cyan, 3))
        p.setBrush(QColor("#0a263e"))
        for nx,ny in nodes:
            p.drawRoundedRect(int(x+w*nx)-10, int(y+h*ny)-8, 20, 16, 4, 4)
        p.setBrush(Qt.NoBrush)

    elif code == "PDF":
        px, py, pw, ph = int(x+w*.34), int(y+h*.18), int(w*.34), int(h*.60)
        p.drawRoundedRect(px, py, pw, ph, 6, 6)
        p.setPen(QPen(pale, 2))
        for frac in (.38,.49,.60):
            yy = int(y+h*frac)
            p.drawLine(int(x+w*.40), yy, int(x+w*.62), yy)
        p.setFont(QFont("Arial", 9, QFont.Bold))
        p.drawText(px, int(y+h*.22), pw, int(h*.15), Qt.AlignCenter, "KID")

    p.setPen(pale)
    f = QFont("Arial", 9)
    f.setBold(True)
    p.setFont(f)
    p.drawText(r.adjusted(10, 7, -10, -7), Qt.AlignRight | Qt.AlignTop, code)


def _paint_brand(self, _event):
    p = QPainter(self)
    p.setRenderHint(QPainter.Antialiasing)
    logo = Path(db.LOGO_PATH)
    if logo.exists():
        pix = QPixmap(str(logo))
        if not pix.isNull():
            pix = pix.scaled(52, 52, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            p.drawPixmap((self.width()-pix.width())//2, (self.height()-pix.height())//2, pix)
            return
    p.setBrush(QColor("#061425"))
    p.setPen(QPen(QColor("#20aaff"), 3))
    p.drawEllipse(3, 3, 52, 52)
    p.setPen(QColor("#eef8ff"))
    f = QFont("Arial", 15)
    f.setBold(True)
    p.setFont(f)
    p.drawText(self.rect(), Qt.AlignCenter, "KID")


def apply():
    import ui_v2
    if getattr(ui_v2, "_kid_master_ui_patch", False):
        return
    MainWindowV2 = ui_v2.MainWindowV2
    ui_v2.CardArt.paintEvent = _paint_card_art
    ui_v2.BrandMark.paintEvent = _paint_brand

    old_init = MainWindowV2.__init__
    old_dtc_page = MainWindowV2._dtc

    def __init__(self, *args, **kwargs):
        old_init(self, *args, **kwargs)
        self.generation_combo = self.gen_combo
        self._stats()

    def _dtc(self):
        page = old_dtc_page(self)
        self.dtc_count_label = QLabel("Baza DTC se încarcă după selectarea vehiculului.")
        self.dtc_count_label.setObjectName("summaryStrip")
        page.layout().insertWidget(2, self.dtc_count_label)
        return page

    def _stats(self):
        total = self.con.execute("SELECT COUNT(*) FROM dtcs").fetchone()[0]
        cols = _table_columns(self.con, "dtcs")
        if "confidence" in cols:
            index_only = self.con.execute("SELECT COUNT(*) FROM dtcs WHERE confidence='index-only'").fetchone()[0]
        else:
            index_only = 0
        detailed = max(0, total - index_only)
        verified = self.con.execute("SELECT COUNT(*) FROM dtcs WHERE verified=1").fetchone()[0]
        proc = self.con.execute("SELECT COUNT(*) FROM procedure_library").fetchone()[0]
        coding = self.con.execute("SELECT COUNT(*) FROM coding").fetchone()[0] if _table_columns(self.con, "coding") else 0
        adapt = self.con.execute("SELECT COUNT(*) FROM adaptations").fetchone()[0] if _table_columns(self.con, "adaptations") else 0
        mods = self.con.execute("SELECT COUNT(*) FROM modules").fetchone()[0]
        self.stat_dtc.value_label.setText(_fmt_int(total))
        self.stat_dtc.setToolTip(f"{_fmt_int(detailed)} fișe cu detalii locale • {_fmt_int(verified)} marcate verificate • {_fmt_int(index_only)} coduri numeric-index pentru recunoaștere Auto-Scan.")
        self.stat_proc.value_label.setText(_fmt_int(proc + coding + adapt))
        self.stat_proc.setToolTip(f"{_fmt_int(proc)} proceduri • {_fmt_int(coding)} intrări coding • {_fmt_int(adapt)} adaptări.")
        self.stat_mod.value_label.setText(_fmt_int(mods))

    def _load_dtcs(self):
        q = self.dtc_search.text().strip()
        cols = _table_columns(self.con, "dtcs")
        wanted = ["code", "title", "severity", "verified", "description", "symptoms", "causes", "diagnosis", "repair", "component", "component_location", "vcds_parameters", "expected_values", "test_path", "replacement_steps", "confidence", "module_hint", "source_id"]
        select_cols = [c for c in wanted if c in cols]
        searchable = [c for c in ("code", "title", "description", "symptoms", "causes", "component", "component_location", "module_hint") if c in cols]
        if q and searchable:
            like = f"%{q}%"
            where = " OR ".join(f"{c} LIKE ?" for c in searchable)
            count = self.con.execute(f"SELECT COUNT(*) FROM dtcs WHERE {where}", [like]*len(searchable)).fetchone()[0]
            rows = self.con.execute(f"SELECT {','.join(select_cols)} FROM dtcs WHERE {where} ORDER BY verified DESC, code LIMIT 5000", [like]*len(searchable)).fetchall()
        else:
            count = self.con.execute("SELECT COUNT(*) FROM dtcs").fetchone()[0]
            rows = self.con.execute(f"SELECT {','.join(select_cols)} FROM dtcs ORDER BY verified DESC, code LIMIT 3000").fetchall()
        self.dtc_table.setRowCount(len(rows))
        self.dtc_table.setProperty("rows", rows)
        for i, r in enumerate(rows):
            confidence = str(_row_get(r, "confidence", ""))
            if confidence == "index-only": status = "INDEX LOCAL"
            elif int(_row_get(r, "verified", 0) or 0): status = "VERIFICAT"
            else: status = "BAZĂ LOCALĂ"
            vals = [_row_get(r, "code"), _row_get(r, "title"), _row_get(r, "severity", "—"), status]
            for j, value in enumerate(vals): self.dtc_table.setItem(i, j, ui_v2.QTableWidgetItem(str(value)))
        self.dtc_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        if hasattr(self, "dtc_count_label"):
            suffix = "" if len(rows) == count else f" • afișate primele {_fmt_int(len(rows))}"
            self.dtc_count_label.setText(f"Rezultate DTC: {_fmt_int(count)}{suffix}. „INDEX LOCAL” recunoaște codul, dar nu pretinde o procedură exactă.")

    def _show_dtc(self):
        row = self.dtc_table.currentRow(); rows = self.dtc_table.property("rows") or []
        if row < 0 or row >= len(rows): return
        r = rows[row]
        confidence = str(_row_get(r, "confidence", ""))
        index_note = ""
        if confidence == "index-only":
            index_note = "ATENȚIE — FIȘĂ INDEX LOCAL\nCodul este recunoscut în baza numerică, însă denumirea exactă, modulul și procedura se confirmă din Auto-Scan-ul real al mașinii. Nu înlocui piese doar pe baza acestei fișe.\n\n"
        source = ""; source_id = _row_get(r, "source_id", "")
        if source_id:
            src = self.con.execute("SELECT title,publisher,url,source_type FROM sources WHERE id=?", (source_id,)).fetchone()
            if src: source = f"\n\nSURSĂ / NIVEL\n{_row_get(src,'source_type')} • {_row_get(src,'publisher')} • {_row_get(src,'title')}\n{_row_get(src,'url')}"
        self.dtc_detail.setPlainText(
            f"{_row_get(r,'code')} • {_row_get(r,'title')}\n\n{index_note}"
            f"DESCRIERE\n{_row_get(r,'description','—')}\n\nSIMPTOME POSIBILE\n{_row_get(r,'symptoms','—')}\n\nCAUZE POSIBILE\n{_row_get(r,'causes','—')}\n\n"
            f"PIESA / SISTEMUL IMPLICAT\n{_row_get(r,'component','—')}\n\nUNDE SE AFLĂ\n{_row_get(r,'component_location','—')}\n\nCE VERIFICI ÎN VCDS\n{_row_get(r,'vcds_parameters','—')}\n\n"
            f"VALORI / COMPORTAMENT AȘTEPTAT\n{_row_get(r,'expected_values','—')}\n\nTRASEU ÎN VCDS\n{_row_get(r,'test_path','—')}\n\nDIAGNOSTIC PAS CU PAS\n{_row_get(r,'diagnosis','—')}\n\n"
            f"CUM O REPARI\n{_row_get(r,'repair','—')}\n\nDUPĂ ÎNLOCUIREA PIESEI\n{_row_get(r,'replacement_steps','—')}\n\nSEVERITATE\n{_row_get(r,'severity','—')}{source}"
        )

    def _load_live(self):
        q = self.live_search.text().strip(); cols = _table_columns(self.con, "dtcs")
        needed = {"code", "title", "vcds_parameters", "expected_values"}
        if not needed.issubset(cols): self.live_table.setRowCount(0); return
        like = f"%{q}%"; confidence_filter = " AND (confidence IS NULL OR confidence<>'index-only')" if "confidence" in cols else ""
        rows = self.con.execute("SELECT code,title,vcds_parameters,expected_values FROM dtcs WHERE (COALESCE(vcds_parameters,'')<>'' OR COALESCE(expected_values,'')<>'') AND (code LIKE ? OR title LIKE ? OR vcds_parameters LIKE ? OR expected_values LIKE ?)" + confidence_filter + " ORDER BY verified DESC, code LIMIT 2000", (like, like, like, like)).fetchall()
        self.live_table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            vals = [r["code"], r["title"], r["vcds_parameters"], r["expected_values"]]
            for j, value in enumerate(vals): self.live_table.setItem(i, j, ui_v2.QTableWidgetItem(str(value or "—")))
        self.live_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.live_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.live_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)

    def _load_modules(self):
        rows = self.con.execute("""SELECT m.address,m.name,m.family,m.protocol FROM generation_modules gm JOIN modules m ON m.id=gm.module_id WHERE gm.generation_id=? ORDER BY m.address,m.name""", (self.selected_generation_id,)).fetchall()
        if not rows: rows = db.modules_for_vehicle(self.con, self.selected_generation_id)
        self.module_table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            for j, key in enumerate(("address", "name", "family", "protocol")): self.module_table.setItem(i, j, ui_v2.QTableWidgetItem(str(r[key] or "—")))
        self.module_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)

    def _catalog_rows(self, page):
        context = _vehicle_context(self); items = []
        for r in db.procedures_for_vehicle(self.con, self.selected_generation_id):
            hay = f'{r["category"]} {r["title"]} {r["vcds_path"]} {r["purpose"]}'.lower()
            if any(k in hay for k in page.keywords): items.append(dict(r))
        keys = set(page.keywords)
        if {"coding", "codare", "long coding"} & keys and _table_columns(self.con, "coding"):
            for r in self.con.execute("""SELECT c.*,s.url source_url,s.title source_title FROM coding c LEFT JOIN sources s ON s.id=c.source_id ORDER BY c.title"""):
                if not _is_catalog_applicable(_row_get(r, "applicability"), context): continue
                items.append({"category":"Codare • catalog","title":_row_get(r,"title"),"module_address":_row_get(r,"module_address"),"vcds_path":f'[{_row_get(r,"module_address","modul")}] > {_row_get(r,"coding_type","Coding")}',"purpose":_row_get(r,"effect"),"prerequisites":"Salvează Auto-Scan-ul și valoarea/codarea originală. Confirmă part number, software și echiparea înainte de scriere.","steps":"Folosește numai valoarea/codarea documentată pentru controllerul exact. Catalogul nu inventează un byte/bit universal când acesta nu este stocat în fișă.","success_criteria":_row_get(r,"effect"),"warnings":_row_get(r,"warnings"),"applicability":_row_get(r,"applicability"),"notes":f'Restaurare: {_row_get(r,"restore_method","—")}',"source_url":_row_get(r,"source_url"),"source_title":_row_get(r,"source_title"),"verified":_row_get(r,"verified",0)})
        if ({"adaptation", "adaptare", "basic settings"} & keys or {"service", "dpf", "epb", "battery", "reset", "brake"} & keys) and _table_columns(self.con, "adaptations"):
            service_mode = bool({"service", "dpf", "epb", "battery", "reset", "brake"} & keys)
            for r in self.con.execute("""SELECT a.*,s.url source_url,s.title source_title FROM adaptations a LEFT JOIN sources s ON s.id=a.source_id ORDER BY a.title"""):
                hay = f'{_row_get(r,"title")} {_row_get(r,"channel")} {_row_get(r,"effect")}'.lower()
                if service_mode and not any(k in hay for k in page.keywords): continue
                if not _is_catalog_applicable(_row_get(r, "applicability"), context): continue
                channel = _row_get(r, "channel", "")
                items.append({"category":"Adaptare • catalog","title":_row_get(r,"title"),"module_address":_row_get(r,"module_address"),"vcds_path":f'[{_row_get(r,"module_address","modul")}] > Adaptation' + (f' > {channel}' if channel else ''),"purpose":_row_get(r,"effect"),"prerequisites":"Salvează Auto-Scan-ul și valoarea originală. Confirmă controllerul și condițiile procedurii înainte de schimbare.","steps":"Selectează canalul/funcția numai dacă este prezentă pe controllerul real. Nu folosi valori presupuse dacă fișa nu conține o valoare explicită.","success_criteria":_row_get(r,"effect"),"warnings":_row_get(r,"warnings"),"applicability":_row_get(r,"applicability"),"notes":f'Restaurare: {_row_get(r,"restore_method","—")}',"source_url":_row_get(r,"source_url"),"source_title":_row_get(r,"source_title"),"verified":_row_get(r,"verified",0)})
        out, seen = [], set()
        for item in items:
            key = (str(item.get("title", "")).strip().lower(), str(item.get("module_address", "")).strip().lower())
            if key in seen: continue
            seen.add(key); out.append(item)
        return out

    def _load_procedures(self, page):
        search = page.search.text().lower().strip(); rows = self._catalog_rows(page)
        if search: rows = [r for r in rows if search in " ".join(str(r.get(k, "")) for k in ("category", "title", "module_address", "vcds_path", "purpose", "applicability")).lower()]
        page.table.setRowCount(len(rows)); page.table.setProperty("rows", rows)
        for i, r in enumerate(rows):
            vals = [r.get("category", ""), r.get("title", ""), r.get("module_address", ""), r.get("vcds_path", ""), r.get("applicability", "")]
            for j, value in enumerate(vals): page.table.setItem(i, j, ui_v2.QTableWidgetItem(str(value or "—")))
        page.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)

    def _show_procedure(self, page):
        row = page.table.currentRow(); rows = page.table.property("rows") or []
        if row < 0 or row >= len(rows): return
        r = rows[row]; verified = "VERIFICAT" if int(r.get("verified", 0) or 0) else "DE CONFIRMAT PE CONTROLLER"
        page.detail.setPlainText(f'{r.get("title","")}\n\nNIVEL FIȘĂ\n{verified}\n\nCATEGORIE\n{r.get("category","—")}\n\nMODUL\n{r.get("module_address","—")}\n\nCALE ÎN VCDS\n{r.get("vcds_path","—")}\n\nSCOP / EFECT\n{r.get("purpose","—")}\n\nCONDIȚII\n{r.get("prerequisites","—")}\n\nPAȘI\n{r.get("steps","—")}\n\nREZULTAT CORECT\n{r.get("success_criteria","—")}\n\nATENȚIONĂRI\n{r.get("warnings","—")}\n\nAPLICABILITATE\n{r.get("applicability","—")}\n\nRESTAURARE / NOTE\n{r.get("notes","—")}\n\nSURSĂ\n{r.get("source_title","—")}\n{r.get("source_url","")}')

    def _export_pdf(self):
        if not self.current_autoscan or not self.autoscan_plans:
            QMessageBox.warning(self, "Raport PDF", "Încarcă mai întâi un Auto-Scan VCDS cu erori."); self.open_page(1); return
        suggested = f"KID_Diagnostic_{Path(self.current_autoscan.source_path).stem}_V2.pdf"
        path, _ = QFileDialog.getSaveFileName(self, "Salvează raportul KID Diagnostic", suggested, "PDF (*.pdf)")
        if not path: return
        if not path.lower().endswith(".pdf"): path += ".pdf"
        try:
            html = ui_v2._build_html(self); custom_logo = Path(db.LOGO_PATH)
            if custom_logo.exists():
                uri = custom_logo.resolve().as_uri(); html = re.sub(r"(<img class='logo' src=')[^']+('>)", lambda m: m.group(1) + uri + m.group(2), html, count=1)
            writer = QPdfWriter(path); writer.setTitle("KID Diagnostic V2 - Raport Auto-Scan VCDS"); writer.setCreator("KID Diagnostic"); writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4)); writer.setPageMargins(QMarginsF(14,14,14,14), QPageLayout.Unit.Millimeter); writer.setResolution(120)
            doc = QTextDocument(); doc.setHtml(html); doc.print_(writer)
        except Exception as exc:
            QMessageBox.critical(self, "Raport PDF", f"Raportul nu a putut fi salvat:\n{exc}"); return
        QMessageBox.information(self, "Raport PDF", f"Raport salvat:\n{path}")

    MainWindowV2.__init__ = __init__; MainWindowV2._dtc = _dtc; MainWindowV2._stats = _stats
    MainWindowV2._load_dtcs = _load_dtcs; MainWindowV2._show_dtc = _show_dtc; MainWindowV2._load_live = _load_live
    MainWindowV2._load_modules = _load_modules; MainWindowV2._catalog_rows = _catalog_rows; MainWindowV2._load_procedures = _load_procedures
    MainWindowV2._show_procedure = _show_procedure; MainWindowV2._export_pdf = _export_pdf
    ui_v2._kid_master_ui_patch = True
