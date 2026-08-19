import sys
import json
import csv
import shutil
import sqlite3
from pathlib import Path
from datetime import datetime

from PySide6.QtCore import Qt, QSize, QStandardPaths, QUrl
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFrame, QLabel, QPushButton, QLineEdit,
    QVBoxLayout, QHBoxLayout, QGridLayout, QStackedWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView, QComboBox, QTextEdit,
    QFileDialog, QMessageBox, QDialog, QDialogButtonBox
)

APP_NAME = "VAG MASTER Diagnostic PRO"
APP_VERSION = "3.0.0"


def app_data_dir():
    base = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
    path = Path(base) if base else Path.home() / ".vag_master_pro"
    path.mkdir(parents=True, exist_ok=True)
    return path


DB_PATH = app_data_dir() / "vag_master.db"


SCHEMA = """
CREATE TABLE IF NOT EXISTS dtc(
    code TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    severity TEXT DEFAULT 'Mediu',
    symptoms TEXT DEFAULT '',
    causes TEXT DEFAULT '',
    repair TEXT DEFAULT '',
    verified INTEGER DEFAULT 0,
    source TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS vehicles(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brand TEXT NOT NULL,
    model TEXT NOT NULL,
    generation TEXT NOT NULL,
    year_from INTEGER,
    year_to INTEGER,
    platform TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS modules(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    address TEXT,
    name TEXT,
    protocol TEXT,
    family TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS coding(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    module TEXT,
    effect TEXT,
    applicability TEXT DEFAULT '',
    restore_method TEXT DEFAULT '',
    verified INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS procedures(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    category TEXT,
    steps TEXT,
    warnings TEXT DEFAULT '',
    verified INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS notes(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT,
    entity_key TEXT,
    note TEXT,
    created_at TEXT
);
"""


def ensure_column(con, table, column, definition):
    cols = {row[1] for row in con.execute(f"PRAGMA table_info({table})")}
    if column not in cols:
        con.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def connect_db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    # Safe migration for databases created by older prototypes.
    for column, definition in [
        ("symptoms", "TEXT DEFAULT ''"), ("causes", "TEXT DEFAULT ''"),
        ("repair", "TEXT DEFAULT ''"), ("verified", "INTEGER DEFAULT 0"),
        ("source", "TEXT DEFAULT ''")
    ]:
        ensure_column(con, "dtc", column, definition)
    ensure_column(con, "vehicles", "platform", "TEXT DEFAULT ''")
    ensure_column(con, "modules", "family", "TEXT DEFAULT ''")
    ensure_column(con, "coding", "applicability", "TEXT DEFAULT ''")
    ensure_column(con, "coding", "restore_method", "TEXT DEFAULT ''")
    ensure_column(con, "coding", "verified", "INTEGER DEFAULT 0")
    ensure_column(con, "procedures", "warnings", "TEXT DEFAULT ''")
    ensure_column(con, "procedures", "verified", "INTEGER DEFAULT 0")
    seed(con)
    return con


