from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
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
        self._simulation_row = 0
        self._simulation_modules: list[ModuleResult] = []
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._simulation_step)

        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(18, 17, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(
            page_header(
                "SCANARE COMPLETĂ",
                "Importă un Auto-Scan VCDS existent sau rulează demonstrația vizuală a fluxului V2.",
            )
        )

        action_row = QHBoxLayout()
        self.import_button = QPushButton("IMPORTĂ AUTO-SCAN")
        self.import_button.setObjectName("accentButton")
        self.import_button.clicked.connect(self.import_scan)
        self.demo_button = QPushButton("RULEAZĂ DEMO")
        self.demo_button.clicked.connect(self.run_demo)
        self.dtc_button = QPushButton("DESCHIDE ERORILE")
        self.dtc_button.clicked.connect(self.dtc_requested.emit)
        self.report_button = QPushButton("RAPORT PDF")
        self.report_button.clicked.connect(self.report_requested.emit)
        action_row.addWidget(self.import_button)
        action_row.addWidget(self.demo_button)
        action_row.addStretch(1)
        action_row.addWidget(self.dtc_button)
        action_row.addWidget(self.report_button)
        layout.addLayout(action_row)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Adresă", "Modul", "Stare", "DTC"])
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
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
        self.status_label.setText(
            f"{scan.source_name} • {len(scan.modules)} module • {scan.total_dtc} DTC"
        )
        self.dtc_button.setEnabled(bool(scan.dtc_codes or scan.total_dtc))

    def _set_module_row(self, row: int, module: ModuleResult) -> None:
        values = (module.address, module.name, module.status, str(module.dtc_count))
        for column, value in enumerate(values):
            item = QTableWidgetItem(value)
            item.setTextAlignment(
                Qt.AlignmentFlag.AlignVCenter
                | (Qt.AlignmentFlag.AlignCenter if column in (0, 2, 3) else Qt.AlignmentFlag.AlignLeft)
            )
            if column in (2, 3):
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
            "Auto-Scan VCDS (*.txt *.log *.csv);;Toate fișierele (*.*)",
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

    def run_demo(self) -> None:
        self.timer.stop()
        self._simulation_modules = list(self.scan.modules)
        self._simulation_row = 0
        self.table.setRowCount(len(self._simulation_modules))
        for row, module in enumerate(self._simulation_modules):
            self._set_module_row(row, ModuleResult(module.address, module.name, "În așteptare", 0))
        self.progress.setValue(0)
        self.percent.setText("0%")
        self.status_label.setText("Inițializare scanare demonstrativă...")
        self.import_button.setEnabled(False)
        self.demo_button.setEnabled(False)
        self.timer.start(180)

    def _simulation_step(self) -> None:
        if self._simulation_row >= len(self._simulation_modules):
            self.timer.stop()
            self.import_button.setEnabled(True)
            self.demo_button.setEnabled(True)
            self.set_scan(self.scan)
            return
        module = self._simulation_modules[self._simulation_row]
        self._set_module_row(self._simulation_row, module)
        self.table.selectRow(self._simulation_row)
        self.table.scrollToItem(self.table.item(self._simulation_row, 0))
        self._simulation_row += 1
        value = int(self._simulation_row * 100 / max(1, len(self._simulation_modules)))
        self.progress.setValue(value)
        self.percent.setText(f"{value}%")
        self.status_label.setText(f"Citire modul {module.address} — {module.name}")

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self.timer.stop()
        super().closeEvent(event)
