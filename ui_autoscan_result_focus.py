"""Large, highly visible diagnosis summary after an Auto-Scan is parsed."""
from pathlib import Path
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel


def _headline(corr, fault_count):
    if not fault_count:
        return "✓ AUTO-SCAN CITIT • NU AU FOST IDENTIFICATE DTC-URI"
    secondary = len((corr or {}).get("secondary", []))
    primary = max(0, fault_count - secondary)
    return f"DIAGNOSTIC AUTO-SCAN • {fault_count} ERORI • {primary} DE ANALIZAT PRIORITAR • {secondary} PROBABIL SECUNDARE"


def _body(result, corr):
    faults = list(getattr(result, "faults", []) or [])
    modules = list(getattr(result, "modules", []) or [])
    codes = []
    for f in faults[:8]:
        code = getattr(f, "code", None) or getattr(f, "vag_code", None) or "DTC"
        addr = getattr(f, "module_address", "") or ""
        codes.append(f"{addr}:{code}" if addr else code)
    extra = len(faults) - len(codes)
    codes_text = " • ".join(codes) if codes else "Nicio eroare identificată"
    if extra > 0:
        codes_text += f" • +{extra} alte erori"
    return (
        f"Raport: {Path(result.source_path).name}   |   Module detectate: {len(modules)}\n"
        f"Coduri: {codes_text}\n"
        "Selectează o eroare din tabel pentru explicația completă sau apasă «Plan diagnostic automat» pentru ordinea de verificare."
    )


def apply(MainWindow):
    old_populate = MainWindow.populate_autoscan
    old_reset = getattr(MainWindow, "reset_autoscan_ui", None)

    def _ensure_focus(self):
        if hasattr(self, "autoscan_result_focus"):
            return
        page = self.stack.widget(self.autoscan_page_index)
        root = page.layout()
        box = QFrame()
        box.setObjectName("autoscanResultFocus")
        box.setStyleSheet(
            "QFrame#autoscanResultFocus { background:#172331; border:2px solid #36a9e1; border-radius:12px; }"
            "QLabel#autoscanResultHeadline { color:#ffffff; font-size:18px; font-weight:800; }"
            "QLabel#autoscanResultBody { color:#dceaf5; font-size:13px; }"
        )
        lay = QVBoxLayout(box)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(7)
        self.autoscan_result_headline = QLabel("REZULTAT AUTO-SCAN")
        self.autoscan_result_headline.setObjectName("autoscanResultHeadline")
        self.autoscan_result_headline.setWordWrap(True)
        self.autoscan_result_body = QLabel("După citirea raportului, diagnosticul principal va apărea aici.")
        self.autoscan_result_body.setObjectName("autoscanResultBody")
        self.autoscan_result_body.setWordWrap(True)
        lay.addWidget(self.autoscan_result_headline)
        lay.addWidget(self.autoscan_result_body)
        # Position: directly under the compact scan summary and above the fault list.
        insert_at = 2 if root.count() >= 2 else root.count()
        root.insertWidget(insert_at, box)
        self.autoscan_result_focus = box

    def populate_autoscan(self, result):
        old_populate(self, result)
        _ensure_focus(self)
        corr = getattr(self, "autoscan_correlation", None)
        count = len(getattr(result, "faults", []) or [])
        self.autoscan_result_headline.setText(_headline(corr, count))
        self.autoscan_result_body.setText(_body(result, corr))
        self.autoscan_result_focus.show()

    def reset_autoscan_ui(self):
        if old_reset:
            old_reset(self)
        if hasattr(self, "autoscan_result_focus"):
            self.autoscan_result_headline.setText("REZULTAT AUTO-SCAN")
            self.autoscan_result_body.setText("Încarcă raportul VCDS pentru mașina selectată.")
            self.autoscan_result_focus.hide()

    MainWindow.populate_autoscan = populate_autoscan
    MainWindow.reset_autoscan_ui = reset_autoscan_ui
