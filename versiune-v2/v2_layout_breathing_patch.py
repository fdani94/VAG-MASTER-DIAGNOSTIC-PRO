from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSplitter,
    QTextEdit,
    QTableWidget,
)

LAYOUT_VERSION = "2.2.2"
RESPONSIVE_BREAKPOINT = 1420


def _page_splitter(owner, index):
    page = (getattr(owner, "_workspace_pages", {}) or {}).get(index)
    if page is None:
        return None
    splitters = page.findChildren(QSplitter)
    return splitters[0] if splitters else None


def _table_for(owner, index):
    if index == 1:
        return getattr(owner, "autoscan_table", None)
    if index == 2:
        return getattr(owner, "dtc_table", None)
    if index in (3, 4, 5):
        page = (getattr(owner, "_workspace_pages", {}) or {}).get(index)
        return getattr(page, "table", None) if page is not None else None
    if index == 6:
        return getattr(owner, "live_table", None)
    if index == 7:
        return getattr(owner, "module_table", None)
    return None


def _detail_for(owner, index):
    if index == 1:
        return getattr(owner, "autoscan_detail", None)
    if index == 2:
        return getattr(owner, "dtc_detail", None)
    if index in (3, 4, 5):
        page = (getattr(owner, "_workspace_pages", {}) or {}).get(index)
        return getattr(page, "detail", None) if page is not None else None
    return None


def _tune_table(table: QTableWidget | None):
    if table is None:
        return
    table.setWordWrap(False)
    table.setShowGrid(False)
    table.setAlternatingRowColors(True)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setSelectionMode(QAbstractItemView.SingleSelection)
    table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
    table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
    table.verticalHeader().setDefaultSectionSize(36)
    table.horizontalHeader().setMinimumHeight(38)
    table.setStyleSheet(
        table.styleSheet()
        + """
        QTableWidget {
            background:#ffffff;
            alternate-background-color:#f6f9fc;
            border:1px solid #d5e1ea;
            border-radius:10px;
            font-size:13px;
            selection-background-color:#dceeff;
            selection-color:#12344d;
        }
        QTableWidget::item { padding:7px 9px; border-bottom:1px solid #edf2f6; }
        QHeaderView::section {
            background:#edf4fa;
            color:#35546d;
            border:none;
            border-bottom:1px solid #d4e0e9;
            padding:8px 9px;
            font-weight:800;
        }
        """
    )


def _tune_detail(detail: QTextEdit | None):
    if detail is None:
        return
    detail.setMinimumWidth(360)
    detail.setStyleSheet(
        detail.styleSheet()
        + """
        QTextEdit {
            background:#ffffff;
            color:#182536;
            border:1px solid #d5e1ea;
            border-radius:10px;
            padding:14px;
            font-size:14px;
            selection-background-color:#cfe9ff;
        }
        """
    )
    try:
        detail.document().setDocumentMargin(12)
    except Exception:
        pass


def _configure_columns(owner, index):
    table = _table_for(owner, index)
    if table is None or table.columnCount() == 0:
        return
    header = table.horizontalHeader()
    header.setStretchLastSection(False)
    for col in range(table.columnCount()):
        header.setSectionResizeMode(col, QHeaderView.Interactive)

    if index == 1 and table.columnCount() >= 5:
        widths = [190, 120, 360, 120, 120]
    elif index == 2 and table.columnCount() >= 4:
        widths = [120, 420, 120, 130]
    elif index in (3, 4, 5) and table.columnCount() >= 5:
        widths = [175, 95, 330, 300, 220, 165]
    elif index == 6 and table.columnCount() >= 4:
        widths = [120, 280, 420, 500]
    elif index == 7 and table.columnCount() >= 4:
        widths = [105, 300, 390, 180, 220]
    else:
        widths = [160] * table.columnCount()

    for col, width in enumerate(widths[: table.columnCount()]):
        table.setColumnWidth(col, width)

    if index in (1, 2, 3, 4, 5) and table.columnCount() > 2:
        header.setSectionResizeMode(2, QHeaderView.Stretch)
    elif index == 6 and table.columnCount() > 3:
        header.setSectionResizeMode(3, QHeaderView.Stretch)
    elif index == 7 and table.columnCount() > 2:
        header.setSectionResizeMode(2, QHeaderView.Stretch)