def seed(con):
    if con.execute("SELECT COUNT(*) FROM dtc").fetchone()[0] == 0:
        con.executemany(
            "INSERT INTO dtc VALUES(?,?,?,?,?,?,?,?,?)",
            [
                ("P0401", "EGR - debit insuficient", "Debit EGR sub valoarea așteptată.", "Mediu",
                 "MIL; răspuns slab; posibil fum", "EGR colmatat; admisie murdară; vacuum/comandă; cablaj",
                 "Compară valorile cerute/reale, verifică traseul de admisie, comanda EGR și cablajul. Confirmă procedura specifică motorului.", 0, "Starter record"),
                ("P0299", "Turbocharger underboost", "Presiune de supraalimentare sub valoarea cerută.", "Ridicat",
                 "Putere redusă; limp mode", "Pierdere presiune; vacuum; actuator; geometrie; MAP",
                 "Compară boost specified/actual și verifică traseul charge-air, vacuumul și actuatorul.", 0, "Starter record"),
                ("P0101", "MAF range/performance", "Semnal MAF în afara intervalului așteptat.", "Mediu",
                 "Consum crescut; putere redusă", "MAF; fals aer; EGR; filtru aer",
                 "Verifică admisia și compară masa de aer cerută/reală înainte de înlocuirea senzorului.", 0, "Starter record"),
                ("P2002", "DPF efficiency below threshold", "Eficiența DPF sub prag.", "Ridicat",
                 "Martor DPF/MIL; regenerări dese", "DPF încărcat; senzori; probleme ardere",
                 "Verifică presiunea diferențială, încărcarea calculată și cauza producerii excesive de funingine.", 0, "Starter record"),
                ("P2463", "DPF soot accumulation", "Acumulare ridicată de funingine.", "Critic",
                 "Limitare putere; martor DPF", "Regenerări întrerupte; senzor diferențial; EGR/injecție",
                 "Nu forța regenerarea fără verificarea încărcării, temperaturilor, nivelului de ulei și condițiilor de siguranță.", 0, "Starter record")
            ]
        )
    if con.execute("SELECT COUNT(*) FROM vehicles").fetchone()[0] == 0:
        con.executemany(
            "INSERT INTO vehicles(brand,model,generation,year_from,year_to,platform) VALUES(?,?,?,?,?,?)",
            [
                ("Volkswagen","Golf","IV 1J",1997,2006,"PQ34"),
                ("Volkswagen","Golf","V 1K",2003,2009,"PQ35"),
                ("Volkswagen","Golf","VI 5K",2008,2013,"PQ35"),
                ("Volkswagen","Golf","VII 5G",2012,2020,"MQB"),
                ("Volkswagen","Golf","VIII CD",2019,2024,"MQB Evo"),
                ("Volkswagen","Passat","B5/B5.5",1996,2005,"PL45"),
                ("Volkswagen","Passat","B6",2005,2010,"PQ46"),
                ("Volkswagen","Passat","B7",2010,2014,"PQ46"),
                ("Volkswagen","Passat","B8",2014,2024,"MQB"),
                ("Audi","A3","8P",2003,2013,"PQ35"),
                ("Audi","A3","8V",2012,2020,"MQB"),
                ("Audi","A4","B7 8E",2004,2008,"PL46"),
                ("Audi","A4","B8 8K",2007,2016,"MLB"),
                ("Audi","A4","B9 8W",2015,2024,"MLB Evo"),
                ("Škoda","Octavia","II 1Z",2004,2013,"PQ35"),
                ("Škoda","Octavia","III 5E",2013,2020,"MQB"),
                ("Škoda","Octavia","IV NX",2019,2024,"MQB Evo"),
                ("SEAT / Cupra","Leon","III 5F",2012,2020,"MQB"),
                ("SEAT / Cupra","Leon","IV KL",2020,2024,"MQB Evo")
            ]
        )
    if con.execute("SELECT COUNT(*) FROM modules").fetchone()[0] == 0:
        con.executemany(
            "INSERT INTO modules(address,name,protocol,family) VALUES(?,?,?,?)",
            [("01","Engine","KWP/CAN/UDS","Powertrain"),("02","Auto Trans","CAN/UDS","Powertrain"),
             ("03","ABS Brakes","KWP/CAN/UDS","Chassis"),("08","HVAC","CAN/UDS","Body"),
             ("09","Central Electrics","KWP/CAN/UDS","Body"),("15","Airbags","KWP/CAN/UDS","Safety"),
             ("17","Instruments","KWP/CAN/UDS","Body"),("19","CAN Gateway","CAN/UDS","Network"),
             ("44","Steering Assist","CAN/UDS","Chassis"),("46","Comfort","KWP/CAN","Body"),
             ("5F","Information Electronics","UDS","Infotainment"),("55","Headlight Range","CAN/UDS","Body")]
        )
    if con.execute("SELECT COUNT(*) FROM coding").fetchone()[0] == 0:
        con.executemany(
            "INSERT INTO coding(title,module,effect,applicability,restore_method,verified) VALUES(?,?,?,?,?,?)",
            [("Coming / Leaving Home","09 Central Electrics","Iluminare de confort","Depinde de BCM/software/echipare","Restabilește coding/adaptation original",0),
             ("Auto Lock","46 Comfort / 09 Central Electrics","Blocare automată în mers","Depinde de generație","Restabilește valoarea originală",0),
             ("Needle Sweep","17 Instruments","Test ace la contact","Doar clustere compatibile","Dezactivează aceeași opțiune",0)]
        )
    if con.execute("SELECT COUNT(*) FROM procedures").fetchone()[0] == 0:
        con.executemany(
            "INSERT INTO procedures(title,category,steps,warnings,verified) VALUES(?,?,?,?,?)",
            [("Auto-Scan complet VCDS","Diagnostic","1. Conectează interfața.\n2. Contact ON.\n3. Rulează Auto-Scan.\n4. Salvează raportul.\n5. Documentează DTC înainte de ștergere.","Folosește tensiune stabilă când contactul rămâne pornit mult timp.",1),
             ("Backup înainte de Coding","Coding","1. Salvează Auto-Scan.\n2. Copiază coding-ul original.\n3. Modifică o singură opțiune.\n4. Testează.\n5. Notează schimbarea.","Nu copia coding de la alt vehicul fără verificarea hardware/software/PR-codes.",1)]
        )
    con.commit()


