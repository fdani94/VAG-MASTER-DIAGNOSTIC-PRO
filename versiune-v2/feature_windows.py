from __future__ import annotations

import math
import random
from collections.abc import Sequence
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from data import DTC_DATABASE, GuidedProcedure, ScanResult, dtc_info
from reporting import create_diagnostic_pdf
from widgets import LiveChart, SectionCard
from window_base import DetachedWindow, ProcedureBrowser, page_header


class GuidedProcedureWindow(DetachedWindow):
    def __init__(
        self,
        title: str,
        subtitle: str,
        procedures: Sequence[GuidedProcedure],
        parent=None,
    ):
        super().__init__(title, (1100, 780), parent)
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(18, 17, 18, 18)
        layout.setSpacing(12)
        header_row = QHBoxLayout()
        header_row.addWidget(page_header(title.upper(), subtitle), 1)
        badge = QLabel("GHID LOCAL • NU SCRIE ÎN ECU")
        badge.setObjectName("successBox")
        header_row.addWidget(badge, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addLayout(header_row)
        layout.addWidget(ProcedureBrowser(procedures), 1)
        self.setCentralWidget(root)


class MetricCard(QFrame):
    def __init__(self, title: str, value: str, unit: str, accent: str = "#2bc2ff"):
        super().__init__()
        self.setObjectName("sectionCard")
        self.accent = accent
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 11, 14, 12)
        layout.setSpacing(2)
        caption = QLabel(title)
        caption.setObjectName("pageSubtitle")
        value_row = QHBoxLayout()
        self.value = QLabel(value)
        self.value.setStyleSheet(f"font-size:26px;font-weight:800;color:{accent}")
        unit_label = QLabel(unit)
        unit_label.setStyleSheet("color:#7990a4;font-size:11px")
        value_row.addWidget(self.value)
        value_row.addWidget(unit_label, alignment=Qt.AlignmentFlag.AlignBottom)
        value_row.addStretch(1)
        layout.addWidget(caption)
        layout.addLayout(value_row)


