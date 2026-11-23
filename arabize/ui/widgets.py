"""Reusable cinematic widgets."""
from __future__ import annotations

import math

from PySide6.QtCore import QEasingCurve, QPointF, QRectF, Qt, QTimer, QVariantAnimation, Signal
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QFont, QLinearGradient, QPainter, QPainterPath, QPen,
                           QRadialGradient)
from PySide6.QtWidgets import (QColorDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QSlider,
                               QVBoxLayout, QWidget)

from .. import render
from . import icons, theme


def card(gold: bool = False) -> tuple[QFrame, QVBoxLayout]:
    f = QFrame()
    f.setObjectName("CardGold" if gold else "Card")
    lay = QVBoxLayout(f)
    lay.setContentsMargins(18, 16, 18, 16)
    lay.setSpacing(10)
    return f, lay


def title(text: str, icon_name: str | None = None) -> QWidget:
    w = QWidget()
    h = QHBoxLayout(w); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(8)
    if icon_name:
        ic = QLabel(); ic.setPixmap(icons.pixmap(icon_name, theme.GOLD, 18)); h.addWidget(ic)
    t = QLabel(text); t.setObjectName("CardTitle"); h.addWidget(t)
    h.addStretch(1)
    return w


def hint(text: str) -> QLabel:
    l = QLabel(text); l.setObjectName("Hint"); l.setWordWrap(True)
    return l


def row(label: str, widget: QWidget, sub: str = "") -> QWidget:
    w = QWidget()
    h = QHBoxLayout(w); h.setContentsMargins(0, 2, 0, 2); h.setSpacing(12)
    v = QVBoxLayout(); v.setSpacing(0)
    l = QLabel(label); v.addWidget(l)
    if sub:
        s = QLabel(sub); s.setObjectName("Hint"); s.setWordWrap(True); v.addWidget(s)
    h.addLayout(v, 1)
    h.addWidget(widget)
    return w


class ValueSlider(QWidget):
    """Slider with its value printed beside it (unit-aware)."""
    valueChanged = Signal(float)

    def __init__(self, lo: float, hi: float, step: float = 1, unit: str = "", value: float = 0, decimals: int = 0):
        super().__init__()
        self.step, self.unit, self.decimals = step, unit, decimals
        h = QHBoxLayout(self); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(10)
        self.s = QSlider(Qt.Horizontal)
        self.s.setLayoutDirection(Qt.LeftToRight)
        self.s.setRange(int(round(lo / step)), int(round(hi / step)))
        self.s.setMinimumWidth(170)
        self.lab = QLabel(); self.lab.setMinimumWidth(56); self.lab.setStyleSheet(f"color:{theme.GOLD2};")
        h.addWidget(self.s, 1); h.addWidget(self.lab)
        self.s.valueChanged.connect(self._changed)
        self.setValue(value)

    def value(self) -> float:
        v = self.s.value() * self.step
        return round(v, self.decimals) if self.decimals else int(round(v))

    def setValue(self, v: float):
        self.s.blockSignals(True); self.s.setValue(int(round(v / self.step))); self.s.blockSignals(False)
        self._label()

    def _label(self):
        v = self.value()
        self.lab.setText(f"{v:.{self.decimals}f}{self.unit}" if self.decimals else f"{v}{self.unit}")

    def _changed(self, _):
        self._label()
        self.valueChanged.emit(self.value())


class ColorPick(QWidget):
    """Quick swatches + custom colour."""
    changed = Signal(str)

    def __init__(self, colors: list[str], value: str):
        super().__init__()
        h = QHBoxLayout(self); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(6)
        self.btns = []
        for c in colors:
            b = QPushButton(); b.setFixedSize(28, 28); b.setCheckable(True); b.setProperty("c", c)
            b.setToolTip(c)
            b.clicked.connect(lambda _=False, c=c: self.set(c, emit=True))
            h.addWidget(b); self.btns.append(b)
        more = QPushButton("…"); more.setFixedSize(34, 28); more.setToolTip("لون مخصص")
        more.clicked.connect(self._custom); h.addWidget(more)
        self.value = value
        self.set(value)

    def set(self, c: str, emit: bool = False):
        self.value = c
        for b in self.btns:
            on = b.property("c").lower() == c.lower()
            b.setChecked(on)
            b.setStyleSheet(f"background:{b.property('c')}; border-radius:14px; border:{'2px solid #FFFFFF' if on else '1px solid #232A4D'};")
        if emit:
            self.changed.emit(c)

    def _custom(self):
        col = QColorDialog.getColor(QColor(self.value), self, "اختر اللون")
        if col.isValid():
            self.set(col.name(), emit=True)


