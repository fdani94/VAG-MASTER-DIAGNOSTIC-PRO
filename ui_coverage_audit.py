"""Developer coverage audit page for the 1996-2024 database."""
from pathlib import Path
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QFileDialog, QMessageBox
from appdb import connect_db
from coverage_audit import AREAS, summary, write_report


def apply(MainWindow):
    old_init = MainWindow.__init__

    def __init__(self, *args, **kwargs):
        old_init(self, *args, **kwargs)
        self._install_coverage_audit_page()

    def _install_coverage_audit_page(self):
        page = QWidget()
        root = QVBoxLayout(page)
        title = QLabel("AUDIT ACOPERIRE 1996–2024")
        title.setStyleSheet("font-size:20px;font-weight:800;")
        info = QLabel("Arată unde baza are proceduri legate de fiecare generație și unde mai există goluri. «Acoperit» nu înseamnă că fiecare ECU/motor este complet documentat.")
        info.setWordWrap(True)
        root.addWidget(title); root.addWidget(info)
        bar = QHBoxLayout()
        refresh = QPushButton("Recalculează auditul")
        export = QPushButton("Exportă audit TXT")
        self.coverage_summary = QLabel("")
        bar.addWidget(refresh); bar.addWidget(export); bar.addWidget(self.coverage_summary, 1)
        root.addLayout(bar)
        cols = ["Marcă", "Model", "Generație", "Ani", "Chassis", "Platformă"] + list(AREAS.keys()) + ["DTC", "Goluri"]
        table = QTableWidget(0, len(cols)); table.setHorizontalHeaderLabels(cols)
        table.setSortingEnabled(True); table.setAlternatingRowColors(True)
        self.coverage_table = table
        root.addWidget(table, 1)
        idx = self.stack.addWidget(page)
        self.coverage_audit_page_index = idx
        # Add a left-side navigation button when the existing UI exposes a navigation layout.
        nav = getattr(self, "nav_layout", None) or getattr(self, "sidebar_layout", None)
        if nav is not None:
            btn = QPushButton("Audit acoperire")
            btn.clicked.connect(lambda: (self.stack.setCurrentIndex(idx), self.refresh_coverage_audit()))
            nav.addWidget(btn)
            self.coverage_audit_button = btn
        refresh.clicked.connect(self.refresh_coverage_audit)
        export.clicked.connect(self.export_coverage_audit)
        self.refresh_coverage_audit()

    def refresh_coverage_audit(self):
        con = connect_db()
        try: data = summary(con)
        finally: con.close()
        rows = data["rows"]; t = self.coverage_table
        t.setSortingEnabled(False); t.setRowCount(len(rows))
        for i, r in enumerate(rows):
            base = [r["brand"], r["model"], r["generation"], r["years"], r["chassis"], r["platform"]]
            values = base + [r["areas"][a]["status"] for a in AREAS] + [r["areas"]["DTC"]["status"], str(r["missing_areas"])]
            for j, value in enumerate(values): t.setItem(i, j, QTableWidgetItem(str(value)))
        t.resizeColumnsToContents(); t.setSortingEnabled(True)
        self.coverage_summary.setText(f'{data["total_generations"]} generații • {data["incomplete_generations"]} cu goluri de completat')

    def export_coverage_audit(self):
        path, _ = QFileDialog.getSaveFileName(self, "Salvează auditul", "audit_vag_1996_2024.txt", "Text (*.txt)")
        if not path: return
        con = connect_db()
        try: write_report(con, path)
        finally: con.close()
        QMessageBox.information(self, "Audit", f"Audit salvat:\n{Path(path)}")

    MainWindow.__init__ = __init__
    MainWindow._install_coverage_audit_page = _install_coverage_audit_page
    MainWindow.refresh_coverage_audit = refresh_coverage_audit
    MainWindow.export_coverage_audit = export_coverage_audit
