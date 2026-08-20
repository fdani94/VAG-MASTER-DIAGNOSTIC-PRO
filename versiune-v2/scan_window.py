from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from data import ModuleResult, ScanResult
from parser import parse_autoscan_file
from window_base import DetachedWindow, page_header


class ScanWindow(DetachedWindow):
    scan_loaded = Signal(object)
    dtc_requested = Signal()
    report_requested = Signal()

    def __init__(self, scan: ScanResult, parent=None):
        super().__init__("Scanare completă", (980, 760), parent)
        self.scan = scan
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(18, 17, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(
            page_header(
                "SCANARE COMPLETĂ",
                "Importă un Auto-Scan VCDS TXT, LOG sau PDF. Aplicația păstrează structura pe module și verifică automat numărul erorilor.",
            )
        )

        action_row = QHBoxLayout()
        self.import_button = QPushButton("IMPORTĂ AUTO-SCAN")
        self.import_button.setObjectName("accentButton")
        self.import_button.clicked.connect(self.import_scan)
        self.dtc_button = QPushButton("DESCHIDE ERORILE")
        self.dtc_button.clicked.connect(self.dtc_requested.emit)
        self.report_button = QPushButton("RAPORT PDF")
        self.report_button.clicked.connect(self.report_requested.emit)
        action_row.addWidget(self.import_button)
        action_row.addStretch(1)
        action_row.addWidget(self.dtc_button)
        action_row.addWidget(self.report_button)
        layout.addLayout(action_row)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Adresă", "Modul", "Număr piesă / componentă", "Stare", "DTC"])
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.doubleClicked.connect(lambda index: self.dtc_requested.emit())
        layout.addWidget(self.table, 1)

        status_row = QHBoxLayout()
        self.status_label = QLabel()
        self.status_label.setObjectName("pageSubtitle")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setFixedWidth(300)
        self.percent = QLabel("100%")
        status_row.addWidget(self.status_label, 1)
        status_row.addWidget(self.progress)
        status_row.addWidget(self.percent)
        layout.addLayout(status_row)
        self.setCentralWidget(root)
        self.set_scan(scan)

    def set_scan(self, scan: ScanResult) -> None:
        self.scan = scan
        self.table.setRowCount(len(scan.modules))
        for row, module in enumerate(scan.modules):
            self._set_module_row(row, module)
        self.progress.setValue(100 if scan.modules else 0)
        self.percent.setText(f"{self.progress.value()}%")
        if scan.modules:
            self.status_label.setText(
                f"{scan.source_name} • {len(scan.modules)} module unice • {scan.total_dtc} DTC\n"
                f"{scan.validation_message}"
            )
        else:
            self.status_label.setText("Așteaptă importul unui Auto-Scan VCDS TXT, LOG sau PDF.")
        self.dtc_button.setEnabled(bool(scan.faults))
        self.report_button.setEnabled(bool(scan.modules))

    def _set_module_row(self, row: int, module: ModuleResult) -> None:
        identity = " • ".join(value for value in (module.part_no, module.component) if value) or "Nedetectat"
        values = (module.address, module.name, identity, module.status, str(module.dtc_count))
        for column, value in enumerate(values):
            item = QTableWidgetItem(value)
            item.setTextAlignment(
                Qt.AlignmentFlag.AlignVCenter
                | (Qt.AlignmentFlag.AlignCenter if column in (0, 3, 4) else Qt.AlignmentFlag.AlignLeft)
            )
            if column in (3, 4):
                if module.dtc_count:
                    item.setForeground(QColor("#ffb43d"))
                elif module.status.upper() == "OK":
                    item.setForeground(QColor("#45d48a"))
            self.table.setItem(row, column, item)

    def import_scan(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Selectează Auto-Scan VCDS",
            str(Path.home()),
            "Auto-Scan VCDS (*.txt *.log *.csv *.pdf);;PDF VCDS (*.pdf);;Fișiere text (*.txt *.log *.csv);;Toate fișierele (*.*)",
        )
        if not path:
            return
        try:
            scan = parse_autoscan_file(path)
        except Exception as exc:  # noqa: BLE001 - malformed external files must not close the UI.
            QMessageBox.critical(self, "Import nereușit", f"Fișierul nu a putut fi analizat.\n\n{exc}")
            return
        self.set_scan(scan)
        self.scan_loaded.emit(scan)
