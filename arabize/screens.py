"""Monitor / TV mapping between capture (physical pixels) and Qt screens, plus the region picker."""
from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import QWidget

from .capture import Capturer, Monitor


def qscreen_for(index: int):
    """The QScreen that shows capture monitor `index` (1-based)."""
    screens = QGuiApplication.screens()
    try:
        mons = Capturer().monitors()
    except Exception:
        mons = []
    if 1 <= index <= len(mons):
        m = mons[index - 1]
        for s in screens:
            g, d = s.geometry(), s.devicePixelRatio()
            if abs(g.x() * d - m.left) < 8 and abs(g.y() * d - m.top) < 8:
                return s
            if abs(g.x() - m.left) < 8 and abs(g.y() - m.top) < 8:
                return s
        # mixed-DPI layouts: fall back to the same left-to-right order
        order_m = sorted(range(len(mons)), key=lambda i: (mons[i].left, mons[i].top))
        order_s = sorted(screens, key=lambda s: (s.geometry().x(), s.geometry().y()))
        pos = order_m.index(index - 1)
        if pos < len(order_s):
            return order_s[pos]
    return QGuiApplication.primaryScreen()


def screen_label(qs) -> str:
    name = (qs.manufacturer() + " " + qs.model()).strip() or qs.name()
    g = qs.geometry()
    d = qs.devicePixelRatio()
    return f"{name} — {int(g.width() * d)}×{int(g.height() * d)}"


class RegionSelector(QWidget):
    """Full-screen picker shown on one monitor: drag a rectangle around the game text."""
    selected = Signal(list)   # [x, y, w, h] physical pixels relative to the monitor
    cancelled = Signal()

    def __init__(self, qscreen, current: list | None = None):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.qs = qscreen
        self.dpr = qscreen.devicePixelRatio()
        self.bg = qscreen.grabWindow(0)
        self.setGeometry(qscreen.geometry())
        self.setCursor(Qt.CrossCursor)
        self.origin: QPoint | None = None
        self.rect_sel = QRect()
        if current:
            x, y, w, h = current
            self.rect_sel = QRect(int(x / self.dpr), int(y / self.dpr), int(w / self.dpr), int(h / self.dpr))

    def paintEvent(self, _):
        p = QPainter(self)
        p.drawPixmap(self.rect(), self.bg)
        p.fillRect(self.rect(), QColor(3, 5, 12, 150))
        if not self.rect_sel.isNull():
            r = self.rect_sel.normalized()
            src = QRectF(r.x() * self.dpr, r.y() * self.dpr, r.width() * self.dpr, r.height() * self.dpr)
            p.drawPixmap(QRectF(r), self.bg, src)
            p.setPen(QPen(QColor("#E7B964"), 2))
            p.drawRect(r)
            p.setPen(QColor("#F6DCA0"))
            f = QFont(); f.setPixelSize(13); p.setFont(f)
            p.drawText(r.adjusted(0, -22, 0, 0).topLeft(), f"{int(r.width() * self.dpr)} × {int(r.height() * self.dpr)}")
        f = QFont(); f.setPixelSize(22); f.setBold(True); p.setFont(f)
        p.setPen(QColor("#FFFFFF"))
        p.drawText(self.rect().adjusted(0, 40, 0, 0), Qt.AlignHCenter | Qt.AlignTop,
                   "حدّد مكان النص في اللعبة بالسحب — Enter للتأكيد، Esc للإلغاء")
        p.end()

    def mousePressEvent(self, e):
        self.origin = e.position().toPoint()
        self.rect_sel = QRect(self.origin, self.origin)
        self.update()

    def mouseMoveEvent(self, e):
        if self.origin is not None:
            self.rect_sel = QRect(self.origin, e.position().toPoint()).normalized()
            self.update()

    def mouseReleaseEvent(self, _):
        self.origin = None
        if self.rect_sel.width() > 12 and self.rect_sel.height() > 8:
            self._confirm()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.cancelled.emit(); self.close()
        elif e.key() in (Qt.Key_Return, Qt.Key_Enter) and not self.rect_sel.isNull():
            self._confirm()

    def _confirm(self):
        r = self.rect_sel.normalized()
        self.selected.emit([int(r.x() * self.dpr), int(r.y() * self.dpr), int(r.width() * self.dpr), int(r.height() * self.dpr)])
        self.close()
