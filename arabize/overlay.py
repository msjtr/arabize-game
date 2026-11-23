"""Click-through subtitle window that floats above the game on any monitor/TV."""
from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPoint, QRectF, Qt, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import QWidget

from . import render
from .platform_utils import exclude_from_capture

FLAGS = Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.WindowDoesNotAcceptFocus


class SubtitleOverlay(QWidget):
    moved = Signal(list)          # [x, y] after the user drags it in edit mode

    def __init__(self):
        super().__init__(None, FLAGS | Qt.WindowTransparentForInput)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setWindowTitle("Arabize Game — subtitle")
        self.items: list[dict] = []
        self.style: dict = {}
        self.screen_obj = None
        self._alpha = 1.0
        self._edit = False
        self._drag: QPoint | None = None
        self._ops = []
        self._anim = QVariantAnimation(self, startValue=0.0, endValue=1.0, easingCurve=QEasingCurve.OutCubic)
        self._anim.valueChanged.connect(self._on_alpha)
        self.excluded = False

    # ---------- public ----------
    def configure(self, style: dict, qscreen) -> None:
        self.style = dict(style)
        self.screen_obj = qscreen
        self._relayout()

    def show_items(self, items: list[dict]) -> None:
        self.items = items
        self._relayout()
        if not self.isVisible():
            self.show()
            self.excluded = exclude_from_capture(int(self.winId()))
        ms = int(self.style.get("fade_ms", 220))
        if ms > 0:
            self._anim.stop(); self._anim.setDuration(ms); self._anim.start()
        else:
            self._alpha = 1.0
        self.update()

    def clear(self):
        self.items = []
        self.hide()

    def set_edit_mode(self, on: bool) -> None:
        """Make the subtitle draggable (normally it ignores the mouse so the game gets every click)."""
        self._edit = on
        vis = self.isVisible()
        flags = FLAGS if on else (FLAGS | Qt.WindowTransparentForInput)
        self.setWindowFlags(flags)
        if on and not self.items:
            self.items = [{"label": "", "tr": "اسحبني إلى المكان المناسب ثم اضغط Enter", "src": ""}]
            self._relayout()
        if vis or on:
            self.show()
            self.excluded = exclude_from_capture(int(self.winId()))
            if on:
                self.activateWindow(); self.setFocus()
        self.update()

    def physical_rect(self) -> tuple[int, int, int, int] | None:
        if not self.isVisible():
            return None
        g = self.frameGeometry()
        dpr = self.screen_obj.devicePixelRatio() if self.screen_obj else 1.0
        return int(g.x() * dpr), int(g.y() * dpr), int(g.width() * dpr), int(g.height() * dpr)

    # ---------- layout ----------
    def _relayout(self) -> None:
        scr = self.screen_obj or QGuiApplication.primaryScreen()
        geo = scr.geometry()
        width = max(320, geo.width() * self.style.get("width_pct", 70) / 100)
        self._ops, h = render.layout(self.items or [{"tr": " "}], self.style, width)
        h = min(h, geo.height() * 0.6)
        pos = self.style.get("custom_pos")
        if pos:
            x, y = pos
        else:
            x = geo.x() + (geo.width() - width) / 2
            anchor, off = self.style.get("anchor", "bottom"), self.style.get("offset", 80)
            y = geo.y() + (off if anchor == "top" else (geo.height() - h) / 2 if anchor == "center" else geo.height() - h - off)
        x = min(max(geo.x(), x), geo.x() + geo.width() - width)
        y = min(max(geo.y(), y), geo.y() + geo.height() - h)
        self.setGeometry(int(x), int(y), int(width), int(h))

    # ---------- painting ----------
    def _on_alpha(self, v):
        self._alpha = float(v)
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        if self.items:
            render.paint(p, QRectF(self.rect()), self.items, self.style, self._alpha, self._ops)
        if self._edit:
            p.setRenderHint(QPainter.Antialiasing)
            p.setPen(QPen(QColor("#E7B964"), 2, Qt.DashLine))
            p.drawRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 16, 16)
            f = QFont(); f.setPixelSize(12); p.setFont(f)
            p.drawText(self.rect().adjusted(0, 0, 0, -4), Qt.AlignBottom | Qt.AlignHCenter, "وضع التحريك — Enter للحفظ، Esc للإلغاء")
        p.end()

    # ---------- edit-mode dragging ----------
    def mousePressEvent(self, e):
        if self._edit and e.button() == Qt.LeftButton:
            self._drag = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._edit and self._drag is not None:
            self.move(e.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, _):
        self._drag = None

    def keyPressEvent(self, e):
        if not self._edit:
            return
        if e.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.moved.emit([self.x(), self.y()])
            self.set_edit_mode(False)
        elif e.key() == Qt.Key_Escape:
            self.set_edit_mode(False)
            self._relayout()
