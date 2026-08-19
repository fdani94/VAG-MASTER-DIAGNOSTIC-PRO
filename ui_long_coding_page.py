from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,QVBoxLayout,QHBoxLayout,QLabel,QLineEdit,QPushButton,QSplitter,QFrame,
    QTextEdit,QTableWidgetItem,QHeaderView,QListWidget,QListWidgetItem
)

SUBCATEGORIES = [
    ("Toate funcțiile", "all"),
    ("Lumini / DRL / Coming Home", "lights"),
    ("Confort / Geamuri / Oglinzi", "comfort"),
    ("Instrumente / Needle Sweep", "cluster"),
    ("ABS / ESP / XDS / TPMS", "abs"),
    ("Multimedia / MMI / PDC", "media"),
    ("Volan / Tempomat / Retrofit", "retrofit"),
    ("Motor / Start-Stop", "engine"),
    ("Community / Piață", "community"),
]


def _bucket(row):
    text=' '.join([row['title'] or '',row['module_address'] or '',row['vcds_path'] or '',row['purpose'] or '']).lower()
    if not row['verified']: return 'community'
    if any(x in text for x in ['drl','cornering','coming home','leaving home','light','lumini','xenon','fog']): return 'lights'
    if any(x in text for x in ['geam','window','mirror','oglind','lock','unlock','rain closing','comfort']): return 'comfort'
    if any(x in text for x in ['needle','staging','lap timer','instrument','cluster','oil temp','temperatură ulei']): return 'cluster'
    if any(x in text for x in ['abs','esp','xds','tsc','tpms']): return 'abs'
    if any(x in text for x in ['mmi','5f','pdc','camera','display','hidden menu','multimedia']): return 'media'
    if any(x in text for x in ['volan','steering wheel','tempomat','cruise','retrofit']): return 'retrofit'
    if any(x in text for x in ['start/stop','engine','motor']): return 'engine'
    return 'comfort'


