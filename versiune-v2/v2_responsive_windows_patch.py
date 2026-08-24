"""Light responsive shell and real separate workspace windows for KID Diagnostic V2.

This patch is intentionally applied last. It keeps the diagnostic/data methods
from the previous V2 patches, but changes the presentation layer so that:
- the dashboard is light, modern and scroll-safe on small displays;
- feature cards reflow from 4 -> 3 -> 2 -> 1 columns;
- each diagnostic area opens in its own top-level window;
- workspace windows maximize to the available screen area;
- the main window can run down to 760x520 without clipping core controls.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication, QAbstractScrollArea, QComboBox, QFrame, QGridLayout,
    QLabel, QMainWindow, QMessageBox, QPushButton, QScrollArea,
    QSizePolicy, QVBoxLayout, QWidget,
)

import appdb as db


ACCENTS = {
    "SCAN": "#208ce5",
    "DTC": "#e59b2f",
    "CODE": "#7367e8",
    "ADAPT": "#22a989",
    "SERV": "#dc6671",
    "LIVE": "#238fc7",
    "MOD": "#4e83d8",
    "PDF": "#bd8d24",
}


class ResponsiveDashboard(QWidget):
    def __init__(self):
        super().__init__()
        self.card_grid = None
        self.card_widgets = []
        self.stat_grid = None
        self.stat_widgets = []
        self._last_card_cols = 0
        self._last_stat_cols = 0

    @staticmethod
    def _clear_grid(layout):
        if layout is None:
            return
        while layout.count():
            layout.takeAt(0)

    def reflow(self, width=None):
        width = int(width or self.width())
        if width >= 1450:
            card_cols = 4
        elif width >= 1080:
            card_cols = 3
        elif width >= 720:
            card_cols = 2
        else:
            card_cols = 1
        stat_cols = 4 if width >= 1080 else 2

        if self.card_grid is not None and card_cols != self._last_card_cols:
            self._clear_grid(self.card_grid)
            for i, widget in enumerate(self.card_widgets):
                self.card_grid.addWidget(widget, i // card_cols, i % card_cols)
            for col in range(4):
                self.card_grid.setColumnStretch(col, 1 if col < card_cols else 0)
            self._last_card_cols = card_cols
            self.setProperty("responsiveColumns", card_cols)

        if self.stat_grid is not None and stat_cols != self._last_stat_cols:
            self._clear_grid(self.stat_grid)
            for i, widget in enumerate(self.stat_widgets):
                self.stat_grid.addWidget(widget, i // stat_cols, i % stat_cols)
            for col in range(4):
                self.stat_grid.setColumnStretch(col, 1 if col < stat_cols else 0)
            self._last_stat_cols = stat_cols
            self.setProperty("responsiveStatColumns", stat_cols)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.reflow(event.size().width())


class WorkspaceWindow(QMainWindow):
    def __init__(self, owner, index, title, page):
        super().__init__(None)
        self.owner = owner
        self.workspace_index = index
        self.setWindowTitle(f"KID Diagnostic V2 • {title}")
        self.setObjectName("workspaceWindow")
        self.setAttribute(Qt.WA_DeleteOnClose, False)
        self.setMinimumSize(700, 500)
        self.setCentralWidget(page)
        qss = getattr(owner, "_kid_light_qss", "")
        if qss:
            self.setStyleSheet(qss)

    def show_for_owner_screen(self):
        screen = self.owner.screen() or QApplication.primaryScreen()
        if screen is not None:
            geo = screen.availableGeometry()
            self.setGeometry(geo)
        self.showMaximized()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event):
        self.hide()
        event.ignore()
        self.owner.show_dashboard()


def _paint_brand_light(self, _event):
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
    grad.setColorAt(0, QColor("#2f96e8"))
    grad.setColorAt(1, QColor("#1b67b0"))
    p.setBrush(grad)
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(rect, 15, 15)
    p.setPen(QColor("#ffffff"))
    p.setFont(QFont("Segoe UI", 14, QFont.Bold))
    p.drawText(rect, Qt.AlignCenter, "KID")


def _paint_card_art_light(self, _event):
    p = QPainter(self)
    p.setRenderHint(QPainter.Antialiasing)
    r = self.rect().adjusted(2, 2, -2, -2)
    code = str(getattr(self, "code", "")).upper()
    accent = QColor(ACCENTS.get(code, "#208ce5"))

    bg = QLinearGradient(r.topLeft(), r.bottomRight())
    bg.setColorAt(0, QColor("#f8fbfe"))
    bg.setColorAt(1, QColor("#e9f2f9"))
    p.setBrush(bg)
    p.setPen(QPen(QColor("#d5e3ee"), 1))
    p.drawRoundedRect(r, 16, 16)

    glow = QColor(accent); glow.setAlpha(25)
    diameter = min(r.height() - 16, 70)
    p.setBrush(glow); p.setPen(Qt.NoPen)
    p.drawEllipse(r.center().x() - diameter // 2, r.center().y() - diameter // 2, diameter, diameter)

    x, y, w, h = r.x(), r.y(), r.width(), r.height()
    p.setBrush(Qt.NoBrush)
    p.setPen(QPen(accent, 3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))

    if code == "SCAN":
        p.drawLine(int(x+w*.25), int(y+h*.61), int(x+w*.75), int(y+h*.61))
        p.drawLine(int(x+w*.34), int(y+h*.61), int(x+w*.41), int(y+h*.42))
        p.drawLine(int(x+w*.41), int(y+h*.42), int(x+w*.60), int(y+h*.42))
        p.drawLine(int(x+w*.60), int(y+h*.42), int(x+w*.68), int(y+h*.61))
        p.drawEllipse(int(x+w*.33), int(y+h*.56), 13, 13)
        p.drawEllipse(int(x+w*.62), int(y+h*.56), 13, 13)
        for f in (.28, .35, .42):
            p.drawLine(int(x+w*.16), int(y+h*f), int(x+w*.27), int(y+h*f))
    elif code == "DTC":
        p.drawRoundedRect(int(x+w*.33), int(y+h*.24), int(w*.34), int(h*.52), 8, 8)
        p.drawLine(int(x+w*.40), int(y+h*.36), int(x+w*.60), int(y+h*.36))
        p.drawLine(int(x+w*.40), int(y+h*.48), int(x+w*.56), int(y+h*.48))
        p.drawPoint(int(x+w*.50), int(y+h*.64))
    elif code == "CODE":
        p.drawLine(int(x+w*.38), int(y+h*.33), int(x+w*.27), int(y+h*.50))
        p.drawLine(int(x+w*.27), int(y+h*.50), int(x+w*.38), int(y+h*.67))
        p.drawLine(int(x+w*.62), int(y+h*.33), int(x+w*.73), int(y+h*.50))
        p.drawLine(int(x+w*.73), int(y+h*.50), int(x+w*.62), int(y+h*.67))
        p.drawLine(int(x+w*.54), int(y+h*.31), int(x+w*.46), int(y+h*.69))
    elif code == "ADAPT":
        for fy, fx in ((.34,.43),(.50,.61),(.66,.36)):
            yy = int(y+h*fy)
            p.drawLine(int(x+w*.28), yy, int(x+w*.72), yy)
            p.setBrush(QColor("#ffffff"))
            p.drawEllipse(int(x+w*fx)-6, yy-6, 12, 12)
            p.setBrush(Qt.NoBrush)
    elif code == "SERV":
        p.drawArc(int(x+w*.31), int(y+h*.25), int(w*.30), int(h*.38), 35*16, 255*16)
        p.drawLine(int(x+w*.49), int(y+h*.52), int(x+w*.67), int(y+h*.69))
        p.drawEllipse(int(x+w*.63), int(y+h*.64), 11, 11)
    elif code == "LIVE":
        p.drawLine(int(x+w*.25), int(y+h*.70), int(x+w*.75), int(y+h*.70))
        p.drawLine(int(x+w*.25), int(y+h*.28), int(x+w*.25), int(y+h*.70))
        pts=[(.28,.62),(.38,.53),(.47,.58),(.55,.38),(.65,.46),(.72,.31)]
        for a,b in zip(pts,pts[1:]):
            p.drawLine(int(x+w*a[0]),int(y+h*a[1]),int(x+w*b[0]),int(y+h*b[1]))
    elif code == "MOD":
        nodes=[(.34,.35),(.66,.35),(.50,.65)]
        for a,b in ((0,1),(0,2),(1,2)):
            p.drawLine(int(x+w*nodes[a][0]),int(y+h*nodes[a][1]),int(x+w*nodes[b][0]),int(y+h*nodes[b][1]))
        p.setBrush(QColor("#ffffff"))
        for nx,ny in nodes:
            p.drawRoundedRect(int(x+w*nx)-10,int(y+h*ny)-8,20,16,4,4)
    elif code == "PDF":
        px,py,pw,ph=int(x+w*.38),int(y+h*.20),int(w*.25),int(h*.60)
        p.drawRoundedRect(px,py,pw,ph,6,6)
        for fy in (.42,.52,.62):
            p.drawLine(int(x+w*.42),int(y+h*fy),int(x+w*.59),int(y+h*fy))


def _dashboard(self):
    import ui_v2
    scroll = QScrollArea()
    scroll.setObjectName("dashboardScroll")
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    scroll.setSizeAdjustPolicy(QAbstractScrollArea.AdjustIgnored)

    page = ResponsiveDashboard()
    page.setObjectName("dashboardPage")
    l = QVBoxLayout(page)
    l.setContentsMargins(22, 20, 22, 24)
    l.setSpacing(14)

    hero = QFrame(); hero.setObjectName("heroPanel")
    hl = QVBoxLayout(hero); hl.setContentsMargins(24, 18, 24, 18); hl.setSpacing(4)
    kicker = QLabel("KID DIAGNOSTIC • VAG MASTER PRO V2"); kicker.setObjectName("heroKicker")
    h = QLabel("Diagnoză VAG, într-o interfață clară pentru atelier."); h.setObjectName("heroTitle"); h.setWordWrap(True)
    s = QLabel("Selectezi mașina o singură dată, apoi fiecare funcție se deschide în fereastra ei: Auto-Scan, DTC, codări, adaptări, service, Live Data, module și rapoarte.")
    s.setObjectName("heroSub"); s.setWordWrap(True)
    hl.addWidget(kicker); hl.addWidget(h); hl.addWidget(s)
    l.addWidget(hero)

    sel = QFrame(); sel.setObjectName("selectorPanel")
    g = QGridLayout(sel); g.setContentsMargins(16, 14, 16, 14); g.setHorizontalSpacing(10); g.setVerticalSpacing(6)
    self.brand_combo = QComboBox(); self.model_combo = QComboBox(); self.gen_combo = QComboBox(); self.year_combo = QComboBox(); self.engine_combo = QComboBox()
    self.brand_combo.currentIndexChanged.connect(self._load_models)
    self.model_combo.currentIndexChanged.connect(self._load_generations)
    self.gen_combo.currentIndexChanged.connect(self._load_years_engines)
    fields = [
        ("MARCĂ", self.brand_combo, 0, 0, 1),
        ("MODEL", self.model_combo, 0, 1, 1),
        ("GENERAȚIE / CHASSIS", self.gen_combo, 0, 2, 1),
        ("AN", self.year_combo, 2, 0, 1),
        ("MOTOR", self.engine_combo, 2, 1, 2),
    ]
    for name, widget, row, col, span in fields:
        label = QLabel(name); label.setObjectName("fieldLabel")
        g.addWidget(label, row, col, 1, span)
        g.addWidget(widget, row + 1, col, 1, span)
    choose = QPushButton("CONFIRMĂ VEHICULUL")
    choose.setObjectName("primaryButton"); choose.setCursor(Qt.PointingHandCursor); choose.setMinimumHeight(42)
    choose.clicked.connect(self._select_vehicle)
    g.addWidget(choose, 4, 0, 1, 3)
    for col in range(3):
        g.setColumnStretch(col, 1)
    l.addWidget(sel)

    stats = QWidget(); stats.setObjectName("statsArea")
    stat_grid = QGridLayout(stats); stat_grid.setContentsMargins(0,0,0,0); stat_grid.setSpacing(10)
    self.stat_dtc=self._stat("CODURI DTC","—")
    self.stat_proc=self._stat("PROCEDURI","—")
    self.stat_mod=self._stat("MODULE","—")
    self.stat_cov=self._stat("ACOPERIRE","1996–2024")
    page.stat_grid = stat_grid
    page.stat_widgets = [self.stat_dtc, self.stat_proc, self.stat_mod, self.stat_cov]
    l.addWidget(stats)

    cards = QWidget(); cards.setObjectName("cardsArea")
    card_grid = QGridLayout(cards); card_grid.setContentsMargins(0,2,0,0); card_grid.setSpacing(12)
    card_widgets = []
    for title, sub, code, idx in ui_v2.CARDS:
        card = ui_v2.FeatureCard(title, sub, code, lambda _=False, x=idx: self.open_page(x))
        card.setMinimumHeight(178)
        card_widgets.append(card)
    page.card_grid = card_grid
    page.card_widgets = card_widgets
    l.addWidget(cards)
    l.addStretch(1)

    self._responsive_dashboard = page
    scroll.setWidget(page)
    QTimer.singleShot(0, lambda: page.reflow(scroll.viewport().width()))
    return scroll


def _light_style(self):
    qss = '''
    QWidget#appRoot, QWidget#dashboardPage, QWidget#workspacePage, QStackedWidget, QScrollArea#dashboardScroll {
        background:#eef3f7; color:#172436; font-family:"Segoe UI",Arial,sans-serif; font-size:13px;
    }
    QScrollArea#dashboardScroll > QWidget > QWidget { background:#eef3f7; }
    #topbar { background:#ffffff; border-bottom:1px solid #d6e1e9; }
    #brandTitle { font-size:19px; font-weight:800; letter-spacing:1.2px; color:#17283b; }
    #brandSub { color:#72879a; font-size:10px; font-weight:650; letter-spacing:.6px; }
    #vehicleBadge { background:#edf6fd; border:1px solid #c7dfef; border-radius:12px; padding:9px 14px; color:#24679b; font-weight:750; }
    #topButton, #backButton, #secondaryButton { background:#ffffff; border:1px solid #c9d8e3; color:#28475f; border-radius:10px; padding:9px 14px; font-weight:700; }
    #topButton:hover, #backButton:hover, #secondaryButton:hover { background:#edf6fd; border-color:#83b9dc; color:#176da9; }

    #heroPanel { background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #e5f3ff,stop:.55 #f3f9fd,stop:1 #ffffff); border:1px solid #c9deec; border-radius:18px; }
    #heroKicker { color:#277fbe; font-size:10px; font-weight:800; letter-spacing:1.4px; }
    #heroTitle { font-size:24px; font-weight:850; color:#18324a; }
    #heroSub { color:#60788c; font-size:12px; }

    #selectorPanel, #workspaceHeader { background:#ffffff; border:1px solid #d4e0e8; border-radius:15px; }
    #fieldLabel { color:#657d90; font-size:9px; font-weight:800; letter-spacing:.9px; }
    QComboBox, QLineEdit { background:#f8fbfd; border:1px solid #cbd9e3; border-radius:9px; padding:8px 10px; min-height:24px; color:#1b2d3e; }
    QComboBox:hover, QLineEdit:hover { border-color:#8ab9d8; }
    QComboBox:focus, QLineEdit:focus { border:1px solid #2a8bd1; background:#ffffff; }
    QComboBox QAbstractItemView { background:#ffffff; color:#1f3142; selection-background-color:#dceffd; border:1px solid #c8d7e2; }

    #primaryButton { background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #2b8ed7,stop:1 #4fa8e8); color:white; border:none; border-radius:10px; padding:10px 16px; font-weight:800; }
    #primaryButton:hover { background:#247fc0; }

    #statCard { background:#ffffff; border:1px solid #d6e1e9; border-radius:13px; min-height:52px; }
    #statLabel { color:#708697; font-size:9px; font-weight:800; letter-spacing:.9px; }
    #statValue { color:#257fc0; font-size:20px; font-weight:850; }

    #featureCard { background:#ffffff; border:1px solid #d7e2ea; border-radius:17px; }
    #featureCard:hover { background:#fbfdff; border:1px solid #8cbcdf; }
    #cardTitle { font-size:17px; font-weight:800; color:#1b3044; }
    #cardSubtitle { color:#71879a; font-size:11px; }
    #cardCode { background:#edf5fb; border:1px solid #d1e3ef; border-radius:8px; padding:3px 7px; color:#327faf; font-size:9px; font-weight:850; letter-spacing:.7px; }
    #cardButton { background:#edf6fd; border:1px solid #c8dfef; color:#246f9f; border-radius:9px; padding:8px 12px; font-weight:800; text-align:left; }
    #cardButton:hover { background:#dfeffc; border-color:#76add3; color:#155f91; }

    #workspaceHeader { min-height:64px; }
    #pageTitle { font-size:23px; font-weight:850; color:#1a3044; }
    #pageSubtitle { color:#70879a; font-size:11px; }
    #summaryStrip { background:#e8f4fc; border:1px solid #bfdced; border-radius:10px; padding:10px 13px; color:#245f86; }

    QTextEdit, QTableWidget { background:#ffffff; border:1px solid #d3dfe7; border-radius:11px; color:#1f3040; selection-background-color:#d7ecfb; selection-color:#16354b; }
    QTextEdit { padding:8px; }
    QHeaderView::section { background:#edf3f7; color:#455d70; border:none; border-bottom:1px solid #d1dee7; padding:9px; font-size:10px; font-weight:800; }
    QTableWidget { gridline-color:#e5edf2; alternate-background-color:#f7fafc; }
    QSplitter::handle { background:#d9e4eb; width:3px; }
    QScrollBar:vertical { background:#edf2f5; width:10px; margin:0; }
    QScrollBar::handle:vertical { background:#b9cad6; min-height:30px; border-radius:5px; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
    '''
    self._kid_light_qss = qss
    self.setStyleSheet(qss)


def _open_page(self, index):
    if index == 0:
        self.show_dashboard()
        return
    if not self.selected_generation_id:
        QMessageBox.warning(self, "Vehicul", "Selectează mai întâi vehiculul.")
        self.show_dashboard()
        return

    page = self._workspace_pages.get(index)
    if page is None:
        QMessageBox.critical(self, "Interfață", f"Workspace-ul {index} nu a putut fi inițializat.")
        return

    if index == 2:
        self._load_dtcs()
    elif index in (3, 4, 5):
        self._load_procedures(page)
    elif index == 6:
        self._load_live()
    elif index == 7:
        self._load_modules()

    win = self._workspace_windows.get(index)
    if win is None:
        import ui_v2
        title = ui_v2.CARDS[index - 1][0]
        win = WorkspaceWindow(self, index, title, page)
        self._workspace_windows[index] = win
    self._active_workspace_index = index
    self.hide()
    win.show_for_owner_screen()


def _show_dashboard(self):
    for win in getattr(self, "_workspace_windows", {}).values():
        if win.isVisible():
            win.hide()
    self._active_workspace_index = 0
    if hasattr(self, "stack"):
        self.stack.setCurrentIndex(0)
    self.show()
    self.raise_()
    self.activateWindow()
    dashboard = getattr(self, "_responsive_dashboard", None)
    if dashboard is not None:
        QTimer.singleShot(0, lambda: dashboard.reflow(self.width()))


def apply():
    import ui_v2
    cls = ui_v2.MainWindowV2
    if getattr(cls, "_kid_v2_responsive_windows_applied", False):
        return

    # These methods must be installed before __init__ runs because _build() calls
    # _dashboard/_style and the workspace Back buttons bind show_dashboard there.
    cls._dashboard = _dashboard
    cls._style = _light_style
    cls.open_page = _open_page
    cls.show_dashboard = _show_dashboard
    ui_v2.BrandMark.paintEvent = _paint_brand_light
    ui_v2.CardArt.paintEvent = _paint_card_art_light

    previous_init = cls.__init__

    def __init__(self, *args, **kwargs):
        previous_init(self, *args, **kwargs)
        all_pages = [self.stack.widget(i) for i in range(self.stack.count())]
        self._workspace_pages = {i: all_pages[i] for i in range(1, min(9, len(all_pages)))}
        for index, page in self._workspace_pages.items():
            self.stack.removeWidget(page)
            page.setParent(None)
        self._workspace_windows = {}
        self._active_workspace_index = 0

        # The previous V2 forced 1180x740. Lower it so 1024x768-class displays
        # can still show a complete, scrollable dashboard.
        self.setMinimumSize(760, 520)
        screen = self.screen() or QApplication.primaryScreen()
        if screen is not None:
            geo = screen.availableGeometry()
            target_w = max(760, min(1500, int(geo.width() * 0.94)))
            target_h = max(520, min(920, int(geo.height() * 0.92)))
            self.resize(target_w, target_h)
            self.move(geo.x() + max(0, (geo.width() - target_w) // 2),
                      geo.y() + max(0, (geo.height() - target_h) // 2))
        if getattr(self, "_responsive_dashboard", None) is not None:
            QTimer.singleShot(0, lambda: self._responsive_dashboard.reflow(self.width()))

    cls.__init__ = __init__
    cls._kid_v2_responsive_windows_applied = True
