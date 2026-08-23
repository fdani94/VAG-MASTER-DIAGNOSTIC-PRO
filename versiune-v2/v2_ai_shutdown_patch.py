from __future__ import annotations

from PySide6.QtCore import QTimer

import v2_ai_ui_patch as ai_ui

SHUTDOWN_PATCH_VERSION = "2.1.2"


def _dialog_has_running_worker(dialog) -> bool:
    if dialog is None:
        return False
    try:
        return any(worker.isRunning() for worker in getattr(dialog, "_workers", []))
    except RuntimeError:
        return False


def apply():
    import ui_v2

    cls = ui_v2.MainWindowV2
    if getattr(cls, "_kid_v2_ai_shutdown_applied", False):
        return

    original_main_close = cls.closeEvent
    original_dialog_send = ai_ui.CopilotDialog.send

    def finish_pending_owner_close(dialog):
        owner = getattr(dialog, "owner", None)
        if owner is None or not getattr(owner, "_kid_close_when_ai_idle", False):
            return
        if _dialog_has_running_worker(dialog):
            return
        owner._kid_close_when_ai_idle = False
        QTimer.singleShot(0, owner.close)

    def dialog_send_with_shutdown(self, *args, **kwargs):
        before = set(getattr(self, "_workers", []))
        result = original_dialog_send(self, *args, **kwargs)
        for worker in list(getattr(self, "_workers", [])):
            if worker in before or getattr(worker, "_kid_shutdown_hooked", False):
                continue
            worker._kid_shutdown_hooked = True
            worker.finished.connect(lambda d=self: finish_pending_owner_close(d))
        return result

    def main_close_hardened(self, event):
        dialog = getattr(self, "v2_ai_dialog", None)
        if _dialog_has_running_worker(dialog):
            self._kid_close_when_ai_idle = True
            try:
                dialog._close_when_idle = True
                dialog.hide()
            except RuntimeError:
                pass
            try:
                self.statusBar().showMessage(
                    "AI finalizează răspunsul curent; KID Diagnostic se va închide automat imediat după finalizare."
                )
            except Exception:
                pass
            event.ignore()
            return
        original_main_close(self, event)

    ai_ui.CopilotDialog.send = dialog_send_with_shutdown
    cls.closeEvent = main_close_hardened
    cls._kid_v2_ai_shutdown_applied = True


__all__ = ["SHUTDOWN_PATCH_VERSION", "apply"]
