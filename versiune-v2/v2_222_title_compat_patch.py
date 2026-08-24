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

    def init_title(self, *args, **kwargs):
        previous_init(self, *args, **kwargs)
        self.setWindowTitle(_title_for(0))
        try:
            self.statusBar().showMessage(
                f"KID Diagnostic V2 v{TITLE_VERSION} • layout aerisit • precision {PRECISION_COMPONENT_VERSION} • AI Copilot"
            )
        except Exception:
            pass

    def open_page_title(self, index):
        previous_open_page(self, index)
        index = int(index)
        if int(getattr(self, "_active_workspace_index", 0) or 0) == index:
            self.setWindowTitle(_title_for(index))

    def show_dashboard_title(self):
        previous_show_dashboard(self)
        self.setWindowTitle(_title_for(0))

    cls.__init__ = init_title
    cls.open_page = open_page_title
    cls.show_dashboard = show_dashboard_title
    cls._kid_222_title_applied = True


__all__ = ["TITLE_VERSION", "PRECISION_COMPONENT_VERSION", "apply"]
