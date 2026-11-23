"""Reusable cinematic widgets."""
from __future__ import annotations

import math

from PySide6.QtCore import QEasingCurve, QPointF, QRectF, Qt, QTimer, QVariantAnimation, Signal
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QFont, QLinearGradient, QPainter, QPainterPath, QPen,
                           QPixmap, QRadialGradient)
from PySide6.QtWidgets import (QColorDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QSlider,
                               QVBoxLayout, QWidget)

from .. import render, styles
from . import icons, theme


def card(gold: bool = False) -> tuple[QFrame, QVBoxLayout]:
    f = QFrame()
    f.setObjectName("CardGold" if gold else "Card")
    lay = QVBoxLayout(f)
    lay.setContentsMargins(18, 16, 18, 16)
    lay.setSpacing(10)
    return f, lay


TITLE_HUES = {"palette": "rose", "move": "blue", "vr": "violet", "monitor": "blue", "lang": "cyan", "games": "violet",
              "hist": "emerald", "keyboard": "slate", "help": "coral", "home": "gold", "layers": "emerald", "wand": "coral",
              "template": "gold", "type": "blue", "scan": "cyan", "cpu": "slate", "zap": "gold", "power": "gold"}


def title(text: str, icon_name: str | None = None, hue: str | None = None) -> QWidget:
    w = QWidget()
    h = QHBoxLayout(w); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(10)
    if icon_name:
        ic = QLabel()
        if icon_name in icons.icons3d.GLYPHS:
            ic.setPixmap(icons.tile(icon_name, hue or TITLE_HUES.get(icon_name, "gold"), 30))
        else:
            ic.setPixmap(icons.pixmap(icon_name, theme.GOLD, 18))
        h.addWidget(ic)
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
    """Live preview over a game-like scene: every layer in its place, playing the template's entrance effect."""

    SAMPLE = styles.SAMPLE_ITEMS

    def __init__(self, height: int = 220):
        super().__init__()
        self.setMinimumHeight(height)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.style: dict = {}
        self.items = list(self.SAMPLE)
        self.vr = False
        self._t = 1.0
        self._anim = QVariantAnimation(self, startValue=0.0, endValue=1.0)
        self._anim.valueChanged.connect(self._tick)

    def set_style(self, style: dict, vr: bool = False, play: bool = False):
        changed_fx = any(self.style.get(k) != style.get(k) for k in ("fx_in", "template"))
        self.style, self.vr = dict(style), vr
        if play or changed_fx:
            self.play()
        self.update()

    def play(self):
        fx, ms = self.style.get("fx_in", "fade"), int(self.style.get("fx_ms", 260))
        if fx == "none" or ms <= 0:
            self._t = 1.0; self.update(); return
        if fx == "type":
            ms = max(ms, 900)
        self._anim.stop(); self._anim.setDuration(ms)
        self._anim.setEasingCurve(QEasingCurve.Linear if fx == "type" else QEasingCurve.OutCubic)
        self._t = 0.0; self._anim.start()

    def _tick(self, v):
        self._t = float(v); self.update()

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
                self._vr_panel(p, eye)
            p.setPen(QPen(QColor("#000"), 3)); p.drawLine(QPointF(r.center().x(), r.top()), QPointF(r.center().x(), r.bottom()))
        else:
            paint_game_scene(p, r)
            paint_layers(p, r, self.items, self.style, self._t)
        p.end()

    def _vr_panel(self, p, area: QRectF):
        st = dict(self.style)
        st["font_size"] = max(9, st.get("font_size", 44) * 0.3)
        width = area.width() * 0.86
        items = [i for i in self.items if i.get("kind") != "choices"][:2]
        ops, h = render.layout(items, st, width)
        y = area.center().y() - h / 2 + st.get("height_m", -0.35) * -area.height() * 0.6
        e = overlay_fx(st, self._t)
        render.paint(p, QRectF(area.x() + (area.width() - width) / 2, y + e["dy"], width, h), items, st, e["alpha"], ops,
                     e["reveal"], e["glow"])


