from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QComboBox,QPushButton,QSplitter,QFrame,QTextEdit,QTableWidgetItem,QHeaderView


def apply(MainWindow):
    old_build_ui=MainWindow.build_ui
    old_open_page=MainWindow.open_page
    old_select_vehicle=MainWindow.select_vehicle

    def build_long_page(self):
        page=QWidget(); lay=QVBoxLayout(page); lay.setContentsMargins(0,8,0,0); lay.setSpacing(10)
        h=QLabel('Long Coding • Activări VAG'); h.setObjectName('sectionTitle')
        sub=QLabel('Alegi mașina sus, apoi vezi numai funcțiile mapate pe generația selectată. VERIFICAT = sursă tehnică; COMUNITATE/PIAȚĂ = funcție cerută frecvent, dar Byte/Bit trebuie confirmat pe controllerul real.')
        sub.setWordWrap(True); sub.setObjectName('muted')
        lay.addWidget(h); lay.addWidget(sub)
        bar=QHBoxLayout()
        self.lc_filter=QComboBox(); self.lc_filter.addItems(['Toate','VERIFICAT','COMUNITATE/PIAȚĂ'])
        self.lc_search=QLineEdit(); self.lc_search.setPlaceholderText('Caută: needle sweep, cornering, US style, mirror dip, DRL, XDS, ADS, geamuri, TPMS...')
        self.lc_filter.currentTextChanged.connect(self.load_long_coding)
        self.lc_search.textChanged.connect(self.load_long_coding)
        bar.addWidget(QLabel('Nivel:')); bar.addWidget(self.lc_filter); bar.addWidget(self.lc_search,1); lay.addLayout(bar)
        split=QSplitter(Qt.Horizontal)
        self.lc_table=self.make_table(['Funcție','Modul','Cale VCDS / Byte-Bit-Canal','Aplicabilitate','Nivel'])
        self.lc_table.itemSelectionChanged.connect(self.show_long_coding)
        self.lc_table.cellDoubleClicked.connect(lambda *_: self.show_long_coding())
        split.addWidget(self.lc_table)
        right=QFrame(); right.setObjectName('detailPanel'); rl=QVBoxLayout(right)
        self.lc_title=QLabel('Selectează o funcție'); self.lc_title.setObjectName('detailTitle'); self.lc_title.setWordWrap(True)
        self.lc_text=QTextEdit(); self.lc_text.setReadOnly(True)
        b=QPushButton('Deschide sursa'); b.clicked.connect(self.open_current_source)
        rl.addWidget(self.lc_title); rl.addWidget(self.lc_text,1); rl.addWidget(b)
        split.addWidget(right); split.setSizes([850,600]); lay.addWidget(split,1)
        return page

    def build_ui(self):
        old_build_ui(self)
        idx=self.stack.addWidget(build_long_page(self))
        self.long_coding_page_index=idx
        if 'Long Coding' not in self.PAGE_NAMES:
            self.PAGE_NAMES=list(self.PAGE_NAMES)+['Long Coding']
        sidebar=self.findChild(QFrame,'sidebar')
        if sidebar:
            btn=QPushButton('Long Coding'); btn.setObjectName('nav'); btn.setCheckable(True); btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _=False,x=idx:self.open_page(x))
            self.nav_buttons.append(btn)
            layout=sidebar.layout()
            pos=max(0,layout.count()-2)
            layout.insertWidget(pos,btn)

    def load_long_coding(self):
        self.lc_table.setRowCount(0)
        if not self.selected_generation_id:return
        sql='''SELECT p.*,vp.applicability,vp.notes,s.title source_title,s.url source_url
               FROM vehicle_procedures vp JOIN procedure_library p ON p.id=vp.procedure_id
               LEFT JOIN sources s ON s.id=p.source_id
               WHERE vp.generation_id=? AND p.category IN ('Long Coding','Long Coding / Activări','Coding')
               ORDER BY p.verified DESC,p.title'''
        rows=list(self.con.execute(sql,(self.selected_generation_id,)).fetchall())
        q=self.lc_search.text().strip().lower() if hasattr(self,'lc_search') else ''
        filt=self.lc_filter.currentText() if hasattr(self,'lc_filter') else 'Toate'
        if q: rows=[r for r in rows if q in (' '.join([r['title'] or '',r['module_address'] or '',r['vcds_path'] or '',r['purpose'] or ''])).lower()]
        if filt=='VERIFICAT': rows=[r for r in rows if r['verified']]
        elif filt=='COMUNITATE/PIAȚĂ': rows=[r for r in rows if not r['verified']]
        self.lc_table.setProperty('rows',rows); self.lc_table.setRowCount(len(rows))
        for i,r in enumerate(rows):
            level='VERIFICAT' if r['verified'] else 'COMUNITATE/PIAȚĂ'
            for j,v in enumerate([r['title'],r['module_address'] or '—',r['vcds_path'],r['applicability'],level]):
                self.lc_table.setItem(i,j,QTableWidgetItem(str(v)))
        self.lc_table.resizeColumnsToContents(); self.lc_table.horizontalHeader().setSectionResizeMode(0,QHeaderView.Stretch); self.lc_table.horizontalHeader().setSectionResizeMode(2,QHeaderView.Stretch)

    def show_long_coding(self):
        row=self.lc_table.currentRow(); rows=self.lc_table.property('rows') or []
        if row<0 or row>=len(rows):return
        r=rows[row]; self.current_source_url=r['source_url'] or ''; self.lc_title.setText(r['title'])
        level='VERIFICAT - sursă tehnică' if r['verified'] else 'COMUNITATE/PIAȚĂ - confirmă pe controller'
        txt=(f"NIVEL: {level}\nMODUL: {r['module_address'] or '—'}\nAPLICABILITATE: {r['applicability']}\n\n"
             f"CALE VCDS / BYTE-BIT-CANAL\n{r['vcds_path']}\n\nCE FACE\n{r['purpose']}\n\n"
             f"CONDIȚII\n{r['prerequisites']}\n\nPAȘI EXACȚI / FLUX\n{r['steps']}\n\n"
             f"REZULTAT\n{r['success_criteria']}\n\nATENȚIE\n{r['warnings']}\n\n"
             f"NOTĂ VEHICUL\n{r['notes']}\n\nSURSĂ\n{r['source_title'] or '—'}\n{r['source_url'] or '—'}")
        self.lc_text.setPlainText(txt)

    def open_page(self,index):
        old_open_page(self,index)
        if hasattr(self,'long_coding_page_index') and index==self.long_coding_page_index:
            self.page_title.setText('Long Coding')
            self.load_long_coding()

    def select_vehicle(self):
        old_select_vehicle(self)
        if hasattr(self,'lc_table'): self.load_long_coding()

    MainWindow.build_ui=build_ui
    MainWindow.load_long_coding=load_long_coding
    MainWindow.show_long_coding=show_long_coding
    MainWindow.open_page=open_page
    MainWindow.select_vehicle=select_vehicle
