from __future__ import annotations

from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QToolBar,
    QVBoxLayout,
)

from v2_ai_copilot import (
    V2AICopilot,
    audit_scan_result,
    build_verified_report,
    parse_autoscan_file_audited,
)

AI_UI_VERSION = "2.1.1"

PAGE_AI = {
    0: (
        "AI GENERAL",
        "Întreabă AI despre vehicul, funcții VCDS sau ce modul trebuie verificat.",
        "Ajută-mă să folosesc KID Diagnostic V2 pentru vehiculul selectat și spune-mi ce funcție VCDS este potrivită.",
    ),
    1: (
        "AI AUTO-SCAN",
        "Verifică citirea, prioritizarea DTC și raportul BEFORE/AFTER.",
        "Analizează Auto-Scan-ul curent, verifică dacă a fost citit complet și spune-mi în ce ordine investighez erorile.",
    ),
    2: (
        "AI DTC",
        "Explică DTC, cauze, verificări și ordinea diagnosticului.",
        "Explică DTC-urile relevante pentru vehiculul curent și spune-mi ce verific mai întâi fără să presupui piese.",
    ),
    3: (
        "AI CODARE",
        "Ajutor Coding / Long Coding bazat pe ECU și Coding ORIGINAL.",
        "Ajută-mă la Coding / Long Coding pentru vehiculul curent. Folosește numai identificarea controllerului și Coding ORIGINAL; nu inventa valori.",
    ),
    4: (
        "AI ADAPTĂRI",
        "Ajutor Adaptation / Basic Settings / calibrări.",
        "Ajută-mă la Adaptation sau Basic Settings pentru vehiculul curent și spune condițiile, backup-ul necesar și verificarea finală.",
    ),
    5: (
        "AI SERVICE",
        "Ajutor resetări, DPF, EPB, baterie și proceduri service.",
        "Ajută-mă cu operația de service pentru vehiculul curent. Spune exact ce trebuie confirmat înainte și cum verific rezultatul.",
    ),
    6: (
        "AI LIVE DATA",
        "Alege parametrii live relevanți și explică actual vs target.",
        "Ajută-mă să aleg valorile Live Data relevante pentru problema curentă și cum interpretez actual versus specified/target.",
    ),
    7: (
        "AI MODULE",
        "Identifică modulul, adresa și traseul VCDS corect.",
        "Ajută-mă să identific controllerul corect, adresa lui și traseul VCDS pentru funcția dorită pe vehiculul curent.",
    ),
    8: (
        "AI RAPORT",
        "Verifică și reface raportul cu dovezi din Auto-Scan.",
        "Refă raportul automat din Auto-Scan, verifică-l și evidențiază Coding ORIGINAL, DTC și pașii de diagnostic.",
    ),
}


def _vehicle_text(owner) -> str:
    badge = getattr(owner, "vehicle_badge", None)
    if badge is not None and hasattr(badge, "text"):
        text = badge.text().strip()
        if text and "Niciun vehicul" not in text:
            return text
    parts = []
    for name in ("brand_combo", "model_combo", "gen_combo", "year_combo", "engine_combo"):
        widget = getattr(owner, name, None)
        if widget is None or not hasattr(widget, "currentText"):
            continue
        text = widget.currentText().strip()
        if not text or text.lower().startswith("alege") or text == "Nespecificat" or text in parts:
            continue
        parts.append(text)
    return " • ".join(parts) or "Vehicul neselectat"


class CopilotWorker(QThread):
    answered = Signal(str)

    def __init__(self, copilot, question, vehicle, scan, plans, report):
        super().__init__()
        self.copilot = copilot
        self.question = question
        self.vehicle = vehicle
        self.scan = scan
        self.plans = plans
        self.report = report

    def run(self):
        try:
            answer = self.copilot.ask(
                self.question,
                selected_vehicle=self.vehicle,
                scan=self.scan,
                plans=self.plans,
                report_text=self.report,
            )
        except Exception as exc:
            answer = f"Eroare Copilot: {exc}"
        self.answered.emit(answer)


