def apply(MainWindow):
    old_style = MainWindow.apply_style

    def apply_style_vag(self):
        # Balanced VAG workshop theme: graphite surfaces + electric blue accents.
        old_style(self)
        self.setStyleSheet('''
        QMainWindow, QWidget {
            background:#17212b;
            color:#e8f0f7;
            font-family:"Segoe UI", Arial;
            font-size:13px;
        }
        QFrame#sidebar {
            background:#111922;
            border-right:1px solid #2b3b4b;
        }
        QFrame#content { background:#17212b; }

        QLabel#brand { font-size:18px; font-weight:900; color:#ffffff; }
        QLabel#brandSub { font-size:10px; color:#36b9ff; font-weight:800; letter-spacing:1px; }
        QLabel#version { color:#8394a5; font-size:11px; padding:8px; }
        QLabel#pageTitle { font-size:27px; font-weight:900; color:#f4f8fb; }
        QLabel#vehicleBadge {
            background:#18334a;
            border:1px solid #28628d;
            border-radius:16px;
            padding:9px 15px;
            color:#7dd3ff;
            font-weight:800;
        }
        QLabel#hero { font-size:30px; font-weight:900; color:#ffffff; }
        QLabel#heroSub { font-size:14px; color:#a5b5c4; }
        QLabel#sectionTitle { font-size:19px; font-weight:900; color:#f1f6fa; }
        QLabel#body { color:#c5d1dc; }
        QLabel#muted { color:#8fa1b2; }
        QLabel#fieldLabel { color:#93a7b8; font-size:11px; font-weight:800; }
        QLabel#detailTitle { font-size:18px; font-weight:900; color:#eaf5ff; padding:4px; }

        QFrame#selector, QFrame#statCard, QFrame#infoCard, QFrame#detailPanel {
            background:#202d39;
            border:1px solid #314354;
            border-radius:14px;
        }
        QFrame#selector { border:1px solid #315c7a; }
        QLabel#statTitle { color:#91a5b6; font-weight:800; }
        QLabel#statValue { font-size:28px; font-weight:900; color:#62c8ff; }
        QLabel#warning {
            background:#392f1f;
            color:#ffd98a;
            border:1px solid #715a2d;
            border-radius:9px;
            padding:10px;
        }

        QPushButton#nav {
            background:transparent;
            border:0;
            text-align:left;
            padding:12px 14px;
            border-radius:10px;
            color:#a9bac8;
            font-weight:700;
        }
        QPushButton#nav:hover { background:#1b2c3a; color:#72d0ff; }
        QPushButton#nav:checked {
            background:#173a54;
            color:#8bd9ff;
            border-left:4px solid #1aa8f0;
        }

        QComboBox, QLineEdit {
            background:#111b24;
            border:1px solid #3b5062;
            border-radius:9px;
            padding:9px 10px;
            color:#edf5fb;
            min-height:20px;
        }
        QComboBox:hover, QLineEdit:focus { border:1px solid #25aef2; }
        QComboBox::drop-down { border:0; width:26px; }
        QComboBox QAbstractItemView { background:#17232e; color:#eef5fa; selection-background-color:#17547a; }

        QPushButton#primary {
            background:#087fc1;
            border:0;
            border-radius:9px;
            padding:11px 19px;
            color:white;
            font-weight:900;
        }
        QPushButton#primary:hover { background:#129ee8; }

        QPushButton {
            background:#243442;
            border:1px solid #3a5062;
            border-radius:9px;
            padding:9px 14px;
            color:#dce8f1;
            font-weight:600;
        }
        QPushButton:hover { background:#29465a; border-color:#298fc5; }
        QPushButton#toolButton { text-align:left; min-height:34px; font-weight:700; }

        QPushButton#categoryChip {
            background:#1e2d39;
            border:1px solid #3b5264;
            border-radius:15px;
            padding:7px 12px;
            color:#b8c8d5;
            font-weight:800;
        }
        QPushButton#categoryChip:hover { border-color:#25aef2; color:#7dd3ff; }
        QPushButton#categoryChip:checked { background:#087fc1; border-color:#21aef2; color:white; }

        QTableWidget {
            background:#1c2934;
            alternate-background-color:#202f3b;
            border:1px solid #344858;
            border-radius:10px;
            gridline-color:#30414f;
            color:#dce7ef;
            selection-background-color:#15567d;
            selection-color:#ffffff;
        }
        QHeaderView::section {
            background:#253744;
            color:#bfe9ff;
            border:0;
            border-bottom:1px solid #3c5364;
            padding:10px;
            font-weight:900;
        }
        QTableWidget::item { padding:6px; }

        QTextEdit {
            background:#141f28;
            border:1px solid #354b5b;
            border-radius:9px;
            padding:10px;
            color:#d8e4ec;
            selection-background-color:#17648e;
        }

        QStatusBar {
            background:#111922;
            color:#8ea1b1;
            border-top:1px solid #2d3e4c;
        }
        QSplitter::handle { background:#334654; width:2px; }
        QScrollBar:vertical { background:#17232d; width:11px; margin:0; }
        QScrollBar::handle:vertical { background:#496071; border-radius:5px; min-height:30px; }
        QScrollBar::handle:vertical:hover { background:#258cc2; }
        ''')

    MainWindow.apply_style = apply_style_vag
