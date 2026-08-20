from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from data import GuidedProcedure, find_procedures
from widgets import SectionCard


def page_header(title: str, subtitle: str) -> QWidget:
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(3)
    title_label = QLabel(title)
    title_label.setObjectName("pageTitle")
    subtitle_label = QLabel(subtitle)
    subtitle_label.setObjectName("pageSubtitle")
    subtitle_label.setWordWrap(True)
    layout.addWidget(title_label)
    layout.addWidget(subtitle_label)
    return widget


class DetachedWindow(QMainWindow):
    def __init__(self, title: str, size: tuple[int, int] = (1020, 720), parent=None):
        super().__init__(parent)
        self.setWindowFlag(Qt.WindowType.Window, True)
        self.setWindowTitle(f"{title} — KID VAG MASTER V2")
        self.resize(*size)
        self.setMinimumSize(780, 560)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)


class ProcedureBrowser(QWidget):
    def __init__(self, procedures: Sequence[GuidedProcedure], parent=None):
        super().__init__(parent)
        self.procedures = list(procedures)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(10)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Caută procedură, modul sau platformă...")
        self.search.textChanged.connect(self.refresh)
        root.addWidget(self.search)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        self.list = QListWidget()
        self.list.setMinimumWidth(300)
        self.list.currentItemChanged.connect(self._selection_changed)
        splitter.addWidget(self.list)

        self.detail_scroll = QScrollArea()
        self.detail_scroll.setWidgetResizable(True)
        self.detail_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.detail = QWidget()
        self.detail_layout = QVBoxLayout(self.detail)
        self.detail_layout.setContentsMargins(14, 5, 10, 10)
        self.detail_layout.setSpacing(10)

        self.title = QLabel("Selectați o procedură")
        self.title.setObjectName("pageTitle")
        self.meta = QLabel()
        self.meta.setObjectName("pageSubtitle")
        self.description = QLabel()
        self.description.setWordWrap(True)
        self.description.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.safety = QLabel()
        self.safety.setObjectName("safetyBox")
        self.safety.setWordWrap(True)
        self.prerequisites = SectionCard("✓", "Condiții înainte de începere", [])
        self.steps = SectionCard("1", "Pași ghidați", [])
        self.verification = SectionCard("✓", "Verificare după procedură", [])

        self.detail_layout.addWidget(self.title)
        self.detail_layout.addWidget(self.meta)
        self.detail_layout.addWidget(self.description)
        self.detail_layout.addWidget(self.safety)
        self.detail_layout.addWidget(self.prerequisites)
        self.detail_layout.addWidget(self.steps)
        self.detail_layout.addWidget(self.verification)
        self.detail_layout.addStretch(1)
        self.detail_scroll.setWidget(self.detail)
        splitter.addWidget(self.detail_scroll)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        root.addWidget(splitter, 1)
        self.refresh()

    def refresh(self) -> None:
        selected_title = self.list.currentItem().data(Qt.ItemDataRole.UserRole).title if self.list.currentItem() else None
        items = find_procedures(self.procedures, self.search.text())
        self.list.clear()
        selected_item = None
        for procedure in items:
            item = QListWidgetItem(f"{procedure.title}\n{procedure.module}")
            item.setData(Qt.ItemDataRole.UserRole, procedure)
            item.setToolTip(procedure.description)
            self.list.addItem(item)
            if procedure.title == selected_title:
                selected_item = item
        if selected_item:
            self.list.setCurrentItem(selected_item)
        elif self.list.count():
            self.list.setCurrentRow(0)

    def _selection_changed(self, current: QListWidgetItem | None, previous: QListWidgetItem | None) -> None:
        if current is None:
            self.title.setText("Nicio procedură găsită")
            self.meta.clear()
            self.description.clear()
            self.safety.clear()
            self.prerequisites.set_lines([])
            self.steps.set_lines([])
            self.verification.set_lines([])
            return
        procedure: GuidedProcedure = current.data(Qt.ItemDataRole.UserRole)
        self.title.setText(procedure.title)
        self.meta.setText(
            f"{procedure.category} • {procedure.module} • {procedure.platform} • {procedure.duration}"
        )
        self.description.setText(procedure.description)
        self.safety.setText(f"ATENȚIE: {procedure.safety}")
        self.prerequisites.set_lines(procedure.prerequisites)
        self.steps.set_lines(
            [f"{index}. {step}" for index, step in enumerate(procedure.steps, start=1)]
        )
        self.verification.set_lines(procedure.verification)
