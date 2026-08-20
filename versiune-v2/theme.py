APP_STYLE = r"""
* {
    font-family: "Segoe UI", "Inter", sans-serif;
    color: #eaf2fb;
    outline: none;
}
QWidget {
    background: transparent;
    font-size: 13px;
}
QMainWindow, QDialog {
    background: #070d15;
}
QFrame#appShell {
    background: #08111c;
    border: 1px solid #28415a;
    border-radius: 14px;
}
QFrame#titleBar {
    background: #0b1521;
    border-bottom: 1px solid #1c3043;
    border-top-left-radius: 14px;
    border-top-right-radius: 14px;
}
QLabel#brandTitle {
    font-size: 20px;
    font-weight: 700;
    letter-spacing: 1px;
}
QLabel#brandSubtitle {
    color: #39b9ff;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.8px;
}
QPushButton#windowButton {
    background: transparent;
    border: none;
    border-radius: 8px;
    min-width: 34px;
    min-height: 30px;
    font-size: 16px;
}
QPushButton#windowButton:hover {
    background: #172638;
}
QPushButton#closeButton {
    background: transparent;
    border: none;
    border-radius: 8px;
    min-width: 34px;
    min-height: 30px;
    font-size: 17px;
}
QPushButton#closeButton:hover {
    background: #d9485f;
    color: white;
}
QFrame#statusChip {
    background: #0d1926;
    border: 1px solid #24384d;
    border-radius: 15px;
}
QFrame#statusChip[state="ok"] {
    border-color: #1c6149;
    background: #0b201c;
}
QFrame#statusChip[state="info"] {
    border-color: #1d5272;
    background: #0b1c29;
}
QFrame#statusChip[state="warn"] {
    border-color: #6f4c1b;
    background: #24190b;
}
QFrame#vehicleHero {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #0b1927, stop:0.5 #101d2b, stop:1 #08131e);
    border: 1px solid #27445f;
    border-left: 3px solid #23aff8;
    border-radius: 12px;
}
QLabel#vehicleName {
    font-size: 25px;
    font-weight: 700;
}
QLabel#vehicleSubtitle {
    color: #c4d1df;
    font-size: 16px;
}
QFrame#brandRoundel {
    background: #0a1723;
    border: 2px solid #80cfff;
    border-radius: 31px;
}
QLabel#brandRoundelText {
    color: #f5fbff;
    font-size: 19px;
    font-weight: 800;
}
QFrame#heroMetric {
    background: #0b1521;
    border: 1px solid #22374b;
    border-radius: 8px;
}
QLabel#metricCaption {
    color: #7f93a8;
    font-size: 10px;
    text-transform: uppercase;
}
QLabel#metricValue {
    color: #e8f3fd;
    font-size: 13px;
    font-weight: 600;
}
QFrame#featureTile {
    background: #0b1521;
    border: 1px solid #284a67;
    border-radius: 12px;
}
QFrame#featureTile[hovered="true"] {
    background: #0d1b29;
    border: 1px solid #28b9ff;
}
QLabel#tileTitle {
    font-size: 15px;
    font-weight: 700;
    color: #f2f8ff;
}
QLabel#tileSubtitle {
    font-size: 10px;
    color: #7890a6;
}
QLabel#accentLine {
    background: #23b6fb;
    border-radius: 1px;
    max-height: 2px;
    min-height: 2px;
}
QFrame#footerBar {
    background: #0a141f;
    border-top: 1px solid #1b3043;
}
QLabel#footerCaption {
    color: #758ba0;
    font-size: 10px;
}
QLabel#footerValue {
    color: #cfeeff;
    font-size: 11px;
    font-weight: 600;
}
QPushButton {
    background: #122235;
    border: 1px solid #2a455f;
    border-radius: 8px;
    padding: 9px 14px;
    color: #e8f4ff;
    font-weight: 600;
}
QPushButton:hover {
    background: #183149;
    border-color: #30baff;
}
QPushButton:pressed {
    background: #0f2639;
}
QPushButton:disabled {
    color: #5e7183;
    background: #0c1620;
    border-color: #1b2a38;
}
QPushButton#accentButton {
    background: #087db8;
    border-color: #27baff;
    color: white;
}
QPushButton#accentButton:hover {
    background: #0b93d3;
}
QPushButton#dangerButton {
    background: #48202a;
    border-color: #82404f;
}
QPushButton#dangerButton:hover {
    background: #6a2938;
    border-color: #e26679;
}
QLineEdit, QComboBox, QSpinBox {
    background: #0a1520;
    border: 1px solid #284157;
    border-radius: 8px;
    padding: 9px 11px;
    selection-background-color: #0c84bd;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    border-color: #25b7fa;
}
QComboBox::drop-down {
    border: none;
    width: 26px;
}
QComboBox QAbstractItemView {
    background: #0c1723;
    border: 1px solid #29445c;
    selection-background-color: #123b56;
}
QTextEdit, QPlainTextEdit {
    background: #09131d;
    border: 1px solid #263e54;
    border-radius: 8px;
    padding: 8px;
    selection-background-color: #0d7fb6;
}
QTableWidget, QTreeWidget, QListWidget {
    background: #09131d;
    alternate-background-color: #0c1824;
    border: 1px solid #243d53;
    border-radius: 9px;
    gridline-color: #1d3042;
    selection-background-color: #123e59;
    selection-color: #ffffff;
}
QHeaderView::section {
    background: #102031;
    color: #a9bed0;
    border: none;
    border-right: 1px solid #233b50;
    border-bottom: 1px solid #233b50;
    padding: 9px;
    font-weight: 600;
}
QTableWidget::item, QTreeWidget::item, QListWidget::item {
    padding: 7px;
}
QScrollBar:vertical {
    background: #09131d;
    width: 10px;
    margin: 4px 2px;
}
QScrollBar::handle:vertical {
    background: #2a4961;
    min-height: 30px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #37a8dd;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QProgressBar {
    background: #0a1520;
    border: 1px solid #233c51;
    border-radius: 5px;
    height: 9px;
    text-align: center;
    color: transparent;
}
QProgressBar::chunk {
    border-radius: 4px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #119dd9, stop:1 #28c0ff);
}
QTabWidget::pane {
    border: 1px solid #263e54;
    border-radius: 9px;
    top: -1px;
    background: #09131d;
}
QTabBar::tab {
    background: #0e1c2a;
    border: 1px solid #263e54;
    padding: 9px 15px;
    color: #8fa5b8;
}
QTabBar::tab:selected {
    color: white;
    border-bottom: 2px solid #28b9ff;
    background: #12283b;
}
QFrame#sectionCard {
    background: #0b1723;
    border: 1px solid #263f55;
    border-radius: 10px;
}
QLabel#sectionTitle {
    font-size: 14px;
    font-weight: 700;
    color: #f1f7fd;
}
QLabel#sectionIcon {
    color: #2dbbff;
    font-size: 18px;
    font-weight: 800;
}
QLabel#pageTitle {
    font-size: 23px;
    font-weight: 700;
}
QLabel#pageSubtitle {
    color: #8399ad;
    font-size: 12px;
}
QLabel#dtcCode {
    color: #ffb432;
    font-size: 31px;
    font-weight: 800;
}
QLabel#severityHigh {
    color: #ffbc45;
    background: #2b1d0b;
    border: 1px solid #704d1b;
    border-radius: 10px;
    padding: 4px 8px;
}
QLabel#safetyBox {
    color: #ffd28b;
    background: #24190d;
    border: 1px solid #68461d;
    border-radius: 8px;
    padding: 9px;
}
QLabel#successBox {
    color: #a9f3cc;
    background: #0b211a;
    border: 1px solid #1e6148;
    border-radius: 8px;
    padding: 9px;
}
QToolTip {
    background: #101e2c;
    color: white;
    border: 1px solid #2b526d;
    padding: 6px;
}
"""
