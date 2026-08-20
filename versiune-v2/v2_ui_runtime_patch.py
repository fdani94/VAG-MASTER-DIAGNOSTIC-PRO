"""Runtime refinements for the KID Diagnostic V2 interface.

Keeps the visual shell small while binding DTC/Live Data pages to the real
expanded `dtcs` schema used by the V1 diagnostic engine.
"""

from PySide6.QtWidgets import QTableWidgetItem, QHeaderView


def _value(row, key, default=""):
    try:
        keys = set(row.keys())
    except Exception:
        return default
    if key not in keys:
        return default
    value = row[key]
    return value if value not in (None, "") else default


def apply():
    import ui_v2

    cls = ui_v2.MainWindowV2
    if getattr(cls, "_kid_v2_ui_patch_applied", False):
        return

    original_init = cls.__init__

    def __init__(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        # Existing PDF helper expects `generation_combo`; V2 calls it `gen_combo`.
        self.generation_combo = self.gen_combo

    def _load_dtcs(self):
        q = self.dtc_search.text().strip()
        like = f"%{q}%"
        rows = self.con.execute(
            """SELECT * FROM dtcs
               WHERE code LIKE ? OR title LIKE ? OR description LIKE ?
                  OR causes LIKE ? OR component LIKE ? OR module_hint LIKE ?
               ORDER BY code LIMIT 1800""",
            (like, like, like, like, like, like),
        ).fetchall()
        self.dtc_table.setRowCount(len(rows))
        self.dtc_table.setProperty("rows", rows)
        for i, row in enumerate(rows):
            confidence = str(_value(row, "confidence", "")).lower()
            if bool(_value(row, "verified", 0)):
                status = "VERIFICAT"
            elif confidence == "index-only":
                status = "INDEX LOCAL"
            else:
                status = "LOCAL / DE VERIFICAT"
            values = [
                _value(row, "code", ""),
                _value(row, "title", ""),
                _value(row, "severity", "Nespecificat"),
                status,
            ]
            for j, value in enumerate(values):
                self.dtc_table.setItem(i, j, QTableWidgetItem(str(value)))
        self.dtc_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)

    def _show_dtc(self):
        row_index = self.dtc_table.currentRow()
        rows = self.dtc_table.property("rows") or []
        if row_index < 0 or row_index >= len(rows):
            return
        row = rows[row_index]
        confidence = str(_value(row, "confidence", "")).lower()
        if bool(_value(row, "verified", 0)):
            level = "Fișă verificată / detaliată"
        elif confidence == "index-only":
            level = "Index local de recunoaștere — confirmă denumirea exactă din Auto-Scan"
        else:
            level = "Fișă locală / ghid orientativ — confirmă pe controllerul exact"

        text = (
            f"{_value(row, 'code', 'DTC')} • {_value(row, 'title', 'DTC')}\n\n"
            f"NIVEL INFORMAȚIE\n{level}\n\n"
            f"DESCRIERE\n{_value(row, 'description', '—')}\n\n"
            f"SIMPTOME POSIBILE\n{_value(row, 'symptoms', '—')}\n\n"
            f"CAUZE POSIBILE\n{_value(row, 'causes', '—')}\n\n"
            f"PIESA / SISTEMUL IMPLICAT\n{_value(row, 'component', 'De confirmat după modul, platformă și cod motor.')}\n\n"
            f"UNDE SE AFLĂ\n{_value(row, 'component_location', 'Locația diferă după model și motorizare.')}\n\n"
            f"CE VERIFICI ÎN VCDS\n{_value(row, 'vcds_parameters', 'Advanced Measuring Values relevante sistemului.')}\n\n"
            f"VALORI / COMPORTAMENT AȘTEPTAT\n{_value(row, 'expected_values', 'Folosește specificația controllerului exact.')}\n\n"
            f"TRASEU ÎN VCDS\n{_value(row, 'test_path', 'Auto-Scan > modul raportor > Fault Codes > Advanced Measuring Values')}\n\n"
            f"DIAGNOSTIC PAS CU PAS\n{_value(row, 'diagnosis', '—')}\n\n"
            f"CUM O REPARI\n{_value(row, 'repair', '—')}\n\n"
            f"DUPĂ ÎNLOCUIREA PIESEI\n{_value(row, 'replacement_steps', 'Coding / Adaptation / Basic Setting numai dacă procedura specifică o cere; apoi test și Auto-Scan final.')}\n\n"
            f"SEVERITATE\n{_value(row, 'severity', 'Nespecificat')}"
        )
        self.dtc_detail.setPlainText(text)

    def _load_live(self):
        q = self.live_search.text().strip()
        like = f"%{q}%"
        rows = self.con.execute(
            """SELECT code,title,vcds_parameters,expected_values,verified,confidence
               FROM dtcs
               WHERE COALESCE(confidence,'') <> 'index-only'
                 AND (COALESCE(vcds_parameters,'') <> '' OR COALESCE(expected_values,'') <> '')
                 AND (code LIKE ? OR title LIKE ? OR vcds_parameters LIKE ? OR expected_values LIKE ?)
               ORDER BY verified DESC, code
               LIMIT 1500""",
            (like, like, like, like),
        ).fetchall()
        self.live_table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            values = [
                _value(row, "code", ""),
                _value(row, "title", ""),
                _value(row, "vcds_parameters", "—"),
                _value(row, "expected_values", "—"),
            ]
            for j, value in enumerate(values):
                self.live_table.setItem(i, j, QTableWidgetItem(str(value)))
        self.live_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.live_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.live_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)

    cls.__init__ = __init__
    cls._load_dtcs = _load_dtcs
    cls._show_dtc = _show_dtc
    cls._load_live = _load_live
    cls._kid_v2_ui_patch_applied = True
