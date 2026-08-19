import sys

import appdb
from PySide6.QtWidgets import QApplication
from appdb import APP_NAME, APP_VERSION, connect_db
from supermaster_expansion import install as install_supermaster
from vag_1996_2024_pack import install as install_1996_2024

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
        # 1) Load the common Super Master library.
        install_supermaster(con)
        # 2) Add/extend the VAG catalog through model year 2024 plus expert records.
        install_1996_2024(con)
        # 3) Re-run the idempotent mapper so newly-added generations receive
        #    the common library as well as their exact/conditional records.
        install_supermaster(con)
    finally:
        con.close()

    window = MainWindow()
    window.show()
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()