class PowerButton(QWidget):
    """The big start/stop button with a breathing glow while translation is running."""
    clicked = Signal()

    def __init__(self, size: int = 180):
        super().__init__()
        self.setFixedSize(size, size)
        self.setCursor(Qt.PointingHandCursor)
        self.on = False
        self.hover = False
        self.phase = 0.0
        self.timer = QTimer(self); self.timer.timeout.connect(self._tick)
        self.setToolTip("ابدأ أو أوقف الترجمة المباشرة")

    def set_on(self, on: bool):
        self.on = on
        (self.timer.start(33) if on else self.timer.stop())
        self.update()

    def _tick(self):
        self.phase = (self.phase + 0.04) % (2 * math.pi)
        self.update()

    def enterEvent(self, _):
        self.hover = True; self.update()

    def leaveEvent(self, _):
        self.hover = False; self.update()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.rect().contains(e.position().toPoint()):
            self.clicked.emit()

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        c = QPointF(self.width() / 2, self.height() / 2)
        R = self.width() / 2 - 6
        gold = QColor(theme.GOLD)
        pulse = (math.sin(self.phase) + 1) / 2 if self.on else 0
        # halo
        halo = QRadialGradient(c, R)
        hc = QColor(gold); hc.setAlphaF(0.18 + 0.25 * pulse if self.on else (0.12 if self.hover else 0.06))
        halo.setColorAt(0.55, hc); halo.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(halo); p.setPen(Qt.NoPen); p.drawEllipse(c, R, R)
        # rotating ring
        r2 = R * 0.78
        ring = QConicalGradient(c, -math.degrees(self.phase) * 2)
        ring.setColorAt(0.0, QColor(theme.GOLD2)); ring.setColorAt(0.5, QColor(gold.red(), gold.green(), gold.blue(), 40 if not self.on else 120))
        ring.setColorAt(1.0, QColor(theme.GOLD2))
        p.setPen(QPen(QBrush(ring), 3 if self.on else 2)); p.setBrush(Qt.NoBrush); p.drawEllipse(c, r2, r2)
        # core
        r3 = R * 0.62
        core = QLinearGradient(c.x(), c.y() - r3, c.x(), c.y() + r3)
        if self.on:
            core.setColorAt(0, QColor(theme.GOLD2)); core.setColorAt(1, gold)
        else:
            core.setColorAt(0, QColor("#1B2246")); core.setColorAt(1, QColor("#0E1330"))
        p.setBrush(core); p.setPen(QPen(QColor(theme.GOLD) if (self.hover or self.on) else QColor(theme.LINE), 1.5))
        p.drawEllipse(c, r3, r3)
        pm = icons.pixmap("power", "#1A1204" if self.on else theme.GOLD2, 40, 2.4)
        p.drawPixmap(int(c.x() - 20), int(c.y() - 30), pm)
        f = theme.ui_font(10, True); p.setFont(f)
        p.setPen(QColor("#1A1204") if self.on else QColor(theme.MIST))
        p.drawText(QRectF(c.x() - r3, c.y() + 14, r3 * 2, 24), Qt.AlignCenter, "إيقاف" if self.on else "ابدأ الترجمة")
        p.end()


def paint_game_scene(p: QPainter, rect: QRectF, t: float = 0.0, seed: int = 0) -> None:
    """Stylised game background used by previews and the tutorial."""
    g = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    g.setColorAt(0, QColor("#0B1033")); g.setColorAt(0.45, QColor("#2A2156")); g.setColorAt(0.75, QColor("#7A4A52")); g.setColorAt(1, QColor("#1A1020"))
    p.fillRect(rect, g)
    sun = QRadialGradient(QPointF(rect.center().x(), rect.y() + rect.height() * 0.5), rect.height() * 0.32)
    sun.setColorAt(0, QColor(246, 220, 160, 160)); sun.setColorAt(1, QColor(0, 0, 0, 0))
    p.fillRect(rect, sun)
    for k, col in enumerate(("#2A1D3D", "#120B1C")):
        path = QPainterPath(QPointF(rect.left(), rect.bottom()))
        base = rect.y() + rect.height() * (0.62 + 0.12 * k)
        x = rect.left()
        while x <= rect.right() + 20:
            y = base - (rect.height() * 0.08) * math.sin((x + t * (12 + 10 * k)) / (60 + 40 * k) + seed + k)
            path.lineTo(x, y); x += 14
        path.lineTo(rect.right(), rect.bottom()); path.closeSubpath()
        p.fillPath(path, QColor(col))


