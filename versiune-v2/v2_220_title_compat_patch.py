from __future__ import annotations

TITLE_COMPAT_VERSION = "2.2.0"


def apply():
    import ui_v2

    cls = ui_v2.MainWindowV2
    if getattr(cls, "_kid_v220_title_compat_applied", False):
        return

    previous_init = cls.__init__
    previous_open_page = cls.open_page
    previous_show_dashboard = cls.show_dashboard

    def init_compat(self, *args, **kwargs):
        previous_init(self, *args, **kwargs)
        self.setWindowTitle("KID Diagnostic V2 • Vehicle First • AI Copilot • v2.2.0")

    def open_page_compat(self, index):
        previous_open_page(self, index)
        if int(index) == 3 and getattr(self, "selected_generation_id", None):
            current = self.windowTitle()
            if "AI Copilot" not in current:
                self.setWindowTitle(current.replace(" • v2.2.0", " • AI Copilot • v2.2.0"))

    def show_dashboard_compat(self):
        previous_show_dashboard(self)
        self.setWindowTitle("KID Diagnostic V2 • Dashboard • Vehicle First • AI Copilot • v2.2.0")

    cls.__init__ = init_compat
    cls.open_page = open_page_compat
    cls.show_dashboard = show_dashboard_compat
    cls._kid_v220_title_compat_applied = True


__all__ = ["TITLE_COMPAT_VERSION", "apply"]