def overlay_fx(style: dict, t: float) -> dict:
    from ..overlay import effect_state
    return effect_state(style, t)


def paint_layers(p: QPainter, area: QRectF, items: list[dict], style: dict, t: float = 1.0, screen_w: float = 1600,
                 min_font_k: float = 0.36) -> None:
    """Draw items the way the real overlay layers would place them on a screen screen_w pixels wide, scaled into area."""
    from ..overlay import anchor_xy
    k = area.width() / screen_w
    font_k = max(k, min_font_k)
    layers_cfg = style.get("layers") or {}
    split = style.get("layers_on", True)
    groups: dict[str, list] = {}
    for it in items:
        kind = it.get("kind", "dialogue") if split else "dialogue"
        cfg = {**styles.DEFAULT_LAYERS.get(kind, {}), **layers_cfg.get(kind, {})}
        if kind not in styles.LAYER_IDS or (kind != "dialogue" and not cfg.get("on", True)):
            kind = "dialogue"
        groups.setdefault(kind, []).append(it)
    for kind, its in groups.items():
        st = styles.layer_style(style, kind, layers_cfg)
        st["custom_pos"] = None
        st["font_size"] = max(8, st.get("font_size", 26) * font_k)
        st["radius"] = max(2, st.get("radius", 16) * font_k * 1.4)
        width = max(90, area.width() * st.get("width_pct", 70) / 100)
        ops, h = render.layout(its, st, width)
        x, y = anchor_xy(area, width, h, st.get("anchor", "bottom"), st.get("offset", 80) * k)
        e = overlay_fx(st, t)
        p.save()
        c = QPointF(x + width / 2, y + h / 2)
        p.translate(c.x(), c.y() + e["dy"]); p.scale(e["scale"], e["scale"]); p.translate(-c.x(), -c.y())
        render.paint(p, QRectF(x, y, width, h), its, st, e["alpha"], ops, e["reveal"], e["glow"])
        p.restore()


def template_thumb(look: dict, w: int = 300, h: int = 168) -> QPixmap:
    """Small picture of a template over the game scene, used on the template cards."""
    pm = QPixmap(w * 2, h * 2); pm.setDevicePixelRatio(2); pm.fill(Qt.transparent)
    p = QPainter(pm); p.setRenderHint(QPainter.Antialiasing)
    r = QRectF(0, 0, w, h)
    clip = QPainterPath(); clip.addRoundedRect(r, 12, 12); p.setClipPath(clip)
    paint_game_scene(p, r, seed=1)
    st = {**look, "rtl": True, "layers_on": True, "layers": styles.DEFAULT_LAYERS}
    items = [styles.SAMPLE_ITEMS[1], *styles.SAMPLE_ITEMS[2:]]
    paint_layers(p, r, items, st, 1.0, screen_w=1280, min_font_k=0.27)
    p.end()
    return pm


class TemplateCard(QFrame):
    clicked = Signal(str)
    delete = Signal(str)

    def __init__(self, tid: str, tpl: dict):
        super().__init__()
        self.tid = tid
        self.setObjectName("TplCard"); self.setCursor(Qt.PointingHandCursor)
        self.setProperty("sel", False)
        v = QVBoxLayout(self); v.setContentsMargins(8, 8, 8, 10); v.setSpacing(6)
        self.img = QLabel(); self.img.setPixmap(template_thumb(tpl["look"], 236, 132)); self.img.setAlignment(Qt.AlignCenter)
        v.addWidget(self.img)
        hh = QHBoxLayout(); hh.setSpacing(6)
        name = QLabel(tpl["name"]); name.setObjectName("CardTitle"); hh.addWidget(name, 1)
        if not tpl.get("builtin"):
            mine = QLabel("قالبي"); mine.setObjectName("Badge"); hh.addWidget(mine)
            x = QPushButton("حذف"); x.setObjectName("Chip"); x.clicked.connect(lambda: self.delete.emit(self.tid)); hh.addWidget(x)
        v.addLayout(hh)
        d = QLabel(tpl.get("desc", "")); d.setObjectName("Hint"); d.setWordWrap(True); d.setMinimumHeight(32)
        v.addWidget(d)
        self.setFixedWidth(256)

    def set_selected(self, on: bool):
        self.setProperty("sel", on)
        self.style().unpolish(self); self.style().polish(self)

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit(self.tid)


