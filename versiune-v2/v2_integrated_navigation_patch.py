"""Stable in-app navigation for KID Diagnostic V2.

The former responsive patch detached pages 1..8 from the main QStackedWidget
and reparented them into separate top-level QMainWindow objects. That works in
source-level/offscreen tests but can produce an empty workspace after PyInstaller
reparenting on a real Windows desktop.

This final patch deliberately reverses that architecture: dashboard and all
diagnostic workspaces live in one main window and one QStackedWidget. Every
workspace has a Back button that returns to dashboard. No feature creates a
secondary top-level application window.
"""
from __future__ import annotations

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMessageBox, QPushButton


NAVIGATION_VERSION = "3.0-integrated-stack"


def apply():
    import ui_v2

    cls = ui_v2.MainWindowV2
    if getattr(cls, "_kid_v2_integrated_navigation_applied", False):
        return

    previous_init = cls.__init__

    def __init__(self, *args, **kwargs):
        previous_init(self, *args, **kwargs)

        # The responsive/windows patch saved the original pages in this map and
        # removed them from the stack. Put the *same widgets* back in the main
        # stack instead of reparenting them into top-level windows.
        pages = dict(getattr(self, "_workspace_pages", {}) or {})
        self._integrated_stack_indices = {}
        for feature_index in range(1, 9):
            page = pages.get(feature_index)
            if page is None:
                continue
            existing = self.stack.indexOf(page)
            if existing < 0:
                existing = self.stack.addWidget(page)
            self._integrated_stack_indices[feature_index] = existing

        # Secondary workspace windows are intentionally disabled in FINAL.
        for win in list(getattr(self, "_workspace_windows", {}).values()):
            try:
                win.hide()
            except Exception:
                pass
        self._workspace_windows = {}
        self._active_workspace_index = 0
        self.stack.setCurrentIndex(0)

        # Make the navigation intent explicit in every diagnostic page.
        for button in self.findChildren(QPushButton):
            if button.text().strip() in {"← Dashboard", "Dashboard"}:
                button.setText("← Înapoi la Dashboard")
                button.setObjectName("backButton")

        self.setWindowTitle("KID Diagnostic • VAG MASTER PRO V2")

    def show_dashboard(self):
        self._active_workspace_index = 0
        if hasattr(self, "stack") and self.stack.count():
            self.stack.setCurrentIndex(0)
        self.setWindowTitle("KID Diagnostic • VAG MASTER PRO V2")
        if not self.isVisible():
            self.show()
        self.raise_()
        self.activateWindow()
        dashboard = getattr(self, "_responsive_dashboard", None)
        if dashboard is not None:
            QTimer.singleShot(0, lambda: dashboard.reflow(self.width()))

    def open_page(self, index):
        index = int(index)
        if index == 0:
            self.show_dashboard()
            return
        if not self.selected_generation_id:
            QMessageBox.warning(self, "Vehicul", "Selectează mai întâi vehiculul.")
            self.show_dashboard()
            return

        page = getattr(self, "_workspace_pages", {}).get(index)
        if page is None:
            QMessageBox.critical(self, "Interfață", f"Pagina {index} nu a putut fi inițializată.")
            return

        stack_index = getattr(self, "_integrated_stack_indices", {}).get(index)
        if stack_index is None or self.stack.indexOf(page) < 0:
            stack_index = self.stack.addWidget(page)
            self._integrated_stack_indices[index] = stack_index
        else:
            stack_index = self.stack.indexOf(page)
            self._integrated_stack_indices[index] = stack_index

        # Refresh the real data before showing the workspace.
        if index == 2:
            self._load_dtcs()
        elif index in (3, 4, 5):
            self._load_procedures(page)
        elif index == 6:
            self._load_live()
        elif index == 7:
            self._load_modules()

        self._active_workspace_index = index
        self.stack.setCurrentIndex(stack_index)
        try:
            title = ui_v2.CARDS[index - 1][0]
            self.setWindowTitle(f"KID Diagnostic V2 • {title}")
        except Exception:
            pass
        if not self.isVisible():
            self.show()
        self.raise_()
        self.activateWindow()

    cls.__init__ = __init__
    cls.show_dashboard = show_dashboard
    cls.open_page = open_page
    cls._kid_v2_integrated_navigation_applied = True
