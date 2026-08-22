"""Safe vector artwork for the V2 dashboard cards."""
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen, QPolygon


def paint_card_art(self, _event):
    p = QPainter(self)
    p.setRenderHint(QPainter.Antialiasing)
    r = self.rect().adjusted(3, 3, -3, -3)
    g = QLinearGradient(r.topLeft(), r.bottomRight())
    g.setColorAt(0, QColor("#123b67"))
    g.setColorAt(.55, QColor("#0b2744"))
    g.setColorAt(1, QColor("#06131f"))
    p.setBrush(g)
    p.setPen(QPen(QColor("#1b557d"), 1))
    p.drawRoundedRect(r, 18, 18)

    x, y, w, h = r.x(), r.y(), r.width(), r.height()
    cyan, pale, dim = QColor("#36c0ff"), QColor("#dff4ff"), QColor("#4f7592")
    code = str(getattr(self, "code", "")).upper()
    p.setPen(QPen(cyan, 4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)

    if code == "SCAN":
        for a, b in [
            ((.18,.62),(.80,.62)), ((.29,.62),(.39,.39)),
            ((.39,.39),(.62,.39)), ((.62,.39),(.73,.62)),
        ]:
            p.drawLine(int(x+w*a[0]), int(y+h*a[1]), int(x+w*b[0]), int(y+h*b[1]))
        p.drawEllipse(int(x+w*.28), int(y+h*.55), 18, 18)
        p.drawEllipse(int(x+w*.65), int(y+h*.55), 18, 18)
        p.setPen(QPen(pale, 2))
        for k in range(3):
            yy = int(y+h*(.22+k*.11))
            p.drawLine(int(x+w*.13), yy, int(x+w*.28), yy)

    elif code == "DTC":
        p.drawPolygon(QPolygon([
            QPoint(int(x+w*.50), int(y+h*.20)),
            QPoint(int(x+w*.27), int(y+h*.72)),
            QPoint(int(x+w*.73), int(y+h*.72)),
        ]))
        p.setPen(QPen(pale, 5, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(int(x+w*.50), int(y+h*.37), int(x+w*.50), int(y+h*.53))
        p.drawPoint(int(x+w*.50), int(y+h*.62))

    elif code == "CODE":
        for a,b in [((.31,.28),(.20,.46)),((.20,.46),(.31,.64)),((.69,.28),(.80,.46)),((.80,.46),(.69,.64))]:
            p.drawLine(int(x+w*a[0]), int(y+h*a[1]), int(x+w*b[0]), int(y+h*b[1]))
        p.setPen(QPen(pale, 3))
        for frac in (.39,.47,.55,.63):
            xx = int(x+w*frac)
            p.drawLine(xx, int(y+h*.34), xx, int(y+h*.58))

    elif code == "ADAPT":
        for frac, knob in ((.30,.40),(.48,.63),(.66,.48)):
            yy = int(y+h*frac)
            p.drawLine(int(x+w*.24), yy, int(x+w*.76), yy)
            p.setBrush(QColor("#0c2740"))
            p.drawEllipse(int(x+w*knob)-7, yy-7, 14, 14)
            p.setBrush(Qt.NoBrush)

    elif code == "SERV":
        p.drawArc(int(x+w*.27), int(y+h*.21), int(w*.28), int(h*.32), 35*16, 270*16)
        p.drawLine(int(x+w*.46), int(y+h*.45), int(x+w*.70), int(y+h*.69))
        p.drawEllipse(int(x+w*.66), int(y+h*.64), 12, 12)

    elif code == "LIVE":
        p.setPen(QPen(dim, 2))
        p.drawLine(int(x+w*.20), int(y+h*.70), int(x+w*.80), int(y+h*.70))
        p.drawLine(int(x+w*.20), int(y+h*.25), int(x+w*.20), int(y+h*.70))
        p.setPen(QPen(cyan, 4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        pts = [(0.24,.60),(0.34,.49),(0.43,.56),(0.53,.32),(0.64,.43),(0.76,.25)]
        for a,b in zip(pts, pts[1:]):
            p.drawLine(int(x+w*a[0]), int(y+h*a[1]), int(x+w*b[0]), int(y+h*b[1]))

    elif code == "MOD":
        nodes = [(0.30,.35),(0.66,.30),(0.50,.66),(0.75,.67)]
        p.setPen(QPen(dim, 2))
        for a,b in ((0,2),(1,2),(2,3),(1,3)):
            p.drawLine(int(x+w*nodes[a][0]), int(y+h*nodes[a][1]),
                       int(x+w*nodes[b][0]), int(y+h*nodes[b][1]))
        p.setPen(QPen(cyan, 3))
        p.setBrush(QColor("#0a263e"))
        for nx,ny in nodes:
            p.drawRoundedRect(int(x+w*nx)-10, int(y+h*ny)-8, 20, 16, 4, 4)
        p.setBrush(Qt.NoBrush)

    elif code == "PDF":
        px, py, pw, ph = int(x+w*.34), int(y+h*.18), int(w*.34), int(h*.60)
        p.drawRoundedRect(px, py, pw, ph, 6, 6)
        p.setPen(QPen(pale, 2))
        for frac in (.38,.49,.60):
            yy = int(y+h*frac)
            p.drawLine(int(x+w*.40), yy, int(x+w*.62), yy)
        p.setFont(QFont("Arial", 9, QFont.Bold))
        p.drawText(px, int(y+h*.22), pw, int(h*.15), Qt.AlignCenter, "KID")

    p.setPen(pale)
    f = QFont("Arial", 9)
    f.setBold(True)
    p.setFont(f)
    p.drawText(r.adjusted(10, 7, -10, -7), Qt.AlignRight | Qt.AlignTop, code)


def apply():
    import ui_v2
    ui_v2.CardArt.paintEvent = paint_card_art
