import sys
import sqlite3
import shutil
import json
from pathlib import Path
from datetime import datetime

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QPainter, QPen, QColor
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QStackedWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QFileDialog, QMessageBox, QFrame, QGridLayout, QAbstractItemView,
    QDialog, QTextEdit, QDialogButtonBox, QComboBox
)

APP_ROOT = Path(__file__).resolve().parent
DATA_DIR = APP_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "vag_master.db"


def connect_db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.executescript('''
    CREATE TABLE IF NOT EXISTS dtc(
        code TEXT PRIMARY KEY,
        title TEXT,
        description TEXT,
        severity TEXT,
        symptoms TEXT DEFAULT '',
        causes TEXT DEFAULT '',
        repair TEXT DEFAULT '',
        verified INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS vehicles(
        brand TEXT,
        model TEXT,
        generation TEXT,
        year_from INTEGER,
        year_to INTEGER
    );
    CREATE TABLE IF NOT EXISTS modules(
        address TEXT,
        name TEXT,
        protocol TEXT
    );
    CREATE TABLE IF NOT EXISTS coding(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        module TEXT,
        effect TEXT,
        applicability TEXT DEFAULT '',
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
    ''')
    if con.execute("SELECT COUNT(*) FROM dtc").fetchone()[0] == 0:
        con.executemany(
            "INSERT INTO dtc(code,title,description,severity,symptoms,causes,repair,verified) VALUES(?,?,?,?,?,?,?,?)",
            [
                ("P0401", "EGR insufficient flow", "Debit EGR insuficient. Diagnosticul exact depinde de motor/ECU.", "Mediu",
                 "Martor motor; răspuns slab; posibil fum", "EGR colmatat; admisie murdară; vacuum/comandă; cablaj",
                 "Verifică DTC-urile asociate, valorile măsurate, comanda EGR, traseul de admisie și cablajul. Confirmă procedura specifică motorului.", 0),
                ("P0299", "Turbocharger underboost", "Presiune de supraalimentare sub valoarea cerută.", "Ridicat",
                 "Putere redusă; limp mode", "Furtun fisurat; actuator; vacuum; geometrie; senzor MAP",
                 "Compară presiunea cerută/reală, verifică traseul charge-air, vacuumul și actuatorul turbinei.", 0),
                ("P0101", "MAF range/performance", "Semnal debitmetru în afara intervalului așteptat.", "Mediu",
                 "Putere redusă; consum crescut", "MAF murdar/defect; fals aer; EGR; filtru aer",
                 "Compară masa de aer cerută/reală și verifică admisia înainte de înlocuirea senzorului.", 0),
                ("P2002", "DPF efficiency below threshold", "Eficiența filtrului de particule sub prag.", "Ridicat",
                 "Martor DPF/MIL; regenerări dese", "DPF încărcat; senzori presiune/temperatură; probleme ardere",
                 "Verifică încărcarea calculată, presiunea diferențială și cauza producerii excesive de funingine înainte de regenerare.", 0),
                ("P2463", "DPF soot accumulation", "Acumulare ridicată de funingine în DPF.", "Ridicat",
                 "Martor DPF; limitare putere", "Regenerări întrerupte; senzor diferențial; EGR/injecție",
                 "Nu forța regenerarea fără verificarea temperaturilor, încărcării, uleiului și condițiilor de siguranță.", 0),
            ],
        )
        con.executemany(
            "INSERT INTO vehicles VALUES(?,?,?,?,?)",
            [
                ("Volkswagen", "Golf", "IV 1J", 1997, 2006),
                ("Volkswagen", "Golf", "V 1K", 2003, 2009),
                ("Volkswagen", "Golf", "VI 5K", 2008, 2013),
                ("Volkswagen", "Golf", "VII 5G", 2012, 2020),
                ("Volkswagen", "Golf", "VIII CD", 2019, 2024),
                ("Volkswagen", "Passat", "B5/B5.5", 1996, 2005),
                ("Volkswagen", "Passat", "B6", 2005, 2010),
                ("Volkswagen", "Passat", "B7", 2010, 2014),
                ("Volkswagen", "Passat", "B8", 2014, 2024),
                ("Audi", "A3", "8P", 2003, 2013),
                ("Audi", "A3", "8V", 2012, 2020),
                ("Audi", "A4", "B7", 2004, 2008),
                ("Audi", "A4", "B8", 2007, 2016),
                ("Audi", "A4", "B9", 2015, 2024),
                ("Škoda", "Octavia", "I 1U", 1996, 2010),
                ("Škoda", "Octavia", "II 1Z", 2004, 2013),
                ("Škoda", "Octavia", "III 5E", 2013, 2020),
                ("Škoda", "Octavia", "IV NX", 2019, 2024),
                ("SEAT / Cupra", "Leon", "III 5F", 2012, 2020),
                ("SEAT / Cupra", "Leon", "IV KL", 2020, 2024),
            ],
        )
        con.executemany(
            "INSERT INTO modules VALUES(?,?,?)",
            [
                ("01", "Engine", "KWP/CAN/UDS"),
                ("02", "Auto Trans", "CAN/UDS"),
                ("03", "ABS Brakes", "KWP/CAN/UDS"),
                ("08", "HVAC", "CAN/UDS"),
                ("09", "Central Electrics", "KWP/CAN/UDS"),
                ("15", "Airbags", "KWP/CAN/UDS"),
                ("17", "Instruments", "KWP/CAN/UDS"),
                ("19", "CAN Gateway", "CAN/UDS"),
                ("44", "Steering Assist", "CAN/UDS"),
                ("46", "Comfort", "KWP/CAN"),
                ("5F", "Information Electronics", "UDS"),
                ("55", "Headlight Range", "CAN/UDS"),
            ],
        )
        con.executemany(
            "INSERT INTO coding(title,module,effect,applicability,verified) VALUES(?,?,?,?,?)",
            [
                ("Coming / Leaving Home", "09 Central Electrics", "Controlează iluminarea de confort", "Depinde de BCM, software și echipare", 0),
                ("Auto Lock", "46 Comfort / 09 Central Electrics", "Blocare automată în mers", "Depinde de generație", 0),
                ("Needle Sweep", "17 Instruments", "Test ace la contact", "Doar clustere compatibile", 0),
            ],
        )
        con.executemany(
            "INSERT INTO procedures(title,category,steps,warnings,verified) VALUES(?,?,?,?,?)",
            [
                ("Scanare completă VCDS", "Diagnostic", "1. Conectează interfața.\n2. Contact ON.\n3. Auto-Scan.\n4. Salvează raportul.\n5. Nu șterge DTC înainte de documentare.", "Folosește alimentare stabilă când lucrezi mult cu contactul pus.", 1),
                ("Backup coding înainte de modificări", "Coding", "1. Deschide modulul.\n2. Copiază coding-ul original.\n3. Salvează Auto-Scan.\n4. Modifică o singură funcție odată.\n5. Testează și documentează.", "Nu aplica coding de pe altă mașină fără verificarea hardware/software/PR-codes.", 1),
            ],
        )
        con.commit()
    return con


class LogoWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(58, 58)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor("#60a5fa"), 3)
        p.setPen(pen)
        p.setBrush(QColor("#0f1b33"))
        p.drawRoundedRect(5, 5, 48, 48, 14, 14)
        p.setPen(QColor("#f8fafc"))
        font = QFont("Arial", 20, QFont.Bold)
        p.setFont(font)
        p.drawText(self.rect(), Qt.AlignCenter, "V")


class Card(QFrame):
    def __init__(self, title, value, subtitle=""):
        super().__init__()
        self.setObjectName("card")
        lay = QVBoxLayout(self)
        title_lbl = QLabel(title)
        title_lbl.setObjectName("cardTitle")
        value_lbl = QLabel(str(value))
        value_lbl.setObjectName("cardValue")
        sub_lbl = QLabel(subtitle)
        sub_lbl.setObjectName("cardSub")
        lay.addWidget(title_lbl)
        lay.addWidget(value_lbl)
        lay.addWidget(sub_lbl)
        lay.addStretch()


class DetailDialog(QDialog):
    def __init__(self, title, body, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(760, 560)
        lay = QVBoxLayout(self)
        header = QLabel(title)
        header.setObjectName("dialogTitle")
        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(body)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        lay.addWidget(header)
        lay.addWidget(text)
        lay.addWidget(buttons)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.con = connect_db()
        self.setWindowTitle("VAG MASTER Diagnostic PRO")
        self.resize(1500, 900)
        self.setMinimumSize(1180, 720)
        self.nav_buttons = []
        self.build_ui()
        self.apply_style()
        self.refresh_all()
        self.statusBar().showMessage("VAG MASTER Diagnostic PRO • baza locală SQLite încărcată")

    def build_ui(self):
        root = QWidget()
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(245)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(20, 24, 20, 20)
        side.setSpacing(8)

        brand = QHBoxLayout()
        brand.addWidget(LogoWidget())
        brand_text = QVBoxLayout()
        name = QLabel("VAG MASTER")
        name.setObjectName("brandName")
        pro = QLabel("DIAGNOSTIC PRO")
        pro.setObjectName("brandSub")
        brand_text.addWidget(name)
        brand_text.addWidget(pro)
        brand.addLayout(brand_text)
        brand.addStretch()
        side.addLayout(brand)
        side.addSpacing(22)

        nav = [
            ("Dashboard", "▦"),
            ("Căutare", "⌕"),
            ("Vehicule", "▣"),
            ("DTC", "⚠"),
            ("Module", "◫"),
            ("Coding", "⌘"),
            ("Proceduri", "☑"),
            ("Instrumente", "⚙"),
        ]
        for index, (text, icon) in enumerate(nav):
            btn = QPushButton(f"{icon}   {text}")
            btn.setObjectName("navButton")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, i=index: self.open_page(i))
            self.nav_buttons.append(btn)
            side.addWidget(btn)
        side.addStretch()

        footer = QLabel("v2.0 • 1996–2024\nLocal database")
        footer.setObjectName("sideFooter")
        side.addWidget(footer)

        content = QFrame()
        content.setObjectName("content")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(30, 24, 30, 24)
        content_layout.setSpacing(18)

        top = QHBoxLayout()
        self.page_title = QLabel("Dashboard")
        self.page_title.setObjectName("pageTitle")
        self.global_search = QLineEdit()
        self.global_search.setPlaceholderText("Caută DTC, model, generație, modul, coding...")
        self.global_search.setMinimumWidth(430)
        self.global_search.returnPressed.connect(self.run_global_search)
        search_btn = QPushButton("Caută")
        search_btn.setObjectName("primaryButton")
        search_btn.clicked.connect(self.run_global_search)
        top.addWidget(self.page_title)
        top.addStretch()
        top.addWidget(self.global_search)
        top.addWidget(search_btn)
        content_layout.addLayout(top)

        self.stack = QStackedWidget()
        self.stack.addWidget(self.build_dashboard())
        self.stack.addWidget(self.build_search_page())
        self.stack.addWidget(self.build_vehicle_page())
        self.stack.addWidget(self.build_dtc_page())
        self.stack.addWidget(self.build_module_page())
        self.stack.addWidget(self.build_coding_page())
        self.stack.addWidget(self.build_procedure_page())
        self.stack.addWidget(self.build_tools_page())
        content_layout.addWidget(self.stack)

        layout.addWidget(sidebar)
        layout.addWidget(content, 1)
        self.setCentralWidget(root)
        self.open_page(0)

    def section_header(self, title, subtitle):
        box = QWidget()
        lay = QVBoxLayout(box)
        lay.setContentsMargins(0, 0, 0, 0)
        a = QLabel(title)
        a.setObjectName("sectionTitle")
        b = QLabel(subtitle)
        b.setObjectName("sectionSub")
        lay.addWidget(a)
        lay.addWidget(b)
        return box

    def build_dashboard(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.section_header("Overview", "Baza VAG, acces rapid și starea conținutului"))
        self.cards = QGridLayout()
        self.card_widgets = {}
        for i, key in enumerate(["Vehicule", "DTC", "Module", "Coding"]):
            card = Card(key, "0", "înregistrări disponibile")
            self.card_widgets[key] = card
            self.cards.addWidget(card, 0, i)
        lay.addLayout(self.cards)

        quick = QLabel("Acces rapid")
        quick.setObjectName("sectionTitle")
        lay.addWidget(quick)
        qrow = QHBoxLayout()
        for text, page_index in [("Caută un DTC", 1), ("Deschide vehicule", 2), ("Vezi coding", 5), ("Proceduri", 6)]:
            b = QPushButton(text)
            b.setObjectName("actionButton")
            b.clicked.connect(lambda checked=False, i=page_index: self.open_page(i))
            qrow.addWidget(b)
        lay.addLayout(qrow)

        note = QFrame()
        note.setObjectName("notice")
        nl = QVBoxLayout(note)
        nt = QLabel("Validare tehnică")
        nt.setObjectName("noticeTitle")
        nb = QLabel("Codările și procedurile model-specifice trebuie marcate ca verificate înainte de utilizarea pe o mașină reală. Aplicația păstrează separat informațiile demonstrative de cele validate.")
        nb.setWordWrap(True)
        nb.setObjectName("noticeBody")
        nl.addWidget(nt)
        nl.addWidget(nb)
        lay.addWidget(note)
        lay.addStretch()
        return page

    def new_table(self, headers):
        t = QTableWidget(0, len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        t.horizontalHeader().setStretchLastSection(True)
        t.verticalHeader().setVisible(False)
        t.setSelectionBehavior(QAbstractItemView.SelectRows)
        t.setEditTriggers(QAbstractItemView.NoEditTriggers)
        t.setAlternatingRowColors(True)
        return t

    def build_search_page(self):
        page = QWidget(); lay = QVBoxLayout(page); lay.setContentsMargins(0,0,0,0)
        lay.addWidget(self.section_header("Căutare globală", "Caută simultan în DTC, vehicule, module, coding și proceduri"))
        self.search_results = self.new_table(["Tip", "Cod / Cheie", "Titlu", "Detalii"])
        self.search_results.doubleClicked.connect(self.open_search_result)
        lay.addWidget(self.search_results)
        return page

    def build_vehicle_page(self):
        page = QWidget(); lay = QVBoxLayout(page); lay.setContentsMargins(0,0,0,0)
        lay.addWidget(self.section_header("Vehicule VAG", "Catalog pe marcă, model, generație și interval de ani"))
        filter_row = QHBoxLayout()
        self.brand_filter = QComboBox(); self.brand_filter.addItem("Toate mărcile")
        self.brand_filter.addItems([r[0] for r in self.con.execute("SELECT DISTINCT brand FROM vehicles ORDER BY brand")])
        self.brand_filter.currentTextChanged.connect(self.load_vehicles)
        filter_row.addWidget(QLabel("Marcă:")); filter_row.addWidget(self.brand_filter); filter_row.addStretch()
        lay.addLayout(filter_row)
        self.vehicle_table = self.new_table(["Marcă", "Model", "Generație", "De la", "Până la"])
        lay.addWidget(self.vehicle_table)
        return page

    def build_dtc_page(self):
        page = QWidget(); lay = QVBoxLayout(page); lay.setContentsMargins(0,0,0,0)
        lay.addWidget(self.section_header("Coduri de eroare", "DTC, simptome, cauze și direcții de diagnostic"))
        self.dtc_table = self.new_table(["Cod", "Titlu", "Severitate", "Verificat"])
        self.dtc_table.doubleClicked.connect(self.open_dtc_detail)
        lay.addWidget(self.dtc_table)
        hint = QLabel("Dublu-click pe un DTC pentru fișa completă.")
        hint.setObjectName("hint")
        lay.addWidget(hint)
        return page

    def build_module_page(self):
        page = QWidget(); lay = QVBoxLayout(page); lay.setContentsMargins(0,0,0,0)
        lay.addWidget(self.section_header("Module VCDS", "Adrese de diagnostic și protocoale uzuale"))
        self.module_table = self.new_table(["Adresă", "Modul", "Protocol"])
        lay.addWidget(self.module_table)
        return page

    def build_coding_page(self):
        page = QWidget(); lay = QVBoxLayout(page); lay.setContentsMargins(0,0,0,0)
        lay.addWidget(self.section_header("Coding & Adaptation", "Funcții documentate, aplicabilitate și stare de verificare"))
        self.coding_table = self.new_table(["Funcție", "Modul", "Efect", "Aplicabilitate", "Verificat"])
        lay.addWidget(self.coding_table)
        return page

    def build_procedure_page(self):
        page = QWidget(); lay = QVBoxLayout(page); lay.setContentsMargins(0,0,0,0)
        lay.addWidget(self.section_header("Proceduri", "Pași de diagnostic, coding și lucru sigur"))
        self.procedure_table = self.new_table(["Titlu", "Categorie", "Verificat"])
        self.procedure_table.doubleClicked.connect(self.open_procedure_detail)
        lay.addWidget(self.procedure_table)
        hint = QLabel("Dublu-click pentru pașii compleți și avertizări.")
        hint.setObjectName("hint")
        lay.addWidget(hint)
        return page

    def build_tools_page(self):
        page = QWidget(); lay = QVBoxLayout(page); lay.setContentsMargins(0,0,0,0)
        lay.addWidget(self.section_header("Instrumente", "Backup, export și întreținerea bazei locale"))
        grid = QGridLayout()
        actions = [
            ("Backup bază de date", "Creează o copie .db a bazei locale", self.backup_database),
            ("Export JSON", "Exportă tabelele principale într-un fișier JSON", self.export_json),
            ("Reîncarcă datele", "Reîncarcă tabelele din SQLite", self.refresh_all),
            ("Despre aplicație", "Informații despre versiune și scop", self.about_app),
        ]
        for i, (title, desc, handler) in enumerate(actions):
            card = QFrame(); card.setObjectName("toolCard")
            cl = QVBoxLayout(card)
            tl = QLabel(title); tl.setObjectName("toolTitle")
            dl = QLabel(desc); dl.setObjectName("toolDesc"); dl.setWordWrap(True)
            btn = QPushButton("Deschide")
            btn.setObjectName("actionButton")
            btn.clicked.connect(handler)
            cl.addWidget(tl); cl.addWidget(dl); cl.addStretch(); cl.addWidget(btn)
            grid.addWidget(card, i // 2, i % 2)
        lay.addLayout(grid)
        lay.addStretch()
        return page

    def open_page(self, index):
        titles = ["Dashboard", "Căutare", "Vehicule", "DTC", "Module", "Coding", "Proceduri", "Instrumente"]
        self.stack.setCurrentIndex(index)
        self.page_title.setText(titles[index])
        for i, b in enumerate(self.nav_buttons):
            b.setChecked(i == index)

    def fill_table(self, table, rows):
        table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, value in enumerate(row):
                item = QTableWidgetItem("" if value is None else str(value))
                table.setItem(i, j, item)

    def refresh_all(self):
        self.load_vehicles()
        self.fill_table(self.dtc_table, self.con.execute("SELECT code,title,severity,CASE verified WHEN 1 THEN 'DA' ELSE 'NU' END FROM dtc ORDER BY code").fetchall())
        self.fill_table(self.module_table, self.con.execute("SELECT address,name,protocol FROM modules ORDER BY address").fetchall())
        self.fill_table(self.coding_table, self.con.execute("SELECT title,module,effect,applicability,CASE verified WHEN 1 THEN 'DA' ELSE 'NU' END FROM coding ORDER BY title").fetchall())
        self.fill_table(self.procedure_table, self.con.execute("SELECT title,category,CASE verified WHEN 1 THEN 'DA' ELSE 'NU' END FROM procedures ORDER BY category,title").fetchall())
        counts = {
            "Vehicule": self.con.execute("SELECT COUNT(*) FROM vehicles").fetchone()[0],
            "DTC": self.con.execute("SELECT COUNT(*) FROM dtc").fetchone()[0],
            "Module": self.con.execute("SELECT COUNT(*) FROM modules").fetchone()[0],
            "Coding": self.con.execute("SELECT COUNT(*) FROM coding").fetchone()[0],
        }
        for key, card in self.card_widgets.items():
            card.findChild(QLabel, "cardValue").setText(str(counts[key]))
        self.statusBar().showMessage("Date reîncărcate cu succes", 3000)

    def load_vehicles(self):
        if not hasattr(self, "vehicle_table"):
            return
        brand = self.brand_filter.currentText() if hasattr(self, "brand_filter") else "Toate mărcile"
        if brand == "Toate mărcile":
            rows = self.con.execute("SELECT brand,model,generation,year_from,year_to FROM vehicles ORDER BY brand,model,year_from").fetchall()
        else:
            rows = self.con.execute("SELECT brand,model,generation,year_from,year_to FROM vehicles WHERE brand=? ORDER BY model,year_from", (brand,)).fetchall()
        self.fill_table(self.vehicle_table, rows)

    def run_global_search(self):
        term = self.global_search.text().strip()
        if not term:
            QMessageBox.information(self, "Căutare", "Scrie un cod DTC, model, modul sau funcție.")
            return
        q = f"%{term}%"
        rows = []
        rows += [("DTC", r[0], r[1], r[2]) for r in self.con.execute("SELECT code,title,description FROM dtc WHERE code LIKE ? OR title LIKE ? OR description LIKE ?", (q,q,q))]
        rows += [("VEHICUL", f"{r[0]} {r[1]}", r[2], f"{r[3]}–{r[4]}") for r in self.con.execute("SELECT brand,model,generation,year_from,year_to FROM vehicles WHERE brand LIKE ? OR model LIKE ? OR generation LIKE ?", (q,q,q))]
        rows += [("MODUL", r[0], r[1], r[2]) for r in self.con.execute("SELECT address,name,protocol FROM modules WHERE address LIKE ? OR name LIKE ?", (q,q))]
        rows += [("CODING", str(r[0]), r[1], r[2]) for r in self.con.execute("SELECT id,title,effect FROM coding WHERE title LIKE ? OR module LIKE ? OR effect LIKE ?", (q,q,q))]
        rows += [("PROCEDURĂ", str(r[0]), r[1], r[2]) for r in self.con.execute("SELECT id,title,category FROM procedures WHERE title LIKE ? OR category LIKE ? OR steps LIKE ?", (q,q,q))]
        self.fill_table(self.search_results, rows)
        self.open_page(1)
        self.statusBar().showMessage(f"{len(rows)} rezultate pentru «{term}»", 4000)

    def open_search_result(self, index):
        row = index.row()
        typ = self.search_results.item(row, 0).text()
        key = self.search_results.item(row, 1).text()
        if typ == "DTC":
            r = self.con.execute("SELECT code,title,description,severity,symptoms,causes,repair,verified FROM dtc WHERE code=?", (key,)).fetchone()
            if r: self.show_dtc(r)
        else:
            title = self.search_results.item(row, 2).text()
            details = self.search_results.item(row, 3).text()
            DetailDialog(f"{typ}: {title}", details, self).exec()

    def open_dtc_detail(self, index):
        code = self.dtc_table.item(index.row(), 0).text()
        r = self.con.execute("SELECT code,title,description,severity,symptoms,causes,repair,verified FROM dtc WHERE code=?", (code,)).fetchone()
        if r: self.show_dtc(r)

    def show_dtc(self, r):
        body = (
            f"Cod: {r['code']}\nTitlu: {r['title']}\nSeveritate: {r['severity']}\nVerificat: {'DA' if r['verified'] else 'NU'}\n\n"
            f"DESCRIERE\n{r['description']}\n\nSIMPTOME\n{r['symptoms']}\n\nCAUZE POSIBILE\n{r['causes']}\n\nDIRECȚIE DE DIAGNOSTIC / REPARAȚIE\n{r['repair']}\n\n"
            "Notă: confirmă întotdeauna procedura pentru motorul, ECU-ul și software-ul vehiculului înainte de intervenție."
        )
        DetailDialog(f"{r['code']} — {r['title']}", body, self).exec()

    def open_procedure_detail(self, index):
        title = self.procedure_table.item(index.row(), 0).text()
        r = self.con.execute("SELECT title,category,steps,warnings,verified FROM procedures WHERE title=?", (title,)).fetchone()
        if not r: return
        body = f"Categorie: {r['category']}\nVerificat: {'DA' if r['verified'] else 'NU'}\n\nPAȘI\n{r['steps']}\n\nAVERTIZĂRI\n{r['warnings']}"
        DetailDialog(r['title'], body, self).exec()

    def backup_database(self):
        dest, _ = QFileDialog.getSaveFileName(self, "Salvează backup", f"vag_master_backup_{datetime.now():%Y%m%d_%H%M%S}.db", "SQLite (*.db)")
        if not dest: return
        self.con.commit()
        shutil.copy2(DB_PATH, dest)
        QMessageBox.information(self, "Backup", "Backup-ul bazei de date a fost creat.")

    def export_json(self):
        dest, _ = QFileDialog.getSaveFileName(self, "Export JSON", "vag_master_export.json", "JSON (*.json)")
        if not dest: return
        out = {}
        for table in ["dtc", "vehicles", "modules", "coding", "procedures"]:
            out[table] = [dict(r) for r in self.con.execute(f"SELECT * FROM {table}")]
        Path(dest).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        QMessageBox.information(self, "Export", "Exportul JSON a fost creat.")

    def about_app(self):
        QMessageBox.information(self, "Despre", "VAG MASTER Diagnostic PRO v2.0\n\nAplicație desktop Python + PySide6 + SQLite pentru structurarea unei baze VAG 1996–2024.\n\nInterfață și funcții reconstruite.")

    def apply_style(self):
        self.setStyleSheet('''
        * { font-family: "Segoe UI", "Arial"; }
        QMainWindow, #content { background: #0b1220; }
        #sidebar { background: #08101d; border-right: 1px solid #1e293b; }
        #brandName { color: #f8fafc; font-size: 20px; font-weight: 800; }
        #brandSub { color: #60a5fa; font-size: 10px; font-weight: 700; letter-spacing: 1px; }
        #sideFooter { color: #64748b; font-size: 11px; }
        QPushButton#navButton { text-align: left; color: #94a3b8; background: transparent; border: 0; border-radius: 10px; padding: 12px 14px; font-size: 14px; }
        QPushButton#navButton:hover { color: #f8fafc; background: #111c2f; }
        QPushButton#navButton:checked { color: #ffffff; background: #172554; border-left: 3px solid #60a5fa; }
        #pageTitle { color: #f8fafc; font-size: 26px; font-weight: 800; }
        #sectionTitle { color: #f8fafc; font-size: 18px; font-weight: 700; }
        #sectionSub { color: #94a3b8; font-size: 12px; }
        QLineEdit { color: #f8fafc; background: #0f172a; border: 1px solid #334155; border-radius: 10px; padding: 11px 13px; selection-background-color: #2563eb; }
        QLineEdit:focus { border: 1px solid #60a5fa; }
        QPushButton#primaryButton { color: white; background: #2563eb; border: 0; border-radius: 10px; padding: 11px 18px; font-weight: 700; }
        QPushButton#primaryButton:hover { background: #3b82f6; }
        QPushButton#actionButton { color: #e2e8f0; background: #111c2f; border: 1px solid #263449; border-radius: 10px; padding: 11px 16px; }
        QPushButton#actionButton:hover { background: #1e293b; border-color: #60a5fa; }
        QFrame#card, QFrame#toolCard { background: #0f172a; border: 1px solid #1e293b; border-radius: 14px; min-height: 120px; }
        #cardTitle { color: #94a3b8; font-size: 12px; }
        #cardValue { color: #f8fafc; font-size: 30px; font-weight: 800; }
        #cardSub { color: #64748b; font-size: 11px; }
        #toolTitle { color: #f8fafc; font-size: 16px; font-weight: 700; }
        #toolDesc { color: #94a3b8; }
        QFrame#notice { background: #111827; border: 1px solid #273449; border-radius: 12px; }
        #noticeTitle { color: #93c5fd; font-size: 14px; font-weight: 700; }
        #noticeBody { color: #cbd5e1; }
        QTableWidget { color: #e2e8f0; background: #0f172a; alternate-background-color: #111827; border: 1px solid #1e293b; border-radius: 10px; gridline-color: #1e293b; selection-background-color: #1d4ed8; selection-color: white; }
        QHeaderView::section { color: #cbd5e1; background: #111827; border: 0; border-bottom: 1px solid #334155; padding: 10px; font-weight: 700; }
        QComboBox { color: #e2e8f0; background: #0f172a; border: 1px solid #334155; border-radius: 8px; padding: 8px 12px; }
        QLabel { color: #e2e8f0; }
        QLabel#hint { color: #64748b; font-size: 11px; }
        QLabel#dialogTitle { color: #f8fafc; font-size: 20px; font-weight: 800; }
        QTextEdit { color: #e2e8f0; background: #0f172a; border: 1px solid #334155; border-radius: 10px; padding: 10px; }
        QDialog { background: #0b1220; }
        QStatusBar { color: #94a3b8; background: #08101d; }
        ''')


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("VAG MASTER Diagnostic PRO")
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
