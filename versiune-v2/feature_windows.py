from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
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

from data import (
    DTCInfo,
    DTCSearchHit,
    GuidedProcedure,
    ScanResult,
    dtc_info,
    search_dtc_infos,
)
from database import get_database
from localization import romanianize
from reporting import create_diagnostic_pdf
from widgets import SectionCard
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
        badge = QLabel(f"{len(procedures)} PROCEDURI • NU SCRIE ÎN ECU")
        badge.setObjectName("successBox")
        header_row.addWidget(badge, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addLayout(header_row)
        layout.addWidget(ProcedureBrowser(procedures), 1)
        self.setCentralWidget(root)


class MetricCard(QFrame):
    def __init__(self, title: str, value: str, unit: str, accent: str = "#2bc2ff"):
        super().__init__()
        self.setObjectName("sectionCard")
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


def _freeze_pairs(scan: ScanResult) -> list[tuple[str, str, str, str]]:
    rows: list[tuple[str, str, str, str]] = []
    for fault in scan.faults:
        seen: set[tuple[str, str]] = set()
        block = fault.freeze_frame or fault.raw_block
        for line in block.splitlines():
            match = re.match(r"\s*([^:]{2,90}):\s*(.+?)\s*$", line)
            if not match:
                continue
            name, value = match.group(1).strip(), match.group(2).strip()
            if name.casefold() in {"freeze frame", "fault status"}:
                continue
            key = (name.casefold(), value)
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                (
                    fault.display_code,
                    fault.module_address,
                    romanianize(name),
                    romanianize(value),
                )
            )
    return rows


def _first_value(rows: list[tuple[str, str, str, str]], terms: tuple[str, ...]) -> str:
    for _, _, name, value in rows:
        low = name.casefold()
        if any(term in low for term in terms):
            return value
    return "—"


class LiveDataWindow(DetachedWindow):
    """Afișează exclusiv valori reale memorate în Auto-Scan."""

    def __init__(self, scan: ScanResult, parent=None):
        super().__init__("Valori măsurate", (1120, 770), parent)
        self.scan = scan
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(18, 17, 18, 18)
        layout.setSpacing(12)
        header_row = QHBoxLayout()
        header_row.addWidget(
            page_header(
                "VALORI MĂSURATE ȘI DATE MEMORATE LA EROARE",
                "Parametri extrași direct din Auto-Scan-ul VCDS. Aplicația nu generează și nu simulează date.",
            ),
            1,
        )
        self.mode = QLabel("SURSĂ: AUTO-SCAN VCDS")
        self.mode.setObjectName("successBox")
        header_row.addWidget(self.mode, alignment=Qt.AlignmentFlag.AlignTop)
        layout.addLayout(header_row)

        metrics = QGridLayout()
        metrics.setSpacing(10)
        self.rpm = MetricCard("Turație la memorare", "—", "")
        self.voltage = MetricCard("Tensiune terminal 30", "—", "", "#45d58a")
        self.coolant = MetricCard("Temperatură lichid", "—", "", "#ffb43c")
        self.mileage = MetricCard("Kilometraj la memorare", "—", "")
        for index, card in enumerate((self.rpm, self.voltage, self.coolant, self.mileage)):
            metrics.addWidget(card, 0, index)
        layout.addLayout(metrics)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["DTC", "Modul", "Parametru VCDS", "Valoare"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table, 1)
        self.guidance = SectionCard(
            "i",
            "Interpretare profesională",
            [
                "Valorile afișate reprezintă momentul memorării erorii, nu un flux actual de la vehicul.",
                "Comparați valorile solicitate și reale în VCDS, în aceleași condiții de sarcină și temperatură.",
                "Un -273,1 °C sau altă valoare-limită poate indica un semnal absent ori o valoare implicită a unității.",
            ],
        )
        layout.addWidget(self.guidance)
        self.setCentralWidget(root)
        self.set_scan(scan)

    def set_scan(self, scan: ScanResult) -> None:
        self.scan = scan
        rows = _freeze_pairs(scan)
        self.table.setRowCount(len(rows))
        for row_index, values in enumerate(rows):
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setForeground(QColor("#ffb43c"))
                self.table.setItem(row_index, column, item)
        self.rpm.value.setText(_first_value(rows, ("engine speed", "crankshaft speed", "rpm", "turație")))
        self.voltage.value.setText(_first_value(rows, ("voltage terminal", "vehicle voltage", "tensiune")))
        self.coolant.value.setText(_first_value(rows, ("coolant temperature", "temperatură lichid")))
        self.mileage.value.setText(_first_value(rows, ("mileage", "kilometerstand", "kilometraj")))
        if rows:
            self.mode.setText(f"{len(rows)} VALORI EXTRASE DIN PDF/TXT")
        else:
            self.mode.setText("NICIO VALOARE MEMORATĂ ÎN RAPORT")


