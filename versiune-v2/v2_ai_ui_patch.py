from __future__ import annotations

from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtWidgets import (
    QDialog,
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

AI_UI_VERSION = "2.1.0"


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
        self.setWindowTitle("KID Diagnostic V2 • AI Copilot VCDS")
        self.resize(940, 720)
        self.setMinimumSize(760, 560)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        title = QLabel("KID V2 AI COPILOT • VCDS")
        title.setStyleSheet("font-size:18px;font-weight:700;color:#dff2ff;")
        mode = "motor local + model extern" if owner.v2_ai_copilot.external_model_ready else "motor local verificabil"
        subtitle = QLabel(f"{mode} • fără coding / Security Access inventat")
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
            ("Funcții VCDS", "Explică funcțiile VCDS principale și când folosesc Coding, Adaptation, Basic Settings, Output Tests și Live Data."),
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


def apply():
    import ui_v2

    cls = ui_v2.MainWindowV2
    if getattr(cls, "_kid_v2_ai_copilot_applied", False):
        return

    ui_v2.parse_autoscan_file = parse_autoscan_file_audited

    original_init = cls.__init__
    original_load_autoscan = cls._load_autoscan

    def __init__(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.v2_ai_copilot = V2AICopilot()
        self.v2_verified_report_text = ""
        self.v2_ai_dialog = None

        toolbar = QToolBar("KID V2 AI Copilot", self)
        toolbar.setObjectName("kidV2AiToolbar")
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        button = QPushButton("AI COPILOT")
        button.setToolTip("Deschide asistentul VCDS ancorat în Auto-Scan și baza KID V2")
        button.setStyleSheet(
            "QPushButton{background:#15679a;color:white;border:1px solid #39a9df;border-radius:8px;padding:7px 14px;font-weight:700;}"
            "QPushButton:hover{background:#1a7db7;}"
        )
        button.clicked.connect(self.open_v2_ai_copilot)
        toolbar.addWidget(button)
        status = QLabel("  AI: verificare locală activă  ")
        status.setStyleSheet("color:#56788e;font-weight:600;")
        toolbar.addWidget(status)
        self.addToolBar(Qt.TopToolBarArea, toolbar)
        self.v2_ai_toolbar = toolbar

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

    cls.__init__ = __init__
    cls._load_autoscan = _load_autoscan
    cls.rebuild_v2_verified_report = rebuild_v2_verified_report
    cls.open_v2_ai_copilot = open_v2_ai_copilot
    cls._kid_v2_ai_copilot_applied = True