def _view_controls(owner, index, splitter):
    page = (getattr(owner, "_workspace_pages", {}) or {}).get(index)
    if page is None or page.layout() is None or splitter is None:
        return None
    existing = page.findChild(QFrame, f"kidViewControls{index}")
    if existing is not None:
        return existing

    bar = QFrame()
    bar.setObjectName(f"kidViewControls{index}")
    bar.setMaximumHeight(44)
    row = QHBoxLayout(bar)
    row.setContentsMargins(10, 4, 10, 4)
    row.setSpacing(7)
    label = QLabel("VIZUALIZARE")
    label.setObjectName("kidViewLabel")
    row.addWidget(label)
    row.addStretch(1)

    first = splitter.widget(0)
    second = splitter.widget(1) if splitter.count() > 1 else None

    def show_list():
        if first is not None:
            first.show()
        if second is not None:
            second.hide()
        bar.setProperty("kidViewMode", "list")

    def show_both():
        if first is not None:
            first.show()
        if second is not None:
            second.show()
        bar.setProperty("kidViewMode", "both")
        _apply_splitter_orientation(owner, index)

    def show_detail():
        if first is not None:
            first.hide()
        if second is not None:
            second.show()
        bar.setProperty("kidViewMode", "detail")

    list_btn = QPushButton("LISTĂ")
    list_btn.setObjectName(f"kidViewList{index}")
    list_btn.clicked.connect(show_list)
    both_btn = QPushButton("LISTĂ + DETALII")
    both_btn.setObjectName(f"kidViewBoth{index}")
    both_btn.clicked.connect(show_both)
    detail_btn = QPushButton("DETALII MARI")
    detail_btn.setObjectName(f"kidViewDetail{index}")
    detail_btn.clicked.connect(show_detail)
    row.addWidget(list_btn)
    row.addWidget(both_btn)
    row.addWidget(detail_btn)
    bar.setProperty("kidViewMode", "both")

    position = page.layout().indexOf(splitter)
    page.layout().insertWidget(max(1, position), bar)
    return bar


def _apply_splitter_orientation(owner, index):
    splitter = _page_splitter(owner, index)
    if splitter is None or splitter.count() < 2:
        return
    width = max(owner.width(), owner.centralWidget().width() if owner.centralWidget() else 0)
    if width < RESPONSIVE_BREAKPOINT:
        splitter.setOrientation(Qt.Vertical)
        available = max(360, splitter.height())
        splitter.setSizes([int(available * 0.43), int(available * 0.57)])
        splitter.setProperty("kidResponsiveOrientation", "vertical")
    else:
        splitter.setOrientation(Qt.Horizontal)
        available = max(900, splitter.width())
        splitter.setSizes([int(available * 0.56), int(available * 0.44)])
        splitter.setProperty("kidResponsiveOrientation", "horizontal")
    splitter.setChildrenCollapsible(False)
    splitter.setHandleWidth(8)


def _compact_redundant_context(owner):
    # The selected vehicle is already always visible in the global top bar.
    # Repeating a full-height vehicle card on every page consumed too much of a
    # 768px-high screen, so V2.2.2 keeps the context globally visible and frees
    # the workspace for actual diagnostic content.
    for strip in (getattr(owner, "_vehicle_context_strips", {}) or {}).values():
        strip.hide()
        strip.setMaximumHeight(0)

    for strip in (getattr(owner, "v2_ai_strips", {}) or {}).values():
        strip.setMinimumHeight(46)
        strip.setMaximumHeight(50)
        layout = strip.layout()
        if layout is not None:
            layout.setContentsMargins(11, 5, 11, 5)
            layout.setSpacing(8)

    overview = getattr(owner, "_coding_overview", None)
    if overview is not None:
        overview.setMinimumHeight(66)
        overview.setMaximumHeight(78)
        if overview.layout() is not None:
            overview.layout().setContentsMargins(12, 8, 12, 8)
            overview.layout().setSpacing(10)

    toolbar = getattr(owner, "v2_ai_toolbar", None)
    if toolbar is not None:
        toolbar.setMaximumHeight(40)


def _tune_page(owner, index):
    page = (getattr(owner, "_workspace_pages", {}) or {}).get(index)
    if page is None:
        return
    page.setProperty("kidBreathingLayout", LAYOUT_VERSION)
    layout = page.layout()
    if layout is not None:
        layout.setContentsMargins(22, 15, 22, 18)
        layout.setSpacing(11)

    table = _table_for(owner, index)
    detail = _detail_for(owner, index)
    _tune_table(table)
    _tune_detail(detail)
    _configure_columns(owner, index)

    splitter = _page_splitter(owner, index)
    if splitter is not None:
        splitter.setObjectName(f"kidWorkspaceSplitter{index}")
        splitter.setMinimumHeight(260)
        _view_controls(owner, index, splitter)
        _apply_splitter_orientation(owner, index)