class BrandMark(QWidget):
    def __init__(self):
        super().__init__(); self.setFixedSize(54,54)
    def paintEvent(self, event):
        p=QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor("#3b82f6"),2)); p.setBrush(QColor("#111c32")); p.drawRoundedRect(3,3,48,48,14,14)
        p.setPen(QColor("#f8fafc")); p.setFont(QFont("Arial",18,QFont.Bold)); p.drawText(self.rect(),Qt.AlignCenter,"VM")


class StatCard(QFrame):
    def __init__(self,title,value,sub):
        super().__init__(); self.setObjectName("statCard")
        l=QVBoxLayout(self); l.setContentsMargins(18,16,18,16)
        a=QLabel(title); a.setObjectName("statLabel")
        self.value=QLabel(str(value)); self.value.setObjectName("statValue")
        b=QLabel(sub); b.setObjectName("muted")
        l.addWidget(a); l.addWidget(self.value); l.addWidget(b)


class DetailDialog(QDialog):
    def __init__(self,title,body,parent=None):
        super().__init__(parent); self.setWindowTitle(title); self.resize(780,600)
        l=QVBoxLayout(self); h=QLabel(title); h.setObjectName("dialogTitle")
        text=QTextEdit(); text.setReadOnly(True); text.setPlainText(body)
        buttons=QDialogButtonBox(QDialogButtonBox.Close); buttons.rejected.connect(self.reject)
        l.addWidget(h); l.addWidget(text); l.addWidget(buttons)


