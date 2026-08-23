from __future__ import annotations

from html import escape

from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtWidgets import QDialog, QPushButton

import v2_ai_copilot as ai_core
import v2_ai_ui_patch as ai_ui

HARDENING_VERSION = "2.1.2"

PAGE_NAMES = {
    0: "Dashboard",
    1: "Auto-Scan VCDS",
    2: "Coduri DTC",
    3: "Codări",
    4: "Adaptări",
    5: "Service & Resetări",
    6: "Date Live",
    7: "Module & Ghiduri",
    8: "Rapoarte",
}

WRITE_SENSITIVE_TERMS = (
    "CODING",
    "CODARE",
    "LONG CODING",
    "ADAPT",
    "BASIC SETTINGS",
    "SECURITY ACCESS",
    "LOGIN",
    "OUTPUT TEST",
    "ACTUATOR",
    "DPF",
    "EPB",
    "RESET",
    "SERVICE",
    "BATERIE",
    "BATTERY",
)

INTENT_TERMS = WRITE_SENSITIVE_TERMS + (
    "DTC",
    "EROARE",
    "ERORI",
    "LIVE",
    "MEASUR",
    "VALORI",
    "RAPORT",
    "AUDIT",
    "VERIFIC",
    "FUNCȚII VCDS",
    "FUNCTII VCDS",
)


def _clip(value, limit=1800):
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + " …"


def _row_context(table):
    if table is None or not hasattr(table, "currentRow"):
        return ""
    row = int(table.currentRow())
    if row < 0 or row >= table.rowCount():
        return ""
    parts = []
    for column in range(table.columnCount()):
        item = table.item(row, column)
        if item is None:
            continue
        value = item.text().strip()
        if not value:
            continue
        header = table.horizontalHeaderItem(column)
        label = header.text().strip() if header is not None else f"Coloana {column + 1}"
        parts.append(f"{label}: {value}")
    return " | ".join(parts)


def _detail_context(widget):
    if widget is None or not hasattr(widget, "toPlainText"):
        return ""
    return _clip(widget.toPlainText(), 1600)


def active_page_context(owner):
    """Return only the currently selected V2 evidence, never guessed data."""
    index = int(getattr(owner, "_active_workspace_index", 0) or 0)
    lines = [f"Funcție activă: {PAGE_NAMES.get(index, 'KID Diagnostic V2')}"]
    vehicle = ai_ui._vehicle_text(owner)
    if vehicle:
        lines.append(f"Vehicul V2: {vehicle}")

    if index == 1:
        row = _row_context(getattr(owner, "autoscan_table", None))
        if row:
            lines.append(f"DTC selectat în Auto-Scan: {row}")
        detail = _detail_context(getattr(owner, "autoscan_detail", None))
        if detail:
            lines.append(f"Detaliu Auto-Scan afișat: {detail}")
    elif index == 2:
        search = getattr(owner, "dtc_search", None)
        if search is not None and search.text().strip():
            lines.append(f"Căutare DTC: {search.text().strip()}")
        row = _row_context(getattr(owner, "dtc_table", None))
        if row:
            lines.append(f"DTC selectat: {row}")
        detail = _detail_context(getattr(owner, "dtc_detail", None))
        if detail:
            lines.append(f"Fișa DTC afișată: {detail}")
    elif index in (3, 4, 5):
        page = (getattr(owner, "_workspace_pages", {}) or {}).get(index)
        search = getattr(page, "search", None)
        if search is not None and search.text().strip():
            lines.append(f"Căutare procedură: {search.text().strip()}")
        row = _row_context(getattr(page, "table", None))
        if row:
            lines.append(f"Procedură selectată: {row}")
        detail = _detail_context(getattr(page, "detail", None))
        if detail:
            lines.append(f"Procedură afișată: {detail}")
    elif index == 6:
        search = getattr(owner, "live_search", None)
        if search is not None and search.text().strip():
            lines.append(f"Căutare Live Data: {search.text().strip()}")
        row = _row_context(getattr(owner, "live_table", None))
        if row:
            lines.append(f"Parametru Live Data selectat: {row}")
    elif index == 7:
        row = _row_context(getattr(owner, "module_table", None))
        if row:
            lines.append(f"Modul selectat: {row}")
    elif index == 8:
        scan = getattr(owner, "current_autoscan", None)
        if scan is not None:
            lines.append(
                f"Auto-Scan disponibil: {len(getattr(scan, 'modules', []) or [])} module, "
                f"{len(getattr(scan, 'faults', []) or [])} DTC"
            )
        if getattr(owner, "v2_verified_report_text", ""):
            lines.append("Raport verificat AI disponibil: DA")

    return _clip("\n".join(lines), 3200)


