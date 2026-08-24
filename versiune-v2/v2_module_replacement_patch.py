from __future__ import annotations

from html import escape
import re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
)

from v2_module_replacement import (
    MODULE_REPLACEMENT_VERSION,
    analyze_replacement_coding,
    render_recovery_text,
)

PATCH_VERSION = "2.3.0"


def _norm_addr(value):
    text = str(value or "").upper()
    match = re.search(r"\b([0-9A-F]{2})\b", text)
    return match.group(1) if match else text.strip()[:2]


def _finding_html(owner, item):
    def e(value):
        return escape(str(value or "")).replace("\n", "<br>")

    evidence = "".join(f"<li>{e(line)}</li>" for line in item.evidence)
    actions = "".join(f"<li>{e(line)}</li>" for line in item.actions)
    online = (
        '<div class="block"><b>BLOCAJ ONLINE</b><br>Acest DTC indică Component Protection. '
        'Coding-ul repetat nu este tratat ca soluție; urmează procedura de fabrică online pentru platforma/controllerul exact.</div>'
        if item.requires_online else ""
    )
    coding = e(item.coding) if item.coding else "NEAFIȘAT ÎN AUTO-SCAN"
    source = f'{e(item.source_title)}<br>{e(item.source_url)}' if item.source_title else "Auto-Scan VCDS"
    return f"""
    <html><head><style>
      body {{ font-family:'Segoe UI',Arial; color:#182536; font-size:14px; line-height:1.58; }}
      h2 {{ margin:0 0 7px 0; color:#173c58; font-size:22px; }}
      .chip {{ display:inline-block; padding:5px 9px; margin:0 6px 7px 0; border-radius:8px; background:#e9f3fb; color:#205b86; font-weight:800; }}
      .danger {{ background:#fff0f0; color:#8b2525; }}
      .warn {{ background:#fff7df; color:#7a5200; }}
      .section {{ margin-top:13px; padding:13px 15px; border:1px solid #d7e3ec; border-radius:10px; background:#fbfdff; }}
      .block {{ margin-top:13px; padding:14px 15px; border:2px solid #df5c5c; border-radius:10px; background:#fff1f1; color:#7d2020; }}
      .code {{ font-family:Consolas,monospace; font-size:15px; font-weight:800; }}
    </style></head><body>
      <h2>{e(item.label)}</h2>
      <span class="chip {'danger' if item.severity in ('CRITIC','BLOCAJ') else 'warn'}">{e(item.severity)}</span>
      <span class="chip">Address {e(item.address)}</span>
      <span class="chip">{e(item.dtc_code or 'DTC text')}</span>
      <span class="chip">CONFIDENȚĂ {e(item.confidence)}%</span>
      <div class="section"><b>VEHICUL ACTIV</b><br>{e(getattr(owner, 'vehicle_badge', None).text() if getattr(owner, 'vehicle_badge', None) else '')}</div>
      <div class="section"><b>CONTROLLER / COMPONENTĂ</b><br>{e(item.module_name)}<br>
        Part No SW: {e(item.part_no_sw or '—')}<br>Part No HW: {e(item.part_no_hw or '—')}<br>
        Component: {e(item.component or '—')}<br>ASAM: {e(item.asam_dataset or '—')}</div>
      <div class="section"><b>CODING DIN AUTO-SCAN</b><br><span class="code">{coding}</span><br>
        <small>Dacă DTC-ul este 01044, valoarea este păstrată ca probă și NU este declarată automat corectă.</small></div>
      {online}
      <div class="section"><b>DE CE A FOST IDENTIFICAT</b><ul>{evidence}</ul></div>
      <div class="section"><b>CE FACI ÎN CONTINUARE</b><ol>{actions}</ol></div>
      <div class="section"><b>VERIFICARE DUPĂ CODARE / ADAPTARE</b><br>
        Șterge DTC-urile, respectă ciclul de contact cerut și încarcă un Auto-Scan nou. KID marchează rezultatul ca rezolvat numai când DTC-ul de coding/configurare nu mai apare și controllerul rămâne prezent.</div>
      <div class="section"><b>SURSĂ REGULĂ</b><br>{source}</div>
      <div class="section"><b>LIMITĂ DE SIGURANȚĂ</b><br>
        KID Diagnostic nu scrie direct în ECU/controller și nu inventează Long Coding, Byte/Bit, Security Access, Adaptation sau Basic Settings. Valorile exacte trebuie să provină din controllerul/mașina corectă și din procedură documentată.</div>
    </body></html>
    """