class CopilotDialog(QDialog):
    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self._workers = []
        self.setWindowTitle("KID Diagnostic V2 • AI Copilot VCDS • 2.1.1")
        self.resize(940, 720)
        self.setMinimumSize(760, 560)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        title = QLabel("KID V2 AI COPILOT • ACTIV")
        title.setStyleSheet("font-size:18px;font-weight:800;color:#dff2ff;")
        mode = "motor local + model extern" if owner.v2_ai_copilot.external_model_ready else "motor local verificabil"
        subtitle = QLabel(f"{mode} • context din toate funcțiile V2 • fără coding / Security Access inventat")
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color:#8fb4cc;")
        root.addWidget(title)
        root.addWidget(subtitle)

        self.transcript = QTextEdit()
        self.transcript.setReadOnly(True)
        self.transcript.setStyleSheet(
            "QTextEdit{background:#081522;color:#e8f5ff;border:1px solid #1b4663;border-radius:10px;padding:10px;}"
        )
        root.addWidget(self.transcript, 1)

        quick = QHBoxLayout()
        actions = [
            ("Verifică Auto-Scan", "Verifică dacă Auto-Scan-ul a fost citit corect și spune exact ce nu se potrivește."),
            ("Explică DTC", "Explică DTC-urile din Auto-Scan în ordinea priorității și spune ce verific mai întâi."),
            ("Ajutor codare", "Ajută-mă la coding VCDS folosind numai identificarea și Coding ORIGINAL din Auto-Scan."),
            ("Adaptări", "Ajută-mă la Adaptation și Basic Settings fără valori inventate."),
            ("Refă raport", "Refă raportul automat din Auto-Scan și verifică-l."),
        ]
        for label, prompt in actions:
            button = QPushButton(label)
            button.clicked.connect(lambda _checked=False, p=prompt: self.send(p))
            quick.addWidget(button)
        root.addLayout(quick)

        bottom = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Ex.: explică P0299, verifică raportul, cum procedez la Coding Address 09...")
        self.input.returnPressed.connect(self.send)
        self.send_button = QPushButton("Trimite")
        self.send_button.clicked.connect(self.send)
        bottom.addWidget(self.input, 1)
        bottom.addWidget(self.send_button)
        root.addLayout(bottom)

        self.setStyleSheet(
            """
            QDialog{background:#06101b;}
            QPushButton{background:#123e5d;color:#eef9ff;border:1px solid #1d6b98;border-radius:8px;padding:7px 10px;font-weight:600;}
            QPushButton:hover{background:#175477;}
            QLineEdit{background:#0b1d2c;color:#f1f8fc;border:1px solid #235a7a;border-radius:8px;padding:9px;}
            """
        )

        intro = owner.v2_ai_copilot.ask(
            "Ce poți face?",
            selected_vehicle=_vehicle_text(owner),
            scan=getattr(owner, "current_autoscan", None),
            plans=getattr(owner, "autoscan_plans", None),
            report_text=getattr(owner, "v2_verified_report_text", ""),
        )
        self._append("AI", intro)

    def _append(self, role, text):
        self.transcript.append(f"<b>{role}:</b><br>{str(text).replace(chr(10), '<br>')}<br>")

    def send(self, preset=None):
        text = str(preset if isinstance(preset, str) else self.input.text()).strip()
        if not text:
            return
        if not isinstance(preset, str):
            self.input.clear()
        self._append("TU", text)
        self.input.setEnabled(False)
        self.send_button.setEnabled(False)

        worker = CopilotWorker(
            self.owner.v2_ai_copilot,
            text,
            _vehicle_text(self.owner),
            getattr(self.owner, "current_autoscan", None),
            getattr(self.owner, "autoscan_plans", None),
            getattr(self.owner, "v2_verified_report_text", ""),
        )
        self._workers.append(worker)

        def done(answer, w=worker):
            self._append("AI", answer)
            self.input.setEnabled(True)
            self.send_button.setEnabled(True)
            self.input.setFocus()
            if w in self._workers:
                self._workers.remove(w)
            w.deleteLater()

        worker.answered.connect(done)
        worker.start()


