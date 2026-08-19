from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog,
    QMessageBox, QSplitter, QFrame, QTextEdit, QTableWidgetItem, QHeaderView
)

from autoscan_parser import parse_autoscan_file, diagnostic_plan, compare_results
from autoscan_correlation import correlate, render_correlation
from autoscan_ro import ro_status, ro_module, ro_title, ro_confidence, ro_vcds_note


def apply(MainWindow):
    old_build_ui = MainWindow.build_ui
    old_open_page = MainWindow.open_page
    old_select_vehicle = MainWindow.select_vehicle

    def build_autoscan_page(self):
        page = QWidget()
        root = QVBoxLayout(page)
        root.setContentsMargins(0, 8, 0, 0)
        root.setSpacing(12)

        title_row = QHBoxLayout()
        title_box = QVBoxLayout()
        h = QLabel("Analiză Auto-Scan VCDS")
        h.setObjectName("sectionTitle")
        sub = QLabel(
            "Încarcă raportul VCDS TXT/LOG sau PDF. KID Diagnostic extrage toate erorile, "
            "le explică în română, le corelează între module și îți arată ce trebuie verificat întâi."
        )
        sub.setWordWrap(True)
        sub.setObjectName("muted")
        title_box.addWidget(h)
        title_box.addWidget(sub)
        title_row.addLayout(title_box, 1)

        self.autoscan_load_btn = QPushButton("Încarcă Auto-Scan")
        self.autoscan_load_btn.setObjectName("primary")
        self.autoscan_load_btn.clicked.connect(self.load_autoscan_file)
        self.autoscan_plan_btn = QPushButton("Plan diagnostic automat")
        self.autoscan_plan_btn.clicked.connect(self.show_autoscan_correlation)
        self.autoscan_compare_btn = QPushButton("Compară după reparație")
        self.autoscan_compare_btn.clicked.connect(self.compare_autoscan_file)
        title_row.addWidget(self.autoscan_load_btn)
        title_row.addWidget(self.autoscan_plan_btn)
        title_row.addWidget(self.autoscan_compare_btn)
        root.addLayout(title_row)

        self.autoscan_summary = QLabel("Selectează mai întâi mașina, apoi încarcă Auto-Scan-ul.")
        self.autoscan_summary.setObjectName("vehicleBadge")
        self.autoscan_summary.setWordWrap(True)
        root.addWidget(self.autoscan_summary)

        split = QSplitter(Qt.Horizontal)

        left = QFrame()
        left.setObjectName("detailPanel")
        ll = QVBoxLayout(left)
        ll.setContentsMargins(10, 12, 10, 12)
        lh = QLabel("ERORI GĂSITE")
        lh.setObjectName("fieldLabel")
        ll.addWidget(lh)
        self.autoscan_table = self.make_table(["Modul", "Cod", "Explicație", "Stare", "Nivel informație"])
        self.autoscan_table.itemSelectionChanged.connect(self.show_autoscan_fault)
        ll.addWidget(self.autoscan_table, 1)
        split.addWidget(left)

        right = QFrame()
        right.setObjectName("detailPanel")
        rl = QVBoxLayout(right)
        rl.setContentsMargins(18, 16, 18, 16)
        self.autoscan_fault_title = QLabel("Selectează o eroare")
        self.autoscan_fault_title.setObjectName("detailTitle")
        self.autoscan_fault_title.setWordWrap(True)
        self.autoscan_detail = QTextEdit()
        self.autoscan_detail.setObjectName("instructionText")
        self.autoscan_detail.setReadOnly(True)
        rl.addWidget(self.autoscan_fault_title)
        rl.addWidget(self.autoscan_detail, 1)
        split.addWidget(right)
        split.setSizes([700, 780])
        root.addWidget(split, 1)

        self.current_autoscan = None
        self.autoscan_plans = []
        self.autoscan_correlation = None
        return page

    def build_ui(self):
        old_build_ui(self)
        idx = self.stack.addWidget(build_autoscan_page(self))
        self.autoscan_page_index = idx
        sidebar = self.findChild(QFrame, "sidebar")
        if sidebar:
            btn = QPushButton("Analiză Auto-Scan")
            btn.setObjectName("nav")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _=False, x=idx: self.open_page(x))
            self.nav_buttons.append(btn)
            layout = sidebar.layout()
            pos = max(0, layout.count() - 2)
            layout.insertWidget(pos, btn)
            self.autoscan_nav_button = btn

    def _require_vehicle(self):
        if not self.selected_generation_id:
            QMessageBox.warning(self, "Auto-Scan", "Selectează mai întâi marca, modelul, generația, anul și motorul din bara de sus.")
            return False
        return True

    def load_autoscan_file(self):
        if not self._require_vehicle():
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Încarcă Auto-Scan VCDS",
            "",
            "Auto-Scan VCDS (*.txt *.log *.pdf);;Text (*.txt *.log);;PDF (*.pdf);;Toate fișierele (*.*)",
        )
        if not path:
            return
        try:
            result = parse_autoscan_file(path)
        except Exception as exc:
            QMessageBox.critical(self, "Auto-Scan", f"Nu am putut citi raportul:\n{exc}")
            return
        self.current_autoscan = result
        self.populate_autoscan(result)

    def populate_autoscan(self, result):
        plans = []
        engine_id = self.engine_combo.currentData() if hasattr(self, "engine_combo") else None
        for fault in result.faults:
            plans.append((fault, diagnostic_plan(self.con, fault, self.selected_generation_id, engine_id)))
        self.autoscan_plans = plans
        self.autoscan_correlation = correlate(result, plans)
        self.autoscan_table.setRowCount(len(plans))
        self.autoscan_table.setProperty("rows", plans)
        for i, (fault, plan) in enumerate(plans):
            module_text = f"{fault.module_address} {ro_module(fault.module_name)}".strip()
            title_ro = ro_title(plan.get("title") or fault.title)
            vals = [
                module_text,
                fault.code or fault.vag_code,
                title_ro,
                ro_status(fault.status),
                ro_confidence(plan.get("found"), plan.get("verified")),
            ]
            for j, value in enumerate(vals):
                self.autoscan_table.setItem(i, j, QTableWidgetItem(str(value)))
        self.autoscan_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.autoscan_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.autoscan_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.autoscan_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.autoscan_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)

        indexed = sum(1 for _, p in plans if p.get("found"))
        static = sum(1 for f, _ in plans if "static" in (f.status or "").lower() or "confirmed" in (f.status or "").lower())
        intermittent = sum(1 for f, _ in plans if "intermittent" in (f.status or "").lower() or "sporadic" in (f.status or "").lower())
        secondary = len(self.autoscan_correlation.get("secondary", [])) if self.autoscan_correlation else 0
        vin = f" • VIN {result.vin}" if result.vin else ""
        self.autoscan_summary.setText(
            f"{Path(result.source_path).name}{vin} • {len(result.modules)} module detectate • {len(result.faults)} erori • "
            f"{indexed} cu fișă locală • {static} statice/confirmate • {intermittent} intermitente • {secondary} probabil secundare"
        )
        if plans:
            self.autoscan_table.selectRow(0)
        else:
            self.autoscan_fault_title.setText("Nu am găsit coduri de eroare în raport")
            self.autoscan_detail.setPlainText(
                "Raportul a fost citit, dar parserul nu a identificat coduri DTC. Dacă raportul este PDF scanat ca imagine, "
                "exportă Auto-Scan-ul direct din VCDS ca TXT."
            )

    def show_autoscan_correlation(self):
        if not self.current_autoscan or not self.autoscan_plans:
            QMessageBox.warning(self, "Plan diagnostic", "Încarcă mai întâi un Auto-Scan cu erori.")
            return
        if not self.autoscan_correlation:
            self.autoscan_correlation = correlate(self.current_autoscan, self.autoscan_plans)
        self.autoscan_fault_title.setText("Plan diagnostic automat • cauze principale și erori secundare")
        self.autoscan_detail.setPlainText(render_correlation(self.autoscan_correlation) + "\n\nNOTĂ VCDS\n" + ro_vcds_note())

    def show_autoscan_fault(self):
        row = self.autoscan_table.currentRow()
        rows = self.autoscan_table.property("rows") or []
        if row < 0 or row >= len(rows):
            return
        fault, p = rows[row]
        code = fault.code or fault.vag_code or "DTC"
        title_ro = ro_title(p.get("title") or fault.title)
        self.autoscan_fault_title.setText(f"{code} • {title_ro}")
        confidence = ro_confidence(p.get("found"), p.get("verified"))
        text = (
            f"MODUL\n{fault.module_address} {ro_module(fault.module_name)}\n\n"
            f"STARE DIN AUTO-SCAN\n{ro_status(p.get('status',''))}\n\n"
            f"NIVELUL INFORMAȚIEI\n{confidence}\n\n"
            f"CE ÎNSEAMNĂ\n{p.get('description','') or 'Explicația completă nu este încă disponibilă în baza locală.'}\n\n"
            f"SIMPTOME POSIBILE\n{p.get('symptoms','') or 'Simptomele depind de sistem și de starea exactă a erorii.'}\n\n"
            f"CAUZE POSIBILE\n{p.get('causes','') or 'Verifică mai întâi alimentarea, masa, cablajul, conectorii și DTC-urile asociate.'}\n\n"
            f"PIESA / SISTEMUL IMPLICAT\n{p.get('component','') or 'De identificat după modul, cod motor și textul complet al DTC-ului.'}\n\n"
            f"UNDE SE AFLĂ\n{p.get('location','') or 'Locația exactă diferă după model, generație și motor.'}\n\n"
            f"CE VERIFICI ÎN VCDS\n{p.get('parameters','')}\n\n"
            f"VALORI / COMPORTAMENT AȘTEPTAT\n{p.get('expected','')}\n\n"
            f"TRASEU ÎN VCDS\n{p.get('test_path','')}\n\n"
            f"DIAGNOSTIC PAS CU PAS\n{p.get('diagnosis','')}\n\n"
            f"CUM O REPARI\n{p.get('repair','')}\n\n"
            f"DACĂ TREBUIE SCHIMBATĂ PIESA / CE FACI DUPĂ MONTAJ\n{p.get('replacement','')}\n\n"
            f"FREEZE FRAME / DATE DIN RAPORT\n{p.get('freeze_frame','')}\n\n"
            f"NOTĂ DESPRE DENUMIRILE VCDS\n{ro_vcds_note()}\n\n"
            f"VERIFICARE FINALĂ\nDupă repararea cauzei: Clear DTC → ciclu de contact conform procedurii → test funcțional sau test drive dacă este necesar → Auto-Scan complet din nou."
        )
        self.autoscan_detail.setPlainText(text)

    def compare_autoscan_file(self):
        if not self.current_autoscan:
            QMessageBox.warning(self, "Comparare", "Încarcă întâi Auto-Scan-ul de dinaintea reparației.")
            return
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Încarcă Auto-Scan după reparație",
            "",
            "Auto-Scan VCDS (*.txt *.log *.pdf);;Text (*.txt *.log);;PDF (*.pdf)",
        )
        if not path:
            return
        try:
            after = parse_autoscan_file(path)
        except Exception as exc:
            QMessageBox.critical(self, "Comparare", f"Nu am putut citi al doilea raport:\n{exc}")
            return
        resolved, remaining, new = compare_results(self.current_autoscan, after)
        def lines(items):
            if not items:
                return "—"
            return "\n".join(
                f"• {x.module_address} {ro_module(x.module_name)}: {x.code or x.vag_code} — {ro_title(x.title)}"
                for x in items
            )
        msg = (
            f"REZOLVATE ({len(resolved)})\n{lines(resolved)}\n\n"
            f"RĂMASE ({len(remaining)})\n{lines(remaining)}\n\n"
            f"ERORI NOI ({len(new)})\n{lines(new)}"
        )
        self.autoscan_fault_title.setText("Comparație Auto-Scan: înainte vs după reparație")
        self.autoscan_detail.setPlainText(msg)
        self.autoscan_summary.setText(
            f"Comparație: {len(resolved)} rezolvate • {len(remaining)} rămase • {len(new)} erori noi"
        )

    def open_page(self, index):
        old_open_page(self, index)
        if hasattr(self, "autoscan_page_index") and index == self.autoscan_page_index:
            self.page_title.setText("Analiză Auto-Scan")
            for b in self.nav_buttons:
                b.setChecked(b is getattr(self, "autoscan_nav_button", None))

    def select_vehicle(self):
        old_select_vehicle(self)
        if hasattr(self, "current_autoscan") and self.current_autoscan:
            self.populate_autoscan(self.current_autoscan)

    MainWindow.build_ui = build_ui
    MainWindow.load_autoscan_file = load_autoscan_file
    MainWindow.populate_autoscan = populate_autoscan
    MainWindow.show_autoscan_correlation = show_autoscan_correlation
    MainWindow.show_autoscan_fault = show_autoscan_fault
    MainWindow.compare_autoscan_file = compare_autoscan_file
    MainWindow._require_vehicle = _require_vehicle
    MainWindow.open_page = open_page
    MainWindow.select_vehicle = select_vehicle