def _strip_previous_recovery(text):
    return re.sub(
        r"\n*=== KID CODING RECOVERY V2\.3\.0 ===.*?=== END KID CODING RECOVERY ===\n*",
        "\n",
        str(text or ""),
        flags=re.S,
    ).strip()


def _make_panel(owner):
    panel = QFrame()
    panel.setObjectName("kidCodingRecoveryPanel")
    row = QHBoxLayout(panel)
    row.setContentsMargins(13, 8, 13, 8)
    row.setSpacing(10)

    text_box = QVBoxLayout()
    title = QLabel("CODING / ÎNLOCUIRE MODUL")
    title.setObjectName("kidCodingRecoveryTitle")
    state = QLabel("Încarcă Auto-Scan-ul VCDS pentru verificare automată.")
    state.setObjectName("kidCodingRecoveryState")
    state.setWordWrap(True)
    text_box.addWidget(title)
    text_box.addWidget(state)
    row.addLayout(text_box, 1)

    badge = QLabel("NEVERIFICAT")
    badge.setObjectName("kidCodingRecoveryBadge")
    badge.setAlignment(Qt.AlignCenter)
    row.addWidget(badge)

    button = QPushButton("ASISTENT CODARE")
    button.setObjectName("kidCodingRecoveryButton")
    button.setEnabled(False)
    button.clicked.connect(owner.open_module_replacement_assistant_v230)
    row.addWidget(button)

    panel._kid_state = state
    panel._kid_badge = badge
    panel._kid_button = button
    panel.setStyleSheet("""
      #kidCodingRecoveryPanel { background:#f7fbff; border:1px solid #cbdce8; border-radius:10px; }
      #kidCodingRecoveryTitle { color:#285b80; font-size:11px; font-weight:900; letter-spacing:.6px; }
      #kidCodingRecoveryState { color:#30485a; font-size:12px; font-weight:650; }
      #kidCodingRecoveryBadge { background:#e9f1f7; color:#536a7b; border-radius:8px; padding:7px 10px; font-weight:900; }
      #kidCodingRecoveryButton { background:#ffffff; color:#205b86; border:1px solid #a9cbe2; border-radius:8px; padding:8px 12px; font-weight:850; }
      #kidCodingRecoveryButton:hover { background:#eaf6ff; }
    """)
    return panel


def _panel_state(panel, analysis, has_scan):
    if not has_scan:
        panel._kid_state.setText("Încarcă Auto-Scan-ul VCDS pentru verificare automată.")
        panel._kid_badge.setText("NEVERIFICAT")
        panel._kid_badge.setStyleSheet("")
        panel._kid_button.setEnabled(False)
        return
    panel._kid_button.setEnabled(True)
    panel._kid_state.setText(
        analysis.summary()
        + f" • {len(analysis.modules_without_coding_line)} module fără linie Coding nu sunt declarate automat necodate."
    )
    if analysis.blocking_count:
        panel._kid_badge.setText("BLOCAJ ONLINE")
        panel._kid_badge.setStyleSheet("background:#ffe7e7;color:#932c2c;border-radius:8px;padding:7px 10px;font-weight:900;")
    elif analysis.coding_fault_count:
        panel._kid_badge.setText("CODING NECESAR")
        panel._kid_badge.setStyleSheet("background:#fff0d7;color:#875400;border-radius:8px;padding:7px 10px;font-weight:900;")
    elif analysis.basic_setting_count:
        panel._kid_badge.setText("ADAPTARE")
        panel._kid_badge.setStyleSheet("background:#fff5dd;color:#7c590e;border-radius:8px;padding:7px 10px;font-weight:900;")
    else:
        panel._kid_badge.setText("FĂRĂ DTC CODING")
        panel._kid_badge.setStyleSheet("background:#e8f7ee;color:#226844;border-radius:8px;padding:7px 10px;font-weight:900;")


