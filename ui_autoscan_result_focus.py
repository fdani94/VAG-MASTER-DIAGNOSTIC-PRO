"""Large, highly visible diagnosis summary after an Auto-Scan is parsed."""
from pathlib import Path
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel


def _headline(corr, fault_count):
    if not fault_count:
        return "✓ AUTO-SCAN CITIT • NU AU FOST IDENTIFICATE DTC-URI"
    secondary = len((corr or {}).get("secondary", []))
    primary = max(0, fault_count - secondary)
    return f"DIAGNOSTIC AUTO-SCAN • {fault_count} ERORI • {primary} DE ANALIZAT PRIORITAR • {secondary} PROBABIL SECUNDARE"


def _short(text, limit=210):
    text = " ".join((text or "").replace("\n", " ").split())
    if len(text) <= limit:
        return text
    return text[:limit].rstrip(" ,.;:-") + "…"


def _unique(items, limit=5):
    out = []
    seen = set()
    for item in items:
        item = _short(item, 180)
        key = item.lower()
        if item and key not in seen:
            seen.add(key)
            out.append(item)
        if len(out) >= limit:
            break
    return out


def _diagnosis_blocks(plans, corr):
    primary = (corr or {}).get("primary", [])
    probable = []
    checks = []
    parts = []

    # Prefer correlation-ranked primary faults.
    for score, idx, fault, plan in primary[:4]:
        code = getattr(fault, "code", "") or getattr(fault, "vag_code", "") or "DTC"
        title = plan.get("title") or getattr(fault, "title", "") or "Eroare de diagnosticat"
        probable.append(f"{code}: {title}")
        if plan.get("diagnosis"):
            checks.append(plan.get("diagnosis"))
        if plan.get("component"):
            parts.append(plan.get("component"))

    # If correlation did not rank anything, use the first indexed plans.
    if not probable:
        for fault, plan in plans[:4]:
            code = getattr(fault, "code", "") or getattr(fault, "vag_code", "") or "DTC"
            probable.append(f"{code}: {plan.get('title') or getattr(fault, 'title', '')}")
            checks.append(plan.get("diagnosis", ""))
            parts.append(plan.get("component", ""))

    # Common causes are more useful than repeating individual checks.
    common = (corr or {}).get("common_causes", [])
    common_checks = [f"{title}: {text}" for title, text in common]
    checks = common_checks + checks

    return _unique(probable, 4), _unique(checks, 4), _unique(parts, 6)


def _body(result, corr, plans):
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

    probable, checks, parts = _diagnosis_blocks(plans, corr)
    probable_text = "\n".join(f"• {x}" for x in probable) or "• Nu există suficiente date pentru o concluzie probabilă."
    checks_text = "\n".join(f"• {x}" for x in checks) or "• Verifică DTC-urile individuale și Freeze Frame-ul."
    parts_text = " • ".join(parts) if parts else "Nu există încă o piesă suficient de bine corelată."

    return (
        f"Raport: {Path(result.source_path).name}   |   Module detectate: {len(modules)}\n"
        f"Coduri: {codes_text}\n\n"
        f"CE ARE PROBABIL MAȘINA\n{probable_text}\n\n"
        f"CE VERIFICI PRIMA DATĂ\n{checks_text}\n\n"
        f"PIESE / SISTEME SUSPECTE\n{parts_text}\n\n"
        "Acesta este un diagnostic probabil calculat din Auto-Scan, nu o confirmare a piesei defecte. "
        "Selectează eroarea pentru procedura completă sau «Plan diagnostic automat» pentru ordinea de lucru."
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
            "QLabel#autoscanResultHeadline { color:#ffffff; font-size:19px; font-weight:800; }"
            "QLabel#autoscanResultBody { color:#dceaf5; font-size:14px; line-height:1.25; }"
        )
        lay = QVBoxLayout(box)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(8)
        self.autoscan_result_headline = QLabel("REZULTAT AUTO-SCAN")
        self.autoscan_result_headline.setObjectName("autoscanResultHeadline")
        self.autoscan_result_headline.setWordWrap(True)
        self.autoscan_result_body = QLabel("După citirea raportului, diagnosticul principal va apărea aici.")
        self.autoscan_result_body.setObjectName("autoscanResultBody")
        self.autoscan_result_body.setWordWrap(True)
        self.autoscan_result_body.setTextInteractionFlags(self.autoscan_result_body.textInteractionFlags() | 1)
        lay.addWidget(self.autoscan_result_headline)
        lay.addWidget(self.autoscan_result_body)
        insert_at = 2 if root.count() >= 2 else root.count()
        root.insertWidget(insert_at, box)
        self.autoscan_result_focus = box

    def populate_autoscan(self, result):
        old_populate(self, result)
        _ensure_focus(self)
        corr = getattr(self, "autoscan_correlation", None)
        plans = getattr(self, "autoscan_plans", []) or []
        count = len(getattr(result, "faults", []) or [])
        self.autoscan_result_headline.setText(_headline(corr, count))
        self.autoscan_result_body.setText(_body(result, corr, plans))
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
