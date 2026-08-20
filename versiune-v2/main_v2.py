from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
V2_DIR = Path(__file__).resolve().parent
for path in (ROOT, V2_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import appdb
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
from all_platforms_models_expansion import install as install_all_platforms_models
from transmission_procedures_expansion import install as install_transmission_procedures
from engine_procedures_expansion import install as install_engine_procedures
from brake_steering_procedures_expansion import install as install_brake_steering_procedures
from lighting_headlight_procedures_expansion import install as install_lighting_headlight_procedures
from hvac_procedures_expansion import install as install_hvac_procedures
from airbag_instruments_immobilizer_expansion import install as install_airbag_instruments_immobilizer
from comfort_gateway_multimedia_expansion import install as install_comfort_gateway_multimedia
from legacy_schema_compat import ensure_legacy_schema, migrate_legacy_procedures
from coverage_gap_filler import install as install_coverage_gap_filler
from long_coding_master_pack import install as install_long_coding_master
from autoscan_dtc_pack import install as install_autoscan_dtc
from autoscan_dtc_expansion_2 import install as install_autoscan_dtc_expansion_2
from autoscan_chassis_dtc_pack import install as install_autoscan_chassis_dtc
from autoscan_mass_dtc_pack import install as install_autoscan_mass_dtc
from autoscan_verified_dtc_pack_3 import install as install_autoscan_verified_dtc_3
from autoscan_bcu_dtc_pack import install as install_autoscan_bcu_dtc
from autoscan_can_gateway_master import install as install_autoscan_can_gateway_master
from autoscan_audi_b8_common_pack import install as install_autoscan_audi_b8_common
from dtc_reference_index_pack import install as install_v2_dtc_reference_index
from obd_reference_index_pack import install as install_v2_obd_reference_index

if not hasattr(appdb, "src_diag"):
    appdb.src_diag = None


def prepare_database():
    con = appdb.connect_db()
    try:
        install_supermaster(con)
        install_1996_2024(con)
        install_catalog_complete(con)
        install_vag_coverage_expansion(con)
        install_all_platforms_models(con)
        install_transmission_procedures(con)
        install_engine_procedures(con)
        install_brake_steering_procedures(con)

        ensure_legacy_schema(con)
        install_lighting_headlight_procedures(con)
        install_hvac_procedures(con)
        install_airbag_instruments_immobilizer(con)
        install_comfort_gateway_multimedia(con)
        migrate_legacy_procedures(con)

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
        install_coverage_gap_filler(con)

        # V2: 40,000 numeric VAG slots + numeric P/B/C/U OBD slots.
        # Detailed/verified rows installed above always win; index-only rows
        # never overwrite workshop data and remain clearly marked in the UI.
        install_v2_dtc_reference_index(con)
        install_v2_obd_reference_index(con)
    finally:
        con.close()


if __name__ == "__main__":
    prepare_database()
    from v2_diagnostic_patch import apply as apply_v2_diagnostic_patch
    apply_v2_diagnostic_patch()
    from v2_ui_runtime_patch import apply as apply_v2_ui_runtime_patch
    apply_v2_ui_runtime_patch()
    from v2_master_ui_patch import apply as apply_v2_master_ui_patch
    apply_v2_master_ui_patch()
    from v2_visual_fix import apply as apply_v2_visual_fix
    apply_v2_visual_fix()
    from v2_redesign_patch import apply as apply_v2_redesign_patch
    apply_v2_redesign_patch()
    from ui_v2 import run
    run()
