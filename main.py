import sys

import appdb
from PySide6.QtWidgets import QApplication
from appdb import APP_NAME, APP_VERSION, connect_db
from supermaster_expansion import install as install_supermaster
from vag_1996_2024_pack import install as install_1996_2024
from expert_data_pack import install as install_expert_data

# Compatibility hotfix for the current v5 seed data.
if not hasattr(appdb, "src_diag"):
    appdb.src_diag = None

from ui_pro import MainWindow
from ui_expert_patch import apply as apply_expert_ui

apply_expert_ui(MainWindow)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("VAG MASTER")

    con = connect_db()
    try:
        install_supermaster(con)
        install_1996_2024(con)
        install_supermaster(con)
        install_expert_data(con)
    finally:
        con.close()

    window = MainWindow()
    window.show()
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()