class RepairGuideWindow(DetachedWindow):
    def __init__(self, parent=None):
        super().__init__("Ghid reparații", (1160, 820), parent)
        self.current_results: list[DTCSearchHit] = []
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(18, 17, 18, 18)
        layout.setSpacing(12)
        stats = get_database().stats()
        layout.addWidget(
            page_header(
                "GHID REPARAȚII",
                f"Caută în {stats['DTC']:,} DTC. Fișele VAG detaliate au prioritate față de definițiile standard de catalog.".replace(",", "."),
            )
        )
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 4, 0)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Caută P0401, EGR, pompă, turbo, CAN, ușă...")
        self.search.textChanged.connect(self.refresh)
        self.count = QLabel()
        self.count.setObjectName("pageSubtitle")
        self.list = QListWidget()
        self.list.setMinimumWidth(340)
        self.list.currentItemChanged.connect(self.selection_changed)
        left_layout.addWidget(self.search)
        left_layout.addWidget(self.count)
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
        self.component = SectionCard("C", "Componentă / sistem implicat", [])
        self.symptoms = SectionCard("i", "Simptome posibile", [])
        self.location = SectionCard("⌖", "Unde se află piesa", [])
        self.causes = SectionCard("!", "Cauze posibile", [])
        self.checks = SectionCard("⌕", "Cum confirmi defectul", [])
        self.measurements = SectionCard("≈", "Parametri și traseu VCDS", [])
        self.repairs = SectionCard("⚒", "Ordinea corectă a reparației", [])
        self.source = SectionCard("S", "Sursă și nivel de confirmare", [])
        self.caution = QLabel()
        self.caution.setObjectName("safetyBox")
        self.caution.setWordWrap(True)
        for widget in (
            self.code,
            self.title,
            self.summary,
            self.caution,
            self.component,
            self.symptoms,
            self.location,
            self.causes,
            self.checks,
            self.measurements,
            self.repairs,
            self.source,
        ):
            detail_layout.addWidget(widget)
        detail_layout.addStretch(1)
        scroll.setWidget(detail)
        splitter.addWidget(scroll)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter, 1)
        self.setCentralWidget(root)
        self.refresh()

    def refresh(self) -> None:
        current_code = (
            self.list.currentItem().data(Qt.ItemDataRole.UserRole)
            if self.list.currentItem()
            else None
        )
        query = self.search.text().strip()
        self.current_results = search_dtc_infos(query, 500)
        self.list.clear()
        selected: QListWidgetItem | None = None
        for info in self.current_results:
            item = QListWidgetItem(
                f"{info.code} {'✓' if info.verified else '○'}\n{info.title}"
            )
            item.setData(Qt.ItemDataRole.UserRole, info.code)
            item.setToolTip(info.summary)
            self.list.addItem(item)
            if info.code == current_code:
                selected = item
        self.count.setText(
            f"{len(self.current_results)} rezultate afișate"
            + (" • rafinați căutarea" if len(self.current_results) >= 500 else "")
        )
        if selected:
            self.list.setCurrentItem(selected)
        elif self.list.count():
            self.list.setCurrentRow(0)
        else:
            self._show_empty()

    def selection_changed(
        self,
        current: QListWidgetItem | None,
        previous: QListWidgetItem | None,
    ) -> None:
        if current is None:
            return
        self.show_info(dtc_info(current.data(Qt.ItemDataRole.UserRole)))

    def show_info(self, info: DTCInfo) -> None:
        self.code.setText(info.code)
        self.title.setText(info.title)
        self.summary.setText(info.summary)
        self.caution.setText(f"ATENȚIE: {info.warning}")
        self.component.set_lines([info.component])
        self.symptoms.set_lines(info.symptoms)
        self.location.set_lines([info.location])
        self.causes.set_lines(info.causes)
        self.checks.set_lines(info.checks)
        self.measurements.set_lines(
            [
                f"Cale VCDS: {info.test_path}",
                f"Parametri: {info.parameters}",
                f"Valori așteptate: {info.expected}",
            ]
        )
        self.repairs.set_lines(info.repairs + info.replacement)
        self.source.set_lines(
            [
                f"Nivel: {'Fișă VAG verificată' if info.verified else 'Definiție standard - confirmați pe vehicul'}",
                f"Sursă: {info.source_title or 'Catalog local KID Diagnostic'}",
                f"Referință: {info.source_url or 'În baza locală'}",
            ]
        )

    def _show_empty(self) -> None:
        self.code.setText("0 rezultate")
        self.title.setText("Nu a fost găsit niciun cod")
        self.summary.setText("Încercați codul exact sau un termen tehnic mai scurt.")
        self.caution.clear()
        for card in (
            self.component,
            self.symptoms,
            self.location,
            self.causes,
            self.checks,
            self.measurements,
            self.repairs,
            self.source,
        ):
            card.set_lines([])