def apply():
    import ui_v2

    cls = ui_v2.MainWindowV2
    if getattr(cls, "_kid_module_replacement_v230_applied", False):
        return

    previous_init = cls.__init__
    previous_load_autoscan = cls._load_autoscan
    previous_select_vehicle = cls._select_vehicle
    previous_show_autoscan_fault = cls._show_autoscan_fault

    def refresh_recovery(self):
        scan = getattr(self, "current_autoscan", None)
        analysis = analyze_replacement_coding(scan)
        self.module_replacement_analysis = analysis
        panel = getattr(self, "kid_coding_recovery_panel", None)
        if panel is not None:
            _panel_state(panel, analysis, scan is not None)

        base = _strip_previous_recovery(getattr(self, "v2_verified_report_text", ""))
        if scan is not None:
            section = render_recovery_text(analysis)
            self.v2_verified_report_text = (base + "\n\n" + section).strip() if base else section
        else:
            self.v2_verified_report_text = base
        return analysis

    def init_recovery(self, *args, **kwargs):
        previous_init(self, *args, **kwargs)
        self.module_replacement_analysis = analyze_replacement_coding(None)
        self._coding_recovery_dialog = None
        page = (getattr(self, "_workspace_pages", {}) or {}).get(1)
        if page is None:
            try:
                page = self.stack.widget(1)
            except Exception:
                page = None
        if page is not None and page.layout() is not None:
            panel = _make_panel(self)
            self.kid_coding_recovery_panel = panel
            position = page.layout().indexOf(getattr(self, "autoscan_summary", None))
            page.layout().insertWidget(max(1, position + 1), panel)
        refresh_recovery(self)

    def load_autoscan_recovery(self):
        previous_load_autoscan(self)
        refresh_recovery(self)

    def select_vehicle_recovery(self):
        previous_select_vehicle(self)
        refresh_recovery(self)

    def show_autoscan_fault_recovery(self):
        previous_show_autoscan_fault(self)
        row = getattr(self, "autoscan_table", None).currentRow() if getattr(self, "autoscan_table", None) is not None else -1
        plans = list(getattr(self, "autoscan_plans", []) or [])
        if row < 0 or row >= len(plans):
            return
        fault = plans[row][0]
        code = str(getattr(fault, "code", "") or getattr(fault, "vag_code", "") or "").upper()
        address = _norm_addr(getattr(fault, "module_address", ""))
        analysis = getattr(self, "module_replacement_analysis", None)
        if analysis is None:
            return
        match = next((item for item in analysis.findings if item.address == address and (not code or item.dtc_code == code)), None)
        if match is None:
            return
        detail = getattr(self, "autoscan_detail", None)
        if detail is None:
            return
        old = detail.toPlainText()
        prefix = (
            f"KID CODING RECOVERY — {match.severity}: {match.label}\n"
            f"Address {match.address} • {match.dtc_code or match.dtc_title}\n"
            "Deschide ASISTENT CODARE pentru pașii de verificare/codare după înlocuire.\n\n"
        )
        if not old.startswith("KID CODING RECOVERY"):
            detail.setPlainText(prefix + old)

    def open_coding_for_item(self, item):
        self.open_page(3)
        page = (getattr(self, "_workspace_pages", {}) or {}).get(3)
        if page is None or getattr(page, "table", None) is None:
            return False
        rows = page.table.property("rows") or []
        target = _norm_addr(item.address)
        for index, row in enumerate(rows):
            try:
                address = _norm_addr(row["module_address"])
            except Exception:
                address = ""
            if address == target:
                page.table.selectRow(index)
                page.table.scrollToItem(page.table.item(index, 0))
                return True
        QMessageBox.information(
            self,
            "Coding Recovery",
            f"Nu există în baza locală o procedură exactă pentru Address {target}. "
            "Păstrează identificarea controllerului și folosește documentația VCDS/fabrică pentru Part No-ul exact; KID nu va inventa coding-ul.",
        )
        return False

    def open_assistant(self):
        analysis = refresh_recovery(self)
        dialog = getattr(self, "_coding_recovery_dialog", None)
        if dialog is not None:
            try:
                dialog.close()
            except RuntimeError:
                pass
        dialog = QDialog(self)
        dialog.setWindowTitle(f"KID Diagnostic • Coding Recovery • v{MODULE_REPLACEMENT_VERSION}")
        dialog.resize(1240, 790)
        root = QVBoxLayout(dialog)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(11)

        heading = QLabel("ÎNLOCUIRE MODUL / CODING RECOVERY")
        heading.setStyleSheet("font-size:20px;font-weight:900;color:#173c58;")
        sub = QLabel(
            (getattr(self, "vehicle_badge", None).text() if getattr(self, "vehicle_badge", None) else "")
            + "\n" + analysis.summary()
        )
        sub.setWordWrap(True)
        sub.setStyleSheet("font-size:13px;color:#486276;")
        root.addWidget(heading)
        root.addWidget(sub)

        split = QSplitter(Qt.Horizontal)
        table = QTableWidget(0, 6)
        table.setHorizontalHeaderLabels(["Nivel", "Adresă", "Modul", "Problemă", "DTC", "Coding din scan"])
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(38)
        table.horizontalHeader().setMinimumHeight(38)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        detail = QTextEdit()
        detail.setReadOnly(True)
        detail.setMinimumWidth(500)
        split.addWidget(table)
        split.addWidget(detail)
        split.setSizes([650, 550])
        root.addWidget(split, 1)

        findings = list(analysis.findings)
        table.setRowCount(len(findings))
        for row, item in enumerate(findings):
            values = [item.severity, item.address, item.module_name, item.label, item.dtc_code or item.dtc_title, item.coding or "—"]
            for column, value in enumerate(values):
                table.setItem(row, column, QTableWidgetItem(str(value)))
        table.setProperty("kidCodingFindings", findings)

        if findings:
            table.selectRow(0)
            detail.setHtml(_finding_html(self, findings[0]))
        else:
            detail.setHtml(
                "<h2>Nu există DTC explicit de coding în scanarea curentă</h2>"
                "<p>KID nu transformă lipsa liniei <b>Coding:</b> într-un diagnostic fals. "
                "Dacă ai schimbat fizic un modul și nu apare 01042/U1013/01044, verifică identificarea modulului, "
                "Installation List și procedura specifică acelui controller.</p>"
            )

        def selection_changed():
            row = table.currentRow()
            if 0 <= row < len(findings):
                detail.setHtml(_finding_html(self, findings[row]))

        def go_coding():
            row = table.currentRow()
            if 0 <= row < len(findings):
                item = findings[row]
                if item.requires_online:
                    QMessageBox.warning(
                        dialog,
                        "Component Protection",
                        "Acest caz este marcat ca blocaj online. KID nu îl tratează ca simplă recodare VCDS. "
                        "Poți consulta procedurile locale, dar eliminarea Component Protection cere procedura de fabrică unde DTC-ul o indică.",
                    )
                self.open_module_replacement_coding_v230(item)
                dialog.close()

        table.itemSelectionChanged.connect(selection_changed)
        buttons = QHBoxLayout()
        coding_btn = QPushButton("DESCHIDE CODĂRI PENTRU MODUL")
        coding_btn.setEnabled(bool(findings))
        coding_btn.clicked.connect(go_coding)
        close_btn = QPushButton("ÎNCHIDE")
        close_btn.clicked.connect(dialog.close)
        buttons.addStretch(1)
        buttons.addWidget(coding_btn)
        buttons.addWidget(close_btn)
        root.addLayout(buttons)
        dialog.setStyleSheet(
            "QDialog{background:#f4f8fb;} QTableWidget,QTextEdit{background:white;border:1px solid #d3e0e9;border-radius:9px;font-size:13px;} "
            "QTableWidget::item{padding:7px;} QPushButton{padding:9px 13px;border-radius:8px;border:1px solid #b8cfdf;background:white;color:#285b80;font-weight:800;}"
        )
        dialog.setAttribute(Qt.WA_DeleteOnClose, True)
        dialog.destroyed.connect(lambda: setattr(self, "_coding_recovery_dialog", None))
        self._coding_recovery_dialog = dialog
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    cls.refresh_module_replacement_v230 = refresh_recovery
    cls.open_module_replacement_assistant_v230 = open_assistant
    cls.open_module_replacement_coding_v230 = open_coding_for_item
    cls.__init__ = init_recovery
    cls._load_autoscan = load_autoscan_recovery
    cls._select_vehicle = select_vehicle_recovery
    cls._show_autoscan_fault = show_autoscan_fault_recovery
    cls._kid_module_replacement_v230_applied = True


__all__ = ["PATCH_VERSION", "apply"]
