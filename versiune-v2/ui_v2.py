from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PySide6.QtCore import Qt, QMarginsF
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QLinearGradient, QTextDocument, QPdfWriter, QPageLayout, QPageSize
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFrame, QLabel, QPushButton, QLineEdit,
    QVBoxLayout, QHBoxLayout, QGridLayout, QStackedWidget, QComboBox,
    QFileDialog, QMessageBox, QTextEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QSplitter
)

import appdb as db
from autoscan_parser import parse_autoscan_file, diagnostic_plan
from autoscan_correlation import correlate, render_correlation
from autoscan_ro import ro_status, ro_module, ro_title, ro_confidence, ro_vcds_note
from ui_autoscan_pdf_export import _build_html


CARDS = [
    ("Auto-Scan VCDS", "Import TXT / LOG / PDF, analiză și plan diagnostic.", "SCAN", 1),
    ("Coduri DTC", "Cauze, simptome, verificări și reparații.", "DTC", 2),
    ("Codări", "Coding, Long Coding și activări pe model.", "CODE", 3),
    ("Adaptări", "Adaptation, Basic Settings și calibrări.", "ADAPT", 4),
    ("Service & Resetări", "DPF, EPB, baterie, service și resetări.", "SERV", 5),
    ("Date Live", "Parametri, valori de referință și verificări.", "LIVE", 6),
    ("Module & Ghiduri", "Module, adrese și trasee VCDS.", "MOD", 7),
    ("Rapoarte", "Rapoarte PDF KID Diagnostic profesionale.", "PDF", 8),
]


class BrandMark(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(58, 58)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QColor("#061425"))
        p.setPen(QPen(QColor("#20aaff"), 3))
        p.drawEllipse(3, 3, 52, 52)
        p.setPen(QColor("#eef8ff"))
        f = QFont("Arial", 15)
        f.setBold(True)
        p.setFont(f)
        p.drawText(self.rect(), Qt.AlignCenter, "KID")


