from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V2 = Path(__file__).resolve().parent
for path in (ROOT, V2):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import main_v2


def choose_first_vehicle(win, app):
    for bi in range(1, win.brand_combo.count()):
        win.brand_combo.setCurrentIndex(bi)
        app.processEvents()
        for mi in range(1, win.model_combo.count()):
            win.model_combo.setCurrentIndex(mi)
            app.processEvents()
            if win.gen_combo.count() > 1:
                win.gen_combo.setCurrentIndex(1)
                app.processEvents()
                if win.year_combo.count():
                    win.year_combo.setCurrentIndex(0)
                win._select_vehicle()
                app.processEvents()
                return win.selected_generation_id is not None
    return False


class SlowLocalCopilot:
    external_model_ready = False

    def ask(self, *_args, **_kwargs):
        time.sleep(0.65)
        return "RĂSPUNS THREAD OK <b>literal</b>"


def wait_until(app, predicate, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return True
        time.sleep(0.05)
    app.processEvents()
    return bool(predicate())


def main():
    main_v2.prepare_database()
    main_v2.apply_v2_patches()

    from PySide6.QtWidgets import QApplication, QMessageBox, QFrame, QToolBar
    import ui_v2
    from v2_ai_hardening_patch import active_page_context

    app = QApplication.instance() or QApplication([])
    QMessageBox.warning = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
    QMessageBox.information = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)
    QMessageBox.critical = staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok)

    win = ui_v2.MainWindowV2()
    win.resize(1180, 760)
    win.show()
    app.processEvents()

    assert "2.1.2" in win.windowTitle(), win.windowTitle()
    assert getattr(win.__class__, "_kid_v2_ai_hardening_applied", False)
    assert getattr(win.__class__, "_kid_v2_ai_shutdown_applied", False)
    toolbar = win.findChild(QToolBar, "kidV2AiToolbar")
    assert toolbar is not None and toolbar.isVisible()
    assert len(getattr(win, "v2_ai_strips", {})) == 9
    assert win._responsive_dashboard.findChild(QFrame, "kidAiStrip0") is not None
    assert win.grab().save(str(ROOT / "v2_ai_212_dashboard.png"), "PNG")

    assert choose_first_vehicle(win, app)
    win.open_page(2)
    app.processEvents()
    win.dtc_search.setText("P0299")
    app.processEvents()
    assert win.dtc_table.rowCount() > 0
    win.dtc_table.setCurrentCell(0, 0)
    app.processEvents()

    context = active_page_context(win)
    assert "Funcție activă: Coduri DTC" in context
    assert "P0299" in context, context
    assert win._workspace_pages[2].findChild(QFrame, "kidAiStrip2") is not None
    assert win.grab().save(str(ROOT / "v2_ai_212_dtc_context.png"), "PNG")

    win.open_v2_ai_copilot()
    app.processEvents()
    dialog = win.v2_ai_dialog
    assert dialog is not None and dialog.isVisible()
    assert "2.1.2" in dialog.windowTitle()

    # Rich-text injection regression: user/model text must remain literal text.
    dialog._append("TU", "<b>NU TREBUIE INTERPRETAT</b> & <img src='x'>")
    plain = dialog.transcript.toPlainText()
    assert "<b>NU TREBUIE INTERPRETAT</b>" in plain, plain
    assert "<img src='x'>" in plain, plain
    assert dialog.grab().save(str(ROOT / "v2_ai_212_chat.png"), "PNG")

    # QThread lifetime regression 1: close CHAT while response is running.
    win.v2_ai_copilot = SlowLocalCopilot()
    dialog.send("test thread chat close")
    app.processEvents()
    worker = dialog._workers[0]
    chat_finished = {"value": False}
    worker.finished.connect(lambda: chat_finished.__setitem__("value", True))
    assert worker.isRunning()
    dialog.close()
    app.processEvents()
    assert not dialog.isVisible(), "Dialog should hide while worker is running"
    assert win.v2_ai_dialog is dialog, "Running worker dialog must stay alive"
    assert worker in dialog._workers, "Worker reference was released before QThread.finished"

    win.open_v2_ai_copilot()
    app.processEvents()
    assert win.v2_ai_dialog is dialog, "Reopen must reuse the live worker dialog"
    assert dialog.isVisible()

    dialog.close()
    app.processEvents()
    assert wait_until(app, lambda: chat_finished["value"]), "QThread.finished was not emitted"
    assert wait_until(app, lambda: win.v2_ai_dialog is None), (
        "Dialog should delete only after QThread.finished"
    )

    # QThread lifetime regression 2: close MAIN APP while AI is running.
    win.open_v2_ai_copilot()
    app.processEvents()
    dialog2 = win.v2_ai_dialog
    assert dialog2 is not None
    win.v2_ai_copilot = SlowLocalCopilot()
    dialog2.send("test thread main close")
    app.processEvents()
    worker2 = dialog2._workers[0]
    main_finished = {"value": False}
    worker2.finished.connect(lambda: main_finished.__setitem__("value", True))
    assert worker2.isRunning()

    win.close()
    app.processEvents()
    assert win.isVisible(), "Main window closed before active AI QThread finished"
    assert getattr(win, "_kid_close_when_ai_idle", False)
    assert not dialog2.isVisible(), "AI dialog should hide during deferred app shutdown"
    assert worker2 in dialog2._workers, "Main close released AI worker too early"

    assert wait_until(app, lambda: main_finished["value"]), "AI worker did not emit finished"
    assert wait_until(app, lambda: not win.isVisible()), (
        "Main window did not close automatically after AI worker finished"
    )

    print(
        "V2 AI 2.1.2 HARDENING AUDIT OK",
        "html_escape=ok",
        "chat_thread_lifecycle=ok",
        "main_shutdown_lifecycle=ok",
        "context=P0299",
        f"ai_strips={len(win.v2_ai_strips)}",
    )

    app.quit()


if __name__ == "__main__":
    main()
