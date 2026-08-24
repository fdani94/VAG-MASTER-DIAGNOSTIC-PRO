from __future__ import annotations

TITLE_VERSION = "2.2.2"
PRECISION_COMPONENT_VERSION = "2.2.1"


def apply():
    import ui_v2

    cls = ui_v2.MainWindowV2
    if getattr(cls, "_kid_222_title_applied", False):
        return

    previous_init = cls.__init__
    previous_open_page = cls.open_page
    previous_show_dashboard = cls.show_dashboard
    previous_select_vehicle = cls._select_vehicle

    def _title_for(index=0):
        if index:
            try:
                area = ui_v2.CARDS[int(index) - 1][0]
            except Exception:
                area = "Workspace"
        else:
            area = "Dashboard"
        return (
            f"KID Diagnostic V2 • {area} • AI Copilot • v{TITLE_VERSION} "
            f"• precision {PRECISION_COMPONENT_VERSION}"
        )

    def _restore_current_title(self):
        active = int(getattr(self, "_active_workspace_index", 0) or 0)
        self.setWindowTitle(_title_for(active))
        try:
            self.statusBar().showMessage(
                f"KID Diagnostic V2 v{TITLE_VERSION} • layout aerisit • precision {PRECISION_COMPONENT_VERSION} • AI Copilot"
            )
        except Exception:
            pass

    def init_title(self, *args, **kwargs):
        previous_init(self, *args, **kwargs)
        _restore_current_title(self)

    def select_vehicle_title(self):
        previous_select_vehicle(self)
        # Precision 2.2.1 intentionally owns vehicle validation and may restore
        # its component version in the title. The product release remains 2.2.2.
        _restore_current_title(self)

    def open_page_title(self, index):
        previous_open_page(self, index)
        index = int(index)
        if int(getattr(self, "_active_workspace_index", 0) or 0) == index:
            self.setWindowTitle(_title_for(index))

    def show_dashboard_title(self):
        previous_show_dashboard(self)
        self.setWindowTitle(_title_for(0))

    cls.__init__ = init_title
    cls._select_vehicle = select_vehicle_title
    cls.open_page = open_page_title
    cls.show_dashboard = show_dashboard_title
    cls._kid_222_title_applied = True


__all__ = ["TITLE_VERSION", "PRECISION_COMPONENT_VERSION", "apply"]
