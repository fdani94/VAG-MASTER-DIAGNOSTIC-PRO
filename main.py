import sys

import appdb
from PySide6.QtWidgets import QApplication
from appdb import APP_NAME, APP_VERSION, connect_db
from supermaster_expansion import install as install_supermaster
from vag_1996_2024_pack import install as install_1996_2024
from expert_data_pack import install as install_expert_data
from replacement_calibration_pack import install as install_replacement_calibration
from service_powertrain_pack import install as install_service_powertrain
from coding_market_pack import install as install_coding_market
from community_coding_pack import install as install_community_coding

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
        install_replacement_calibration(con)
        install_service_powertrain(con)
        install_coding_market(con)
        install_community_coding(con)
    finally:
        con.close()

    window = MainWindow()
    window.show()
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()
