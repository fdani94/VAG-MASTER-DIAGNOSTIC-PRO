from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QPushButton,QSplitter,QFrame,QTextEdit,
    QListWidget,QListWidgetItem
)

CATEGORY_ORDER=[
    'Toate','Proceduri','Diagnostic','Parametri live','Baterie','Adaptation','Calibrări','Resetări',
    'Long Coding','Coding','Basic Settings','Output Tests','Security Access','Service','Frâne','Motor','Transmisie'
]

DISPLAY_NAMES={
    'Toate':'Toate funcțiile','Proceduri':'Proceduri','Diagnostic':'Diagnostic general','Parametri live':'Parametri live',
    'Baterie':'Baterie','Adaptation':'Adaptări','Calibrări':'Calibrări','Resetări':'Resetări','Long Coding':'Long Coding',
    'Coding':'Coding','Basic Settings':'Basic Settings','Output Tests':'Output Tests','Security Access':'Security Access',
    'Service':'Service','Frâne':'Frâne / ABS / ESP','Motor':'Motor','Transmisie':'Transmisie / DSG'
}


def apply(MainWindow):
    def build_workspace_page_expert(self):
        page=QWidget(); root=QVBoxLayout(page); root.setContentsMargins(0,8,0,0); root.setSpacing(12)
        top=QHBoxLayout()
        titlebox=QVBoxLayout()
        title=QLabel('Centru VCDS pe vehicul'); title.setObjectName('sectionTitle')
        hint=QLabel('Selectează mașina sus. Apoi alegi categoria din stânga și procedura din centru.')
        hint.setObjectName('muted'); hint.setWordWrap(True)
        titlebox.addWidget(title); titlebox.addWidget(hint)
        self.proc_search=QLineEdit(); self.proc_search.setMinimumWidth(380)
        self.proc_search.setPlaceholderText('Caută: baterie, G85, DPF, suspensie, service, clapetă...')
        self.proc_search.textChanged.connect(self.load_procedures)
        top.addLayout(titlebox,1); top.addWidget(self.proc_search)
        root.addLayout(top)

        split=QSplitter(Qt.Horizontal)
        left=QFrame(); left.setObjectName('detailPanel'); left.setMinimumWidth(205); left.setMaximumWidth(245)
        ll=QVBoxLayout(left); ll.setContentsMargins(10,12,10,12)
        label=QLabel('CATEGORII'); label.setObjectName('fieldLabel'); ll.addWidget(label)
        self.proc_category_list=QListWidget(); self.proc_category_list.setObjectName('categoryList')
        self.proc_category_list.currentItemChanged.connect(lambda *_: self.load_procedures())
        ll.addWidget(self.proc_category_list,1); split.addWidget(left)

        center=QFrame(); center.setObjectName('detailPanel'); cl=QVBoxLayout(center); cl.setContentsMargins(10,12,10,12)
        self.proc_count=QLabel('0 proceduri'); self.proc_count.setObjectName('muted'); cl.addWidget(self.proc_count)
        self.proc_table=self.make_table(['Procedură','Modul','Status'])
        self.proc_table.itemSelectionChanged.connect(self.show_selected_procedure)
        self.proc_table.cellDoubleClicked.connect(lambda *_: self.show_selected_procedure())
        cl.addWidget(self.proc_table,1); split.addWidget(center)

        right=QFrame(); right.setObjectName('detailPanel'); rl=QVBoxLayout(right); rl.setContentsMargins(18,16,18,16)
        self.proc_detail_title=QLabel('Selectează o procedură'); self.proc_detail_title.setObjectName('detailTitle'); self.proc_detail_title.setWordWrap(True)
        self.proc_detail=QTextEdit(); self.proc_detail.setReadOnly(True); self.proc_detail.setObjectName('instructionText')
        src_btn=QPushButton('Deschide sursa'); src_btn.clicked.connect(self.open_current_source)
        rl.addWidget(self.proc_detail_title); rl.addWidget(self.proc_detail,1); rl.addWidget(src_btn,0,Qt.AlignRight)
        split.addWidget(right); split.setSizes([220,520,760]); root.addWidget(split,1)
        return page

    def current_proc_category(self):
        item=self.proc_category_list.currentItem() if hasattr(self,'proc_category_list') else None
        return item.data(Qt.UserRole) if item else 'Toate'

    def set_workspace_category(self,name):
        if not hasattr(self,'proc_category_list'): return
        for i in range(self.proc_category_list.count()):
            item=self.proc_category_list.item(i)
            if item.data(Qt.UserRole)==name:
                self.proc_category_list.setCurrentRow(i); return

    def refresh_categories_expert(self):
        if not hasattr(self,'proc_category_list'): return
        current=self.current_proc_category()
        existing=[r[0] for r in self.con.execute("SELECT DISTINCT category FROM procedure_library WHERE category<>'' ORDER BY category")]
        ordered=['Toate']+[x for x in CATEGORY_ORDER if x!='Toate' and x in existing]+[x for x in existing if x not in CATEGORY_ORDER]
        self.proc_category_list.blockSignals(True); self.proc_category_list.clear()
        selected=0
        for idx,cat in enumerate(ordered):
            item=QListWidgetItem(DISPLAY_NAMES.get(cat,cat)); item.setData(Qt.UserRole,cat); self.proc_category_list.addItem(item)
            if cat==current:selected=idx
        self.proc_category_list.setCurrentRow(selected); self.proc_category_list.blockSignals(False)

    def load_procedures_expert(self):
        if not hasattr(self,'proc_table'): return
        self.proc_table.setRowCount(0)
        if not self.selected_generation_id:
            self.proc_count.setText('Selectează mai întâi o mașină'); return
        category=self.current_proc_category()
        rows=self.con.execute('''SELECT p.*,vp.applicability,vp.notes,s.title source_title,s.url source_url
            FROM vehicle_procedures vp JOIN procedure_library p ON p.id=vp.procedure_id
            LEFT JOIN sources s ON s.id=p.source_id WHERE vp.generation_id=?
            ORDER BY p.verified DESC,p.category,p.title''',(self.selected_generation_id,)).fetchall()
        rows=list(rows)
        if category!='Toate': rows=[r for r in rows if r['category']==category]
        q=self.proc_search.text().strip().lower() if hasattr(self,'proc_search') else ''
        if q: rows=[r for r in rows if q in (' '.join([r['title'] or '',r['category'] or '',r['vcds_path'] or '',r['purpose'] or ''])).lower()]
        self.proc_count.setText(f'{len(rows)} proceduri pentru vehiculul selectat')
        self.proc_table.setProperty('rows',rows); self.proc_table.setRowCount(len(rows))
        for i,r in enumerate(rows):
            for j,v in enumerate([r['title'],r['module_address'] or '—','VERIFICAT' if r['verified'] else 'COMUNITATE']):
                from PySide6.QtWidgets import QTableWidgetItem
                self.proc_table.setItem(i,j,QTableWidgetItem(str(v)))
        from PySide6.QtWidgets import QHeaderView
        self.proc_table.horizontalHeader().setSectionResizeMode(0,QHeaderView.Stretch)
        self.proc_table.resizeColumnToContents(1); self.proc_table.resizeColumnToContents(2)

    def show_selected_procedure_expert(self):
        row=self.proc_table.currentRow(); rows=self.proc_table.property('rows') or []
        if row<0 or row>=len(rows): return
        r=rows[row]; self.current_source_url=r['source_url'] or ''; self.proc_detail_title.setText(r['title'])
        text=(
            f"CATEGORIE\n{DISPLAY_NAMES.get(r['category'],r['category'])}\n\n"
            f"MODUL\n{r['module_address'] or '—'}\n\n"
            f"CALE ÎN VCDS\n{r['vcds_path']}\n\n"
            f"SCOP\n{r['purpose']}\n\n"
            f"ÎNAINTE SĂ ÎNCEPI\n{r['prerequisites']}\n\n"
            f"PAȘI\n{r['steps']}\n\n"
            f"REZULTAT CORECT\n{r['success_criteria']}\n\n"
            f"ATENȚIE\n{r['warnings']}\n\n"
            f"APLICABILITATE\n{r['applicability']}\n\n"
            f"SURSĂ\n{r['source_title'] or '—'}"
        )
        self.proc_detail.setPlainText(text)

    def load_years_engines_expert(self):
        self.year_combo.clear(); self.engine_combo.clear(); self.engine_combo.addItem('Nespecificat',None)
        gid=self.gen_combo.currentData()
        if not gid:return
        h=self.con.execute('SELECT year_from,year_to FROM generations WHERE id=?',(gid,)).fetchone()
        if h:
            for y in range(h['year_from'],h['year_to']+1): self.year_combo.addItem(str(y),y)
        rows=self.con.execute('''SELECT e.* FROM engines e JOIN vehicle_engines ve ON ve.engine_id=e.id
                                 WHERE ve.generation_id=? ORDER BY COALESCE(NULLIF(e.powertrain_type,''),e.fuel),e.displacement,e.code''',(gid,)).fetchall()
        for e in rows:
            keys=set(e.keys()); kind=(e['powertrain_type'] if 'powertrain_type' in keys and e['powertrain_type'] else e['fuel'] or 'Motor')
            disp=f"{e['displacement']}L " if e['displacement'] else ''; power=f"{e['power_hp']}CP" if e['power_hp'] else ''
            self.engine_combo.addItem(f"{kind} | {e['code']} • {disp}{power}".strip(),e['id'])

    def show_selected_dtc_expert(self):
        row=self.dtc_table.currentRow(); rows=self.dtc_table.property('rows') or []
        if row<0 or row>=len(rows):return
        r=rows[row]; self.dtc_title.setText(f"{r['code']} • {r['title']}")
        keys=set(r.keys())
        def value(k,f=''): return r[k] if k in keys and r[k] else f
        text=(f"DESCRIERE\n{r['description']}\n\nSIMPTOME\n{r['symptoms']}\n\nCAUZE POSIBILE\n{r['causes']}\n\n"
              f"PIESA / SISTEM\n{value('component','Depinde de motorizare')}\n\nUNDE ESTE\n{value('component_location','Confirmă după cod motor')}\n\n"
              f"PARAMETRI VCDS\n{value('vcds_parameters','Vezi Advanced Measuring Values')}\n\nVALORI / COMPORTAMENT\n{value('expected_values','Compară specified/actual')}\n\n"
              f"CALE TEST VCDS\n{value('test_path','Vezi Workspace VCDS')}\n\nDIAGNOSTIC PAS CU PAS\n{r['diagnosis']}\n\nCUM O REPARI\n{r['repair']}\n\n"
              f"ÎNLOCUIRE / DUPĂ REPARAȚIE\n{value('replacement_steps','Urmează procedura specifică piesei')}\n\nSEVERITATE\n{r['severity']}")
        self.dtc_text.setPlainText(text)

    MainWindow.build_workspace_page=build_workspace_page_expert
    MainWindow.current_proc_category=current_proc_category
    MainWindow.set_workspace_category=set_workspace_category
    MainWindow.refresh_categories=refresh_categories_expert
    MainWindow.load_procedures=load_procedures_expert
    MainWindow.show_selected_procedure=show_selected_procedure_expert
    MainWindow.load_years_engines=load_years_engines_expert
    MainWindow.show_selected_dtc=show_selected_dtc_expert
