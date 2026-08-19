from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QLineEdit, QPushButton,
    QSplitter, QFrame, QTextEdit
)


CATEGORY_ORDER = [
    "Toate", "Proceduri", "Diagnostic", "Parametri live", "Baterie", "Adaptation",
    "Calibrări", "Resetări", "Long Coding", "Coding", "Basic Settings",
    "Output Tests", "Security Access", "Service", "Frâne", "Motor", "Transmisie"
]


def apply(MainWindow):
    def build_workspace_page_expert(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(10)

        title = QLabel("Centru VCDS • funcții pe vehicul")
        title.setObjectName("sectionTitle")
        hint = QLabel(
            "Alege o categorie. Sunt afișate numai procedurile mapate pe generația selectată. "
            "Pe UDS se folosesc denumiri IDE/MAS când sunt documentate; pe CAN/KWP sunt afișate Group/Channel/Byte/Bit când sursa le confirmă."
        )
        hint.setWordWrap(True)
        hint.setObjectName("muted")
        layout.addWidget(title)
        layout.addWidget(hint)

        chips = QHBoxLayout()
        self.category_buttons = []
        for label, category in [
            ("Proceduri", "Proceduri"), ("Baterie", "Baterie"), ("Adaptări", "Adaptation"), ("Calibrări", "Calibrări"),
            ("Resetări", "Resetări"), ("Long Coding", "Long Coding"), ("Coding", "Coding"),
            ("Basic Settings", "Basic Settings"), ("Output Tests", "Output Tests"),
            ("Security Access", "Security Access"), ("Parametri live", "Parametri live")
        ]:
            b = QPushButton(label)
            b.setProperty("target_category", category)
            b.setCheckable(True)
            b.setObjectName("categoryChip")
            b.clicked.connect(lambda checked=False, n=category: self.set_workspace_category(n))
            chips.addWidget(b)
            self.category_buttons.append(b)
        chips.addStretch()
        layout.addLayout(chips)

        bar = QHBoxLayout()
        self.proc_category = QComboBox()
        self.proc_category.addItem("Toate")
        self.proc_search = QLineEdit()
        self.proc_search.setPlaceholderText("Caută: baterie, G85, suspensie, clapetă, service, DPF, Byte, Bit, IDE, MAS...")
        self.proc_category.currentTextChanged.connect(self.load_procedures)
        self.proc_search.textChanged.connect(self.load_procedures)
        bar.addWidget(QLabel("Categorie:"))
        bar.addWidget(self.proc_category)
        bar.addWidget(self.proc_search, 1)
        layout.addLayout(bar)

        split = QSplitter(Qt.Horizontal)
        self.proc_table = self.make_table(["Categorie", "Procedură", "Modul", "Cale exactă VCDS", "Aplicabilitate", "Status"])
        self.proc_table.itemSelectionChanged.connect(self.show_selected_procedure)
        self.proc_table.cellDoubleClicked.connect(lambda *_: self.show_selected_procedure())
        split.addWidget(self.proc_table)

        right = QFrame()
        right.setObjectName("detailPanel")
        rl = QVBoxLayout(right)
        self.proc_detail_title = QLabel("Selectează o procedură")
        self.proc_detail_title.setObjectName("detailTitle")
        self.proc_detail_title.setWordWrap(True)
        self.proc_detail = QTextEdit()
        self.proc_detail.setReadOnly(True)
        src_btn = QPushButton("Deschide sursa oficială")
        src_btn.clicked.connect(self.open_current_source)
        rl.addWidget(self.proc_detail_title)
        rl.addWidget(self.proc_detail, 1)
        rl.addWidget(src_btn)
        split.addWidget(right)
        split.setSizes([900, 540])
        layout.addWidget(split, 1)
        return page

    def set_workspace_category(self, name):
        idx = self.proc_category.findText(name)
        if idx >= 0:
            self.proc_category.setCurrentIndex(idx)
        else:
            aliases = {"Proceduri": "Diagnostic", "Parametri live": "Live Data", "Resetări": "Service"}
            target = aliases.get(name)
            if target:
                idx = self.proc_category.findText(target)
                if idx >= 0:
                    self.proc_category.setCurrentIndex(idx)
        for b in getattr(self, "category_buttons", []):
            b.setChecked(b.property("target_category") == name)

    def refresh_categories_expert(self):
        self.proc_category.blockSignals(True)
        self.proc_category.clear()
        self.proc_category.addItem("Toate")
        existing = [r[0] for r in self.con.execute("SELECT DISTINCT category FROM procedure_library WHERE category<>'' ORDER BY category")]
        preferred = [x for x in CATEGORY_ORDER if x != "Toate" and x in existing]
        rest = [x for x in existing if x not in preferred]
        for x in preferred + rest:
            self.proc_category.addItem(x)
        self.proc_category.blockSignals(False)

    def load_years_engines_expert(self):
        self.year_combo.clear()
        self.engine_combo.clear()
        self.engine_combo.addItem("Nespecificat", None)
        gid = self.gen_combo.currentData()
        if not gid:
            return
        h = self.con.execute("SELECT year_from,year_to FROM generations WHERE id=?", (gid,)).fetchone()
        if h:
            for y in range(h["year_from"], h["year_to"] + 1):
                self.year_combo.addItem(str(y), y)
        rows = self.con.execute("""SELECT e.* FROM engines e JOIN vehicle_engines ve ON ve.engine_id=e.id
                                  WHERE ve.generation_id=? ORDER BY COALESCE(NULLIF(e.powertrain_type,''),e.fuel), e.displacement, e.code""", (gid,)).fetchall()
        for e in rows:
            keys=set(e.keys())
            kind=(e["powertrain_type"] if "powertrain_type" in keys and e["powertrain_type"] else e["fuel"] or "Motor")
            disp=f'{e["displacement"]}L ' if e["displacement"] else ""
            power=f'{e["power_hp"]}CP' if e["power_hp"] else ""
            self.engine_combo.addItem(f'{kind} | {e["code"]} • {disp}{power}'.strip(), e["id"])

    def show_selected_dtc_expert(self):
        row = self.dtc_table.currentRow()
        rows = self.dtc_table.property("rows") or []
        if row < 0 or row >= len(rows):
            return
        r = rows[row]
        self.dtc_title.setText(f'{r["code"]} • {r["title"]}')
        keys = set(r.keys())
        def value(key, fallback=""):
            return r[key] if key in keys and r[key] else fallback
        component = value("component", "Depinde de codul motor / echipare")
        location = value("component_location", "Poziția exactă trebuie confirmată după cod motor / platformă")
        test_path = value("test_path", "Vezi procedura specifică din Workspace VCDS")
        params = value("vcds_parameters", "Parametrii exacți diferă după ECU; caută denumirile relevante în Advanced Measuring Values.")
        expected = value("expected_values", "Compară specified/actual și limitele controllerului; nu există o valoare universală pentru toate motoarele.")
        replacement = value("replacement_steps", "Confirmă piesa defectă înainte de demontare și urmează manualul de reparație pentru codul motor/chassis.")
        text = (
            f'DESCRIERE\n{r["description"]}\n\nSIMPTOME\n{r["symptoms"]}\n\nCAUZE POSIBILE\n{r["causes"]}\n\n'
            f'PIESA / SISTEM SUSPECT\n{component}\n\nUNDE ESTE\n{location}\n\nPARAMETRI DE URMĂRIT ÎN VCDS\n{params}\n\n'
            f'CE TREBUIE SĂ VEZI / VALORI\n{expected}\n\nCALE TEST VCDS\n{test_path}\n\nDIAGNOSTIC PAS CU PAS\n{r["diagnosis"]}\n\n'
            f'CUM O REPARI\n{r["repair"]}\n\nCUM SCHIMBI PIESA / CE FACI DUPĂ\n{replacement}\n\nSEVERITATE\n{r["severity"]}\n\n'
            f'STATUS\n{"VERIFICAT" if r["verified"] else "DE VERIFICAT / starter"}'
        )
        self.dtc_text.setPlainText(text)

    old_style = MainWindow.apply_style
    def apply_style_expert(self):
        old_style(self)
        self.setStyleSheet(self.styleSheet() + '''
        QPushButton#categoryChip{background:#0f1a2d;border:1px solid #253650;border-radius:14px;padding:7px 12px;color:#a9b8cd;font-weight:700}
        QPushButton#categoryChip:hover{border-color:#3b82f6;color:white}
        QPushButton#categoryChip:checked{background:#1d4ed8;border-color:#3b82f6;color:white}
        ''')

    MainWindow.build_workspace_page = build_workspace_page_expert
    MainWindow.set_workspace_category = set_workspace_category
    MainWindow.refresh_categories = refresh_categories_expert
    MainWindow.load_years_engines = load_years_engines_expert
    MainWindow.show_selected_dtc = show_selected_dtc_expert
    MainWindow.apply_style = apply_style_expert
