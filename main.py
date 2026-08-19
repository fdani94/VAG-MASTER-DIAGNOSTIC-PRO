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
from vcds_workshop_pack import install as install_vcds_workshop
from model_specific_pack import install as install_model_specific
from model_specific_pack_2 import install as install_model_specific_2
from battery_visibility_pack import install as install_battery_visibility
from engine_battery_fix_pack import install as install_engine_battery_fix
from catalog_complete_1996_2024 import install as install_catalog_complete
from vag_1996_2024_coverage_expansion import install as install_vag_coverage_expansion
from transmission_procedures_expansion import install as install_transmission_procedures
from engine_procedures_expansion import install as install_engine_procedures
from brake_steering_procedures_expansion import install as install_brake_steering_procedures
from lighting_headlight_procedures_expansion import install as install_lighting_headlight_procedures
from hvac_procedures_expansion import install as install_hvac_procedures
from airbag_instruments_immobilizer_expansion import install as install_airbag_instruments_immobilizer
from long_coding_master_pack import install as install_long_coding_master
from autoscan_dtc_pack import install as install_autoscan_dtc
from autoscan_dtc_expansion_2 import install as install_autoscan_dtc_expansion_2
from autoscan_chassis_dtc_pack import install as install_autoscan_chassis_dtc
from autoscan_mass_dtc_pack import install as install_autoscan_mass_dtc
from autoscan_verified_dtc_pack_3 import install as install_autoscan_verified_dtc_3
from autoscan_bcu_dtc_pack import install as install_autoscan_bcu_dtc
from autoscan_can_gateway_master import install as install_autoscan_can_gateway_master
from autoscan_audi_b8_common_pack import install as install_autoscan_audi_b8_common

if not hasattr(appdb, "src_diag"):
    appdb.src_diag = None

from ui_pro import MainWindow
from ui_expert_patch import apply as apply_expert_ui
from ui_long_coding_page import apply as apply_long_coding_page
from ui_autoscan_page import apply as apply_autoscan_page
from autoscan_runtime_fix import apply as apply_autoscan_runtime_fix
from ui_autoscan_result_focus import apply as apply_autoscan_result_focus
from ui_autoscan_pdf_export import apply as apply_autoscan_pdf_export
from ui_vag_light_theme import apply as apply_vag_light_theme

apply_expert_ui(MainWindow)
apply_long_coding_page(MainWindow)
apply_autoscan_page(MainWindow)
apply_autoscan_runtime_fix(MainWindow)
apply_autoscan_result_focus(MainWindow)
apply_autoscan_pdf_export(MainWindow)
apply_vag_light_theme(MainWindow)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("KID Diagnostic")

    con = connect_db()
    try:
        install_supermaster(con)
        install_1996_2024(con)
        install_catalog_complete(con)
        install_vag_coverage_expansion(con)
        install_transmission_procedures(con)
        install_engine_procedures(con)
        install_brake_steering_procedures(con)
        install_lighting_headlight_procedures(con)
        install_hvac_procedures(con)
        install_airbag_instruments_immobilizer(con)
        install_supermaster(con)
        install_expert_data(con)
        install_replacement_calibration(con)
        install_service_powertrain(con)
        install_coding_market(con)
        install_community_coding(con)
        install_vcds_workshop(con)
        install_model_specific(con)
        install_model_specific_2(con)
        install_battery_visibility(con)
        install_engine_battery_fix(con)
        install_long_coding_master(con)
        install_autoscan_dtc(con)
        install_autoscan_dtc_expansion_2(con)
        install_autoscan_chassis_dtc(con)
        install_autoscan_mass_dtc(con)
        install_autoscan_verified_dtc_3(con)
        install_autoscan_bcu_dtc(con)
        install_autoscan_can_gateway_master(con)
        install_autoscan_audi_b8_common(con)
    finally:
        con.close()

    window = MainWindow()
    window.show()
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()