def _is_write_sensitive(question, ui_context=""):
    upper = f"{question}\n{ui_context}".upper()
    return any(term in upper for term in WRITE_SENSITIVE_TERMS)


def _route_generic_question(question, ui_context):
    """Give generic 'ce fac aici?' questions the active page intent."""
    q = str(question or "").strip()
    upper = q.upper()
    if any(term in upper for term in INTENT_TERMS):
        return q
    ctx = str(ui_context or "")
    if "Funcție activă: Coduri DTC" in ctx:
        return "Explică DTC-ul selectat și spune ce verific mai întâi. " + q
    if "Funcție activă: Codări" in ctx:
        return "Ajută-mă la Coding / Long Coding folosind numai valorile originale și documentate. " + q
    if "Funcție activă: Adaptări" in ctx:
        return "Ajută-mă la Adaptation / Basic Settings fără valori inventate. " + q
    if "Funcție activă: Service & Resetări" in ctx:
        return "Ajută-mă cu procedura de service selectată și condițiile ei. " + q
    if "Funcție activă: Date Live" in ctx:
        return "Ajută-mă să interpretez Live Data selectat. " + q
    if "Funcție activă: Auto-Scan VCDS" in ctx:
        return "Verifică Auto-Scan-ul și DTC-ul selectat. " + q
    return q


class HardenedCopilotWorker(QThread):
    answered = Signal(str)

    def __init__(self, copilot, question, vehicle, scan, plans, report, ui_context):
        super().__init__()
        self.copilot = copilot
        self.question = question
        self.vehicle = vehicle
        self.scan = scan
        self.plans = plans
        self.report = report
        self.ui_context = ui_context

    def run(self):
        try:
            answer = self.copilot.ask(
                self.question,
                selected_vehicle=self.vehicle,
                scan=self.scan,
                plans=self.plans,
                report_text=self.report,
                ui_context=self.ui_context,
            )
        except Exception as exc:
            answer = f"Eroare Copilot: {exc}"
        self.answered.emit(answer)


