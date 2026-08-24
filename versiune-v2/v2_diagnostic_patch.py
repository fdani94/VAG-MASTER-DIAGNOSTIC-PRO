"""V2 runtime refinements for diagnostic plans."""


def apply():
    import autoscan_parser as parser

    if getattr(parser, "_kid_v2_patch_applied", False):
        return

    original = parser.diagnostic_plan

    def diagnostic_plan(con, fault, generation_id=None, engine_id=None):
        plan = original(con, fault, generation_id, engine_id)
        title = str(plan.get("title") or "")

        # The large V2 numeric index is deliberately generic. When an actual
        # VCDS Auto-Scan contains the code, its real fault text is more useful
        # than the index label and must remain visible to the technician.
        if title.startswith("DTC VAG ") and title.endswith("- index local"):
            if getattr(fault, "title", ""):
                plan["title"] = fault.title
            plan["index_only"] = True
            plan["verified"] = False
            plan["found"] = True
        else:
            plan["index_only"] = False
        return plan

    parser.diagnostic_plan = diagnostic_plan
    parser._kid_v2_patch_applied = True