class CardArt(QWidget):
    def __init__(self, code):
        super().__init__()
        self.code = code
        self.setMinimumHeight(92)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = self.rect().adjusted(3, 3, -3, -3)
        g = QLinearGradient(r.topLeft(), r.bottomRight())
        g.setColorAt(0, QColor("#12365d"))
        g.setColorAt(1, QColor("#071522"))
        p.setBrush(g)
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(r, 18, 18)
        p.setPen(QPen(QColor("#29b8ff"), 4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        x, y, w, h = r.x(), r.y(), r.width(), r.height()
        p.drawLine(x + int(w*.20), y + int(h*.63), x + int(w*.80), y + int(h*.63))
        p.drawLine(x + int(w*.31), y + int(h*.63), x + int(w*.40), y + int(h*.39))
        p.drawLine(x + int(w*.40), y + int(h*.39), x + int(w*.63), y + int(h*.39))
        p.drawLine(x + int(w*.63), y + int(h*.39), x + int(w*.72), y + int(h*.63))
        p.drawEllipse(x + int(w*.30), y + int(h*.55), 18, 18)
        p.drawEllipse(x + int(w*.64), y + int(h*.55), 18, 18)
        p.setPen(QColor("#dff2ff"))
        f = QFont("Arial", 10)
        f.setBold(True)
        p.setFont(f)
        p.drawText(r.adjusted(12, 8, -12, -8), Qt.AlignRight | Qt.AlignTop, self.code)


class FeatureCard(QFrame):
    def __init__(self, title, subtitle, code, callback):
        super().__init__()
        self.setObjectName("featureCard")
        l = QVBoxLayout(self)
        l.setContentsMargins(16, 16, 16, 16)
        l.setSpacing(9)
        l.addWidget(CardArt(code))
        a = QLabel(title); a.setObjectName("cardTitle")
        b = QLabel(subtitle); b.setObjectName("cardSubtitle"); b.setWordWrap(True)
        btn = QPushButton("DESCHIDE"); btn.setObjectName("cardButton"); btn.clicked.connect(callback)
        l.addWidget(a); l.addWidget(b); l.addStretch(); l.addWidget(btn)


class MainWindowV2(QMainWindow):
    def __init__(self):
        super().__init__()
        self.con = db.connect_db()
        self.selected_generation_id = None
        self.selected_year = None
        self.current_autoscan = None
        self.autoscan_plans = []
        self.autoscan_correlation = None
        self.setWindowTitle("KID Diagnostic • VAG MASTER PRO V2")
        self.resize(1540, 920)
        self.setMinimumSize(1180, 740)
        self._build()
        self._style()
        self._load_brands()
        self._stats()

    def closeEvent(self, event):
        try:
            self.con.close()
        finally:
            super().closeEvent(event)

    def _build(self):
        root = QWidget(); rl = QVBoxLayout(root); rl.setContentsMargins(0,0,0,0); rl.setSpacing(0)
        top = QFrame(); top.setObjectName("topbar"); tl = QHBoxLayout(top); tl.setContentsMargins(24,15,24,15)
        tl.addWidget(BrandMark())
        bb = QVBoxLayout(); a = QLabel("KID DIAGNOSTIC"); a.setObjectName("brandTitle"); b = QLabel("VAG MASTER PRO • V2"); b.setObjectName("brandSub"); bb.addWidget(a); bb.addWidget(b); tl.addLayout(bb); tl.addStretch()
        self.vehicle_badge = QLabel("Niciun vehicul selectat"); self.vehicle_badge.setObjectName("vehicleBadge"); tl.addWidget(self.vehicle_badge)
        change = QPushButton("Schimbă vehicul"); change.setObjectName("secondaryButton"); change.clicked.connect(lambda: self.open_page(0)); tl.addWidget(change)
        rl.addWidget(top)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._dashboard())
        self.stack.addWidget(self._autoscan())
        self.stack.addWidget(self._dtc())
        self.stack.addWidget(self._procedures("Codări", ["coding", "codare", "long coding"]))
        self.stack.addWidget(self._procedures("Adaptări", ["adaptation", "adaptare", "basic settings"]))
        self.stack.addWidget(self._procedures("Service & Resetări", ["service", "dpf", "epb", "battery", "reset", "brake"]))
        self.stack.addWidget(self._live())
        self.stack.addWidget(self._modules())
        self.stack.addWidget(self._reports())
        rl.addWidget(self.stack, 1)
        self.setCentralWidget(root)

    def _shell(self, title, subtitle):
        page = QWidget(); l = QVBoxLayout(page); l.setContentsMargins(28,24,28,24); l.setSpacing(15)
        row = QHBoxLayout(); back = QPushButton("← Dashboard"); back.setObjectName("secondaryButton"); back.clicked.connect(self.show_dashboard); row.addWidget(back)
        box = QVBoxLayout(); h = QLabel(title); h.setObjectName("pageTitle"); s = QLabel(subtitle); s.setObjectName("pageSubtitle"); s.setWordWrap(True); box.addWidget(h); box.addWidget(s); row.addLayout(box,1); l.addLayout(row)
        return page, l

    def _dashboard(self):
        page = QWidget(); l = QVBoxLayout(page); l.setContentsMargins(34,26,34,26); l.setSpacing(17)
        hero = QFrame(); hero.setObjectName("heroPanel"); hl = QVBoxLayout(hero); hl.setContentsMargins(26,20,26,20)
        h = QLabel("VAG MASTER Diagnostic PRO"); h.setObjectName("heroTitle")
        s = QLabel("Selectează vehiculul, apoi intră în funcția dorită. Fiecare operație are propriul workspace, fără ecrane aglomerate."); s.setObjectName("heroSub"); s.setWordWrap(True)
        hl.addWidget(h); hl.addWidget(s); l.addWidget(hero)

        sel = QFrame(); sel.setObjectName("selectorPanel"); g = QGridLayout(sel); g.setContentsMargins(20,18,20,18); g.setHorizontalSpacing(10)
        self.brand_combo = QComboBox(); self.model_combo = QComboBox(); self.gen_combo = QComboBox(); self.year_combo = QComboBox(); self.engine_combo = QComboBox()
        self.brand_combo.currentIndexChanged.connect(self._load_models); self.model_combo.currentIndexChanged.connect(self._load_generations); self.gen_combo.currentIndexChanged.connect(self._load_years_engines)
        fields = [("Marcă",self.brand_combo),("Model",self.model_combo),("Generație / chassis",self.gen_combo),("An",self.year_combo),("Motor",self.engine_combo)]
        for i,(name,w) in enumerate(fields):
            q=QLabel(name); q.setObjectName("fieldLabel"); g.addWidget(q,0,i); g.addWidget(w,1,i)
        choose = QPushButton("DESCHIDE VEHICULUL"); choose.setObjectName("primaryButton"); choose.clicked.connect(self._select_vehicle); g.addWidget(choose,2,0,1,5)
        l.addWidget(sel)

        sr = QHBoxLayout(); self.stat_dtc=self._stat("DTC","—"); self.stat_proc=self._stat("Proceduri","—"); self.stat_mod=self._stat("Module","—"); self.stat_cov=self._stat("Acoperire","1996–2024")
        for w in (self.stat_dtc,self.stat_proc,self.stat_mod,self.stat_cov): sr.addWidget(w)
        l.addLayout(sr)
        cards = QWidget(); cg = QGridLayout(cards); cg.setContentsMargins(0,3,0,0); cg.setSpacing(13)
        for i,(title,sub,code,idx) in enumerate(CARDS): cg.addWidget(FeatureCard(title,sub,code,lambda _=False,x=idx:self.open_page(x)),i//4,i%4)
        l.addWidget(cards,1)
        return page

    def _stat(self, title, value):
        f=QFrame(); f.setObjectName("statCard"); l=QVBoxLayout(f); l.setContentsMargins(15,11,15,11); a=QLabel(title); a.setObjectName("statLabel"); b=QLabel(str(value)); b.setObjectName("statValue"); l.addWidget(a); l.addWidget(b); f.value_label=b; return f

    def _autoscan(self):
        page,l=self._shell("Auto-Scan VCDS","Încarcă raport TXT / LOG / PDF. Erorile sunt explicate în română și corelate între module.")
        row=QHBoxLayout(); load=QPushButton("Încarcă Auto-Scan"); load.setObjectName("primaryButton"); load.clicked.connect(self._load_autoscan); plan=QPushButton("Plan diagnostic automat"); plan.setObjectName("secondaryButton"); plan.clicked.connect(self._show_correlation); pdf=QPushButton("Salvează raport PDF"); pdf.setObjectName("secondaryButton"); pdf.clicked.connect(self._export_pdf); row.addWidget(load); row.addWidget(plan); row.addWidget(pdf); row.addStretch(); l.addLayout(row)
        self.autoscan_summary=QLabel("Niciun raport încărcat."); self.autoscan_summary.setObjectName("summaryStrip"); l.addWidget(self.autoscan_summary)
        split=QSplitter(Qt.Horizontal); self.autoscan_table=self._table(["Modul","Cod","Explicație","Stare","Nivel"]); self.autoscan_table.itemSelectionChanged.connect(self._show_autoscan_fault); self.autoscan_detail=QTextEdit(); self.autoscan_detail.setReadOnly(True); split.addWidget(self.autoscan_table); split.addWidget(self.autoscan_detail); split.setSizes([760,700]); l.addWidget(split,1)
        return page

    def _dtc(self):
        page,l=self._shell("Coduri DTC","Caută după cod, denumire sau simptom în baza locală.")
        self.dtc_search=QLineEdit(); self.dtc_search.setPlaceholderText("Ex.: P0299, 00778, DPF, EGR, steering..."); self.dtc_search.textChanged.connect(self._load_dtcs); l.addWidget(self.dtc_search)
        split=QSplitter(Qt.Horizontal); self.dtc_table=self._table(["Cod","Denumire","Severitate","Status"]); self.dtc_table.itemSelectionChanged.connect(self._show_dtc); self.dtc_detail=QTextEdit(); self.dtc_detail.setReadOnly(True); split.addWidget(self.dtc_table); split.addWidget(self.dtc_detail); split.setSizes([680,780]); l.addWidget(split,1)
        return page

    def _procedures(self,title,keywords):
        page,l=self._shell(title,f"Proceduri {title.lower()} filtrate pentru vehiculul selectat.")
        page.keywords=keywords; page.search=QLineEdit(); page.search.setPlaceholderText(f"Caută în {title.lower()}..."); l.addWidget(page.search)
        page.table=self._table(["Categorie","Procedură","Modul","Cale VCDS","Aplicabilitate"]); page.detail=QTextEdit(); page.detail.setReadOnly(True); split=QSplitter(Qt.Horizontal); split.addWidget(page.table); split.addWidget(page.detail); split.setSizes([820,620]); l.addWidget(split,1)
        page.search.textChanged.connect(lambda _=None,p=page:self._load_procedures(p)); page.table.itemSelectionChanged.connect(lambda p=page:self._show_procedure(p)); return page

    def _live(self):
        page,l=self._shell("Date Live","Caută parametri și valori de referință din fișele de diagnostic locale.")
        self.live_search=QLineEdit(); self.live_search.setPlaceholderText("boost, EGR, DPF, temperatură, presiune..."); self.live_search.textChanged.connect(self._load_live); l.addWidget(self.live_search)
        self.live_table=self._table(["Cod","Element","Ce verifici","Valori / comportament așteptat"]); l.addWidget(self.live_table,1); return page

    def _modules(self):
        page,l=self._shell("Module & Ghiduri","Module posibile pentru platformă; Auto-Scan confirmă ce este instalat pe mașină.")
        self.module_table=self._table(["Adresă","Modul","Familie","Protocol"]); l.addWidget(self.module_table,1); return page

    def _reports(self):
        page,l=self._shell("Rapoarte","Centrul de raportare KID Diagnostic.")
        box=QFrame(); box.setObjectName("selectorPanel"); bl=QVBoxLayout(box); h=QLabel("Raport Auto-Scan profesional"); h.setObjectName("cardTitle"); s=QLabel("Raportul poate include VIN, module, DTC-uri, cauze, localizarea piesei, valori live, pași de diagnostic și reparație."); s.setObjectName("cardSubtitle"); s.setWordWrap(True); go=QPushButton("Generează din Auto-Scan"); go.setObjectName("primaryButton"); go.clicked.connect(self._export_pdf); bl.addWidget(h); bl.addWidget(s); bl.addWidget(go); l.addWidget(box); l.addStretch(); return page

    def _table(self,headers):
        t=QTableWidget(0,len(headers)); t.setHorizontalHeaderLabels(headers); t.setSelectionBehavior(QAbstractItemView.SelectRows); t.setSelectionMode(QAbstractItemView.SingleSelection); t.setEditTriggers(QAbstractItemView.NoEditTriggers); t.setAlternatingRowColors(True); t.verticalHeader().setVisible(False); t.horizontalHeader().setStretchLastSection(True); return t

    def _load_brands(self):
        self.brand_combo.blockSignals(True); self.brand_combo.clear(); self.brand_combo.addItem("Alege marca",None)
        for r in db.brands(self.con): self.brand_combo.addItem(r["name"],r["id"])
        self.brand_combo.blockSignals(False); self._load_models()

    def _load_models(self):
        self.model_combo.blockSignals(True); self.model_combo.clear(); self.model_combo.addItem("Alege modelul",None); bid=self.brand_combo.currentData()
        if bid:
            for r in db.models_for_brand(self.con,bid): self.model_combo.addItem(r["name"],r["id"])
        self.model_combo.blockSignals(False); self._load_generations()

    def _load_generations(self):
        self.gen_combo.blockSignals(True); self.gen_combo.clear(); self.gen_combo.addItem("Alege generația",None); mid=self.model_combo.currentData()
        if mid:
            for r in db.generations_for_model(self.con,mid): self.gen_combo.addItem(f'{r["name"]} • {r["year_from"]}-{r["year_to"]} • {r["platform"]}',r["id"])
        self.gen_combo.blockSignals(False); self._load_years_engines()

    def _load_years_engines(self):
        self.year_combo.clear(); self.engine_combo.clear(); self.engine_combo.addItem("Nespecificat",None); gid=self.gen_combo.currentData()
        if not gid: return
        h=db.vehicle_header(self.con,gid)
        for y in range(int(h["year_from"]),int(h["year_to"])+1): self.year_combo.addItem(str(y),y)
        for e in db.engines_for_generation(self.con,gid): self.engine_combo.addItem(f'{e["code"]} • {e["fuel"]} {e["displacement"] or ""}L {e["power_hp"] or ""}CP',e["id"])

    def _select_vehicle(self):
        gid=self.gen_combo.currentData()
        if not gid: QMessageBox.warning(self,"Vehicul","Selectează marca, modelul și generația."); return
        self.selected_generation_id=gid; self.selected_year=self.year_combo.currentData(); h=db.vehicle_header(self.con,gid); self.vehicle_badge.setText(f'{h["brand"]} {h["model"]} • {h["name"]} • {self.selected_year or ""} • {self.engine_combo.currentText()}'); db.log(self.con,"select_vehicle_v2","generation",gid,self.vehicle_badge.text())

    def show_dashboard(self): self.stack.setCurrentIndex(0)

    def open_page(self,index):
        if index and not self.selected_generation_id: QMessageBox.warning(self,"Vehicul","Selectează mai întâi vehiculul."); self.stack.setCurrentIndex(0); return
        self.stack.setCurrentIndex(index)
        if index==2: self._load_dtcs()
        elif index in (3,4,5): self._load_procedures(self.stack.widget(index))
        elif index==6: self._load_live()
        elif index==7: self._load_modules()

    def _stats(self):
        s=db.stats(self.con); self.stat_dtc.value_label.setText(f'{s.get("dtcs",0):,}'.replace(",",".")); self.stat_proc.value_label.setText(f'{s.get("procedures",0):,}'.replace(",",".")); self.stat_mod.value_label.setText(f'{s.get("modules",0):,}'.replace(",","."))

    def _load_autoscan(self):
        path,_=QFileDialog.getOpenFileName(self,"Încarcă Auto-Scan VCDS","","Auto-Scan VCDS (*.txt *.log *.pdf);;Text (*.txt *.log);;PDF (*.pdf);;Toate fișierele (*.*)")
        if not path:return
        try: result=parse_autoscan_file(path)
        except Exception as exc: QMessageBox.critical(self,"Auto-Scan",f"Raportul nu a putut fi citit:\n{exc}"); return
        self.current_autoscan=result; engine_id=self.engine_combo.currentData(); self.autoscan_plans=[(f,diagnostic_plan(self.con,f,self.selected_generation_id,engine_id)) for f in result.faults]; self.autoscan_correlation=correlate(result,self.autoscan_plans); self.autoscan_table.setRowCount(len(self.autoscan_plans)); self.autoscan_table.setProperty("rows",self.autoscan_plans)
        for i,(f,p) in enumerate(self.autoscan_plans):
            vals=[f"{f.module_address} {ro_module(f.module_name)}".strip(),f.code or f.vag_code,ro_title(p.get("title") or f.title),ro_status(f.status),ro_confidence(p.get("found"),p.get("verified"))]
            for j,v in enumerate(vals): self.autoscan_table.setItem(i,j,QTableWidgetItem(str(v)))
        self.autoscan_table.horizontalHeader().setSectionResizeMode(2,QHeaderView.Stretch); self.autoscan_summary.setText(f"{Path(path).name} • {len(result.modules)} module • {len(result.faults)} erori • {sum(1 for _,p in self.autoscan_plans if p.get('found'))} fișe locale")
        if self.autoscan_plans:self.autoscan_table.selectRow(0)

    def _show_autoscan_fault(self):
        row=self.autoscan_table.currentRow(); rows=self.autoscan_table.property("rows") or []
        if row<0 or row>=len(rows):return
        f,p=rows[row]; code=f.code or f.vag_code or "DTC"; self.autoscan_detail.setPlainText(f"{code} • {ro_title(p.get('title') or f.title)}\n\nMODUL\n{f.module_address} {ro_module(f.module_name)}\n\nSTARE\n{ro_status(f.status)}\n\nCE ÎNSEAMNĂ\n{p.get('description','')}\n\nSIMPTOME\n{p.get('symptoms','')}\n\nCAUZE POSIBILE\n{p.get('causes','')}\n\nPIESA / SISTEM\n{p.get('component','')}\n\nUNDE SE AFLĂ\n{p.get('location','')}\n\nCE VERIFICI ÎN VCDS\n{p.get('parameters','')}\n\nVALORI AȘTEPTATE\n{p.get('expected','')}\n\nTRASEU VCDS\n{p.get('test_path','')}\n\nDIAGNOSTIC PAS CU PAS\n{p.get('diagnosis','')}\n\nREPARAȚIE\n{p.get('repair','')}\n\nDUPĂ ÎNLOCUIRE\n{p.get('replacement','')}\n\n{ro_vcds_note()}")

    def _show_correlation(self):
        if not self.autoscan_correlation: QMessageBox.warning(self,"Plan diagnostic","Încarcă mai întâi un Auto-Scan cu erori."); return
        self.autoscan_detail.setPlainText(render_correlation(self.autoscan_correlation)+"\n\n"+ro_vcds_note())

    def _export_pdf(self):
        if not self.current_autoscan or not self.autoscan_plans: QMessageBox.warning(self,"Raport PDF","Încarcă mai întâi un Auto-Scan VCDS cu erori."); self.open_page(1); return
        suggested=f"KID_Diagnostic_{Path(self.current_autoscan.source_path).stem}_V2.pdf"; path,_=QFileDialog.getSaveFileName(self,"Salvează raportul KID Diagnostic",suggested,"PDF (*.pdf)")
        if not path:return
        if not path.lower().endswith(".pdf"):path+=".pdf"
        try:
            writer=QPdfWriter(path); writer.setTitle("KID Diagnostic V2 - Raport Auto-Scan VCDS"); writer.setCreator("KID Diagnostic"); writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4)); writer.setPageMargins(QMarginsF(14,14,14,14),QPageLayout.Unit.Millimeter); writer.setResolution(120); doc=QTextDocument(); doc.setHtml(_build_html(self)); doc.print_(writer)
        except Exception as exc: QMessageBox.critical(self,"Raport PDF",f"Raportul nu a putut fi salvat:\n{exc}"); return
        QMessageBox.information(self,"Raport PDF",f"Raport salvat:\n{path}")

    def _load_dtcs(self):
        q=self.dtc_search.text().strip(); like=f"%{q}%"; rows=self.con.execute("SELECT code,title,severity,verified,description,symptoms,causes,diagnosis,repair FROM dtcs WHERE code LIKE ? OR title LIKE ? OR description LIKE ? ORDER BY code LIMIT 1800",(like,like,like)).fetchall(); self.dtc_table.setRowCount(len(rows)); self.dtc_table.setProperty("rows",rows)
        for i,r in enumerate(rows):
            for j,v in enumerate([r["code"],r["title"],r["severity"],"VERIFICAT" if r["verified"] else "LOCAL"]): self.dtc_table.setItem(i,j,QTableWidgetItem(str(v)))
        self.dtc_table.horizontalHeader().setSectionResizeMode(1,QHeaderView.Stretch)

    def _show_dtc(self):
        row=self.dtc_table.currentRow(); rows=self.dtc_table.property("rows") or []
        if row<0 or row>=len(rows):return
        r=rows[row]; self.dtc_detail.setPlainText(f'{r["code"]} • {r["title"]}\n\nDESCRIERE\n{r["description"]}\n\nSIMPTOME\n{r["symptoms"]}\n\nCAUZE\n{r["causes"]}\n\nDIAGNOSTIC\n{r["diagnosis"]}\n\nREPARAȚIE\n{r["repair"]}\n\nSEVERITATE\n{r["severity"]}')

    def _load_procedures(self,page):
        search=page.search.text().lower().strip(); rows=[]
        for r in db.procedures_for_vehicle(self.con,self.selected_generation_id):
            hay=f'{r["category"]} {r["title"]} {r["vcds_path"]} {r["purpose"]}'.lower()
            if not any(k in hay for k in page.keywords):continue
            if search and search not in hay:continue
            rows.append(r)
        page.table.setRowCount(len(rows)); page.table.setProperty("rows",rows)
        for i,r in enumerate(rows):
            for j,v in enumerate([r["category"],r["title"],r["module_address"],r["vcds_path"],r["applicability"]]):page.table.setItem(i,j,QTableWidgetItem(str(v)))
        page.table.horizontalHeader().setSectionResizeMode(1,QHeaderView.Stretch)

    def _show_procedure(self,page):
        row=page.table.currentRow(); rows=page.table.property("rows") or []
        if row<0 or row>=len(rows):return
        r=rows[row]; page.detail.setPlainText(f'{r["title"]}\n\nCATEGORIE\n{r["category"]}\n\nMODUL\n{r["module_address"]}\n\nCALE ÎN VCDS\n{r["vcds_path"]}\n\nSCOP\n{r["purpose"]}\n\nCONDIȚII\n{r["prerequisites"]}\n\nPAȘI\n{r["steps"]}\n\nREZULTAT CORECT\n{r["success_criteria"]}\n\nATENȚIONĂRI\n{r["warnings"]}\n\nAPLICABILITATE\n{r["applicability"]}')

    def _load_live(self):
        q=self.live_search.text().strip(); rows=[]
        if self._table_exists("autoscan_dtc_knowledge"):
            try: rows=self.con.execute("SELECT code,title,parameters,expected FROM autoscan_dtc_knowledge WHERE code LIKE ? OR title LIKE ? OR parameters LIKE ? OR expected LIKE ? ORDER BY code LIMIT 1500",(*(f"%{q}%",)*4,)).fetchall()
            except Exception: rows=[]
        self.live_table.setRowCount(len(rows))
        for i,r in enumerate(rows):
            for j,v in enumerate([r["code"],r["title"],r["parameters"],r["expected"]]):self.live_table.setItem(i,j,QTableWidgetItem(str(v)))
        self.live_table.horizontalHeader().setSectionResizeMode(3,QHeaderView.Stretch)

    def _load_modules(self):
        rows=db.modules_for_vehicle(self.con,self.selected_generation_id); self.module_table.setRowCount(len(rows))
        for i,r in enumerate(rows):
            for j,k in enumerate(["address","name","family","protocol"]):self.module_table.setItem(i,j,QTableWidgetItem(str(r[k])))
        self.module_table.horizontalHeader().setSectionResizeMode(1,QHeaderView.Stretch)

    def _table_exists(self,name): return bool(self.con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(name,)).fetchone())

    def _style(self):
        self.setStyleSheet('''
        QWidget{background:#07111f;color:#edf6ff;font-family:"Segoe UI",Arial,sans-serif;font-size:13px}
        #topbar{background:#09182a;border-bottom:1px solid #17304a}
        #brandTitle{font-size:19px;font-weight:800;letter-spacing:1px} #brandSub,#pageSubtitle,#heroSub,#cardSubtitle,#statLabel{color:#8fa9bf}
        #vehicleBadge{background:#0d2239;border:1px solid #1f557c;border-radius:14px;padding:9px 14px;color:#bce6ff;font-weight:600}
        #heroPanel{background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #0e2b4d,stop:1 #091728);border:1px solid #1d4f77;border-radius:22px} #heroTitle{font-size:30px;font-weight:800}
        #selectorPanel,#statCard,#featureCard{background:#0b1b2d;border:1px solid #183957;border-radius:18px} #featureCard:hover{background:#0d2238;border:1px solid #249fe4}
        #cardTitle{font-size:18px;font-weight:750} #pageTitle{font-size:25px;font-weight:800} #statValue{font-size:22px;font-weight:800;color:#42c1ff} #fieldLabel{color:#91aac1;font-weight:600}
        QComboBox,QLineEdit,QTextEdit,QTableWidget{background:#081624;border:1px solid #24445f;border-radius:10px;padding:8px;selection-background-color:#1577b7} QComboBox{min-height:24px}
        QHeaderView::section{background:#10243a;color:#cfe9fb;border:none;border-bottom:1px solid #31506b;padding:9px;font-weight:700} QTableWidget{gridline-color:#173149}
        QPushButton{border-radius:10px;padding:9px 14px;font-weight:700} #primaryButton,#cardButton{background:#1389d3;color:white;border:1px solid #34b6ff} #primaryButton:hover,#cardButton:hover{background:#18a1ef}
        #secondaryButton{background:#0f2237;border:1px solid #2b5778;color:#d8efff} #secondaryButton:hover{background:#15314d}
        #summaryStrip{background:#0e2943;border:1px solid #1d608e;border-radius:11px;padding:10px 14px;color:#bfeaff} QSplitter::handle{background:#17334c;width:2px}
        ''')


def run():
    app=QApplication(sys.argv); app.setApplicationName("KID Diagnostic V2"); app.setOrganizationName("KID Diagnostic"); win=MainWindowV2(); win.show(); raise SystemExit(app.exec())


if __name__=="__main__": run()
