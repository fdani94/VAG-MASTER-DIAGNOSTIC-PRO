from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from data import DTCInfo, ScanResult, dtc_info
from widgets import SectionCard
from window_base import DetachedWindow, page_header


class DTCWindow(DetachedWindow):
    def __init__(self, scan: ScanResult, parent=None):
        super().__init__("Detalii eroare", (1080, 790), parent)
        self.scan = scan
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(18, 17, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(
            page_header(
                "ERORI DTC",
                "Coduri detectate, cauze posibile, verificări recomandate, direcție de reparație și localizare orientativă.",
            )
        )
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 4, 0)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Caută P0401, EGR, turbo...")
        self.search.textChanged.connect(self.refresh_list)
        self.list = QListWidget()
        self.list.setMinimumWidth(315)
        self.list.currentItemChanged.connect(self._selection_changed)
        left_layout.addWidget(self.search)
        left_layout.addWidget(self.list, 1)
        splitter.addWidget(left)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        detail = QWidget()
        detail_layout = QVBoxLayout(detail)
        detail_layout.setContentsMargins(14, 2, 10, 10)
        detail_layout.setSpacing(10)
        header = QHBoxLayout()
        header_box = QVBoxLayout()
        self.code = QLabel("—")
        self.code.setObjectName("dtcCode")
        self.title = QLabel("Selectați un cod")
        self.title.setObjectName("pageTitle")
        self.title.setWordWrap(True)
        self.system = QLabel()
        self.system.setObjectName("pageSubtitle")
        header_box.addWidget(self.code)
        header_box.addWidget(self.title)
        header_box.addWidget(self.system)
        header.addLayout(header_box, 1)
        self.severity = QLabel()
        self.severity.setObjectName("severityHigh")
        header.addWidget(self.severity, alignment=Qt.AlignmentFlag.AlignTop)
        detail_layout.addLayout(header)

        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.warning = QLabel()
        self.warning.setObjectName("safetyBox")
        self.warning.setWordWrap(True)
        self.causes = SectionCard("!", "Cauze posibile", [])
        self.checks = SectionCard("⌕", "Verificări", [])
        self.repairs = SectionCard("⚒", "Direcție de reparație", [])
        self.location = SectionCard("⌖", "Localizare orientativă", [])
        detail_layout.addWidget(self.summary)
        detail_layout.addWidget(self.warning)
        detail_layout.addWidget(self.causes)
        detail_layout.addWidget(self.checks)
        detail_layout.addWidget(self.repairs)
        detail_layout.addWidget(self.location)
        detail_layout.addStretch(1)
        scroll.setWidget(detail)
        splitter.addWidget(scroll)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter, 1)
        self.setCentralWidget(root)
        self.set_scan(scan)

    def set_scan(self, scan: ScanResult) -> None:
        self.scan = scan
        self.refresh_list()

    def refresh_list(self) -> None:
        selected_code = self.list.currentItem().data(Qt.ItemDataRole.UserRole) if self.list.currentItem() else None
        needle = self.search.text().strip().casefold()
        self.list.clear()
        codes = self.scan.dtc_codes
        for code in codes:
            info = dtc_info(code)
            haystack = f"{info.code} {info.title} {info.system}".casefold()
            if needle and needle not in haystack:
                continue
            item = QListWidgetItem(f"{info.code}\n{info.title}")
            item.setData(Qt.ItemDataRole.UserRole, info.code)
            item.setToolTip(info.summary)
            self.list.addItem(item)
            if info.code == selected_code:
                self.list.setCurrentItem(item)
        if self.list.count() and self.list.currentRow() < 0:
            self.list.setCurrentRow(0)
        elif not self.list.count():
            self._clear_details()

    def _selection_changed(self, current: QListWidgetItem | None, previous: QListWidgetItem | None) -> None:
        if current is None:
            return
        self.show_info(dtc_info(current.data(Qt.ItemDataRole.UserRole)))

    def show_info(self, info: DTCInfo) -> None:
        self.code.setText(info.code)
        self.title.setText(info.title)
        self.system.setText(info.system)
        self.severity.setText(f"Severitate: {info.severity}")
        self.summary.setText(info.summary)
        self.warning.setText(f"IMPORTANT: {info.warning}")
        self.causes.set_lines(info.causes)
        self.checks.set_lines(info.checks)
        self.repairs.set_lines(info.repairs)
        self.location.set_lines([info.location])

    def _clear_details(self) -> None:
        self.code.setText("0 DTC")
        self.title.setText("Nu există coduri de afișat")
        self.system.setText("Importați un Auto-Scan care conține erori.")
        self.severity.clear()
        self.summary.clear()
        self.warning.clear()
        self.causes.set_lines([])
        self.checks.set_lines([])
        self.repairs.set_lines([])
        self.location.set_lines([])
