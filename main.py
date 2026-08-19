import sys
from PySide6.QtWidgets import QApplication
from appdb import APP_NAME, APP_VERSION
from ui_pro import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("VAG MASTER")
    window = MainWindow()
    window.show()
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()
