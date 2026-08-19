import sys
from PySide6.QtWidgets import QApplication
from appdb import APP_NAME, APP_VERSION, connect_db
from supermaster_expansion import install as install_supermaster
from ui_pro import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("VAG MASTER")

    # Expand/migrate the local database before the UI opens.
    con = connect_db()
    try:
        install_supermaster(con)
    finally:
        con.close()

    window = MainWindow()
    window.show()
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()