def _ai_strip(owner, index: int) -> QFrame:
    label, description, _prompt = PAGE_AI.get(index, PAGE_AI[0])
    frame = QFrame()
    frame.setObjectName(f"kidAiStrip{index}")
    frame.setMinimumHeight(54)
    frame.setStyleSheet(
        "QFrame{background:#082236;border:1px solid #1e8ac0;border-radius:10px;}"
        "QLabel{background:transparent;border:none;}"
        "QPushButton{background:#1475aa;color:white;border:1px solid #43b9ef;border-radius:7px;padding:7px 12px;font-weight:800;}"
        "QPushButton:hover{background:#188dc8;}"
    )
    row = QHBoxLayout(frame)
    row.setContentsMargins(12, 8, 12, 8)
    row.setSpacing(10)

    badge = QLabel(label)
    badge.setStyleSheet("color:#72d5ff;font-weight:900;font-size:12px;")
    text = QLabel(description)
    text.setWordWrap(True)
    text.setStyleSheet("color:#d7effb;font-weight:600;")
    action = QPushButton("AJUTOR AI AICI")
    action.clicked.connect(lambda _checked=False, i=index: owner.ask_v2_ai_for_page(i))
    chat = QPushButton("CHAT AI")
    chat.clicked.connect(owner.open_v2_ai_copilot)

    row.addWidget(badge)
    row.addWidget(text, 1)
    row.addWidget(action)
    row.addWidget(chat)
    return frame


def _install_ai_strips(owner):
    """Attach AI controls to the final responsive dashboard and workspace pages."""
    targets = {0: getattr(owner, "_responsive_dashboard", None)}
    targets.update(dict(getattr(owner, "_workspace_pages", {}) or {}))
    owner.v2_ai_strips = {}

    for index in range(9):
        page = targets.get(index)
        if page is None:
            continue
        layout = page.layout()
        if layout is None:
            continue
        existing = page.findChild(QFrame, f"kidAiStrip{index}")
        if existing is not None:
            owner.v2_ai_strips[index] = existing
            continue
        strip = _ai_strip(owner, index)
        if hasattr(layout, "insertWidget"):
            layout.insertWidget(1, strip)
        else:
            layout.addWidget(strip)
        owner.v2_ai_strips[index] = strip


