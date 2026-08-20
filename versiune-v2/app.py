from __future__ import annotations

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from data import (
    ADAPTATION_PROCEDURES,
    CODING_PROCEDURES,
    SERVICE_PROCEDURES,
    ScanResult,
    default_scan,
)
from dtc_window import DTCWindow
from feature_windows import (
    GuidedProcedureWindow,
    LiveDataWindow,
    RepairGuideWindow,
    ReportWindow,
)
from scan_window import ScanWindow
from widgets import FeatureTile, StatusChip, TitleBar, VehicleHero

FEATURES = (
    ("scan", "SCANARE AUTO", "Toate modulele", 0),
    ("dtc", "ERORI DTC", "Cauze și reparații", 1),
    ("coding", "CODĂRI", "Proceduri ghidate", 2),
    ("adaptation", "ADAPTĂRI", "Calibrări și inițializări", 3),
    ("service", "SERVICE", "Resetări și mentenanță", 4),
    ("live", "DATE LIVE", "Grafice și parametri", 5),
    ("repair", "GHID REPARAȚII", "Piese, verificări, pași", 6),
    ("reports", "RAPOARTE PDF", "Export profesional", 7),
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("KID VAG MASTER — Diagnostic PRO V2")
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(1536, 920)
        self.setMinimumSize(1260, 780)
        self.scan: ScanResult = default_scan()
        self.windows: dict[str, QMainWindow] = {}

        outer = QWidget()
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(8, 8, 8, 8)
        outer_layout.setSpacing(0)
        self.shell = QFrame()
        self.shell.setObjectName("appShell")
        outer_layout.addWidget(self.shell)
        self.setCentralWidget(outer)

        layout = QVBoxLayout(self.shell)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.title_bar = TitleBar(self)
        self.interface_chip = StatusChip("◉", "MOD DEMO", "warn")
        self.voltage_chip = StatusChip("▣", "13.8 V", "info")
        self.title_bar.add_status_widget(self.interface_chip)
        self.title_bar.add_status_widget(self.voltage_chip)
        layout.addWidget(self.title_bar)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(18, 14, 18, 12)
        content_layout.setSpacing(14)
        self.hero = VehicleHero(self.scan.vehicle)
        content_layout.addWidget(self.hero)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)
        for index, (key, title, subtitle, image_index) in enumerate(FEATURES):
            tile = FeatureTile(key, title, subtitle, image_index)
            tile.clicked.connect(self.open_feature)
            row, column = divmod(index, 4)
            grid.addWidget(tile, row, column)
            grid.setColumnStretch(column, 1)
        content_layout.addLayout(grid, 1)
        layout.addWidget(content, 1)
        layout.addWidget(self._build_footer())

    def _build_footer(self) -> QFrame:
        footer = QFrame()
        footer.setObjectName("footerBar")
        footer.setFixedHeight(58)
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(19, 7, 15, 7)
        layout.setSpacing(25)

        def group(caption: str, value: str) -> QVBoxLayout:
            box = QVBoxLayout()
            box.setSpacing(0)
            caption_label = QLabel(caption)
            caption_label.setObjectName("footerCaption")
            value_label = QLabel(value)
            value_label.setObjectName("footerValue")
            box.addWidget(caption_label)
            box.addWidget(value_label)
            return box

        layout.addLayout(group("Tehnician", "MOD EXPERT GHIDAT"))
        layout.addStretch(1)
        layout.addLayout(group("Sursă date", "AUTO-SCAN / DEMO"))
        layout.addLayout(group("Bază locală", "V2 • ROMÂNĂ"))
        layout.addLayout(group("Siguranță", "BACKUP ÎNAINTE DE CODARE"))
        settings = QPushButton("⚙  SETĂRI")
        settings.clicked.connect(self.show_settings)
        layout.addWidget(settings)
        return footer

    def open_feature(self, key: str) -> None:
        window = self.windows.get(key)
        if window is None:
            window = self._create_feature_window(key)
            self.windows[key] = window
        if hasattr(window, "set_scan"):
            window.set_scan(self.scan)  # type: ignore[attr-defined]
        if window.isMinimized():
            window.showNormal()
        window.show()
        window.raise_()
        window.activateWindow()
        self._position_window(window, key)

    def _create_feature_window(self, key: str) -> QMainWindow:
        if key == "scan":
            window = ScanWindow(self.scan, self)
            window.scan_loaded.connect(self.handle_scan_loaded)
            window.dtc_requested.connect(lambda: self.open_feature("dtc"))
            window.report_requested.connect(lambda: self.open_feature("reports"))
            return window
        if key == "dtc":
            return DTCWindow(self.scan, self)
        if key == "coding":
            return GuidedProcedureWindow(
                "Codări",
                "Proceduri filtrate după modul și platformă, cu backup și verificare după modificare.",
                CODING_PROCEDURES,
                self,
            )
        if key == "adaptation":
            return GuidedProcedureWindow(
                "Adaptări",
                "Calibrări și inițializări explicate pas cu pas, fără valori universale riscante.",
                ADAPTATION_PROCEDURES,
                self,
            )
        if key == "service":
            return GuidedProcedureWindow(
                "Service",
                "Funcții de întreținere cu condiții, pași, criterii de succes și avertizări.",
                SERVICE_PROCEDURES,
                self,
            )
        if key == "live":
            return LiveDataWindow(self)
        if key == "repair":
            return RepairGuideWindow(self)
        if key == "reports":
            return ReportWindow(self.scan, self)
        raise KeyError(key)

    def _position_window(self, window: QMainWindow, key: str) -> None:
        if not window.isVisible():
            return
        offsets = {
            "scan": (90, 45),
            "dtc": (135, 70),
            "coding": (70, 55),
            "adaptation": (105, 65),
            "service": (120, 50),
            "live": (85, 60),
            "repair": (110, 65),
            "reports": (140, 75),
        }
        offset = offsets.get(key, (80, 50))
        origin = self.frameGeometry().topLeft()
        current_screen = self.screen().availableGeometry()
        target = QPoint(origin.x() + offset[0], origin.y() + offset[1])
        if target.x() + window.width() > current_screen.right():
            target.setX(max(current_screen.left(), current_screen.right() - window.width()))
        if target.y() + window.height() > current_screen.bottom():
            target.setY(max(current_screen.top(), current_screen.bottom() - window.height()))
        window.move(target)

    def handle_scan_loaded(self, scan: ScanResult) -> None:
        self.scan = scan
        self.hero.set_vehicle(scan.vehicle)
        self.interface_chip.set_status("AUTO-SCAN IMPORTAT", "ok", "✓")
        for key in ("dtc", "reports", "scan"):
            window = self.windows.get(key)
            if window is not None and hasattr(window, "set_scan"):
                window.set_scan(scan)  # type: ignore[attr-defined]

    def show_settings(self) -> None:
        QMessageBox.information(
            self,
            "Setări V2",
            "Versiunea V2 rulează în mod sigur de import și demonstrație.\n\n"
            "• Auto-Scan VCDS: activ\n"
            "• Raport PDF: activ\n"
            "• Ghiduri locale: active\n"
            "• Scriere directă în ECU: dezactivată până la validarea driverului\n"
            "• Interfață hardware: etapă viitoare separată",
        )

    def closeEvent(self, event) -> None:  # type: ignore[override]
        for window in self.windows.values():
            window.close()
        super().closeEvent(event)
