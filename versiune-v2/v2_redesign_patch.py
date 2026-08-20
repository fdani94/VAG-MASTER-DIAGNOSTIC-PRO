"""Professional visual redesign for KID Diagnostic V2.

Applied after the data/runtime patches so the visual layer can evolve without
changing the diagnostic engine. The goal is a clean automotive-tool layout:
large illustrated actions, compact vehicle selection, generous spacing and
clear separate workspaces.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen, QBrush, QPixmap
from PySide6.QtWidgets import (
    QWidget, QFrame, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QGridLayout,
    QComboBox, QSizePolicy, QGraphicsDropShadowEffect
)

import appdb as db


ACCENTS = {
    "SCAN": "#1db6ff",
    "DTC": "#ffb347",
    "CODE": "#8b7dff",
    "ADAPT": "#37d7b2",
    "SERV": "#ff6b7a",
    "LIVE": "#3fc7ff",
    "MOD": "#5ba5ff",
    "PDF": "#e9c46a",
}


def _shadow(widget, blur=30, y=7, alpha=90):
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(0, y)
    effect.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(effect)


def _paint_brand(self, _event):
    p = QPainter(self)
    p.setRenderHint(QPainter.Antialiasing)
    rect = self.rect().adjusted(2, 2, -2, -2)
    logo = getattr(db, "LOGO_PATH", None)
    if logo:
        pix = QPixmap(str(logo))
        if not pix.isNull():
            pix = pix.scaled(rect.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            p.drawPixmap(rect.center().x() - pix.width() // 2, rect.center().y() - pix.height() // 2, pix)
            return
    grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
    grad.setColorAt(0, QColor("#123e6a")); grad.setColorAt(1, QColor("#071421"))
    p.setBrush(grad); p.setPen(QPen(QColor("#32bfff"), 2))
    p.drawRoundedRect(rect, 15, 15)
    p.setPen(QColor("#f4fbff")); f = QFont("Segoe UI", 14, QFont.Bold); p.setFont(f)
    p.drawText(rect, Qt.AlignCenter, "KID")


def _paint_card_art(self, _event):
    p = QPainter(self)
    p.setRenderHint(QPainter.Antialiasing)
    r = self.rect().adjusted(2, 2, -2, -2)
    code = str(getattr(self, "code", "")).upper()
    accent = QColor(ACCENTS.get(code, "#28b8ff"))

    bg = QLinearGradient(r.topLeft(), r.bottomRight())
    bg.setColorAt(0, QColor("#102a45")); bg.setColorAt(.6, QColor("#0a1d31")); bg.setColorAt(1, QColor("#07131f"))
    p.setBrush(bg); p.setPen(QPen(QColor("#183c59"), 1)); p.drawRoundedRect(r, 16, 16)

    # glow circle for a more polished, less technical-wireframe look
    glow = QColor(accent); glow.setAlpha(35)
    p.setBrush(glow); p.setPen(Qt.NoPen)
    diameter = min(r.height() - 18, 72)
    cx, cy = r.center().x(), r.center().y()
    p.drawEllipse(cx - diameter//2, cy - diameter//2, diameter, diameter)

    p.setBrush(Qt.NoBrush); p.setPen(QPen(accent, 3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    x, y, w, h = r.x(), r.y(), r.width(), r.height()

    if code == "SCAN":
        # car + scanning beam
        p.drawLine(int(x+w*.25), int(y+h*.61), int(x+w*.75), int(y+h*.61))
        p.drawLine(int(x+w*.34), int(y+h*.61), int(x+w*.41), int(y+h*.42))
        p.drawLine(int(x+w*.41), int(y+h*.42), int(x+w*.60), int(y+h*.42))
        p.drawLine(int(x+w*.60), int(y+h*.42), int(x+w*.68), int(y+h*.61))
        p.drawEllipse(int(x+w*.33), int(y+h*.56), 13, 13); p.drawEllipse(int(x+w*.62), int(y+h*.56), 13, 13)
        p.setPen(QPen(QColor("#d7f2ff"), 2))
        for f in (.28,.35,.42): p.drawLine(int(x+w*.16), int(y+h*f), int(x+w*.27), int(y+h*f))
    elif code == "DTC":
        p.drawRoundedRect(int(x+w*.33), int(y+h*.24), int(w*.34), int(h*.52), 8, 8)
        p.drawLine(int(x+w*.40), int(y+h*.36), int(x+w*.60), int(y+h*.36))
        p.drawLine(int(x+w*.40), int(y+h*.48), int(x+w*.56), int(y+h*.48))
        p.setPen(QPen(QColor("#ffe0a8"), 4, Qt.SolidLine, Qt.RoundCap)); p.drawPoint(int(x+w*.50), int(y+h*.64))
    elif code == "CODE":
        p.drawLine(int(x+w*.38), int(y+h*.33), int(x+w*.27), int(y+h*.50)); p.drawLine(int(x+w*.27), int(y+h*.50), int(x+w*.38), int(y+h*.67))
        p.drawLine(int(x+w*.62), int(y+h*.33), int(x+w*.73), int(y+h*.50)); p.drawLine(int(x+w*.73), int(y+h*.50), int(x+w*.62), int(y+h*.67))
        p.setPen(QPen(QColor("#e5e0ff"), 2)); p.drawLine(int(x+w*.54), int(y+h*.31), int(x+w*.46), int(y+h*.69))
    elif code == "ADAPT":
        for fy, fx in ((.34,.43),(.50,.61),(.66,.36)):
            yy = int(y+h*fy); p.drawLine(int(x+w*.28), yy, int(x+w*.72), yy); p.setBrush(QColor("#092334")); p.drawEllipse(int(x+w*fx)-6, yy-6, 12, 12); p.setBrush(Qt.NoBrush)
    elif code == "SERV":
        p.drawArc(int(x+w*.31), int(y+h*.25), int(w*.30), int(h*.38), 35*16, 255*16)
        p.drawLine(int(x+w*.49), int(y+h*.52), int(x+w*.67), int(y+h*.69)); p.drawEllipse(int(x+w*.63), int(y+h*.64), 11, 11)
    elif code == "LIVE":
        p.setPen(QPen(QColor("#3a627e"), 1)); p.drawLine(int(x+w*.25), int(y+h*.70), int(x+w*.75), int(y+h*.70)); p.drawLine(int(x+w*.25), int(y+h*.28), int(x+w*.25), int(y+h*.70))
        p.setPen(QPen(accent, 3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        pts=[(.28,.62),(.38,.53),(.47,.58),(.55,.38),(.65,.46),(.72,.31)]
        for a,b in zip(pts,pts[1:]): p.drawLine(int(x+w*a[0]),int(y+h*a[1]),int(x+w*b[0]),int(y+h*b[1]))
    elif code == "MOD":
        nodes=[(.34,.35),(.66,.35),(.50,.65)]
        p.setPen(QPen(QColor("#456b87"), 2))
        for a,b in ((0,1),(0,2),(1,2)): p.drawLine(int(x+w*nodes[a][0]),int(y+h*nodes[a][1]),int(x+w*nodes[b][0]),int(y+h*nodes[b][1]))
        p.setPen(QPen(accent,2)); p.setBrush(QColor("#0a2134"))
        for nx,ny in nodes: p.drawRoundedRect(int(x+w*nx)-10,int(y+h*ny)-8,20,16,4,4)
    elif code == "PDF":
        px,py,pw,ph=int(x+w*.38),int(y+h*.20),int(w*.25),int(h*.60); p.drawRoundedRect(px,py,pw,ph,6,6)
        p.setPen(QPen(QColor("#f7e6af"),2))
        for fy in (.42,.52,.62): p.drawLine(int(x+w*.42),int(y+h*fy),int(x+w*.59),int(y+h*fy))


def _feature_card_init(self, title, subtitle, code, callback):
    QFrame.__init__(self)
    self.setObjectName("featureCard")
    self.setProperty("accent", code)
    self.setMinimumHeight(190)
    self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    _shadow(self, 26, 6, 70)

    l = QVBoxLayout(self); l.setContentsMargins(18, 17, 18, 16); l.setSpacing(8)
    top = QHBoxLayout();
    icon = __import__("ui_v2").CardArt(code); icon.setFixedSize(112, 82); top.addWidget(icon)
    top.addStretch()
    badge = QLabel(code); badge.setObjectName("cardCode"); badge.setAlignment(Qt.AlignCenter); badge.setFixedHeight(26); badge.setMinimumWidth(48); top.addWidget(badge, 0, Qt.AlignTop)
    l.addLayout(top)
    a = QLabel(title); a.setObjectName("cardTitle")
    b = QLabel(subtitle); b.setObjectName("cardSubtitle"); b.setWordWrap(True); b.setMinimumHeight(36)
    l.addWidget(a); l.addWidget(b); l.addStretch()
    btn = QPushButton("DESCHIDE  →"); btn.setObjectName("cardButton"); btn.setCursor(Qt.PointingHandCursor); btn.clicked.connect(callback); btn.setMinimumHeight(38)
    l.addWidget(btn)


def _build(self):
    import ui_v2
    root = QWidget(); root.setObjectName("appRoot")
    rl = QVBoxLayout(root); rl.setContentsMargins(0,0,0,0); rl.setSpacing(0)

    top = QFrame(); top.setObjectName("topbar"); top.setFixedHeight(78)
    tl = QHBoxLayout(top); tl.setContentsMargins(28, 11, 28, 11); tl.setSpacing(13)
    mark = ui_v2.BrandMark(); mark.setFixedSize(52,52); tl.addWidget(mark)
    bb = QVBoxLayout(); bb.setSpacing(0)
    a = QLabel("KID DIAGNOSTIC"); a.setObjectName("brandTitle")
    b = QLabel("VAG MASTER DIAGNOSTIC PRO  •  V2"); b.setObjectName("brandSub")
    bb.addWidget(a); bb.addWidget(b); tl.addLayout(bb); tl.addStretch()
    self.vehicle_badge = QLabel("SELECTEAZĂ VEHICULUL"); self.vehicle_badge.setObjectName("vehicleBadge"); self.vehicle_badge.setMinimumWidth(280); self.vehicle_badge.setAlignment(Qt.AlignCenter); tl.addWidget(self.vehicle_badge)
    change = QPushButton("Vehicul"); change.setObjectName("topButton"); change.setCursor(Qt.PointingHandCursor); change.clicked.connect(lambda: self.open_page(0)); tl.addWidget(change)
    rl.addWidget(top)

    self.stack = ui_v2.QStackedWidget()
    self.stack.addWidget(self._dashboard()); self.stack.addWidget(self._autoscan()); self.stack.addWidget(self._dtc())
    self.stack.addWidget(self._procedures("Codări", ["coding", "codare", "long coding"]))
    self.stack.addWidget(self._procedures("Adaptări", ["adaptation", "adaptare", "basic settings"]))
    self.stack.addWidget(self._procedures("Service & Resetări", ["service", "dpf", "epb", "battery", "reset", "brake"]))
    self.stack.addWidget(self._live()); self.stack.addWidget(self._modules()); self.stack.addWidget(self._reports())
    rl.addWidget(self.stack, 1); self.setCentralWidget(root)


def _dashboard(self):
    import ui_v2
    page = QWidget(); page.setObjectName("dashboardPage")
    l = QVBoxLayout(page); l.setContentsMargins(30, 24, 30, 28); l.setSpacing(14)

    hero = QFrame(); hero.setObjectName("heroPanel"); hero.setMinimumHeight(112); _shadow(hero, 34, 7, 80)
    hl = QHBoxLayout(hero); hl.setContentsMargins(28, 19, 28, 19); hl.setSpacing(20)
    left = QVBoxLayout(); left.setSpacing(4)
    kicker = QLabel("ATELIER DIGITAL VAG"); kicker.setObjectName("heroKicker")
    h = QLabel("Diagnostic rapid. Informație clară. Proceduri separate."); h.setObjectName("heroTitle")
    s = QLabel("Auto-Scan VCDS, DTC, codări, adaptări, service și Live Data într-o interfață gândită pentru lucru real în atelier."); s.setObjectName("heroSub"); s.setWordWrap(True)
    left.addWidget(kicker); left.addWidget(h); left.addWidget(s); hl.addLayout(left, 1)
    pill = QLabel("VAG  •  1996–2024\nROMÂNĂ  •  LOCAL DB"); pill.setObjectName("heroPill"); pill.setAlignment(Qt.AlignCenter); pill.setFixedSize(190,64); hl.addWidget(pill)
    l.addWidget(hero)

    sel = QFrame(); sel.setObjectName("selectorPanel"); _shadow(sel, 24, 5, 55)
    g = QGridLayout(sel); g.setContentsMargins(18, 14, 18, 14); g.setHorizontalSpacing(10); g.setVerticalSpacing(6)
    self.brand_combo = QComboBox(); self.model_combo = QComboBox(); self.gen_combo = QComboBox(); self.year_combo = QComboBox(); self.engine_combo = QComboBox()
    self.brand_combo.currentIndexChanged.connect(self._load_models); self.model_combo.currentIndexChanged.connect(self._load_generations); self.gen_combo.currentIndexChanged.connect(self._load_years_engines)
    fields=[("MARCĂ",self.brand_combo,1),("MODEL",self.model_combo,1),("GENERAȚIE / CHASSIS",self.gen_combo,2),("AN",self.year_combo,1),("MOTOR",self.engine_combo,2)]
    col=0
    for name,w,span in fields:
        q=QLabel(name); q.setObjectName("fieldLabel"); g.addWidget(q,0,col,1,span); g.addWidget(w,1,col,1,span); col += span
    choose=QPushButton("CONFIRMĂ VEHICULUL"); choose.setObjectName("primaryButton"); choose.setCursor(Qt.PointingHandCursor); choose.clicked.connect(self._select_vehicle); choose.setMinimumHeight(42); g.addWidget(choose,2,0,1,col)
    l.addWidget(sel)

    statrow=QHBoxLayout(); statrow.setSpacing(10)
    self.stat_dtc=self._stat("CODURI DTC","—"); self.stat_proc=self._stat("PROCEDURI","—"); self.stat_mod=self._stat("MODULE","—"); self.stat_cov=self._stat("ACOPERIRE","1996–2024")
    for w in (self.stat_dtc,self.stat_proc,self.stat_mod,self.stat_cov): statrow.addWidget(w)
    l.addLayout(statrow)

    cards=QWidget(); cards.setObjectName("cardsArea"); cg=QGridLayout(cards); cg.setContentsMargins(0,2,0,0); cg.setHorizontalSpacing(12); cg.setVerticalSpacing(12)
    for i,(title,sub,code,idx) in enumerate(ui_v2.CARDS):
        cg.addWidget(ui_v2.FeatureCard(title,sub,code,lambda _=False,x=idx:self.open_page(x)), i//4, i%4)
        cg.setColumnStretch(i%4,1)
    l.addWidget(cards,1)
    return page


def _shell(self, title, subtitle):
    page = QWidget(); page.setObjectName("workspacePage")
    l = QVBoxLayout(page); l.setContentsMargins(28, 22, 28, 26); l.setSpacing(14)
    header = QFrame(); header.setObjectName("workspaceHeader"); hl = QHBoxLayout(header); hl.setContentsMargins(14,12,18,12)
    back = QPushButton("←  Dashboard"); back.setObjectName("backButton"); back.setCursor(Qt.PointingHandCursor); back.clicked.connect(self.show_dashboard); hl.addWidget(back)
    box=QVBoxLayout(); box.setSpacing(1); h=QLabel(title); h.setObjectName("pageTitle"); s=QLabel(subtitle); s.setObjectName("pageSubtitle"); s.setWordWrap(True); box.addWidget(h); box.addWidget(s); hl.addLayout(box,1)
    l.addWidget(header)
    return page,l


def _style(self):
    self.setStyleSheet('''
    QWidget#appRoot, QWidget#dashboardPage, QWidget#workspacePage, QStackedWidget { background:#06111d; color:#eef7ff; font-family:"Segoe UI",Arial,sans-serif; font-size:13px; }
    #topbar { background:#081725; border-bottom:1px solid #17354e; }
    #brandTitle { font-size:19px; font-weight:800; letter-spacing:1.4px; color:#f4fbff; }
    #brandSub { color:#7695ab; font-size:10px; font-weight:650; letter-spacing:.7px; }
    #vehicleBadge { background:#0c2235; border:1px solid #1c4f70; border-radius:12px; padding:9px 14px; color:#aee5ff; font-weight:750; }
    #topButton, #backButton { background:#0d2133; border:1px solid #285674; color:#d8efff; border-radius:10px; padding:9px 15px; font-weight:700; }
    #topButton:hover, #backButton:hover { background:#12304a; border-color:#3baee9; }

    #heroPanel { background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #103457,stop:.55 #0b2238,stop:1 #081624); border:1px solid #1d4f73; border-radius:20px; }
    #heroKicker { color:#48c6ff; font-size:10px; font-weight:800; letter-spacing:1.5px; }
    #heroTitle { font-size:25px; font-weight:850; color:#f5fbff; }
    #heroSub { color:#8eacbf; font-size:12px; }
    #heroPill { background:#081b2c; border:1px solid #2b7099; border-radius:15px; color:#bfeaff; font-weight:750; font-size:11px; }

    #selectorPanel, #workspaceHeader { background:#0a1928; border:1px solid #173a54; border-radius:16px; }
    #fieldLabel { color:#7898ae; font-size:9px; font-weight:800; letter-spacing:1px; }
    QComboBox, QLineEdit { background:#071521; border:1px solid #23445d; border-radius:9px; padding:8px 10px; min-height:24px; color:#edf7ff; }
    QComboBox:hover, QLineEdit:hover { border-color:#2f7aa5; }
    QComboBox:focus, QLineEdit:focus { border:1px solid #36bfff; }
    QComboBox QAbstractItemView { background:#0a1a29; color:#edf7ff; selection-background-color:#1479ad; border:1px solid #28506d; }

    #primaryButton { background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #1188d1,stop:1 #20a9e8); color:white; border:1px solid #43c6ff; border-radius:10px; padding:9px 16px; font-weight:800; letter-spacing:.3px; }
    #primaryButton:hover { background:#1aa8ee; }
    #secondaryButton { background:#0c2236; border:1px solid #2a5875; color:#d8efff; border-radius:10px; padding:9px 14px; font-weight:700; }
    #secondaryButton:hover { background:#12314b; border-color:#3e9dcc; }

    #statCard { background:#091a2a; border:1px solid #173b55; border-radius:13px; min-height:52px; }
    #statLabel { color:#6f91a9; font-size:9px; font-weight:800; letter-spacing:1px; }
    #statValue { color:#54caff; font-size:20px; font-weight:850; }

    #featureCard { background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #0d2033,stop:1 #081521); border:1px solid #193d58; border-radius:17px; }
    #featureCard:hover { background:#0f263b; border:1px solid #2f9acb; }
    #cardTitle { font-size:17px; font-weight:800; color:#f1f8fd; }
    #cardSubtitle { color:#7899af; font-size:11px; }
    #cardCode { background:#102d44; border:1px solid #275976; border-radius:8px; padding:3px 7px; color:#74d5ff; font-size:9px; font-weight:850; letter-spacing:.8px; }
    #cardButton { background:#0e2a40; border:1px solid #255a79; color:#d9f2ff; border-radius:9px; padding:8px 12px; font-weight:800; text-align:left; }
    #cardButton:hover { background:#123b58; border-color:#35b8f1; color:white; }

    #workspaceHeader { min-height:64px; }
    #pageTitle { font-size:23px; font-weight:850; color:#f3faff; }
    #pageSubtitle { color:#7e9eb3; font-size:11px; }
    #summaryStrip { background:#0d2a42; border:1px solid #22638a; border-radius:10px; padding:10px 13px; color:#bdeaff; }
    QTextEdit, QTableWidget { background:#071521; border:1px solid #1e3c54; border-radius:11px; color:#eaf5fc; selection-background-color:#126c9f; }
    QTextEdit { padding:8px; }
    QHeaderView::section { background:#0e2639; color:#bcd6e6; border:none; border-bottom:1px solid #2c5069; padding:9px; font-size:10px; font-weight:800; }
    QTableWidget { gridline-color:#102a3f; alternate-background-color:#091a28; }
    QSplitter::handle { background:#17384f; width:2px; }
    QScrollBar:vertical { background:#07131e; width:10px; margin:0; }
    QScrollBar::handle:vertical { background:#24465e; min-height:30px; border-radius:5px; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
    ''')


def apply():
    import ui_v2
    if getattr(ui_v2, "_kid_v2_redesign_applied", False):
        return
    ui_v2.BrandMark.paintEvent = _paint_brand
    ui_v2.CardArt.paintEvent = _paint_card_art
    ui_v2.FeatureCard.__init__ = _feature_card_init
    ui_v2.MainWindowV2._build = _build
    ui_v2.MainWindowV2._dashboard = _dashboard
    ui_v2.MainWindowV2._shell = _shell
    ui_v2.MainWindowV2._style = _style
    ui_v2._kid_v2_redesign_applied = True