def apply():
    import ui_v2

    cls = ui_v2.MainWindowV2
    if getattr(cls, "_kid_v2_ai_hardening_applied", False):
        return

    # Version markers are diagnostic only; the DB catalog revision stays 2.1.1
    # because this patch changes runtime behavior, not the seeded catalog data.
    ai_core.COPILOT_VERSION = HARDENING_VERSION
    ai_ui.AI_UI_VERSION = HARDENING_VERSION

    original_dialog_init = ai_ui.CopilotDialog.__init__
    original_main_init = cls.__init__
    original_open_page = cls.open_page
    original_show_dashboard = cls.show_dashboard

    def hardened_ask(
        self,
        question,
        selected_vehicle="",
        scan=None,
        plans=None,
        report_text="",
        ui_context="",
    ):
        context = _clip(ui_context, 3200)
        routed_question = _route_generic_question(question, context)
        local = self._local_answer(routed_question, selected_vehicle, scan, plans, report_text)
        if context:
            local += "\n\nContext selectat în KID Diagnostic V2:\n" + context

        # For any function that can change ECU/controller state, external models
        # are deliberately excluded. This makes the deterministic verified layer
        # the only source for coding/adaptation/service guidance.
        if not self.external_model_ready or _is_write_sensitive(routed_question, context):
            return local

        try:
            external = self._external_answer(question, local, selected_vehicle, scan)
        except Exception:
            return local + "\n\n[Modelul extern nu a răspuns; rămâne răspunsul local verificabil.]"
        external = _clip(external, 8000)
        if not external:
            return local
        return (
            local
            + "\n\n---\nAI extern — explicație suplimentară READ-ONLY; "
              "valorile de scriere rămân exclusiv cele documentate mai sus:\n"
            + external
        )

    def dialog_init(self, owner):
        original_dialog_init(self, owner)
        self._close_when_idle = False
        self.setWindowTitle("KID Diagnostic V2 • AI Copilot VCDS • 2.1.2")

    def append_safe(self, role, text):
        safe_role = escape(str(role))
        safe_text = escape(str(text)).replace("\n", "<br>")
        self.transcript.append(f"<b>{safe_role}:</b><br>{safe_text}<br>")

    def set_busy(self, busy):
        self.input.setEnabled(not busy)
        self.send_button.setEnabled(not busy)
        for button in self.findChildren(QPushButton):
            if button is self.send_button:
                continue
            # Keep all question buttons single-flight to avoid races where an
            # earlier worker re-enables controls while a later one is still busy.
            button.setEnabled(not busy)

    def send_hardened(self, preset=None):
        if any(worker.isRunning() for worker in getattr(self, "_workers", [])):
            self._append("AI", "Așteaptă răspunsul curent înainte de o nouă întrebare.")
            return

        text = str(preset if isinstance(preset, str) else self.input.text()).strip()
        if not text:
            return
        if not isinstance(preset, str):
            self.input.clear()
        self._append("TU", text)
        set_busy(self, True)

        worker = HardenedCopilotWorker(
            self.owner.v2_ai_copilot,
            text,
            ai_ui._vehicle_text(self.owner),
            getattr(self.owner, "current_autoscan", None),
            getattr(self.owner, "autoscan_plans", None),
            getattr(self.owner, "v2_verified_report_text", ""),
            active_page_context(self.owner),
        )
        self._workers.append(worker)

        def answer_received(answer, w=worker):
            # Do not remove/delete the QThread here. answered is emitted from
            # inside run(), therefore the thread can still report isRunning().
            self._append("AI", answer)
            w._kid_answer_received = True

        def thread_finished(w=worker):
            if w in self._workers:
                self._workers.remove(w)
            w.deleteLater()
            if not any(x.isRunning() for x in self._workers):
                set_busy(self, False)
                if self.isVisible():
                    self.input.setFocus()
                if getattr(self, "_close_when_idle", False):
                    self._close_when_idle = False
                    self.close()

        worker.answered.connect(answer_received)
        worker.finished.connect(thread_finished)
        worker.start()

    def close_event_hardened(self, event):
        if any(worker.isRunning() for worker in getattr(self, "_workers", [])):
            # Hiding instead of deleting keeps both the dialog and worker alive
            # until QThread.finished, not merely until the answer signal arrives.
            self._close_when_idle = True
            self.hide()
            event.ignore()
            return
        QDialog.closeEvent(self, event)

    def main_init(self, *args, **kwargs):
        original_main_init(self, *args, **kwargs)
        self.setWindowTitle("KID Diagnostic V2 • AI Copilot • v2.1.2")
        status = getattr(self, "v2_ai_status", None)
        if status is not None:
            status.setText("  AI 2.1.2 • context real din Dashboard + toate cele 8 funcții  ")
        try:
            self.statusBar().showMessage(
                "KID Diagnostic V2 v2.1.2 • AI Copilot activ • context selectat • bază V2 separată"
            )
        except Exception:
            pass

    def open_ai_hardened(self):
        dialog = getattr(self, "v2_ai_dialog", None)
        if dialog is not None:
            try:
                dialog._close_when_idle = False
                dialog.show()
                dialog.raise_()
                dialog.activateWindow()
                return
            except RuntimeError:
                self.v2_ai_dialog = None

        dialog = ai_ui.CopilotDialog(self)
        dialog.setAttribute(Qt.WA_DeleteOnClose, True)
        dialog.destroyed.connect(lambda: setattr(self, "v2_ai_dialog", None))
        self.v2_ai_dialog = dialog
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def open_page_hardened(self, index):
        original_open_page(self, index)
        index = int(index)
        if int(getattr(self, "_active_workspace_index", 0) or 0) == index:
            self.setWindowTitle(
                f"KID Diagnostic V2 • {PAGE_NAMES.get(index, 'Funcție')} • AI Copilot v2.1.2"
            )

    def show_dashboard_hardened(self):
        original_show_dashboard(self)
        self.setWindowTitle("KID Diagnostic V2 • Dashboard • AI Copilot v2.1.2")

    ai_core.V2AICopilot.ask = hardened_ask
    ai_ui.CopilotDialog.__init__ = dialog_init
    ai_ui.CopilotDialog._append = append_safe
    ai_ui.CopilotDialog.send = send_hardened
    ai_ui.CopilotDialog.closeEvent = close_event_hardened
    cls.__init__ = main_init
    cls.open_v2_ai_copilot = open_ai_hardened
    cls.open_page = open_page_hardened
    cls.show_dashboard = show_dashboard_hardened
    cls._kid_v2_ai_hardening_applied = True


__all__ = [
    "HARDENING_VERSION",
    "active_page_context",
    "apply",
]
