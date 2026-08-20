from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QPoint, QRectF, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QLinearGradient,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


def resource_path(relative: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / relative


_SPRITE: QPixmap | None = None
_SPRITE_CELLS: dict[int, QPixmap] = {}


def sprite_cell(index: int) -> QPixmap:
    global _SPRITE
    index = max(0, min(7, index))
    if index in _SPRITE_CELLS:
        return _SPRITE_CELLS[index]
    if _SPRITE is None:
        _SPRITE = QPixmap(str(resource_path("assets/diagnostic_tiles.jpg")))
    if _SPRITE.isNull():
        return QPixmap()
    width = _SPRITE.width() // 4
    height = _SPRITE.height() // 2
    row, column = divmod(index, 4)
    cell = _SPRITE.copy(column * width, row * height, width, height)
    _SPRITE_CELLS[index] = cell
    return cell


class AspectPixmapLabel(QLabel):
    def __init__(self, pixmap: QPixmap | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self._source = pixmap or QPixmap()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_source(self, pixmap: QPixmap) -> None:
        self._source = pixmap
        self._refresh()

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._refresh()

    def _refresh(self) -> None:
        if self._source.isNull() or self.width() < 2 or self.height() < 2:
            return
        scaled = self._source.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.setPixmap(scaled)


class BrandMark(QWidget):
    def __init__(self, size: int = 42, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedSize(size, size)

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(4, 4, self.width() - 8, self.height() - 8)
        gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
        gradient.setColorAt(0, QColor("#e7f7ff"))
        gradient.setColorAt(0.45, QColor("#4fc5ff"))
        gradient.setColorAt(1, QColor("#1c5681"))
        path = QPainterPath()
        path.moveTo(rect.left(), rect.top() + rect.height() * 0.15)
        path.lineTo(rect.left() + rect.width() * 0.36, rect.bottom())
        path.lineTo(rect.center().x(), rect.bottom() - rect.height() * 0.29)
        path.lineTo(rect.left() + rect.width() * 0.64, rect.bottom())
        path.lineTo(rect.right(), rect.top() + rect.height() * 0.15)
        path.lineTo(rect.left() + rect.width() * 0.67, rect.top() + rect.height() * 0.44)
        path.lineTo(rect.center().x(), rect.top() + rect.height() * 0.68)
        path.lineTo(rect.left() + rect.width() * 0.33, rect.top() + rect.height() * 0.44)
        path.closeSubpath()
        painter.fillPath(path, gradient)
        painter.setPen(QPen(QColor("#bfeaff"), 1.0))
        painter.drawPath(path)


class StatusChip(QFrame):
    def __init__(self, icon: str, text: str, state: str = "info", parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("statusChip")
        self.setProperty("state", state)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(11, 5, 11, 5)
        layout.setSpacing(7)
        self.icon_label = QLabel(icon)
        self.icon_label.setStyleSheet("color:#42caff;font-weight:800")
        self.text_label = QLabel(text)
        self.text_label.setStyleSheet("font-size:11px;color:#c9d8e5")
        layout.addWidget(self.icon_label)
        layout.addWidget(self.text_label)

    def set_status(self, text: str, state: str = "info", icon: str | None = None) -> None:
        self.text_label.setText(text)
        if icon is not None:
            self.icon_label.setText(icon)
        self.setProperty("state", state)
        self.style().unpolish(self)
        self.style().polish(self)


class TitleBar(QFrame):
    def __init__(self, window: QWidget, subtitle: str = "DIAGNOSTIC PRO V2"):
        super().__init__(window)
        self.window = window
        self.setObjectName("titleBar")
        self.setFixedHeight(66)
        self._drag_position = QPoint()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(17, 8, 12, 8)
        layout.setSpacing(12)
        layout.addWidget(BrandMark(42))

        title_box = QVBoxLayout()
        title_box.setSpacing(0)
        title = QLabel("KID VAG MASTER")
        title.setObjectName("brandTitle")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("brandSubtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle_label)
        layout.addLayout(title_box)
        layout.addStretch(1)

        self.status_area = QHBoxLayout()
        self.status_area.setSpacing(8)
        layout.addLayout(self.status_area)

        self.minimize = QPushButton("−")
        self.minimize.setObjectName("windowButton")
        self.maximize = QPushButton("□")
        self.maximize.setObjectName("windowButton")
        self.close = QPushButton("×")
        self.close.setObjectName("closeButton")
        self.minimize.clicked.connect(window.showMinimized)
        self.maximize.clicked.connect(self._toggle_maximize)
        self.close.clicked.connect(window.close)
        layout.addWidget(self.minimize)
        layout.addWidget(self.maximize)
        layout.addWidget(self.close)

    def add_status_widget(self, widget: QWidget) -> None:
        self.status_area.addWidget(widget)

    def _toggle_maximize(self) -> None:
        if self.window.isMaximized():
            self.window.showNormal()
            self.maximize.setText("□")
        else:
            self.window.showMaximized()
            self.maximize.setText("❐")

    def mousePressEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            handle = self.window.windowHandle()
            if handle and hasattr(handle, "startSystemMove"):
                handle.startSystemMove()
            else:
                self._drag_position = event.globalPosition().toPoint() - self.window.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        if (
            event.buttons() & Qt.MouseButton.LeftButton
            and not self.window.isMaximized()
            and not self._drag_position.isNull()
        ):
            self.window.move(event.globalPosition().toPoint() - self._drag_position)
        super().mouseMoveEvent(event)


class FeatureTile(QFrame):
    clicked = Signal(str)

    def __init__(
        self,
        key: str,
        title: str,
        subtitle: str,
        image_index: int,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.key = key
        self.setObjectName("featureTile")
        self.setProperty("hovered", False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumSize(215, 210)
        self.setToolTip(f"Deschide {title}")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 12)
        layout.setSpacing(4)

        image = AspectPixmapLabel(sprite_cell(image_index))
        image.setMinimumHeight(135)
        layout.addWidget(image, 1)

        title_label = QLabel(title)
        title_label.setObjectName("tileTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("tileSubtitle")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        line = QLabel()
        line.setObjectName("accentLine")
        line.setFixedWidth(35)

        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        line_row = QHBoxLayout()
        line_row.addStretch(1)
        line_row.addWidget(line)
        line_row.addStretch(1)
        layout.addLayout(line_row)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(22)
        shadow.setOffset(0, 5)
        shadow.setColor(QColor(0, 0, 0, 115))
        self.setGraphicsEffect(shadow)

    def enterEvent(self, event) -> None:  # type: ignore[override]
        self.setProperty("hovered", True)
        self.style().unpolish(self)
        self.style().polish(self)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        self.setProperty("hovered", False)
        self.style().unpolish(self)
        self.style().polish(self)
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            self.clicked.emit(self.key)
        super().mouseReleaseEvent(event)


class HeroMetric(QFrame):
    def __init__(self, caption: str, value: str):
        super().__init__()
        self.setObjectName("heroMetric")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(11, 7, 11, 7)
        layout.setSpacing(1)
        caption_label = QLabel(caption)
        caption_label.setObjectName("metricCaption")
        self.value_label = QLabel(value)
        self.value_label.setObjectName("metricValue")
        layout.addWidget(caption_label)
        layout.addWidget(self.value_label)


class VehicleHero(QFrame):
    def __init__(self, vehicle, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("vehicleHero")
        self.setMinimumHeight(176)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 15, 18, 15)
        layout.setSpacing(20)

        roundel = QFrame()
        roundel.setObjectName("brandRoundel")
        roundel.setFixedSize(62, 62)
        roundel_layout = QVBoxLayout(roundel)
        roundel_layout.setContentsMargins(0, 0, 0, 0)
        self.brand_label = QLabel("VAG")
        self.brand_label.setObjectName("brandRoundelText")
        self.brand_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        roundel_layout.addWidget(self.brand_label)
        layout.addWidget(roundel, alignment=Qt.AlignmentFlag.AlignTop)

        info = QVBoxLayout()
        info.setSpacing(6)
        self.name_label = QLabel(vehicle.display_name)
        self.name_label.setObjectName("vehicleName")
        self.subtitle_label = QLabel(vehicle.subtitle)
        self.subtitle_label.setObjectName("vehicleSubtitle")
        info.addWidget(self.name_label)
        info.addWidget(self.subtitle_label)
        info.addStretch(1)
        metric_row = QHBoxLayout()
        metric_row.setSpacing(8)
        self.vin_metric = HeroMetric("VIN", vehicle.vin or "—")
        self.mileage_metric = HeroMetric(
            "Kilometraj",
            f"{vehicle.mileage_km:,} km".replace(",", ".") if vehicle.mileage_km else "—",
        )
        self.module_metric = HeroMetric("ECU", f"{vehicle.modules} module")
        metric_row.addWidget(self.vin_metric, 2)
        metric_row.addWidget(self.mileage_metric, 1)
        metric_row.addWidget(self.module_metric, 1)
        info.addLayout(metric_row)
        layout.addLayout(info, 3)

        self.vehicle_image = AspectPixmapLabel(sprite_cell(0))
        self.vehicle_image.setMinimumWidth(360)
        layout.addWidget(self.vehicle_image, 2)

    def set_vehicle(self, vehicle) -> None:
        brand = vehicle.brand.casefold()
        if "volkswagen" in brand:
            brand_code = "VW"
        elif "audi" in brand:
            brand_code = "AUDI"
        elif "škoda" in brand or "skoda" in brand:
            brand_code = "Š"
        elif "seat" in brand or "cupra" in brand:
            brand_code = "SEAT"
        else:
            brand_code = "VAG"
        self.brand_label.setText(brand_code)
        self.name_label.setText(vehicle.display_name)
        self.subtitle_label.setText(vehicle.subtitle)
        self.vin_metric.value_label.setText(vehicle.vin or "—")
        mileage = f"{vehicle.mileage_km:,} km".replace(",", ".") if vehicle.mileage_km else "—"
        self.mileage_metric.value_label.setText(mileage)
        self.module_metric.value_label.setText(f"{vehicle.modules} module")


class SectionCard(QFrame):
    def __init__(self, icon: str, title: str, lines: tuple[str, ...] | list[str], parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("sectionCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(13, 11, 13, 12)
        layout.setSpacing(7)
        header = QHBoxLayout()
        icon_label = QLabel(icon)
        icon_label.setObjectName("sectionIcon")
        title_label = QLabel(title)
        title_label.setObjectName("sectionTitle")
        header.addWidget(icon_label)
        header.addWidget(title_label)
        header.addStretch(1)
        layout.addLayout(header)
        self.body = QLabel()
        self.body.setWordWrap(True)
        self.body.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.set_lines(lines)
        layout.addWidget(self.body)

    def set_lines(self, lines: tuple[str, ...] | list[str]) -> None:
        self.body.setText("\n".join(f"• {line}" for line in lines))