def _enhance_coding_html():
    import v2_vehicle_first_patch as vf

    original = vf._render_coding_detail
    if getattr(original, "_kid_222_wrapped", False):
        return

    def rendered(owner, row):
        html = original(owner, row)
        html = html.replace("font-size:13px; line-height:1.45", "font-size:14px; line-height:1.62")
        html = html.replace("font-size:21px", "font-size:23px")
        html = html.replace("margin-top:12px; padding:11px 12px", "margin-top:15px; padding:14px 16px")
        html = html.replace("margin:10px 0; padding:12px", "margin:13px 0; padding:14px 16px")
        html = html.replace("margin-top:12px; padding:12px", "margin-top:15px; padding:14px 16px")
        return html

    rendered._kid_222_wrapped = True
    vf._render_coding_detail = rendered


def apply():
    import ui_v2

    cls = ui_v2.MainWindowV2
    if getattr(cls, "_kid_layout_breathing_applied", False):
        return

    _enhance_coding_html()

    previous_init = cls.__init__
    previous_open_page = cls.open_page
    previous_resize_event = getattr(cls, "resizeEvent", None)
    previous_load_procedures = cls._load_procedures
    previous_load_dtcs = cls._load_dtcs
    previous_load_live = cls._load_live
    previous_load_modules = cls._load_modules
    previous_load_autoscan = cls._load_autoscan

    def init_breathing(self, *args, **kwargs):
        previous_init(self, *args, **kwargs)
        _compact_redundant_context(self)
        for index in range(1, 9):
            _tune_page(self, index)
        self.setWindowTitle("KID Diagnostic V2 • Vehicle First • AI Copilot • v2.2.2")
        try:
            self.statusBar().showMessage("KID Diagnostic V2 v2.2.2 • layout aerisit • vehicle-first • AI Copilot")
        except Exception:
            pass
        self.setStyleSheet(
            self.styleSheet()
            + """
            #kidViewLabel { color:#6a8295; font-size:10px; font-weight:900; letter-spacing:.7px; }
            QFrame[objectName^="kidViewControls"] { background:transparent; border:none; }
            QFrame[objectName^="kidViewControls"] QPushButton {
                background:#ffffff; color:#315a78; border:1px solid #cbdce8;
                border-radius:7px; padding:6px 10px; font-size:11px; font-weight:800;
            }
            QFrame[objectName^="kidViewControls"] QPushButton:hover { background:#eaf5ff; border-color:#82b9de; }
            """
        )
        QTimer.singleShot(0, lambda: [_apply_splitter_orientation(self, i) for i in range(1, 6)])

    def open_page_breathing(self, index):
        previous_open_page(self, index)
        index = int(index)
        if index in range(1, 9):
            _compact_redundant_context(self)
            _tune_page(self, index)
            if index in range(1, 6):
                QTimer.singleShot(0, lambda i=index: _apply_splitter_orientation(self, i))
            if int(getattr(self, "_active_workspace_index", 0) or 0) == index:
                title = ui_v2.CARDS[index - 1][0]
                self.setWindowTitle(f"KID Diagnostic V2 • {title} • v2.2.2")

    def resize_breathing(self, event):
        if previous_resize_event is not None:
            previous_resize_event(self, event)
        for index in range(1, 6):
            _apply_splitter_orientation(self, index)

    def load_procedures_breathing(self, page):
        result = previous_load_procedures(self, page)
        for index in (3, 4, 5):
            if page is (getattr(self, "_workspace_pages", {}) or {}).get(index):
                _tune_page(self, index)
                break
        return result

    def load_dtcs_breathing(self):
        result = previous_load_dtcs(self)
        _tune_page(self, 2)
        return result

    def load_live_breathing(self):
        result = previous_load_live(self)
        _tune_page(self, 6)
        return result

    def load_modules_breathing(self):
        result = previous_load_modules(self)
        _tune_page(self, 7)
        return result

    def load_autoscan_breathing(self):
        result = previous_load_autoscan(self)
        _tune_page(self, 1)
        return result

    cls.__init__ = init_breathing
    cls.open_page = open_page_breathing
    cls.resizeEvent = resize_breathing
    cls._load_procedures = load_procedures_breathing
    cls._load_dtcs = load_dtcs_breathing
    cls._load_live = load_live_breathing
    cls._load_modules = load_modules_breathing
    cls._load_autoscan = load_autoscan_breathing
    cls._kid_layout_breathing_applied = True


__all__ = ["LAYOUT_VERSION", "RESPONSIVE_BREAKPOINT", "apply"]
