from pathlib import Path
import shutil

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPixmap, QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFrame, QLabel, QPushButton, QLineEdit,
    QVBoxLayout, QHBoxLayout, QGridLayout, QStackedWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QComboBox, QTextEdit,
    QFileDialog, QMessageBox, QSplitter, QSizePolicy
)

import appdb as db


class LogoBox(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(58, 58)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if db.LOGO_PATH.exists():
            pix = QPixmap(str(db.LOGO_PATH))
            if not pix.isNull():
                pix = pix.scaled(52, 52, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                p.drawPixmap((58-pix.width())//2, (58-pix.height())//2, pix)
                return
        p.setPen(QPen(QColor("#3b82f6"), 2))
        p.setBrush(QColor("#111b31"))
        p.drawRoundedRect(3, 3, 52, 52, 15, 15)
        p.setPen(QColor("#f8fafc"))
        p.setFont(QFont("Arial", 16, QFont.Bold))
        p.drawText(self.rect(), Qt.AlignCenter, "VM")


class StatCard(QFrame):
    def __init__(self, title, value, subtitle):
        super().__init__()
        self.setObjectName("statCard")
        l = QVBoxLayout(self)
        l.setContentsMargins(18, 15, 18, 15)
        a = QLabel(title); a.setObjectName("statTitle")
        b = QLabel(str(value)); b.setObjectName("statValue")
        c = QLabel(subtitle); c.setObjectName("muted")
        l.addWidget(a); l.addWidget(b); l.addWidget(c)


class MainWindow(QMainWindow):
    PAGE_NAMES = ["Selectare vehicul", "Workspace VCDS", "DTC", "Module", "Surse", "Instrumente"]

    def __init__(self):
        super().__init__()
        self.con = db.connect_db()
        self.selected_generation_id = None
        self.selected_year = None
        self.current_source_url = ""
        self.nav_buttons = []
        self.setWindowTitle(f"{db.APP_NAME} • v{db.APP_VERSION}")
        self.resize(1580, 940)
        self.setMinimumSize(1220, 760)
        self.build_ui()
        self.apply_style()
        self.load_brand_combo()
        self.refresh_start()
        self.open_page(0)

    def build_ui(self):
        root = QWidget()
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        side = QFrame(); side.setObjectName("sidebar"); side.setFixedWidth(235)
        sl = QVBoxLayout(side); sl.setContentsMargins(18, 22, 18, 18); sl.setSpacing(7)
        brand_row = QHBoxLayout(); brand_row.addWidget(LogoBox())
        brand_text = QVBoxLayout()
        b1 = QLabel("VAG MASTER"); b1.setObjectName("brand")
        b2 = QLabel("DIAGNOSTIC PRO"); b2.setObjectName("brandSub")
        brand_text.addWidget(b1); brand_text.addWidget(b2)
        brand_row.addLayout(brand_text); brand_row.addStretch(); sl.addLayout(brand_row)
        sl.addSpacing(22)
        for i, name in enumerate(self.PAGE_NAMES):
            btn = QPushButton(name); btn.setObjectName("nav"); btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _=False, x=i: self.open_page(x))
            self.nav_buttons.append(btn); sl.addWidget(btn)
        sl.addStretch()
        v = QLabel(f"SUPER MASTER v{db.APP_VERSION}\n1996–2024"); v.setObjectName("version")
        sl.addWidget(v)

        content = QFrame(); content.setObjectName("content")
        cl = QVBoxLayout(content); cl.setContentsMargins(28, 22, 28, 22); cl.setSpacing(14)
        top = QHBoxLayout()
        self.page_title = QLabel("Selectare vehicul"); self.page_title.setObjectName("pageTitle")
        self.vehicle_badge = QLabel("Niciun vehicul selectat"); self.vehicle_badge.setObjectName("vehicleBadge")
        top.addWidget(self.page_title); top.addStretch(); top.addWidget(self.vehicle_badge)
        cl.addLayout(top)

        self.selector = self.build_vehicle_selector()
        cl.addWidget(self.selector)
        self.stack = QStackedWidget()
        self.stack.addWidget(self.build_start_page())
        self.stack.addWidget(self.build_workspace_page())
        self.stack.addWidget(self.build_dtc_page())
        self.stack.addWidget(self.build_modules_page())
        self.stack.addWidget(self.build_sources_page())
        self.stack.addWidget(self.build_tools_page())
        cl.addWidget(self.stack, 1)

        outer.addWidget(side); outer.addWidget(content, 1)
        self.setCentralWidget(root)
        self.statusBar().showMessage(f"Baza locală: {db.DB_PATH}")

    def build_vehicle_selector(self):
        box = QFrame(); box.setObjectName("selector")
        l = QHBoxLayout(box); l.setContentsMargins(16, 14, 16, 14); l.setSpacing(10)
        self.brand_combo = QComboBox(); self.brand_combo.setMinimumWidth(150)
        self.model_combo = QComboBox(); self.model_combo.setMinimumWidth(150)
        self.gen_combo = QComboBox(); self.gen_combo.setMinimumWidth(220)
        self.year_combo = QComboBox(); self.year_combo.setMinimumWidth(90)
        self.engine_combo = QComboBox(); self.engine_combo.setMinimumWidth(150)
        self.brand_combo.currentIndexChanged.connect(self.load_models)
        self.model_combo.currentIndexChanged.connect(self.load_generations)
        self.gen_combo.currentIndexChanged.connect(self.load_years_engines)
        for label, widget in [("Marcă",self.brand_combo),("Model",self.model_combo),("Generație / chassis",self.gen_combo),("An",self.year_combo),("Motor",self.engine_combo)]:
            group = QVBoxLayout(); a=QLabel(label); a.setObjectName("fieldLabel"); group.addWidget(a); group.addWidget(widget); l.addLayout(group)
        open_btn = QPushButton("DESCHIDE VEHICUL"); open_btn.setObjectName("primary"); open_btn.setMinimumHeight(42); open_btn.clicked.connect(self.select_vehicle)
        l.addWidget(open_btn, 0, Qt.AlignBottom)
        return box

    def build_start_page(self):
        page=QWidget(); l=QVBoxLayout(page); l.setContentsMargins(0,8,0,0)
        title=QLabel("Alege mașina înainte de diagnostic"); title.setObjectName("hero")
        sub=QLabel("Flux: Marcă → Model → Generație/Chassis → An → Motor → Workspace VCDS. Procedurile sunt filtrate pe generația selectată și au cale VCDS, condiții, avertismente și sursă."); sub.setWordWrap(True); sub.setObjectName("heroSub")
        l.addWidget(title); l.addWidget(sub); l.addSpacing(18)
        self.stats_grid=QGridLayout(); l.addLayout(self.stats_grid)
        info=QFrame(); info.setObjectName("infoCard"); il=QVBoxLayout(info)
        h=QLabel("Cum se folosește"); h.setObjectName("sectionTitle")
        body=QLabel("1. Selectează vehiculul sus.\n2. Intră în Workspace VCDS.\n3. Filtrează după Diagnostic, Basic Settings, Coding, Adaptation, DPF, Frâne etc.\n4. Dublu-click pe procedură pentru pașii în română.\n5. Confirmă întotdeauna modulul și part number-ul real prin Auto-Scan.")
        body.setWordWrap(True); body.setObjectName("body")
        il.addWidget(h); il.addWidget(body); l.addWidget(info); l.addStretch()
        return page

    def build_workspace_page(self):
        page=QWidget(); l=QVBoxLayout(page); l.setContentsMargins(0,8,0,0)
        bar=QHBoxLayout(); self.proc_category=QComboBox(); self.proc_category.addItem("Toate")
        self.proc_search=QLineEdit(); self.proc_search.setPlaceholderText("Caută: G85, DPF, coding, clapetă, EPB, service...")
        self.proc_category.currentTextChanged.connect(self.load_procedures)
        self.proc_search.textChanged.connect(self.load_procedures)
        bar.addWidget(QLabel("Categorie:")); bar.addWidget(self.proc_category); bar.addWidget(self.proc_search,1)
        l.addLayout(bar)
        split=QSplitter(Qt.Horizontal)
        self.proc_table=self.make_table(["Categorie","Procedură","Modul","Cale în VCDS","Aplicabilitate","Status"])
        self.proc_table.itemSelectionChanged.connect(self.show_selected_procedure)
        self.proc_table.cellDoubleClicked.connect(lambda *_: self.show_selected_procedure())
        split.addWidget(self.proc_table)
        right=QFrame(); right.setObjectName("detailPanel"); rl=QVBoxLayout(right)
        self.proc_detail_title=QLabel("Selectează o procedură"); self.proc_detail_title.setObjectName("detailTitle"); self.proc_detail_title.setWordWrap(True)
        self.proc_detail=QTextEdit(); self.proc_detail.setReadOnly(True)
        src_btn=QPushButton("Deschide sursa oficială"); src_btn.clicked.connect(self.open_current_source)
        rl.addWidget(self.proc_detail_title); rl.addWidget(self.proc_detail,1); rl.addWidget(src_btn)
        split.addWidget(right); split.setSizes([900,520]); l.addWidget(split,1)
        return page

    def build_dtc_page(self):
        page=QWidget(); l=QVBoxLayout(page); l.setContentsMargins(0,8,0,0)
        bar=QHBoxLayout(); self.dtc_search=QLineEdit(); self.dtc_search.setPlaceholderText("Cod sau descriere DTC..."); self.dtc_search.textChanged.connect(self.load_dtcs)
        bar.addWidget(self.dtc_search); l.addLayout(bar)
        split=QSplitter(Qt.Horizontal)
        self.dtc_table=self.make_table(["Cod","Titlu","Severitate","Status"]); self.dtc_table.itemSelectionChanged.connect(self.show_selected_dtc)
        split.addWidget(self.dtc_table)
        right=QFrame(); right.setObjectName("detailPanel"); rl=QVBoxLayout(right)
        self.dtc_title=QLabel("Selectează un DTC"); self.dtc_title.setObjectName("detailTitle"); self.dtc_text=QTextEdit(); self.dtc_text.setReadOnly(True)
        rl.addWidget(self.dtc_title); rl.addWidget(self.dtc_text); split.addWidget(right); split.setSizes([760,620]); l.addWidget(split)
        return page

    def build_modules_page(self):
        page=QWidget(); l=QVBoxLayout(page); l.setContentsMargins(0,8,0,0)
        hint=QLabel("Module POSIBILE pentru platformă. Auto-Scan confirmă ce este instalat efectiv pe mașina selectată."); hint.setWordWrap(True); hint.setObjectName("warning")
        self.module_table=self.make_table(["Adresă","Modul","Familie","Protocol"])
        l.addWidget(hint); l.addWidget(self.module_table); return page

    def build_sources_page(self):
        page=QWidget(); l=QVBoxLayout(page); l.setContentsMargins(0,8,0,0)
        h=QLabel("Surse și nivel de încredere"); h.setObjectName("sectionTitle")
        p=QLabel("Nucleul verificat folosește documentația oficială Ross-Tech. Forumurile pot fi folosite ulterior ca strat Community, separat de datele verificate."); p.setWordWrap(True); p.setObjectName("body")
        self.source_table=self.make_table(["Titlu","Publisher","Tip","URL","Accesat"])
        self.source_table.cellDoubleClicked.connect(self.open_source_row)
        l.addWidget(h); l.addWidget(p); l.addWidget(self.source_table); return page

    def build_tools_page(self):
        page=QWidget(); l=QVBoxLayout(page); l.setContentsMargins(0,8,0,0)
        h=QLabel("Instrumente"); h.setObjectName("sectionTitle"); l.addWidget(h)
        for text, fn in [("Setează logo-ul meu",self.set_logo),("Backup bază SQLite",self.backup),("Export complet JSON",self.export_json),("Export proceduri vehicul CSV",self.export_vehicle_csv),("Deschide folderul bazei",self.open_data_folder)]:
            b=QPushButton(text); b.setObjectName("toolButton"); b.clicked.connect(fn); l.addWidget(b)
        l.addStretch(); return page

    def make_table(self, headers):
        t=QTableWidget(0,len(headers)); t.setHorizontalHeaderLabels(headers)
        t.setSelectionBehavior(QAbstractItemView.SelectRows); t.setSelectionMode(QAbstractItemView.SingleSelection); t.setEditTriggers(QAbstractItemView.NoEditTriggers); t.setAlternatingRowColors(True)
        t.verticalHeader().setVisible(False); t.horizontalHeader().setStretchLastSection(True); return t

    def open_page(self,index):
        self.stack.setCurrentIndex(index); self.page_title.setText(self.PAGE_NAMES[index])
        for i,b in enumerate(self.nav_buttons): b.setChecked(i==index)
        if index==1:self.load_procedures()
        elif index==2:self.load_dtcs()
        elif index==3:self.load_modules()
        elif index==4:self.load_sources()

    def load_brand_combo(self):
        self.brand_combo.blockSignals(True); self.brand_combo.clear(); self.brand_combo.addItem("Alege marca",None)
        for r in db.brands(self.con): self.brand_combo.addItem(r["name"],r["id"])
        self.brand_combo.blockSignals(False); self.load_models()

    def load_models(self):
        self.model_combo.blockSignals(True); self.model_combo.clear(); self.model_combo.addItem("Alege modelul",None)
        bid=self.brand_combo.currentData()
        if bid:
            for r in db.models_for_brand(self.con,bid):self.model_combo.addItem(r["name"],r["id"])
        self.model_combo.blockSignals(False); self.load_generations()

    def load_generations(self):
        self.gen_combo.blockSignals(True); self.gen_combo.clear(); self.gen_combo.addItem("Alege generația",None)
        mid=self.model_combo.currentData()
        if mid:
            for r in db.generations_for_model(self.con,mid):
                self.gen_combo.addItem(f'{r["name"]} • {r["year_from"]}-{r["year_to"]} • {r["platform"]}',r["id"])
        self.gen_combo.blockSignals(False); self.load_years_engines()

    def load_years_engines(self):
        self.year_combo.clear(); self.engine_combo.clear(); self.engine_combo.addItem("Nespecificat",None)
        gid=self.gen_combo.currentData()
        if not gid:return
        h=db.vehicle_header(self.con,gid)
        for y in range(h["year_from"],h["year_to"]+1):self.year_combo.addItem(str(y),y)
        for e in db.engines_for_generation(self.con,gid):self.engine_combo.addItem(f'{e["code"]} • {e["fuel"]} {e["displacement"]}L {e["power_hp"]}CP',e["id"])

    def select_vehicle(self):
        gid=self.gen_combo.currentData()
        if not gid:
            QMessageBox.warning(self,"Vehicul","Selectează marca, modelul și generația."); return
        self.selected_generation_id=gid; self.selected_year=self.year_combo.currentData()
        h=db.vehicle_header(self.con,gid); engine=self.engine_combo.currentText()
        self.vehicle_badge.setText(f'{h["brand"]} {h["model"]} • {h["name"]} • {self.selected_year or "an?"} • {engine}')
        db.log(self.con,"select_vehicle","generation",gid,self.vehicle_badge.text())
        self.refresh_categories(); self.load_procedures(); self.load_modules(); self.open_page(1)
        self.statusBar().showMessage(f'Vehicul activ: {self.vehicle_badge.text()}')

    def refresh_categories(self):
        self.proc_category.blockSignals(True); self.proc_category.clear(); self.proc_category.addItem("Toate")
        rows=self.con.execute("SELECT DISTINCT category FROM procedure_library ORDER BY category")
        for r in rows:self.proc_category.addItem(r[0])
        self.proc_category.blockSignals(False)

    def load_procedures(self):
        self.proc_table.setRowCount(0)
        if not self.selected_generation_id:
            return
        rows=db.procedures_for_vehicle(self.con,self.selected_generation_id,self.proc_category.currentText())
        q=self.proc_search.text().strip().lower()
        if q: rows=[r for r in rows if q in (r["title"]+" "+r["category"]+" "+r["vcds_path"]+" "+r["purpose"]).lower()]
        self.proc_table.setRowCount(len(rows)); self.proc_table.setProperty("rows",rows)
        for i,r in enumerate(rows):
            vals=[r["category"],r["title"],r["module_address"] or "—",r["vcds_path"],r["applicability"],"VERIFICAT" if r["verified"] else "DE VERIFICAT"]
            for j,v in enumerate(vals): self.proc_table.setItem(i,j,QTableWidgetItem(str(v)))
        self.proc_table.resizeColumnsToContents(); self.proc_table.horizontalHeader().setSectionResizeMode(1,QHeaderView.Stretch); self.proc_table.horizontalHeader().setSectionResizeMode(3,QHeaderView.Stretch)

    def show_selected_procedure(self):
        row=self.proc_table.currentRow(); rows=self.proc_table.property("rows") or []
        if row<0 or row>=len(rows):return
        r=rows[row]; self.current_source_url=r["source_url"] or ""; self.proc_detail_title.setText(r["title"])
        text=f'''CATEGORIE: {r["category"]}\nMODUL: {r["module_address"] or "Depinde de procedură"}\nAPLICABILITATE: {r["applicability"]}\nSTATUS: {"VERIFICAT - sursă oficială" if r["verified"] else "DE VERIFICAT"}\n\nCALE ÎN VCDS\n{r["vcds_path"]}\n\nSCOP\n{r["purpose"]}\n\nCONDIȚII\n{r["prerequisites"]}\n\nPAȘI\n{r["steps"]}\n\nREZULTAT CORECT\n{r["success_criteria"]}\n\nATENȚIE\n{r["warnings"]}\n\nNOTĂ VEHICUL\n{r["notes"]}\n\nSURSĂ\n{r["source_title"]}\n{r["source_url"]}'''
        self.proc_detail.setPlainText(text)

    def load_dtcs(self):
        q=f'%{self.dtc_search.text().strip()}%'; rows=self.con.execute("SELECT * FROM dtcs WHERE code LIKE ? OR title LIKE ? OR description LIKE ? ORDER BY code LIMIT 500",(q,q,q)).fetchall()
        self.dtc_table.setProperty("rows",rows); self.dtc_table.setRowCount(len(rows))
        for i,r in enumerate(rows):
            for j,v in enumerate([r["code"],r["title"],r["severity"],"VERIFICAT" if r["verified"] else "DE VERIFICAT"]):self.dtc_table.setItem(i,j,QTableWidgetItem(str(v)))
        self.dtc_table.resizeColumnsToContents(); self.dtc_table.horizontalHeader().setSectionResizeMode(1,QHeaderView.Stretch)

    def show_selected_dtc(self):
        row=self.dtc_table.currentRow(); rows=self.dtc_table.property("rows") or []
        if row<0 or row>=len(rows):return
        r=rows[row]; self.dtc_title.setText(f'{r["code"]} • {r["title"]}')
        self.dtc_text.setPlainText(f'DESCRIERE\n{r["description"]}\n\nSIMPTOME\n{r["symptoms"]}\n\nCAUZE\n{r["causes"]}\n\nDIAGNOSTIC\n{r["diagnosis"]}\n\nREPARAȚIE\n{r["repair"]}\n\nSEVERITATE\n{r["severity"]}\n\nSTATUS\n{"VERIFICAT" if r["verified"] else "DE VERIFICAT / starter"}')

    def load_modules(self):
        self.module_table.setRowCount(0)
        if not self.selected_generation_id:return
        rows=db.modules_for_vehicle(self.con,self.selected_generation_id); self.module_table.setRowCount(len(rows))
        for i,r in enumerate(rows):
            for j,v in enumerate([r["address"],r["name"],r["family"],r["protocol"]]):self.module_table.setItem(i,j,QTableWidgetItem(str(v)))
        self.module_table.resizeColumnsToContents(); self.module_table.horizontalHeader().setSectionResizeMode(1,QHeaderView.Stretch)

    def load_sources(self):
        rows=self.con.execute("SELECT title,publisher,source_type,url,accessed FROM sources ORDER BY title").fetchall(); self.source_table.setRowCount(len(rows)); self.source_table.setProperty("rows",rows)
        for i,r in enumerate(rows):
            for j,v in enumerate(r):self.source_table.setItem(i,j,QTableWidgetItem(str(v)))
        self.source_table.resizeColumnsToContents(); self.source_table.horizontalHeader().setSectionResizeMode(0,QHeaderView.Stretch); self.source_table.horizontalHeader().setSectionResizeMode(3,QHeaderView.Stretch)

    def open_source_row(self,row,col):
        rows=self.source_table.property("rows") or []
        if 0<=row<len(rows):QDesktopServices.openUrl(QUrl(rows[row]["url"]))

    def open_current_source(self):
        if self.current_source_url:QDesktopServices.openUrl(QUrl(self.current_source_url))

    def refresh_start(self):
        while self.stats_grid.count():
            item=self.stats_grid.takeAt(0)
            if item.widget():item.widget().deleteLater()
        s=db.stats(self.con); cards=[("Mărci",s["brands"],"VAG"),("Modele",s["models"],"catalog"),("Generații",s["generations"],"chassis"),("Proceduri",s["procedures"],"bibliotecă"),("Mapări",s["vehicle_procedures"],"vehicul → procedură"),("DTC",s["dtcs"],"fișe")]
        for i,(a,b,c) in enumerate(cards):self.stats_grid.addWidget(StatCard(a,b,c),i//3,i%3)

    def set_logo(self):
        f,_=QFileDialog.getOpenFileName(self,"Alege logo","","Imagini (*.png *.jpg *.jpeg)")
        if not f:return
        pix=QPixmap(f)
        if pix.isNull():QMessageBox.warning(self,"Logo","Fișier imagine invalid.");return
        pix.save(str(db.LOGO_PATH),"PNG"); QMessageBox.information(self,"Logo","Logo salvat. Repornește aplicația pentru actualizare completă.")

    def backup(self):
        f,_=QFileDialog.getSaveFileName(self,"Backup","vag_master_super_v5.db","SQLite (*.db)")
        if f:db.backup_database(f); QMessageBox.information(self,"Backup","Backup creat.")

    def export_json(self):
        f,_=QFileDialog.getSaveFileName(self,"Export","vag_master_super_v5.json","JSON (*.json)")
        if f:db.export_json(self.con,f); QMessageBox.information(self,"Export","Export complet creat.")

    def export_vehicle_csv(self):
        if not self.selected_generation_id:QMessageBox.warning(self,"Export","Selectează întâi vehiculul.");return
        f,_=QFileDialog.getSaveFileName(self,"Export proceduri","proceduri_vehicul.csv","CSV (*.csv)")
        if f:db.export_vehicle_csv(self.con,self.selected_generation_id,f); QMessageBox.information(self,"Export","CSV creat.")

    def open_data_folder(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(db.APP_DATA)))

    def apply_style(self):
        self.setStyleSheet('''
        QMainWindow,QWidget{background:#080d18;color:#e8edf6;font-family:Segoe UI,Arial;font-size:13px}
        QFrame#sidebar{background:#0b1220;border-right:1px solid #1e293b}
        QFrame#content{background:#080d18}
        QLabel#brand{font-size:17px;font-weight:800} QLabel#brandSub{font-size:10px;color:#60a5fa;font-weight:700;letter-spacing:1px}
        QLabel#version{color:#64748b;font-size:11px;padding:8px}
        QPushButton#nav{background:transparent;border:0;text-align:left;padding:12px 14px;border-radius:8px;color:#94a3b8;font-weight:600}
        QPushButton#nav:hover{background:#111c2f;color:#fff} QPushButton#nav:checked{background:#17233a;color:#fff;border-left:3px solid #3b82f6}
        QLabel#pageTitle{font-size:25px;font-weight:800} QLabel#vehicleBadge{background:#101a2c;border:1px solid #24334d;border-radius:14px;padding:8px 14px;color:#bfdbfe;font-weight:600}
        QFrame#selector{background:#0d1525;border:1px solid #1e2b42;border-radius:12px}
        QLabel#fieldLabel{color:#8090a8;font-size:11px;font-weight:700}
        QComboBox,QLineEdit{background:#0a1220;border:1px solid #25334a;border-radius:8px;padding:9px;color:#f1f5f9;min-height:20px}
        QComboBox:hover,QLineEdit:focus{border-color:#3b82f6}
        QPushButton#primary{background:#2563eb;border:0;border-radius:8px;padding:10px 18px;color:white;font-weight:800} QPushButton#primary:hover{background:#3b82f6}
        QLabel#hero{font-size:28px;font-weight:800} QLabel#heroSub{font-size:14px;color:#94a3b8;max-width:900px} QLabel#sectionTitle{font-size:18px;font-weight:800} QLabel#body{color:#cbd5e1;line-height:1.5}
        QFrame#statCard,QFrame#infoCard,QFrame#detailPanel{background:#0d1525;border:1px solid #1e2b42;border-radius:12px}
        QLabel#statTitle{color:#94a3b8;font-weight:700} QLabel#statValue{font-size:26px;font-weight:800;color:#f8fafc} QLabel#muted{color:#64748b}
        QLabel#warning{background:#2a1d0b;color:#fbbf24;border:1px solid #5b3b0b;border-radius:8px;padding:10px}
        QLabel#detailTitle{font-size:18px;font-weight:800;padding:4px}
        QTableWidget{background:#0b1322;alternate-background-color:#0f192a;border:1px solid #1e2b42;border-radius:9px;gridline-color:#18243a;selection-background-color:#1d4ed8;selection-color:white}
        QHeaderView::section{background:#111c2f;color:#94a3b8;border:0;border-bottom:1px solid #26354e;padding:10px;font-weight:700}
        QTextEdit{background:#09111e;border:1px solid #1e2b42;border-radius:8px;padding:8px;color:#dbeafe}
        QPushButton{background:#142037;border:1px solid #263752;border-radius:8px;padding:9px 14px;color:#e2e8f0} QPushButton:hover{background:#1b2b48}
        QPushButton#toolButton{text-align:left;min-height:34px;font-weight:600}
        QStatusBar{background:#070b13;color:#64748b;border-top:1px solid #172033}
        ''')
