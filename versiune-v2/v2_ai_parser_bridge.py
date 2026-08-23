"""Ensure every V2 runtime path uses the audited Auto-Scan parser."""

from v2_ai_copilot import parse_autoscan_file_audited


def apply():
    import ui_v2
    import v2_functional_windows_patch

    ui_v2.parse_autoscan_file = parse_autoscan_file_audited
    v2_functional_windows_patch.parse_autoscan_file = parse_autoscan_file_audited