def apply(MainWindow):
    old_build_ui=MainWindow.build_ui
    old_open_page=MainWindow.open_page
    old_select_vehicle=MainWindow.select_vehicle

    def build_long_page(self):
        page=QWidget(); root=QVBoxLayout(page); root.setContentsMargins(0,8,0,0); root.setSpacing(12)
        top=QHBoxLayout(); titlebox=QVBoxLayout()
        h=QLabel('Long Coding pe mașina selectată'); h.setObjectName('sectionTitle')
        sub=QLabel('Alege vehiculul din bara de sus. În stânga alegi sistemul, în centru funcția, iar în dreapta ai pașii VCDS.')
        sub.setWordWrap(True); sub.setObjectName('muted'); titlebox.addWidget(h); titlebox.addWidget(sub)
        self.lc_search=QLineEdit(); self.lc_search.setPlaceholderText('Caută funcție: needle sweep, cornering, mirror dip, DRL, XDS...'); self.lc_search.setMinimumWidth(360)
        self.lc_search.textChanged.connect(self.load_long_coding)
        top.addLayout(titlebox,1); top.addWidget(self.lc_search); root.addLayout(top)

        split=QSplitter(Qt.Horizontal)
        left=QFrame(); left.setObjectName('detailPanel'); left.setMinimumWidth(210); left.setMaximumWidth(260)
        ll=QVBoxLayout(left); ll.setContentsMargins(10,12,10,12)
        lab=QLabel('CATEGORII'); lab.setObjectName('fieldLabel'); ll.addWidget(lab)
        self.lc_categories=QListWidget(); self.lc_categories.setObjectName('categoryList')
        for label,key in SUBCATEGORIES:
            item=QListWidgetItem(label); item.setData(Qt.UserRole,key); self.lc_categories.addItem(item)
        self.lc_categories.setCurrentRow(0); self.lc_categories.currentItemChanged.connect(lambda *_: self.load_long_coding())
        ll.addWidget(self.lc_categories,1); split.addWidget(left)

        center=QFrame(); center.setObjectName('detailPanel'); cl=QVBoxLayout(center); cl.setContentsMargins(10,12,10,12)
        self.lc_count=QLabel('0 funcții'); self.lc_count.setObjectName('muted'); cl.addWidget(self.lc_count)
        self.lc_table=self.make_table(['Funcție','Modul','Nivel'])
        self.lc_table.itemSelectionChanged.connect(self.show_long_coding); self.lc_table.cellDoubleClicked.connect(lambda *_: self.show_long_coding())
        cl.addWidget(self.lc_table,1); split.addWidget(center)

        right=QFrame(); right.setObjectName('detailPanel'); rl=QVBoxLayout(right); rl.setContentsMargins(18,16,18,16)
        self.lc_title=QLabel('Selectează o funcție'); self.lc_title.setObjectName('detailTitle'); self.lc_title.setWordWrap(True)
        self.lc_text=QTextEdit(); self.lc_text.setReadOnly(True); self.lc_text.setObjectName('instructionText')
        b=QPushButton('Deschide sursa'); b.clicked.connect(self.open_current_source)
        rl.addWidget(self.lc_title); rl.addWidget(self.lc_text,1); rl.addWidget(b,0,Qt.AlignRight)
        split.addWidget(right); split.setSizes([230,520,760]); root.addWidget(split,1)
        return page

    def build_ui(self):
        old_build_ui(self)
        idx=self.stack.addWidget(build_long_page(self)); self.long_coding_page_index=idx
        if len(self.PAGE_NAMES)<=idx:
            self.PAGE_NAMES=list(self.PAGE_NAMES)+['Long Coding']
        sidebar=self.findChild(QFrame,'sidebar')
        if sidebar:
            btn=QPushButton('Long Coding'); btn.setObjectName('nav'); btn.setCheckable(True); btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _=False,x=idx:self.open_page(x)); self.nav_buttons.append(btn)
            layout=sidebar.layout(); pos=max(0,layout.count()-2); layout.insertWidget(pos,btn)

    def load_long_coding(self):
        if not hasattr(self,'lc_table'): return
        self.lc_table.setRowCount(0)
        if not self.selected_generation_id:
            self.lc_count.setText('Selectează mai întâi o mașină'); return
        sql='''SELECT p.*,vp.applicability,vp.notes,s.title source_title,s.url source_url
               FROM vehicle_procedures vp JOIN procedure_library p ON p.id=vp.procedure_id
               LEFT JOIN sources s ON s.id=p.source_id
               WHERE vp.generation_id=? AND p.category IN ('Long Coding','Long Coding / Activări','Coding')
               ORDER BY p.verified DESC,p.title'''
        rows=list(self.con.execute(sql,(self.selected_generation_id,)).fetchall())
        current=self.lc_categories.currentItem() if hasattr(self,'lc_categories') else None
        bucket=current.data(Qt.UserRole) if current else 'all'
        if bucket!='all': rows=[r for r in rows if _bucket(r)==bucket]
        q=self.lc_search.text().strip().lower() if hasattr(self,'lc_search') else ''
        if q: rows=[r for r in rows if q in (' '.join([r['title'] or '',r['module_address'] or '',r['vcds_path'] or '',r['purpose'] or ''])).lower()]
        self.lc_count.setText(f'{len(rows)} funcții pentru vehiculul selectat')
        self.lc_table.setProperty('rows',rows); self.lc_table.setRowCount(len(rows))
        for i,r in enumerate(rows):
            level='VERIFICAT' if r['verified'] else 'COMUNITATE'
            for j,v in enumerate([r['title'],r['module_address'] or '—',level]): self.lc_table.setItem(i,j,QTableWidgetItem(str(v)))
        self.lc_table.horizontalHeader().setSectionResizeMode(0,QHeaderView.Stretch); self.lc_table.resizeColumnToContents(1); self.lc_table.resizeColumnToContents(2)

    def show_long_coding(self):
        row=self.lc_table.currentRow(); rows=self.lc_table.property('rows') or []
        if row<0 or row>=len(rows): return
        r=rows[row]; self.current_source_url=r['source_url'] or ''; self.lc_title.setText(r['title'])
        level='VERIFICAT' if r['verified'] else 'COMUNITATE / PIAȚĂ – confirmă pe controller'
        self.lc_text.setPlainText(
            f"MODUL\n{r['module_address'] or '—'}\n\nCALE ÎN VCDS\n{r['vcds_path']}\n\nCE FACE\n{r['purpose']}\n\n"
            f"ÎNAINTE SĂ ÎNCEPI\n{r['prerequisites']}\n\nPAȘI\n{r['steps']}\n\nCUM VERIFICI\n{r['success_criteria']}\n\n"
            f"ATENȚIE\n{r['warnings']}\n\nAPLICABILITATE\n{r['applicability']}\n\nNIVEL\n{level}\n\nSURSĂ\n{r['source_title'] or '—'}"
        )

    def open_page(self,index):
        old_open_page(self,index)
        if hasattr(self,'long_coding_page_index') and index==self.long_coding_page_index:
            self.page_title.setText('Long Coding'); self.load_long_coding()

    def select_vehicle(self):
        old_select_vehicle(self)
        if hasattr(self,'lc_table'): self.load_long_coding()

    MainWindow.build_ui=build_ui
    MainWindow.load_long_coding=load_long_coding
    MainWindow.show_long_coding=show_long_coding
    MainWindow.open_page=open_page
    MainWindow.select_vehicle=select_vehicle
