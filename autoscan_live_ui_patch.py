"""UI patch: enrich Auto-Scan plans with VCDS live-data reference values."""
from autoscan_live_values import enrich_plan


def apply(MainWindow):
    old_populate = MainWindow.populate_autoscan
    old_show_fault = MainWindow.show_autoscan_fault
    old_show_corr = MainWindow.show_autoscan_correlation

    def populate_autoscan(self, result):
        old_populate(self, result)
        enriched = []
        for fault, plan in list(getattr(self, "autoscan_plans", []) or []):
            enriched.append((fault, enrich_plan(fault, plan)))
        self.autoscan_plans = enriched
        if hasattr(self, "autoscan_table"):
            self.autoscan_table.setProperty("rows", enriched)
            if enriched and self.autoscan_table.currentRow() >= 0:
                self.show_autoscan_fault()

    def show_autoscan_fault(self):
        old_show_fault(self)
        row = self.autoscan_table.currentRow() if hasattr(self, "autoscan_table") else -1
        rows = self.autoscan_table.property("rows") or [] if hasattr(self, "autoscan_table") else []
        if row < 0 or row >= len(rows):
            return
        _fault, plan = rows[row]
        live = str(plan.get("live_reference", "") or "").strip()
        if live and hasattr(self, "autoscan_detail"):
            base = self.autoscan_detail.toPlainText().rstrip()
            marker = "VALORI LIVE DATA / INTERVALE DE REFERINȚĂ"
            if marker not in base:
                self.autoscan_detail.setPlainText(base + "\n\n" + marker + "\n" + live)

    def show_autoscan_correlation(self):
        old_show_corr(self)
        plans = list(getattr(self, "autoscan_plans", []) or [])
        if not plans or not hasattr(self, "autoscan_detail"):
            return
        chunks = []
        for fault, plan in plans[:8]:
            ref = str(plan.get("live_reference", "") or "").strip()
            if ref:
                code = getattr(fault, "code", "") or getattr(fault, "vag_code", "") or "DTC"
                chunks.append(f"{code} • {getattr(fault, 'module_address', '')}\n{ref}")
        if chunks:
            base = self.autoscan_detail.toPlainText().rstrip()
            self.autoscan_detail.setPlainText(
                base + "\n\nVALORI LIVE DATA DE VERIFICAT ÎN VCDS\n\n" + "\n\n--------------------\n\n".join(chunks)
            )

    MainWindow.populate_autoscan = populate_autoscan
    MainWindow.show_autoscan_fault = show_autoscan_fault
    MainWindow.show_autoscan_correlation = show_autoscan_correlation
