import sys

import appdb
from PySide6.QtWidgets import QApplication
from appdb import APP_NAME, APP_VERSION, connect_db
from supermaster_expansion import install as install_supermaster

# Compatibility hotfix for the current v5 seed data. Some procedure rows
# reference src_diag as a module-level variable; define it so the database
# can initialize instead of crashing at startup. The normal seed() routine
# still creates the official Diagnostic Procedures source for DTC records.
if not hasattr(appdb, "src_diag"):
    appdb.src_diag = None

from ui_pro import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("VAG MASTER")

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
