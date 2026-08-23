from __future__ import annotations

from PySide6.QtCore import QTimer

SHUTDOWN_PATCH_VERSION = "2.1.2"


def _running_workers(dialog):
    if dialog is None:
        return []
    try:
        return [worker for worker in getattr(dialog, "_workers", []) if worker.isRunning()]
    except RuntimeError:
        return []


def _finish_owner_close(owner):
    if owner is None or not getattr(owner, "_kid_close_when_ai_idle", False):
        return
    dialog = getattr(owner, "v2_ai_dialog", None)
    if _running_workers(dialog):
        return
    owner._kid_close_when_ai_idle = False
    QTimer.singleShot(0, owner.close)


def apply():
    import ui_v2

    cls = ui_v2.MainWindowV2
    if getattr(cls, "_kid_v2_ai_shutdown_applied", False):
        return

    original_main_close = cls.closeEvent

    def main_close_hardened(self, event):
        dialog = getattr(self, "v2_ai_dialog", None)
        workers = _running_workers(dialog)
        if workers:
            self._kid_close_when_ai_idle = True
            for worker in workers:
                if getattr(worker, "_kid_owner_close_hooked", False):
                    continue
                worker._kid_owner_close_hooked = True
                worker.finished.connect(lambda owner=self: _finish_owner_close(owner))
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

    cls.closeEvent = main_close_hardened
    cls._kid_v2_ai_shutdown_applied = True


__all__ = ["SHUTDOWN_PATCH_VERSION", "apply"]
