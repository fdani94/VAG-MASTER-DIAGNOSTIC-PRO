import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication

    from app import MainWindow
    GUI_IMPORT_ERROR = ""
except (ImportError, OSError) as exc:  # Linux minimal containers may not ship libEGL.
    QApplication = None
    MainWindow = None
    GUI_IMPORT_ERROR = str(exc)


class GuiSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if QApplication is None:
            raise unittest.SkipTest(f"Qt runtime indisponibil: {GUI_IMPORT_ERROR}")
        cls.app = QApplication.instance() or QApplication([])

    def test_dashboard_and_all_detached_windows_construct(self):
        window = MainWindow()
        self.assertEqual(len(window.findChildren(type(window.hero))), 1)
        for key in ("scan", "dtc", "coding", "adaptation", "service", "live", "repair", "reports"):
            child = window._create_feature_window(key)
            self.assertTrue(child.windowTitle())
            child.close()
        window.close()


if __name__ == "__main__":
    unittest.main()
