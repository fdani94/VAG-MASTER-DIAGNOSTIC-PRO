from __future__ import annotations

import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from app import MainWindow
from theme import APP_STYLE


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("KID VAG MASTER Diagnostic PRO V2")
    app.setOrganizationName("KID Diagnostic")
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(APP_STYLE)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