class ReportWindow(DetachedWindow):
    def __init__(self, scan: ScanResult, parent=None):
        super().__init__("Rapoarte PDF", (1020, 760), parent)
        self.scan = scan
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(18, 17, 18, 18)
        layout.setSpacing(12)
        header_row = QHBoxLayout()
        header_row.addWidget(
            page_header(
                "RAPORT PDF DE ATELIER",
                "Raport profesional cu identificare vehicul, validarea importului, module, prioritizare DTC, date memorate, verificări, reparații și surse.",
            ),
            1,
        )
        self.export_button = QPushButton("GENEREAZĂ RAPORTUL DETALIAT")
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

        self.validation = QLabel()
        self.validation.setObjectName("successBox")
        self.validation.setWordWrap(True)
        layout.addWidget(self.validation)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Adresă", "Modul", "Număr piesă", "Stare", "DTC"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
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
        self.validation.setText(scan.validation_message)
        self.export_button.setEnabled(bool(scan.modules))
        self.table.setRowCount(len(scan.modules))
        for row, module in enumerate(scan.modules):
            values = (
                module.address,
                module.name,
                module.part_no or "Nedetectat",
                module.status,
                str(module.dtc_count),
            )
            for column, text in enumerate(values):
                item = QTableWidgetItem(text)
                if column in (3, 4) and module.dtc_count:
                    item.setForeground(QColor("#ffb43c"))
                self.table.setItem(row, column, item)

    def export_pdf(self) -> None:
        vin = re.sub(r"[^A-Z0-9_-]", "_", self.scan.vehicle.vin.upper()) or "vehicul"
        date = datetime.now().strftime("%Y%m%d_%H%M")
        suggested = f"Raport_KID_VAG_{vin}_{date}.pdf"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Salvează raportul PDF",
            str(Path.home() / suggested),
            "Document PDF (*.pdf)",
        )
        if not path:
            return
        if not path.casefold().endswith(".pdf"):
            path += ".pdf"
        try:
            result = create_diagnostic_pdf(path, self.scan)
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Raport nereușit",
                f"PDF-ul nu a putut fi generat.\n\n{exc}",
            )
            return
        self.last_file.setText(f"Ultimul raport: {result}")
        choice = QMessageBox.question(
            self,
            "Raport generat",
            "Raportul detaliat a fost creat cu succes. Doriți să îl deschideți acum?",
        )
        if choice == QMessageBox.StandardButton.Yes:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(result)))