class LiveDataWindow(DetachedWindow):
    def __init__(self, parent=None):
        super().__init__("Date live", (1120, 770), parent)
        self._phase = 0.0
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(18, 17, 18, 18)
        layout.setSpacing(12)
        header_row = QHBoxLayout()
        header_row.addWidget(
            page_header(
                "DATE LIVE",
                "Panou demonstrativ pentru parametri măsurați. Conectarea hardware va fi activată numai printr-un driver validat.",
            ),
            1,
        )
        self.mode = QLabel("SURSĂ: DEMO")
        self.mode.setObjectName("safetyBox")
        header_row.addWidget(self.mode, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addLayout(header_row)

        metrics = QGridLayout()
        metrics.setSpacing(10)
        self.rpm = MetricCard("Turație motor", "825", "rpm")
        self.voltage = MetricCard("Tensiune terminal 30", "14.2", "V", "#45d58a")
        self.coolant = MetricCard("Temperatură lichid", "92", "°C", "#ffb43c")
        self.boost = MetricCard("Presiune supraalimentare", "1005", "mbar")
        for index, card in enumerate((self.rpm, self.voltage, self.coolant, self.boost)):
            metrics.addWidget(card, 0, index)
        layout.addLayout(metrics)

        content = QSplitter(Qt.Orientation.Horizontal)
        chart_panel = QFrame()
        chart_panel.setObjectName("sectionCard")
        chart_layout = QVBoxLayout(chart_panel)
        chart_header = QHBoxLayout()
        chart_title = QLabel("Presiune turbo: solicitată vs. reală")
        chart_title.setObjectName("sectionTitle")
        self.start_button = QPushButton("OPREȘTE")
        self.start_button.clicked.connect(self.toggle)
        chart_header.addWidget(chart_title)
        chart_header.addStretch(1)
        chart_header.addWidget(self.start_button)
        chart_layout.addLayout(chart_header)
        self.chart = LiveChart()
        chart_layout.addWidget(self.chart, 1)
        content.addWidget(chart_panel)

        self.table = QTableWidget(6, 3)
        self.table.setHorizontalHeaderLabels(["Parametru", "Valoare", "Stare"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        content.addWidget(self.table)
        content.setStretchFactor(0, 2)
        content.setStretchFactor(1, 1)
        layout.addWidget(content, 1)
        self.setCentralWidget(root)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_values)
        self.timer.start(350)
        self.update_values()

    def toggle(self) -> None:
        if self.timer.isActive():
            self.timer.stop()
            self.chart.timer.stop()
            self.start_button.setText("PORNEȘTE")
        else:
            self.timer.start(350)
            self.chart.timer.start(180)
            self.start_button.setText("OPREȘTE")

    def update_values(self) -> None:
        self._phase += 0.19
        rpm = int(825 + 110 * (1 + math.sin(self._phase * 0.6)))
        voltage = 14.15 + random.uniform(-0.08, 0.08)
        coolant = 91.5 + 1.5 * math.sin(self._phase * 0.25)
        boost = int(1000 + 160 * max(0.0, math.sin(self._phase)))
        self.rpm.value.setText(str(rpm))
        self.voltage.value.setText(f"{voltage:.1f}")
        self.coolant.value.setText(f"{coolant:.0f}")
        self.boost.value.setText(str(boost))
        values = (
            ("Turație motor", f"{rpm} rpm", "Plauzibil"),
            ("Tensiune baterie", f"{voltage:.2f} V", "OK"),
            ("Temperatură lichid", f"{coolant:.1f} °C", "OK"),
            ("Presiune turbo reală", f"{boost} mbar", "Urmărire"),
            ("Masă aer", f"{310 + random.uniform(-12, 12):.1f} mg/str", "Plauzibil"),
            ("Poziție EGR", f"{45 + 8 * math.sin(self._phase):.1f} %", "Urmărire"),
        )
        for row, (name, value, state) in enumerate(values):
            for column, text in enumerate((name, value, state)):
                item = QTableWidgetItem(text)
                if column == 2:
                    item.setForeground(QColor("#45d58a") if state in ("OK", "Plauzibil") else QColor("#2bc2ff"))
                self.table.setItem(row, column, item)


class RepairGuideWindow(DetachedWindow):
    def __init__(self, parent=None):
        super().__init__("Ghid reparații", (1120, 800), parent)
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(18, 17, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(
            page_header(
                "GHID REPARAȚII",
                "Caută după cod sau sistem pentru a vedea verificările, ordinea reparației și localizarea orientativă a piesei.",
            )
        )
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 4, 0)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Caută EGR, turbo, DPF, P0401...")
        self.search.textChanged.connect(self.refresh)
        self.list = QListWidget()
        self.list.setMinimumWidth(320)
        self.list.currentItemChanged.connect(self.selection_changed)
        left_layout.addWidget(self.search)
        left_layout.addWidget(self.list, 1)
        splitter.addWidget(left)

        scroll = QScrollArea()
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        detail = QWidget()
        detail_layout = QVBoxLayout(detail)
        detail_layout.setContentsMargins(14, 2, 10, 10)
        detail_layout.setSpacing(10)
        self.code = QLabel()
        self.code.setObjectName("dtcCode")
        self.title = QLabel()
        self.title.setObjectName("pageTitle")
        self.title.setWordWrap(True)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.location = SectionCard("⌖", "Unde se află piesa", [])
        self.checks = SectionCard("⌕", "Cum confirmi defectul", [])
        self.repairs = SectionCard("⚒", "Ordinea corectă a reparației", [])
        self.caution = QLabel()
        self.caution.setObjectName("safetyBox")
        self.caution.setWordWrap(True)
        detail_layout.addWidget(self.code)
        detail_layout.addWidget(self.title)
        detail_layout.addWidget(self.summary)
        detail_layout.addWidget(self.location)
        detail_layout.addWidget(self.checks)
        detail_layout.addWidget(self.repairs)
        detail_layout.addWidget(self.caution)
        detail_layout.addStretch(1)
        scroll.setWidget(detail)
        splitter.addWidget(scroll)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter, 1)
        self.setCentralWidget(root)
        self.refresh()

    def refresh(self) -> None:
        current_code = self.list.currentItem().data(Qt.ItemDataRole.UserRole) if self.list.currentItem() else None
        needle = self.search.text().strip().casefold()
        self.list.clear()
        for info in DTC_DATABASE.values():
            haystack = f"{info.code} {info.title} {info.system} {info.summary}".casefold()
            if needle and needle not in haystack:
                continue
            item = QListWidgetItem(f"{info.code}\n{info.title}")
            item.setData(Qt.ItemDataRole.UserRole, info.code)
            self.list.addItem(item)
            if info.code == current_code:
                self.list.setCurrentItem(item)
        if self.list.count() and self.list.currentRow() < 0:
            self.list.setCurrentRow(0)

    def selection_changed(self, current: QListWidgetItem | None, previous: QListWidgetItem | None) -> None:
        if current is None:
            return
        info = dtc_info(current.data(Qt.ItemDataRole.UserRole))
        self.code.setText(info.code)
        self.title.setText(info.title)
        self.summary.setText(info.summary)
        self.location.set_lines([info.location])
        self.checks.set_lines(info.checks)
        self.repairs.set_lines(info.repairs)
        self.caution.setText(f"ATENȚIE: {info.warning}")


class ReportWindow(DetachedWindow):
    def __init__(self, scan: ScanResult, parent=None):
        super().__init__("Rapoarte PDF", (980, 740), parent)
        self.scan = scan
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(18, 17, 18, 18)
        layout.setSpacing(12)
        header_row = QHBoxLayout()
        header_row.addWidget(
            page_header(
                "RAPOARTE PDF",
                "Raport profesional cu vehicul, module, coduri DTC, verificări și recomandări de reparație.",
            ),
            1,
        )
        self.export_button = QPushButton("GENEREAZĂ PDF")
        self.export_button.setObjectName("accentButton")
        self.export_button.clicked.connect(self.export_pdf)
        header_row.addWidget(self.export_button, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addLayout(header_row)

        metrics = QGridLayout()
        metrics.setSpacing(10)
        self.vehicle_card = MetricCard("Vehicul", scan.vehicle.display_name, "")
        self.modules_card = MetricCard("Module scanate", str(len(scan.modules)), "module")
        self.dtc_card = MetricCard("Erori identificate", str(scan.total_dtc), "DTC", "#ffb43c")
        metrics.addWidget(self.vehicle_card, 0, 0)
        metrics.addWidget(self.modules_card, 0, 1)
        metrics.addWidget(self.dtc_card, 0, 2)
        layout.addLayout(metrics)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Adresă", "Modul", "Stare", "DTC"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self.table, 1)
        self.last_file = QLabel("Niciun raport generat în această sesiune.")
        self.last_file.setObjectName("pageSubtitle")
        self.last_file.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.last_file)
        self.setCentralWidget(root)
        self.set_scan(scan)

    def set_scan(self, scan: ScanResult) -> None:
        self.scan = scan
        self.vehicle_card.value.setText(scan.vehicle.display_name)
        self.modules_card.value.setText(str(len(scan.modules)))
        self.dtc_card.value.setText(str(scan.total_dtc))
        self.table.setRowCount(len(scan.modules))
        for row, module in enumerate(scan.modules):
            for column, text in enumerate((module.address, module.name, module.status, str(module.dtc_count))):
                item = QTableWidgetItem(text)
                if column in (2, 3) and module.dtc_count:
                    item.setForeground(QColor("#ffb43c"))
                self.table.setItem(row, column, item)

    def export_pdf(self) -> None:
        vin = self.scan.vehicle.vin.replace(" ", "_") or "vehicul"
        suggested = f"Raport_VAG_{vin}.pdf"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Salvează raportul PDF",
            str(Path.home() / suggested),
            "Document PDF (*.pdf)",
        )
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        try:
            result = create_diagnostic_pdf(path, self.scan)
        except Exception as exc:  # noqa: BLE001 - UI boundary must surface PDF errors.
            QMessageBox.critical(self, "Raport nereușit", f"PDF-ul nu a putut fi generat.\n\n{exc}")
            return
        self.last_file.setText(f"Ultimul raport: {result}")
        choice = QMessageBox.question(
            self,
            "Raport generat",
            "Raportul a fost creat cu succes. Doriți să îl deschideți acum?",
        )
        if choice == QMessageBox.StandardButton.Yes:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(result)))