class SubtitlePreview(QWidget):
    """Live preview of the subtitle look over a game-like scene."""

    SAMPLE = [{"label": "Captain Mara", "label_tr": "القائدة مارا", "src": "We leave at dawn. Bring your sword.",
               "tr": "سننطلق عند الفجر. أحضر سيفك."}]

    def __init__(self, height: int = 220):
        super().__init__()
        self.setMinimumHeight(height)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.style: dict = {}
        self.items = list(self.SAMPLE)
        self.vr = False

    def set_style(self, style: dict, vr: bool = False):
        self.style, self.vr = dict(style), vr
        self.update()

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        clip = QPainterPath(); clip.addRoundedRect(r, 16, 16); p.setClipPath(clip)
        if self.vr:
            p.fillRect(r, QColor("#05060F"))
            for i in range(2):
                eye = QRectF(r.x() + i * r.width() / 2, r.y(), r.width() / 2, r.height())
                rg = QRadialGradient(eye.center(), eye.width() * 0.6)
                rg.setColorAt(0, QColor("#2A2156")); rg.setColorAt(1, QColor("#05060F"))
                p.fillRect(eye, rg)
                self._sub(p, eye, scale=0.55, vr=True)
            p.setPen(QPen(QColor("#000"), 3)); p.drawLine(QPointF(r.center().x(), r.top()), QPointF(r.center().x(), r.bottom()))
        else:
            paint_game_scene(p, r)
            self._sub(p, r, scale=0.5)
        p.end()

    def _sub(self, p, area: QRectF, scale: float, vr: bool = False):
        st = dict(self.style)
        st["font_size"] = max(10, st.get("font_size", 26) * scale)
        st.setdefault("font_family", "Noto Sans Arabic")
        width = area.width() * (0.86 if vr else max(0.3, min(1.0, st.get("width_pct", 70) / 100)))
        ops, h = render.layout(self.items, st, width)
        x = area.x() + (area.width() - width) / 2
        anchor = st.get("anchor", "bottom") if not vr else "center"
        off = st.get("offset", 80) * scale * 0.5
        y = area.y() + (off if anchor == "top" else (area.height() - h) / 2 if anchor == "center" else area.height() - h - off)
        if vr:
            y += st.get("height_m", -0.35) * -area.height() * 0.6
        render.paint(p, QRectF(x, y, width, h), self.items, st, 1.0, ops)


class MonitorMap(QWidget):
    """Draws the monitors/TVs to scale; click one to choose it."""
    picked = Signal(int)

    def __init__(self):
        super().__init__()
        self.setMinimumHeight(170)
        self.mons = []
        self.sel = 1
        self.region = None
        self._rects = []

    def set_data(self, mons, sel: int, region=None):
        self.mons, self.sel, self.region = mons, sel, region
        self.update()

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        self._rects = []
        if not self.mons:
            p.setPen(QColor(theme.MUTED)); p.drawText(self.rect(), Qt.AlignCenter, "لم يُعثر على شاشات"); return
        x0 = min(m.left for m in self.mons); y0 = min(m.top for m in self.mons)
        x1 = max(m.left + m.width for m in self.mons); y1 = max(m.top + m.height for m in self.mons)
        W, H = self.width() - 20, self.height() - 20
        s = min(W / (x1 - x0), H / (y1 - y0))
        ox = 10 + (W - (x1 - x0) * s) / 2; oy = 10 + (H - (y1 - y0) * s) / 2
        for m in self.mons:
            r = QRectF(ox + (m.left - x0) * s + 4, oy + (m.top - y0) * s + 4, m.width * s - 8, m.height * s - 8)
            self._rects.append((m.index, r))
            on = m.index == self.sel
            p.setBrush(QColor(231, 185, 100, 40) if on else QColor(255, 255, 255, 12))
            p.setPen(QPen(QColor(theme.GOLD) if on else QColor(theme.LINE), 2 if on else 1))
            p.drawRoundedRect(r, 8, 8)
            if on and self.region:
                rx, ry, rw, rh = self.region
                rr = QRectF(r.x() + rx / m.width * r.width(), r.y() + ry / m.height * r.height(), rw / m.width * r.width(), rh / m.height * r.height())
                p.setBrush(QColor(231, 185, 100, 90)); p.setPen(QPen(QColor(theme.GOLD2), 1.5, Qt.DashLine)); p.drawRect(rr)
            p.setPen(QColor(theme.GOLD2 if on else theme.MUTED))
            f = theme.ui_font(11, True); p.setFont(f)
            p.drawText(r, Qt.AlignCenter, f"{m.index}\n{m.width}×{m.height}")
        p.end()

    def mouseReleaseEvent(self, e):
        for idx, r in self._rects:
            if r.contains(e.position()):
                self.sel = idx; self.update(); self.picked.emit(idx); return


class Toast(QLabel):
    """Small transient message at the bottom of the window."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setStyleSheet(f"background:{theme.PANEL}; border:1px solid {theme.GOLD}; border-radius:12px; padding:10px 18px; color:{theme.MIST};")
        self.hide()
        self.t = QTimer(self); self.t.setSingleShot(True); self.t.timeout.connect(self.hide)

    def show_msg(self, text: str, ms: int = 2800, err: bool = False):
        self.setStyleSheet(f"background:{theme.PANEL}; border:1px solid {theme.ERR if err else theme.GOLD}; border-radius:12px; padding:10px 18px; color:{theme.MIST};")
        self.setText(text); self.adjustSize()
        pw = self.parentWidget()
        self.move((pw.width() - self.width()) // 2, pw.height() - self.height() - 24)
        self.raise_(); self.show(); self.t.start(ms)