def apply():
    import ui_v2

    cls = ui_v2.MainWindowV2
    if getattr(cls, "_kid_v2_ai_copilot_applied", False):
        return

    ui_v2.parse_autoscan_file = parse_autoscan_file_audited

    original_init = cls.__init__
    original_load_autoscan = cls._load_autoscan
    original_open_page = cls.open_page
    original_show_dashboard = cls.show_dashboard

    def __init__(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.v2_ai_copilot = V2AICopilot()
        self.v2_verified_report_text = ""
        self.v2_ai_dialog = None
        self.setWindowTitle("KID Diagnostic V2 • AI Copilot • v2.1.1")

        toolbar = QToolBar("KID V2 AI Copilot", self)
        toolbar.setObjectName("kidV2AiToolbar")
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setStyleSheet("QToolBar{background:#061a2a;border-bottom:1px solid #17638c;padding:4px;}")
        button = QPushButton("AI COPILOT • ACTIV")
        button.setToolTip("Deschide asistentul VCDS ancorat în Auto-Scan și baza KID V2")
        button.setStyleSheet(
            "QPushButton{background:#156f9f;color:white;border:1px solid #4bc7ff;border-radius:8px;padding:8px 16px;font-weight:900;}"
            "QPushButton:hover{background:#1a8bc4;}"
        )
        button.clicked.connect(self.open_v2_ai_copilot)
        toolbar.addWidget(button)
        status = QLabel("  AI disponibil în Dashboard + toate cele 8 funcții  ")
        status.setStyleSheet("color:#8fdcff;font-weight:700;")
        toolbar.addWidget(status)
        self.addToolBar(Qt.TopToolBarArea, toolbar)
        self.v2_ai_toolbar = toolbar
        self.v2_ai_status = status

        _install_ai_strips(self)
        try:
            self.statusBar().showMessage("KID Diagnostic V2 v2.1.1 • AI Copilot activ • bază V2 separată")
        except Exception:
            pass

    def _load_autoscan(self):
        original_load_autoscan(self)
        scan = getattr(self, "current_autoscan", None)
        if scan is None:
            return
        audit = getattr(scan, "audit", None) or audit_scan_result(
            scan, getattr(scan, "extraction_warnings", [])
        )
        self.v2_verified_report_text = build_verified_report(
            scan,
            getattr(self, "autoscan_plans", None),
            _vehicle_text(self),
            audit,
        )
        summary = getattr(self, "autoscan_summary", None)
        if summary is not None:
            base = summary.text().split(" • Audit AI ")[0]
            summary.setText(
                f"{base} • Audit AI {audit['score']}/100 {audit['confidence']}"
                + (" • VERIFICAT" if audit["verified"] else " • ATENȚIE")
            )
            summary.setToolTip("\n".join(
                f"{x['severity'].upper()}: {x['message']}" for x in audit.get("issues", [])
            ))

    def rebuild_v2_verified_report(self):
        scan = getattr(self, "current_autoscan", None)
        if scan is None:
            return ""
        audit = audit_scan_result(scan, getattr(scan, "extraction_warnings", []))
        self.v2_verified_report_text = build_verified_report(
            scan,
            getattr(self, "autoscan_plans", None),
            _vehicle_text(self),
            audit,
        )
        return self.v2_verified_report_text

    def open_v2_ai_copilot(self):
        if self.v2_ai_dialog is not None:
            try:
                if self.v2_ai_dialog.isVisible():
                    self.v2_ai_dialog.raise_()
                    self.v2_ai_dialog.activateWindow()
                    return
            except RuntimeError:
                self.v2_ai_dialog = None
        dialog = CopilotDialog(self)
        dialog.setAttribute(Qt.WA_DeleteOnClose, True)
        dialog.destroyed.connect(lambda: setattr(self, "v2_ai_dialog", None))
        self.v2_ai_dialog = dialog
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def ask_v2_ai_for_page(self, index=None):
        if index is None:
            index = int(getattr(self, "_active_workspace_index", 0) or 0)
        _label, _description, prompt = PAGE_AI.get(int(index), PAGE_AI[0])
        self.open_v2_ai_copilot()
        if self.v2_ai_dialog is not None:
            self.v2_ai_dialog.send(prompt)

    def open_page(self, index):
        original_open_page(self, index)
        index = int(index)
        if index in PAGE_AI and int(getattr(self, "_active_workspace_index", 0) or 0) == index:
            label = PAGE_AI[index][0].replace("AI ", "")
            self.setWindowTitle(f"KID Diagnostic V2 • {label} • AI Copilot v2.1.1")

    def show_dashboard(self):
        original_show_dashboard(self)
        self.setWindowTitle("KID Diagnostic V2 • Dashboard • AI Copilot v2.1.1")

    cls.__init__ = __init__
    cls._load_autoscan = _load_autoscan
    cls.rebuild_v2_verified_report = rebuild_v2_verified_report
    cls.open_v2_ai_copilot = open_v2_ai_copilot
    cls.ask_v2_ai_for_page = ask_v2_ai_for_page
    cls.open_page = open_page
    cls.show_dashboard = show_dashboard
    cls._kid_v2_ai_copilot_applied = True
