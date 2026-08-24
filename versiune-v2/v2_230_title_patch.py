from __future__ import annotations

TITLE_VERSION = "2.3.0"
PRECISION_COMPONENT_VERSION = "2.2.1"


def apply():
    import ui_v2

    cls = ui_v2.MainWindowV2
    if getattr(cls, "_kid_230_title_applied", False):
        return

    previous_init = cls.__init__
    previous_open_page = cls.open_page
    previous_show_dashboard = cls.show_dashboard
    previous_select_vehicle = cls._select_vehicle

    def _title(index=0):
        if index:
            try:
                area = ui_v2.CARDS[int(index) - 1][0]
            except Exception:
                area = "Workspace"
        else:
            area = "Dashboard"
        return f"KID Diagnostic V2 • {area} • Coding Recovery • AI Copilot • v{TITLE_VERSION}"

    def init_title(self, *args, **kwargs):
        previous_init(self, *args, **kwargs)
        self.setWindowTitle(_title(0))
        try:
            self.statusBar().showMessage(
                f"KID Diagnostic V2 v{TITLE_VERSION} • Coding Recovery • layout aerisit • precision {PRECISION_COMPONENT_VERSION} • AI Copilot"
            )
        except Exception:
            pass

    def open_page_title(self, index):
        previous_open_page(self, index)
        index = int(index)
        if int(getattr(self, "_active_workspace_index", 0) or 0) == index:
            self.setWindowTitle(_title(index))

    def dashboard_title(self):
        previous_show_dashboard(self)
        self.setWindowTitle(_title(0))

    def select_vehicle_title(self):
        previous_select_vehicle(self)
        index = int(getattr(self, "_active_workspace_index", 0) or 0)
        self.setWindowTitle(_title(index))

    cls.__init__ = init_title
    cls.open_page = open_page_title
    cls.show_dashboard = dashboard_title
    cls._select_vehicle = select_vehicle_title
    cls._kid_230_title_applied = True


__all__ = ["TITLE_VERSION", "PRECISION_COMPONENT_VERSION", "apply"]