class TemplateGallery(QWidget):
    """All templates as picture cards in a wrapping grid. One click applies a template."""
    applied = Signal(str)
    deleted = Signal(str)

    def __init__(self, cols: int = 3):
        super().__init__()
        self.cols = cols
        self.grid = QGridLayout(self); self.grid.setContentsMargins(0, 0, 0, 0); self.grid.setSpacing(12)
        self.cards: dict[str, TemplateCard] = {}

    def set_templates(self, templates: dict, current: str):
        sig = tuple((k, v["name"]) for k, v in templates.items())
        if sig != getattr(self, "_sig", None):
            while self.grid.count():
                w = self.grid.takeAt(0).widget()
                if w:
                    w.deleteLater()
            self.cards = {}
            for i, (tid, t) in enumerate(templates.items()):
                c = TemplateCard(tid, t)
                c.clicked.connect(self.applied.emit); c.delete.connect(self.deleted.emit)
                self.grid.addWidget(c, i // self.cols, i % self.cols)
                self.cards[tid] = c
            self._sig = sig
        for tid, c in self.cards.items():
            c.set_selected(tid == current)


class FontPicker(QWidget):
    """The bundled Arabic fonts, each button written in its own font so the choice is made by eye."""
    changed = Signal(str)

    def __init__(self, cols: int = 3):
        super().__init__()
        g = QGridLayout(self); g.setContentsMargins(0, 0, 0, 0); g.setSpacing(8)
        self.buttons: dict[str, QPushButton] = {}
        for i, (fam, ar, note) in enumerate(styles.FONTS):
            b = QPushButton(); b.setObjectName("FontBtn"); b.setCheckable(True); b.setToolTip(f"{fam} — {note}")
            lay = QVBoxLayout(b); lay.setContentsMargins(12, 8, 12, 8); lay.setSpacing(0)
            big = QLabel("عرّب لعبتك"); f = QFont(fam); f.setFamilies([fam]); f.setPixelSize(22); f.setBold(True); big.setFont(f)
            big.setAlignment(Qt.AlignCenter); big.setAttribute(Qt.WA_TransparentForMouseEvents)
            small = QLabel(ar); small.setObjectName("Hint"); small.setAlignment(Qt.AlignCenter)
            small.setAttribute(Qt.WA_TransparentForMouseEvents)
            lay.addWidget(big); lay.addWidget(small)
            b.setMinimumHeight(74)
            b.clicked.connect(lambda _=False, fam=fam: self._pick(fam))
            g.addWidget(b, i // cols, i % cols)
            self.buttons[fam] = b

    def _pick(self, fam):
        self.set(fam); self.changed.emit(fam)

    def set(self, fam: str):
        fam = styles.normalize_font(fam)
        for k, b in self.buttons.items():
            b.setChecked(k == fam)


class Chips(QWidget):
    """A row of options where exactly one is chosen."""
    changed = Signal(str)

    def __init__(self, options: list[tuple[str, str]], wrap: int = 0):
        super().__init__()
        lay = QGridLayout(self); lay.setContentsMargins(0, 0, 0, 0); lay.setSpacing(6)
        self.buttons: dict[str, QPushButton] = {}
        for i, (k, label) in enumerate(options):
            b = QPushButton(label); b.setObjectName("Opt"); b.setCheckable(True)
            b.clicked.connect(lambda _=False, k=k: self._pick(k))
            if wrap:
                lay.addWidget(b, i // wrap, i % wrap)
            else:
                lay.addWidget(b, 0, i)
            self.buttons[k] = b

    def _pick(self, k):
        self.set(k); self.changed.emit(k)

    def set(self, k: str):
        for key, b in self.buttons.items():
            b.setChecked(key == k)


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