class MainWindow(QMainWindow):
    PAGES=["Dashboard","Căutare","Vehicule","DTC","Module","Coding VCDS","Proceduri","Instrumente"]
    def __init__(self):
        super().__init__(); self.con=connect_db(); self.nav=[]
        self.setWindowTitle(f"{APP_NAME} • v{APP_VERSION}"); self.resize(1520,920); self.setMinimumSize(1180,720)
        self.build_ui(); self.apply_style(); self.refresh_all(); self.open_page(0)
        self.statusBar().showMessage(f"Database: {DB_PATH}")

    def build_ui(self):
        root=QWidget(); outer=QHBoxLayout(root); outer.setContentsMargins(0,0,0,0); outer.setSpacing(0)
        side=QFrame(); side.setObjectName("sidebar"); side.setFixedWidth(255); sl=QVBoxLayout(side); sl.setContentsMargins(20,24,20,20)
        brand=QHBoxLayout(); brand.addWidget(BrandMark()); bt=QVBoxLayout(); name=QLabel("VAG MASTER"); name.setObjectName("brand"); ver=QLabel("DIAGNOSTIC PRO"); ver.setObjectName("brandSub"); bt.addWidget(name); bt.addWidget(ver); brand.addLayout(bt); brand.addStretch(); sl.addLayout(brand); sl.addSpacing(24)
        for i,label in enumerate(self.PAGES):
            b=QPushButton(label); b.setObjectName("nav"); b.setCheckable(True); b.setCursor(Qt.PointingHandCursor); b.clicked.connect(lambda _=False,x=i:self.open_page(x)); self.nav.append(b); sl.addWidget(b)
        sl.addStretch(); badge=QLabel(f"v{APP_VERSION}\n1996–2024"); badge.setObjectName("version"); sl.addWidget(badge)

        content=QFrame(); content.setObjectName("content"); cl=QVBoxLayout(content); cl.setContentsMargins(30,24,30,24); cl.setSpacing(16)
        top=QHBoxLayout(); self.page_title=QLabel("Dashboard"); self.page_title.setObjectName("pageTitle"); self.search=QLineEdit(); self.search.setPlaceholderText("DTC, model, generație, modul, coding..."); self.search.setMinimumWidth(420); self.search.returnPressed.connect(self.global_search)
        sb=QPushButton("Caută"); sb.setObjectName("primary"); sb.clicked.connect(self.global_search); top.addWidget(self.page_title); top.addStretch(); top.addWidget(self.search); top.addWidget(sb); cl.addLayout(top)
        self.stack=QStackedWidget(); self.stack.addWidget(self.page_dashboard()); self.stack.addWidget(self.page_search()); self.stack.addWidget(self.page_vehicles()); self.stack.addWidget(self.page_dtc()); self.stack.addWidget(self.page_modules()); self.stack.addWidget(self.page_coding()); self.stack.addWidget(self.page_procedures()); self.stack.addWidget(self.page_tools()); cl.addWidget(self.stack)
        outer.addWidget(side); outer.addWidget(content,1); self.setCentralWidget(root)

    def heading(self,title,sub):
        w=QWidget(); l=QVBoxLayout(w); l.setContentsMargins(0,0,0,0); a=QLabel(title); a.setObjectName("sectionTitle"); b=QLabel(sub); b.setObjectName("muted"); l.addWidget(a); l.addWidget(b); return w
    def make_table(self,headers):
        t=QTableWidget(0,len(headers)); t.setHorizontalHeaderLabels(headers); t.setSelectionBehavior(QAbstractItemView.SelectRows); t.setEditTriggers(QAbstractItemView.NoEditTriggers); t.setAlternatingRowColors(True); t.verticalHeader().setVisible(False); t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents); t.horizontalHeader().setStretchLastSection(True); return t
    def fill(self,t,rows):
        t.setRowCount(len(rows))
        for r,row in enumerate(rows):
            for c,val in enumerate(row): t.setItem(r,c,QTableWidgetItem("" if val is None else str(val)))

    def page_dashboard(self):
        w=QWidget(); l=QVBoxLayout(w); l.setContentsMargins(0,0,0,0); l.addWidget(self.heading("Overview","Starea bazei locale și acces rapid")); g=QGridLayout(); self.stats={}
        for i,k in enumerate(["Vehicule","DTC","Module","Coding"]): self.stats[k]=StatCard(k,0,"înregistrări"); g.addWidget(self.stats[k],0,i)
        l.addLayout(g); panel=QFrame(); panel.setObjectName("panel"); pl=QVBoxLayout(panel); ttl=QLabel("Flux recomandat"); ttl.setObjectName("panelTitle"); pl.addWidget(ttl); pl.addWidget(QLabel("1. Auto-Scan → 2. Salvează raportul → 3. Identifică DTC → 4. Verifică aplicabilitatea → 5. Repară → 6. Basic Settings / Adaptation doar dacă procedura o cere.")); l.addWidget(panel); l.addStretch(); return w

    def page_search(self):
        w=QWidget(); l=QVBoxLayout(w); l.setContentsMargins(0,0,0,0); l.addWidget(self.heading("Căutare globală","Caută în DTC, vehicule, module, coding și proceduri")); self.search_table=self.make_table(["Tip","Cheie","Titlu","Detalii"]); self.search_table.doubleClicked.connect(self.open_search_item); l.addWidget(self.search_table); return w

    def page_vehicles(self):
        w=QWidget(); l=QVBoxLayout(w); l.setContentsMargins(0,0,0,0); row=QHBoxLayout(); row.addWidget(self.heading("Vehicule","Catalog pe marcă, model, generație și platformă")); row.addStretch(); self.brand_filter=QComboBox(); self.brand_filter.addItems(["Toate","Volkswagen","Audi","Škoda","SEAT / Cupra"]); self.brand_filter.currentTextChanged.connect(self.load_vehicles); row.addWidget(self.brand_filter); l.addLayout(row); self.vehicle_table=self.make_table(["Marcă","Model","Generație","Ani","Platformă"]); l.addWidget(self.vehicle_table); return w

    def page_dtc(self):
        w=QWidget(); l=QVBoxLayout(w); l.setContentsMargins(0,0,0,0); row=QHBoxLayout(); row.addWidget(self.heading("DTC Knowledge Base","Dublu-click pentru fișa completă")); row.addStretch(); self.severity_filter=QComboBox(); self.severity_filter.addItems(["Toate","Mediu","Ridicat","Critic"]); self.severity_filter.currentTextChanged.connect(self.load_dtc); row.addWidget(self.severity_filter); l.addLayout(row); self.dtc_table=self.make_table(["Cod","Descriere","Severitate","Status","Sursă"]); self.dtc_table.doubleClicked.connect(self.open_dtc); l.addWidget(self.dtc_table); return w

    def page_modules(self):
        w=QWidget(); l=QVBoxLayout(w); l.setContentsMargins(0,0,0,0); l.addWidget(self.heading("Module VAG","Adrese de diagnoză și familii de controlere")); self.module_table=self.make_table(["Adresă","Modul","Protocol","Familie"]); l.addWidget(self.module_table); return w

    def page_coding(self):
        w=QWidget(); l=QVBoxLayout(w); l.setContentsMargins(0,0,0,0); l.addWidget(self.heading("Coding VCDS","Opțiuni documentate cu aplicabilitate și metodă de revenire")); self.coding_table=self.make_table(["Funcție","Modul","Efect","Aplicabilitate","Revenire","Status"]); self.coding_table.doubleClicked.connect(self.open_coding); l.addWidget(self.coding_table); return w

    def page_procedures(self):
        w=QWidget(); l=QVBoxLayout(w); l.setContentsMargins(0,0,0,0); l.addWidget(self.heading("Proceduri","Proceduri pas cu pas și avertismente")); self.proc_table=self.make_table(["Titlu","Categorie","Status"]); self.proc_table.doubleClicked.connect(self.open_procedure); l.addWidget(self.proc_table); return w

    def page_tools(self):
        w=QWidget(); l=QVBoxLayout(w); l.setContentsMargins(0,0,0,0); l.addWidget(self.heading("Instrumente","Backup, export și locația datelor aplicației")); p=QFrame(); p.setObjectName("panel"); pl=QGridLayout(p)
        actions=[("Backup SQLite",self.backup_db),("Export JSON",self.export_json),("Export DTC CSV",self.export_csv),("Deschide folder date",self.open_data_folder)]
        for i,(txt,fn) in enumerate(actions): b=QPushButton(txt); b.setObjectName("toolButton"); b.clicked.connect(fn); pl.addWidget(b,i//2,i%2)
        info=QLabel(f"Baza activă:\n{DB_PATH}"); info.setObjectName("muted"); pl.addWidget(info,2,0,1,2); l.addWidget(p); l.addStretch(); return w

    def open_page(self,index):
        self.stack.setCurrentIndex(index); self.page_title.setText(self.PAGES[index])
        for i,b in enumerate(self.nav): b.setChecked(i==index)

    def refresh_all(self):
        self.load_vehicles(); self.load_dtc(); self.fill(self.module_table,[(r['address'],r['name'],r['protocol'],r['family']) for r in self.con.execute("SELECT * FROM modules ORDER BY address")]); self.load_coding(); self.load_procedures(); self.update_stats()
    def update_stats(self):
        counts={"Vehicule":self.con.execute("SELECT COUNT(*) FROM vehicles").fetchone()[0],"DTC":self.con.execute("SELECT COUNT(*) FROM dtc").fetchone()[0],"Module":self.con.execute("SELECT COUNT(*) FROM modules").fetchone()[0],"Coding":self.con.execute("SELECT COUNT(*) FROM coding").fetchone()[0]}
        for k,v in counts.items(): self.stats[k].value.setText(str(v))
    def load_vehicles(self):
        brand=self.brand_filter.currentText() if hasattr(self,'brand_filter') else "Toate"; sql="SELECT brand,model,generation,year_from,year_to,platform FROM vehicles"; p=[]
        if brand!="Toate": sql+=" WHERE brand=?"; p=[brand]
        sql+=" ORDER BY brand,model,year_from"; self.fill(self.vehicle_table,[(r['brand'],r['model'],r['generation'],f"{r['year_from']}–{r['year_to']}",r['platform']) for r in self.con.execute(sql,p)])
    def load_dtc(self):
        sev=self.severity_filter.currentText() if hasattr(self,'severity_filter') else "Toate"; sql="SELECT * FROM dtc"; p=[]
        if sev!="Toate": sql+=" WHERE severity=?"; p=[sev]
        sql+=" ORDER BY code"; self.fill(self.dtc_table,[(r['code'],r['title'],r['severity'],"Verificat" if r['verified'] else "De verificat",r['source']) for r in self.con.execute(sql,p)])
    def load_coding(self): self.fill(self.coding_table,[(r['title'],r['module'],r['effect'],r['applicability'],r['restore_method'],"Verificat" if r['verified'] else "De verificat") for r in self.con.execute("SELECT * FROM coding ORDER BY module,title")])
    def load_procedures(self): self.fill(self.proc_table,[(r['title'],r['category'],"Verificat" if r['verified'] else "De verificat") for r in self.con.execute("SELECT * FROM procedures ORDER BY category,title")])

    def global_search(self):
        q=self.search.text().strip();
        if not q: return
        like=f"%{q}%"; out=[]
        out += [("DTC",r['code'],r['title'],r['description']) for r in self.con.execute("SELECT * FROM dtc WHERE code LIKE ? OR title LIKE ? OR description LIKE ?",(like,like,like))]
        out += [("Vehicul",r['model'],r['generation'],f"{r['brand']} • {r['platform']}") for r in self.con.execute("SELECT * FROM vehicles WHERE brand LIKE ? OR model LIKE ? OR generation LIKE ? OR platform LIKE ?",(like,like,like,like))]
        out += [("Modul",r['address'],r['name'],r['protocol']) for r in self.con.execute("SELECT * FROM modules WHERE address LIKE ? OR name LIKE ? OR family LIKE ?",(like,like,like))]
        out += [("Coding",str(r['id']),r['title'],r['module']) for r in self.con.execute("SELECT * FROM coding WHERE title LIKE ? OR module LIKE ? OR effect LIKE ?",(like,like,like))]
        out += [("Procedură",str(r['id']),r['title'],r['category']) for r in self.con.execute("SELECT * FROM procedures WHERE title LIKE ? OR category LIKE ? OR steps LIKE ?",(like,like,like))]
        self.fill(self.search_table,out); self.open_page(1); self.statusBar().showMessage(f"{len(out)} rezultate pentru «{q}»",5000)
    def open_search_item(self,index):
        t=self.search_table.item(index.row(),0).text(); key=self.search_table.item(index.row(),1).text()
        if t=="DTC": self.show_dtc(key)
    def open_dtc(self,index): self.show_dtc(self.dtc_table.item(index.row(),0).text())
    def show_dtc(self,code):
        r=self.con.execute("SELECT * FROM dtc WHERE code=?",(code,)).fetchone();
        if not r:return
        body=f"COD: {r['code']}\nTITLU: {r['title']}\nSEVERITATE: {r['severity']}\nSTATUS: {'Verificat' if r['verified'] else 'De verificat'}\nSURSA: {r['source']}\n\nDESCRIERE\n{r['description']}\n\nSIMPTOME\n{r['symptoms']}\n\nCAUZE POSIBILE\n{r['causes']}\n\nDIAGNOSTIC / REPARAȚIE\n{r['repair']}\n\nNotă: aplicabilitatea exactă depinde de vehicul, motor, ECU și versiunea software."
        DetailDialog(f"{r['code']} • {r['title']}",body,self).exec()
    def open_coding(self,index):
        title=self.coding_table.item(index.row(),0).text(); r=self.con.execute("SELECT * FROM coding WHERE title=?",(title,)).fetchone();
        if r: DetailDialog(title,f"MODUL\n{r['module']}\n\nEFECT\n{r['effect']}\n\nAPLICABILITATE\n{r['applicability']}\n\nREVENIRE\n{r['restore_method']}\n\nSTATUS\n{'Verificat' if r['verified'] else 'De verificat'}",self).exec()
    def open_procedure(self,index):
        title=self.proc_table.item(index.row(),0).text(); r=self.con.execute("SELECT * FROM procedures WHERE title=?",(title,)).fetchone();
        if r: DetailDialog(title,f"CATEGORIE\n{r['category']}\n\nPAȘI\n{r['steps']}\n\nAVERTISMENTE\n{r['warnings']}\n\nSTATUS\n{'Verificat' if r['verified'] else 'De verificat'}",self).exec()

    def backup_db(self):
        f,_=QFileDialog.getSaveFileName(self,"Backup database",f"vag_master_backup_{datetime.now():%Y%m%d_%H%M%S}.db","SQLite (*.db)")
        if f: self.con.commit(); shutil.copy2(DB_PATH,f); QMessageBox.information(self,"Backup","Backup creat cu succes.")
    def export_json(self):
        f,_=QFileDialog.getSaveFileName(self,"Export JSON","vag_master_export.json","JSON (*.json)")
        if not f:return
        tables=["dtc","vehicles","modules","coding","procedures"]; data={t:[dict(r) for r in self.con.execute(f"SELECT * FROM {t}")] for t in tables}; Path(f).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8"); QMessageBox.information(self,"Export","Export JSON finalizat.")
    def export_csv(self):
        f,_=QFileDialog.getSaveFileName(self,"Export DTC CSV","dtc_export.csv","CSV (*.csv)")
        if not f:return
        rows=self.con.execute("SELECT code,title,severity,verified,source FROM dtc ORDER BY code").fetchall()
        with open(f,"w",newline="",encoding="utf-8-sig") as h:
            w=csv.writer(h); w.writerow(["Code","Title","Severity","Verified","Source"]); w.writerows(rows)
        QMessageBox.information(self,"Export","Export CSV finalizat.")
    def open_data_folder(self): QDesktopServices.openUrl(QUrl.fromLocalFile(str(app_data_dir())))

    def apply_style(self):
        self.setStyleSheet("""
        QMainWindow,QWidget{background:#0b1220;color:#dbe7f5;font-family:'Segoe UI',Arial;font-size:13px}
        QFrame#sidebar{background:#0a1020;border-right:1px solid #1d2a3d}
        QFrame#content{background:#0d1525}
        QLabel#brand{font-size:19px;font-weight:800;color:#f8fbff} QLabel#brandSub{font-size:10px;font-weight:700;color:#5fa8ff;letter-spacing:2px}
        QLabel#version{color:#64748b;font-size:11px;padding:8px} QLabel#pageTitle{font-size:25px;font-weight:800;color:#f8fbff}
        QLabel#sectionTitle{font-size:18px;font-weight:750;color:#eef6ff} QLabel#muted{color:#7f93ab} QLabel#panelTitle{font-size:15px;font-weight:700}
        QLabel#statLabel{color:#8ea3ba;font-weight:600} QLabel#statValue{font-size:28px;font-weight:850;color:#f8fbff}
        QPushButton#nav{background:transparent;border:0;border-radius:8px;text-align:left;padding:12px 14px;color:#91a4ba;font-weight:600}
        QPushButton#nav:hover{background:#111c31;color:#e8f2ff} QPushButton#nav:checked{background:#14243e;color:#70b4ff;border-left:3px solid #3b82f6}
        QPushButton#primary{background:#2563eb;border:0;border-radius:8px;padding:10px 18px;color:white;font-weight:700} QPushButton#primary:hover{background:#3478f6}
        QPushButton#toolButton{background:#111d31;border:1px solid #253650;border-radius:10px;padding:18px;text-align:left;font-weight:700} QPushButton#toolButton:hover{border-color:#3b82f6;background:#14243e}
        QLineEdit,QComboBox{background:#0a1120;border:1px solid #24334a;border-radius:8px;padding:10px 12px;color:#e5eef9} QLineEdit:focus,QComboBox:focus{border:1px solid #3b82f6}
        QFrame#statCard,QFrame#panel{background:#101a2c;border:1px solid #1f3048;border-radius:12px}
        QTableWidget{background:#0d1627;alternate-background-color:#101b2e;border:1px solid #1d2d44;border-radius:10px;gridline-color:#18273b;selection-background-color:#17345c;selection-color:#fff}
        QHeaderView::section{background:#101b2d;color:#8fa6bf;border:0;border-bottom:1px solid #263851;padding:10px;font-weight:700}
        QTableWidget::item{padding:7px;border:0} QScrollBar:vertical{background:#0b1322;width:10px} QScrollBar::handle:vertical{background:#2a3c55;border-radius:5px;min-height:30px}
        QStatusBar{background:#09101d;color:#6f839b;border-top:1px solid #1b293c} QTextEdit{background:#0a1120;border:1px solid #253650;border-radius:8px;padding:12px;color:#dce8f7} QLabel#dialogTitle{font-size:18px;font-weight:800}
        """)


def main():
    app=QApplication(sys.argv); app.setApplicationName(APP_NAME); app.setOrganizationName("VAG MASTER"); app.setStyle("Fusion")
    w=MainWindow(); w.show(); return app.exec()


if __name__=="__main__":
    raise SystemExit(main())
