import sys, sqlite3
from pathlib import Path
from PySide6.QtWidgets import QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QPushButton,QTabWidget,QTableWidget,QTableWidgetItem,QFileDialog

DB=Path(__file__).parent/"data"/"vag_master.db"
DB.parent.mkdir(exist_ok=True)
con=sqlite3.connect(DB)
con.executescript('''
CREATE TABLE IF NOT EXISTS dtc(code TEXT PRIMARY KEY,title TEXT,description TEXT,severity TEXT);
CREATE TABLE IF NOT EXISTS vehicles(brand TEXT,model TEXT,generation TEXT,year_from INTEGER,year_to INTEGER);
CREATE TABLE IF NOT EXISTS modules(address TEXT,name TEXT,protocol TEXT);
CREATE TABLE IF NOT EXISTS coding(id INTEGER PRIMARY KEY,title TEXT,module TEXT,effect TEXT,verified INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS procedures(id INTEGER PRIMARY KEY,title TEXT,category TEXT,steps TEXT,verified INTEGER DEFAULT 0);
''')
if con.execute("SELECT COUNT(*) FROM dtc").fetchone()[0]==0:
    con.executemany("INSERT INTO dtc VALUES(?,?,?,?)",[
      ("P0401","EGR insufficient flow","Engine-specific diagnosis required.","Medium"),
      ("P0299","Turbocharger underboost","Check boost control and charge-air system.","High"),
      ("P0101","MAF range/performance","Compare measured and specified air mass.","Medium"),
      ("P2002","DPF efficiency below threshold","Use engine-specific DPF diagnosis.","High"),
      ("P2463","DPF soot accumulation","Verify regeneration prerequisites first.","High")])
    con.executemany("INSERT INTO vehicles VALUES(?,?,?,?,?)",[
      ("Volkswagen","Golf","IV 1J",1997,2006),("Volkswagen","Golf","V 1K",2003,2009),
      ("Volkswagen","Golf","VI 5K",2008,2013),("Volkswagen","Golf","VII 5G",2012,2020),
      ("Volkswagen","Golf","VIII CD",2019,2024),("Volkswagen","Passat","B5/B5.5",1996,2005),
      ("Volkswagen","Passat","B6",2005,2010),("Volkswagen","Passat","B7",2010,2014),
      ("Volkswagen","Passat","B8",2014,2024),("Audi","A3","8P",2003,2013),
      ("Audi","A3","8V",2012,2020),("Audi","A4","B7",2004,2008),("Audi","A4","B8",2007,2016),
      ("Audi","A4","B9",2015,2024),("Škoda","Octavia","I 1U",1996,2010),
      ("Škoda","Octavia","II 1Z",2004,2013),("Škoda","Octavia","III 5E",2013,2020),
      ("Škoda","Octavia","IV NX",2019,2024),("SEAT / Cupra","Leon","III 5F",2012,2020),
      ("SEAT / Cupra","Leon","IV KL",2020,2024)])
    con.executemany("INSERT INTO modules VALUES(?,?,?)",[
      ("01","Engine","KWP/CAN/UDS"),("02","Auto Trans","CAN/UDS"),("03","ABS Brakes","KWP/CAN/UDS"),
      ("08","HVAC","CAN/UDS"),("09","Central Electrics","KWP/CAN/UDS"),("15","Airbags","KWP/CAN/UDS"),
      ("17","Instruments","KWP/CAN/UDS"),("19","CAN Gateway","CAN/UDS"),("44","Steering Assist","CAN/UDS"),
      ("46","Comfort","KWP/CAN"),("5F","Information Electronics","UDS"),("55","Headlight Range","CAN/UDS")])
    con.commit()

class Main(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle("VAG MASTER Diagnostic PRO"); self.resize(1400,850)
        c=QWidget(); l=QVBoxLayout(c); h=QHBoxLayout(); title=QLabel("VAG MASTER"); title.setObjectName("logo")
        h.addWidget(title); h.addWidget(QLabel("Diagnostic Database PRO • 1996–2024")); h.addStretch(); l.addLayout(h)
        sr=QHBoxLayout(); self.q=QLineEdit(); self.q.setPlaceholderText("Caută DTC, model, generație, modul...")
        b=QPushButton("Caută"); b.clicked.connect(self.search); self.q.returnPressed.connect(self.search); sr.addWidget(self.q); sr.addWidget(b); l.addLayout(sr)
        self.tabs=QTabWidget(); self.result=self.table(["Tip","Cheie","Titlu","Detalii"]); self.veh=self.table(["Marcă","Model","Generație","De la","Până la"]); self.dtc=self.table(["Cod","Titlu","Descriere","Severitate"]); self.mod=self.table(["Adresă","Modul","Protocol"])
        for n,w in [("Căutare",self.result),("Vehicule",self.veh),("DTC",self.dtc),("Module",self.mod)]: self.tabs.addTab(w,n)
        l.addWidget(self.tabs); self.setCentralWidget(c); self.load()
        self.setStyleSheet("QMainWindow{background:#0b1120} QWidget{color:#e5e7eb;font-size:13px} QLabel#logo{font-size:30px;font-weight:bold} QLineEdit{background:#111827;border:1px solid #334155;border-radius:8px;padding:12px} QPushButton{background:#1e293b;padding:10px 16px;border-radius:8px} QTableWidget{background:#111827;alternate-background-color:#172033} QHeaderView::section{background:#1e293b;padding:8px} QTabBar::tab{padding:10px 16px}")
    def table(self,h):
        t=QTableWidget(0,len(h)); t.setHorizontalHeaderLabels(h); t.setAlternatingRowColors(True); t.horizontalHeader().setStretchLastSection(True); return t
    def fill(self,t,rows):
        t.setRowCount(len(rows))
        for i,r in enumerate(rows):
            for j,v in enumerate(r): t.setItem(i,j,QTableWidgetItem(str(v)))
        t.resizeColumnsToContents()
    def load(self):
        self.fill(self.veh,con.execute("SELECT * FROM vehicles ORDER BY brand,model,year_from").fetchall())
        self.fill(self.dtc,con.execute("SELECT * FROM dtc ORDER BY code").fetchall())
        self.fill(self.mod,con.execute("SELECT * FROM modules ORDER BY address").fetchall())
    def search(self):
        x="%"+self.q.text().strip()+"%"
        rows=[]
        rows += [("DTC",r[0],r[1],r[2]) for r in con.execute("SELECT code,title,description FROM dtc WHERE code LIKE ? OR title LIKE ?",(x,x))]
        rows += [("VEHICLE",r[0]+" "+r[1],r[2],str(r[3])+"-"+str(r[4])) for r in con.execute("SELECT * FROM vehicles WHERE brand LIKE ? OR model LIKE ? OR generation LIKE ?",(x,x,x))]
        rows += [("MODULE",r[0],r[1],r[2]) for r in con.execute("SELECT * FROM modules WHERE address LIKE ? OR name LIKE ?",(x,x))]
        self.fill(self.result,rows); self.tabs.setCurrentWidget(self.result)

app=QApplication(sys.argv); w=Main(); w.show(); sys.exit(app.exec())
