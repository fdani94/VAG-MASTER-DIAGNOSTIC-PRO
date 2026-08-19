from PySide6.QtGui import QColor, QPalette


def apply(MainWindow):
    old_style = MainWindow.apply_style

    def apply_style_vag(self):
        # Bright VAG-inspired workshop theme. Keeps all existing widgets/functions intact.
        old_style(self)
        self.setStyleSheet('''
        QMainWindow, QWidget {
            background:#f4f8fc;
            color:#122033;
            font-family:"Segoe UI", Arial;
            font-size:13px;
        }
        QFrame#sidebar {
            background:#ffffff;
            border-right:1px solid #d9e5f2;
        }
        QFrame#content { background:#f4f8fc; }

        QLabel#brand { font-size:18px; font-weight:900; color:#0a3d78; }
        QLabel#brandSub { font-size:10px; color:#08a9d6; font-weight:800; letter-spacing:1px; }
        QLabel#version { color:#6d7f93; font-size:11px; padding:8px; }
        QLabel#pageTitle { font-size:27px; font-weight:900; color:#0a2f5a; }
        QLabel#vehicleBadge {
            background:#e8f4ff;
            border:1px solid #a8d8f6;
            border-radius:16px;
            padding:9px 15px;
            color:#0b5f9e;
            font-weight:800;
        }
        QLabel#hero { font-size:30px; font-weight:900; color:#0a2f5a; }
        QLabel#heroSub { font-size:14px; color:#60748a; }
        QLabel#sectionTitle { font-size:19px; font-weight:900; color:#173a62; }
        QLabel#body { color:#40566f; }
        QLabel#muted { color:#74879a; }
        QLabel#fieldLabel { color:#5f7489; font-size:11px; font-weight:800; }
        QLabel#detailTitle { font-size:18px; font-weight:900; color:#163c67; padding:4px; }

        QFrame#selector, QFrame#statCard, QFrame#infoCard, QFrame#detailPanel {
            background:#ffffff;
            border:1px solid #d8e5f1;
            border-radius:14px;
        }
        QFrame#selector { border:1px solid #bddaf0; }
        QLabel#statTitle { color:#6f8194; font-weight:800; }
        QLabel#statValue { font-size:28px; font-weight:900; color:#0b4c86; }
        QLabel#warning {
            background:#fff7dc;
            color:#8a5a00;
            border:1px solid #f2d47a;
            border-radius:9px;
            padding:10px;
        }

        QPushButton#nav {
            background:transparent;
            border:0;
            text-align:left;
            padding:12px 14px;
            border-radius:10px;
            color:#49627d;
            font-weight:700;
        }
        QPushButton#nav:hover { background:#edf6ff; color:#0b5f9e; }
        QPushButton#nav:checked {
            background:#dff1ff;
            color:#075f9e;
            border-left:4px solid #079dcc;
        }

        QComboBox, QLineEdit {
            background:#ffffff;
            border:1px solid #c7d7e6;
            border-radius:9px;
            padding:9px 10px;
            color:#17324d;
            min-height:20px;
        }
        QComboBox:hover, QLineEdit:focus { border:1px solid #079dcc; }
        QComboBox::drop-down { border:0; width:26px; }

        QPushButton#primary {
            background:#0b6fb2;
            border:0;
            border-radius:9px;
            padding:11px 19px;
            color:white;
            font-weight:900;
        }
        QPushButton#primary:hover { background:#078ec2; }

        QPushButton {
            background:#ffffff;
            border:1px solid #c7d7e6;
            border-radius:9px;
            padding:9px 14px;
            color:#24435f;
            font-weight:600;
        }
        QPushButton:hover { background:#edf7ff; border-color:#86c8ea; }
        QPushButton#toolButton { text-align:left; min-height:34px; font-weight:700; }

        QPushButton#categoryChip {
            background:#ffffff;
            border:1px solid #bfd6e8;
            border-radius:15px;
            padding:7px 12px;
            color:#3e5e78;
            font-weight:800;
        }
        QPushButton#categoryChip:hover { border-color:#079dcc; color:#0b5f9e; }
        QPushButton#categoryChip:checked { background:#0b6fb2; border-color:#0b6fb2; color:white; }

        QTableWidget {
            background:#ffffff;
            alternate-background-color:#f7fbff;
            border:1px solid #d7e4ef;
            border-radius:10px;
            gridline-color:#e5eef6;
            selection-background-color:#ccecff;
            selection-color:#0a2f5a;
        }
        QHeaderView::section {
            background:#eaf4fb;
            color:#315774;
            border:0;
            border-bottom:1px solid #cddfea;
            padding:10px;
            font-weight:900;
        }
        QTableWidget::item { padding:6px; }

        QTextEdit {
            background:#ffffff;
            border:1px solid #d5e3ee;
            border-radius:9px;
            padding:10px;
            color:#233e58;
            selection-background-color:#b8e3ff;
        }

        QStatusBar {
            background:#ffffff;
            color:#6f8194;
            border-top:1px solid #dce7f0;
        }
        QSplitter::handle { background:#dce9f3; width:2px; }
        QScrollBar:vertical { background:#eef4f8; width:11px; margin:0; }
        QScrollBar::handle:vertical { background:#b7cada; border-radius:5px; min-height:30px; }
        QScrollBar::handle:vertical:hover { background:#8db7d2; }
        ''')

    MainWindow.apply_style = apply_style_vag
