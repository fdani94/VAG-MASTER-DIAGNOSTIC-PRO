import os
import shutil
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QFont, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFrame,
    QGridLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMainWindow,
    QMessageBox, QPushButton, QStackedWidget, QTableWidget, QTableWidgetItem,
    QTextEdit, QVBoxLayout, QWidget
)

from appdb import (
    APP_DATA, APP_NAME, APP_VERSION, DB_PATH, LOGO_PATH, add_favorite, add_note,
    backup_database, counts, export_json, export_table_csv, global_search, log
)


class BrandLogo(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(70, 70)
        self.pixmap = QPixmap(str(LOGO_PATH)) if LOGO_PATH.exists() else QPixmap()

    def reload(self):
        self.pixmap = QPixmap(str(LOGO_PATH)) if LOGO_PATH.exists() else QPixmap()
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if not self.pixmap.isNull():
            scaled = self.pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            p.drawPixmap(x, y, scaled)
            return
        p.setPen(QPen(QColor("#2563eb"), 2))
        p.setBrush(QColor("#0f172a"))
        p.drawRoundedRect(4, 4, 62, 62, 16, 16)
        p.setPen(QColor("#f8fafc"))
        p.setFont(QFont("Arial", 22, QFont.Bold))
        p.drawText(self.rect(), Qt.AlignCenter, "VM")


class StatCard(QFrame):
    def __init__(self, title, value, subtitle):
        super().__init__()
        self.setObjectName("statCard")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        a = QLabel(title); a.setObjectName("statTitle")
        self.value = QLabel(str(value)); self.value.setObjectName("statValue")
        b = QLabel(subtitle); b.setObjectName("muted")
        lay.addWidget(a); lay.addWidget(self.value); lay.addWidget(b)


class DetailDialog(QDialog):
    def __init__(self, title, body, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(840, 640)
        lay = QVBoxLayout(self)
        h = QLabel(title); h.setObjectName("dialogTitle")
        text = QTextEdit(); text.setReadOnly(True); text.setPlainText(body)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        lay.addWidget(h); lay.addWidget(text); lay.addWidget(buttons)


class MainWindow(QMainWindow):
    PAGE_NAMES = [
        "Dashboard", "Căutare", "Vehicule", "Motoare", "DTC", "Module",
        "Coding", "Adaptation", "Basic Settings", "Output Tests",
        "Security Access", "Measuring Values", "Resetări", "Proceduri",
        "Componente", "Favorite & Note", "Instrumente"
    ]

    def __init__(self, con):
        super().__init__()
        self.con = con
        self.nav_buttons = []
        self.setWindowTitle(f"{APP_NAME} • Super Master v{APP_VERSION}")
        self.resize(1680, 960)
        self.setMinimumSize(1280, 760)
        self.build_ui()
        self.apply_style()
        self.refresh_all()
        self.open_page(0)
        self.statusBar().showMessage(f"Database: {DB_PATH}")

    def build_ui(self):
        root = QWidget()
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        sidebar = QFrame(); sidebar.setObjectName("sidebar"); sidebar.setFixedWidth(280)
        side = QVBoxLayout(sidebar); side.setContentsMargins(22, 22, 22, 18); side.setSpacing(7)
        brand = QHBoxLayout()
        self.logo = BrandLogo(); brand.addWidget(self.logo)
        bt = QVBoxLayout(); name = QLabel("VAG MASTER"); name.setObjectName("brandName")
        sub = QLabel("SUPER MASTER DATABASE"); sub.setObjectName("brandSub")
        bt.addWidget(name); bt.addWidget(sub); brand.addLayout(bt); brand.addStretch()
        side.addLayout(brand); side.addSpacing(18)

        icons = ["▦","⌕","▣","◉","⚠","◫","⌘","≡","◈","▶","🔐","▤","↻","☑","⚙","★","🛠"]
        for i, label in enumerate(self.PAGE_NAMES):
            b = QPushButton(f"{icons[i]}   {label}")
            b.setObjectName("navButton"); b.setCheckable(True); b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda checked=False, x=i: self.open_page(x))
            self.nav_buttons.append(b); side.addWidget(b)
        side.addStretch()
        footer = QLabel(f"v{APP_VERSION}\nLocal SQLite • 1996–2024")
        footer.setObjectName("sideFooter"); side.addWidget(footer)

        content = QFrame(); content.setObjectName("content")
        cl = QVBoxLayout(content); cl.setContentsMargins(30, 24, 30, 24); cl.setSpacing(14)
        top = QHBoxLayout()
        self.page_title = QLabel("Dashboard"); self.page_title.setObjectName("pageTitle")
        self.global_search_box = QLineEdit(); self.global_search_box.setPlaceholderText("DTC, model, motor, modul, coding, procedură...")
        self.global_search_box.setMinimumWidth(470); self.global_search_box.returnPressed.connect(self.run_global_search)
        search_btn = QPushButton("Caută"); search_btn.setObjectName("primaryButton"); search_btn.clicked.connect(self.run_global_search)
        top.addWidget(self.page_title); top.addStretch(); top.addWidget(self.global_search_box); top.addWidget(search_btn)
        cl.addLayout(top)

        self.stack = QStackedWidget()
        self.stack.addWidget(self.build_dashboard())
        self.stack.addWidget(self.build_search())
        self.stack.addWidget(self.build_vehicles())
        self.stack.addWidget(self.build_engines())
        self.stack.addWidget(self.build_dtc())
        self.stack.addWidget(self.build_modules())
        self.stack.addWidget(self.build_generic_page("coding", ["ID","Titlu","Modul","Tip","Efect","Aplicabilitate","Verificat"]))
        self.stack.addWidget(self.build_generic_page("adaptations", ["ID","Titlu","Modul","Canal","Efect","Aplicabilitate","Verificat"]))
        self.stack.addWidget(self.build_generic_page("basic_settings", ["ID","Titlu","Modul","Group/Funcție","Aplicabilitate","Verificat"]))
        self.stack.addWidget(self.build_generic_page("output_tests", ["ID","Titlu","Modul","Aplicabilitate","Verificat"]))
        self.stack.addWidget(self.build_generic_page("security_access", ["ID","Titlu","Modul","Scop","Aplicabilitate","Verificat"]))
        self.stack.addWidget(self.build_generic_page("measuring_values", ["ID","Titlu","Modul","Parametru","Valoare","Unități","Verificat"]))
        self.stack.addWidget(self.build_generic_page("resets", ["ID","Titlu","Modul","Aplicabilitate","Verificat"]))
        self.stack.addWidget(self.build_generic_page("procedures", ["ID","Titlu","Categorie","Dificultate","Verificat"]))
        self.stack.addWidget(self.build_generic_page("components", ["ID","Componentă","Familie","Locație","Verificat"]))
        self.stack.addWidget(self.build_favorites_notes())
        self.stack.addWidget(self.build_tools())
        cl.addWidget(self.stack)

        outer.addWidget(sidebar)
        outer.addWidget(content, 1)
        self.setCentralWidget(root)

    def section_header(self, title, subtitle):
        w = QWidget(); lay = QVBoxLayout(w); lay.setContentsMargins(0,0,0,0)
        a = QLabel(title); a.setObjectName("sectionTitle")
        b = QLabel(subtitle); b.setObjectName("muted")
        lay.addWidget(a); lay.addWidget(b)
        return w

    def make_table(self, headers):
        t = QTableWidget(0, len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.setSelectionBehavior(QAbstractItemView.SelectRows)
        t.setSelectionMode(QAbstractItemView.SingleSelection)
        t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        t.setAlternatingRowColors(True)
        t.horizontalHeader().setStretchLastSection(True)
        t.verticalHeader().setVisible(False)
        return t

    def build_dashboard(self):
        page = QWidget(); lay = QVBoxLayout(page); lay.setContentsMargins(0,0,0,0)
        lay.addWidget(self.section_header("Super Master Overview", "Baza locală, funcțiile VCDS și conținutul tehnic"))
        grid = QGridLayout(); self.cards = {}
        keys = [("Vehicule","generations"),("Motoare","engines"),("DTC","dtcs"),("Module","modules"),
                ("Coding","coding"),("Adaptation","adaptations"),("Basic Settings","basic_settings"),("Proceduri","procedures")]
        for i,(label,key) in enumerate(keys):
            card = StatCard(label, "0", "înregistrări")
            self.cards[key] = card
            grid.addWidget(card, i//4, i%4)
        lay.addLayout(grid)
        quick = QFrame(); quick.setObjectName("panel"); ql = QVBoxLayout(quick)
        h = QLabel("Acces rapid"); h.setObjectName("panelTitle"); ql.addWidget(h)
        row = QHBoxLayout()
        for text, idx in [("Caută DTC",4),("Coding",6),("Adaptation",7),("Basic Settings",8),("Measuring Values",11)]:
            b = QPushButton(text); b.clicked.connect(lambda _=False, x=idx:self.open_page(x)); row.addWidget(b)
        row.addStretch(); ql.addLayout(row); lay.addWidget(quick); lay.addStretch()
        return page

    def build_search(self):
        page=QWidget(); l=QVBoxLayout(page); l.setContentsMargins(0,0,0,0)
        l.addWidget(self.section_header("Căutare globală", "Caută simultan în DTC, vehicule, motoare, module și proceduri"))
        self.search_table=self.make_table(["Tip","Cheie","Titlu","Detalii"]); l.addWidget(self.search_table)
        return page

    def build_vehicles(self):
        page=QWidget(); l=QVBoxLayout(page); l.setContentsMargins(0,0,0,0)
        l.addWidget(self.section_header("Vehicule", "Marcă → Model → Generație → Platformă"))
        filters=QHBoxLayout(); self.brand_filter=QComboBox(); self.brand_filter.addItem("Toate mărcile")
        for r in self.con.execute("SELECT name FROM brands ORDER BY name"): self.brand_filter.addItem(r[0])
        self.brand_filter.currentTextChanged.connect(self.refresh_vehicles)
        filters.addWidget(QLabel("Marcă:")); filters.addWidget(self.brand_filter); filters.addStretch(); l.addLayout(filters)
        self.vehicle_table=self.make_table(["Marcă","Model","Generație","Ani","Platformă"]); l.addWidget(self.vehicle_table)
        return page

    def build_engines(self):
        page=QWidget(); l=QVBoxLayout(page); l.setContentsMargins(0,0,0,0)
        l.addWidget(self.section_header("Motoare", "Cod motor, familie, putere și combustibil"))
        self.engine_table=self.make_table(["Cod","Fuel","L","CP","kW","Familie"]); l.addWidget(self.engine_table)
        return page

    def build_dtc(self):
        page=QWidget(); l=QVBoxLayout(page); l.setContentsMargins(0,0,0,0)
        l.addWidget(self.section_header("DTC Expert", "Coduri de eroare cu simptome, cauze, diagnostic și reparație"))
        bar=QHBoxLayout(); self.dtc_filter=QLineEdit(); self.dtc_filter.setPlaceholderText("Filtrează după cod sau descriere...")
        self.dtc_filter.textChanged.connect(self.refresh_dtc); self.severity_filter=QComboBox(); self.severity_filter.addItems(["Toate","Mediu","Ridicat","Critic"]); self.severity_filter.currentTextChanged.connect(self.refresh_dtc)
        bar.addWidget(self.dtc_filter); bar.addWidget(self.severity_filter); l.addLayout(bar)
        self.dtc_table=self.make_table(["Cod","Titlu","Severitate","Verificat"]); self.dtc_table.itemDoubleClicked.connect(self.open_dtc_detail); l.addWidget(self.dtc_table)
        return page

    def build_modules(self):
        page=QWidget(); l=QVBoxLayout(page); l.setContentsMargins(0,0,0,0)
        l.addWidget(self.section_header("Module VAG", "Adrese VCDS, familii și protocoale"))
        self.module_table=self.make_table(["Adresă","Modul","Familie","Protocol"]); l.addWidget(self.module_table)
        return page

    def build_generic_page(self, table_name, headers):
        page=QWidget(); l=QVBoxLayout(page); l.setContentsMargins(0,0,0,0)
        title=table_name.replace("_"," ").title(); l.addWidget(self.section_header(title, "Dublu-click pentru fișa completă"))
        table=self.make_table(headers); table.setProperty("source_table",table_name); table.itemDoubleClicked.connect(lambda item,t=table:self.open_generic_detail(t)); setattr(self,f"table_{table_name}",table); l.addWidget(table)
        return page

    def build_favorites_notes(self):
        page=QWidget(); l=QVBoxLayout(page); l.setContentsMargins(0,0,0,0)
        l.addWidget(self.section_header("Favorite & Note", "Salvează rapid elemente și observații proprii"))
        self.favorite_table=self.make_table(["Tip","Cheie","Etichetă","Creat"]); l.addWidget(QLabel("Favorite")); l.addWidget(self.favorite_table)
        self.notes_table=self.make_table(["Tip","Cheie","Notă","Creat"]); l.addWidget(QLabel("Note")); l.addWidget(self.notes_table)
        return page

    def build_tools(self):
        page=QWidget(); l=QVBoxLayout(page); l.setContentsMargins(0,0,0,0)
        l.addWidget(self.section_header("Instrumente", "Logo personal, backup, export și acces la baza locală"))
        panel=QFrame(); panel.setObjectName("panel"); pl=QVBoxLayout(panel)
        buttons=[("Setează logo-ul meu",self.choose_logo),("Backup SQLite",self.backup_db),("Export complet JSON",self.export_json_action),("Export DTC CSV",lambda:self.export_csv_action("dtcs")),("Export Vehicule CSV",lambda:self.export_csv_action("generations")),("Deschide folderul aplicației",self.open_app_folder)]
        for text,fn in buttons:
            b=QPushButton(text); b.clicked.connect(fn); pl.addWidget(b)
        pl.addStretch(); l.addWidget(panel); l.addStretch(); return page

    def open_page(self, index):
        self.stack.setCurrentIndex(index); self.page_title.setText(self.PAGE_NAMES[index])
        for i,b in enumerate(self.nav_buttons): b.setChecked(i==index)
        self.refresh_all()

    def fill(self, table, rows):
        table.setRowCount(len(rows))
        for i,row in enumerate(rows):
            vals=list(row)
            for j,v in enumerate(vals): table.setItem(i,j,QTableWidgetItem("" if v is None else str(v)))
        table.resizeColumnsToContents()

    def refresh_all(self):
        c=counts(self.con)
        for key,card in self.cards.items(): card.value.setText(str(c.get(key,0)))
        self.refresh_vehicles(); self.fill(self.engine_table,self.con.execute("SELECT code,fuel,displacement,power_hp,power_kw,family FROM engines ORDER BY code").fetchall()); self.refresh_dtc(); self.fill(self.module_table,self.con.execute("SELECT address,name,family,protocol FROM modules ORDER BY address").fetchall())
        self.refresh_generic_tables(); self.fill(self.favorite_table,self.con.execute("SELECT entity_type,entity_key,label,created_at FROM favorites ORDER BY id DESC").fetchall()); self.fill(self.notes_table,self.con.execute("SELECT entity_type,entity_key,note,created_at FROM notes ORDER BY id DESC LIMIT 200").fetchall())

    def refresh_vehicles(self):
        if not hasattr(self,"vehicle_table"): return
        brand=self.brand_filter.currentText() if hasattr(self,"brand_filter") else "Toate mărcile"
        sql="SELECT b.name,m.name,g.name,g.year_from||'–'||g.year_to,g.platform FROM generations g JOIN models m ON m.id=g.model_id JOIN brands b ON b.id=m.brand_id"
        args=()
        if brand!="Toate mărcile": sql+=" WHERE b.name=?"; args=(brand,)
        sql+=" ORDER BY b.name,m.name,g.year_from"; self.fill(self.vehicle_table,self.con.execute(sql,args).fetchall())

    def refresh_dtc(self):
        if not hasattr(self,"dtc_table"): return
        text=self.dtc_filter.text().strip() if hasattr(self,"dtc_filter") else ""; severity=self.severity_filter.currentText() if hasattr(self,"severity_filter") else "Toate"
        q="SELECT code,title,severity,CASE verified WHEN 1 THEN 'DA' ELSE 'DE VERIFICAT' END FROM dtcs WHERE (code LIKE ? OR title LIKE ? OR description LIKE ?)"; args=[f"%{text}%"]*3
        if severity!="Toate": q+=" AND severity=?"; args.append(severity)
        q+=" ORDER BY code"; self.fill(self.dtc_table,self.con.execute(q,args).fetchall())

    def refresh_generic_tables(self):
        mappings={
            "coding":"SELECT id,title,module_address,coding_type,effect,applicability,CASE verified WHEN 1 THEN 'DA' ELSE 'DE VERIFICAT' END FROM coding ORDER BY id",
            "adaptations":"SELECT id,title,module_address,channel,effect,applicability,CASE verified WHEN 1 THEN 'DA' ELSE 'DE VERIFICAT' END FROM adaptations ORDER BY id",
            "basic_settings":"SELECT id,title,module_address,group_name,applicability,CASE verified WHEN 1 THEN 'DA' ELSE 'DE VERIFICAT' END FROM basic_settings ORDER BY id",
            "output_tests":"SELECT id,title,module_address,applicability,CASE verified WHEN 1 THEN 'DA' ELSE 'DE VERIFICAT' END FROM output_tests ORDER BY id",
            "security_access":"SELECT id,title,module_address,purpose,applicability,CASE verified WHEN 1 THEN 'DA' ELSE 'DE VERIFICAT' END FROM security_access ORDER BY id",
            "measuring_values":"SELECT id,title,module_address,parameter,expected_value,units,CASE verified WHEN 1 THEN 'DA' ELSE 'DE VERIFICAT' END FROM measuring_values ORDER BY id",
            "resets":"SELECT id,title,module_address,applicability,CASE verified WHEN 1 THEN 'DA' ELSE 'DE VERIFICAT' END FROM resets ORDER BY id",
            "procedures":"SELECT id,title,category,difficulty,CASE verified WHEN 1 THEN 'DA' ELSE 'DE VERIFICAT' END FROM procedures ORDER BY id",
            "components":"SELECT id,name,family,location,CASE verified WHEN 1 THEN 'DA' ELSE 'DE VERIFICAT' END FROM components ORDER BY id"
        }
        for name,sql in mappings.items():
            table=getattr(self,f"table_{name}",None)
            if table: self.fill(table,self.con.execute(sql).fetchall())

    def run_global_search(self):
        q=self.global_search_box.text().strip()
        if not q: return
        self.fill(self.search_table,global_search(self.con,q)); log(self.con,"Global search","search",q,""); self.open_page(1)

    def open_dtc_detail(self, item):
        code=self.dtc_table.item(item.row(),0).text(); r=self.con.execute("SELECT d.*,s.title source_title,s.url FROM dtcs d LEFT JOIN sources s ON s.id=d.source_id WHERE code=?",(code,)).fetchone()
        if not r:return
        body=f"Cod: {r['code']}\nTitlu: {r['title']}\nSeveritate: {r['severity']}\nVerificat: {'DA' if r['verified'] else 'NU'}\n\nDESCRIERE\n{r['description']}\n\nSIMPTOME\n{r['symptoms']}\n\nCAUZE\n{r['causes']}\n\nDIAGNOSTIC\n{r['diagnosis']}\n\nREPARAȚIE\n{r['repair']}\n\nSURSĂ\n{r['source_title'] or ''}\n{r['url'] or ''}"
        dlg=DetailDialog(code,body,self); dlg.exec(); add_favorite(self.con,"DTC",code,r['title']); self.refresh_all()

    def open_generic_detail(self, table):
        row=table.currentRow(); source=table.property("source_table")
        if row<0:return
        rid=table.item(row,0).text(); r=self.con.execute(f"SELECT * FROM {source} WHERE id=?",(rid,)).fetchone()
        if not r:return
        body="\n\n".join(f"{k.upper()}\n{r[k] if r[k] is not None else ''}" for k in r.keys())
        DetailDialog(f"{source} #{rid}",body,self).exec(); add_favorite(self.con,source,rid,str(r[1] if len(r)>1 else rid)); self.refresh_all()

    def choose_logo(self):
        f,_=QFileDialog.getOpenFileName(self,"Alege logo","","Imagini (*.png *.jpg *.jpeg *.bmp *.webp)")
        if not f:return
        pix=QPixmap(f)
        if pix.isNull(): QMessageBox.warning(self,"Logo","Fișierul selectat nu este o imagine validă."); return
        pix.save(str(LOGO_PATH),"PNG"); self.logo.reload(); log(self.con,"Logo changed","settings",LOGO_PATH,""); QMessageBox.information(self,"Logo","Logo-ul tău a fost salvat și va rămâne în aplicație.")

    def backup_db(self):
        f,_=QFileDialog.getSaveFileName(self,"Backup bază","vag_master_super_backup.db","SQLite (*.db)")
        if f: backup_database(self.con,Path(f)); QMessageBox.information(self,"Backup","Backup creat cu succes.")

    def export_json_action(self):
        f,_=QFileDialog.getSaveFileName(self,"Export JSON","vag_master_super.json","JSON (*.json)")
        if f: export_json(self.con,Path(f)); QMessageBox.information(self,"Export","Export complet finalizat.")

    def export_csv_action(self, table):
        f,_=QFileDialog.getSaveFileName(self,"Export CSV",f"{table}.csv","CSV (*.csv)")
        if f: export_table_csv(self.con,table,Path(f)); QMessageBox.information(self,"Export","CSV exportat.")

    def open_app_folder(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(APP_DATA)))

    def apply_style(self):
        self.setStyleSheet("""
        QMainWindow{background:#08101f} QWidget{color:#e5edf7;font-size:13px;font-family:'Segoe UI'}
        #sidebar{background:#0b1425;border-right:1px solid #1f2b3d} #content{background:#0a1220}
        #brandName{font-size:22px;font-weight:800;color:#f8fafc} #brandSub{font-size:10px;font-weight:700;color:#60a5fa;letter-spacing:1px}
        #sideFooter{color:#64748b;padding-top:12px} #pageTitle{font-size:27px;font-weight:800;color:#f8fafc}
        #sectionTitle{font-size:20px;font-weight:750;color:#f8fafc} #muted{color:#8ea0b8} #panelTitle{font-size:16px;font-weight:700}
        #navButton{background:transparent;border:0;text-align:left;padding:10px 12px;border-radius:8px;color:#a9b7c9;font-weight:600}
        #navButton:hover{background:#111e33;color:white} #navButton:checked{background:#172554;color:#dbeafe;border-left:3px solid #3b82f6}
        QLineEdit,QComboBox,QTextEdit{background:#0e1a2d;border:1px solid #27364d;border-radius:8px;padding:9px;color:#f8fafc}
        QPushButton{background:#142239;border:1px solid #2b3a52;border-radius:8px;padding:9px 14px;font-weight:650}
        QPushButton:hover{background:#1b2d49} #primaryButton{background:#2563eb;border:1px solid #3b82f6;color:white}
        #statCard,#panel{background:#0f1b2e;border:1px solid #24324a;border-radius:12px} #statTitle{color:#93a4ba;font-weight:650}
        #statValue{font-size:26px;font-weight:800;color:#ffffff} QTableWidget{background:#0d1728;alternate-background-color:#101d31;border:1px solid #22314a;border-radius:8px;gridline-color:#1f2b3d;selection-background-color:#1d4ed8}
        QHeaderView::section{background:#142239;color:#dbe5f2;padding:9px;border:0;border-right:1px solid #22314a;font-weight:700}
        QScrollBar:vertical{background:#0d1728;width:11px} QScrollBar::handle:vertical{background:#334155;border-radius:5px;min-height:25px}
        #dialogTitle{font-size:20px;font-weight:800} QStatusBar{background:#0b1425;color:#7f91a8}
        """)
