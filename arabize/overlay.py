"""Click-through subtitle windows that float above the game on any monitor/TV.

There is one window per layer (dialogue, quest, choices, other) so each kind of text can sit in its own place.
Each window plays the template's entrance and exit effects.
"""
from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QObject, QPoint, QPointF, QRectF, Qt, QTimer, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import QWidget

from . import render, styles
from .platform_utils import exclude_from_capture

FLAGS = Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.WindowDoesNotAcceptFocus
LAYER_NAMES = {k: n for k, n, _ in styles.LAYERS}


def anchor_xy(geo, width: float, height: float, anchor: str, off: float) -> tuple[float, float]:
    """Top-left of a box of width x height placed at anchor on screen geometry geo, off pixels from the edge."""
    v, _, h = anchor.partition("-")
    if v in ("left", "right"):
        v, h = "center", v
    if v == "center" and not h:
        h = "center"
    h = h or "center"
    x = {"left": geo.x() + off, "right": geo.x() + geo.width() - width - off}.get(h, geo.x() + (geo.width() - width) / 2)
    y = {"top": geo.y() + off, "bottom": geo.y() + geo.height() - height - off}.get(v, geo.y() + (geo.height() - height) / 2)
    return x, y


def effect_state(style: dict, t: float, leaving: bool = False) -> dict:
    """How a frame is transformed at effect progress t (0..1): opacity, vertical offset, scale, reveal and glow."""
    t = max(0.0, min(1.0, t))
    fx = style.get("fx_out" if leaving else "fx_in", "fade")
    size = style.get("font_size", 26)
    st = {"alpha": t, "dy": 0.0, "scale": 1.0, "reveal": 1.0, "glow": 0.0}
    if fx == "slide":
        st["dy"] = (1 - t) * size * (0.9 if not leaving else 0.7)
    elif fx == "zoom":
        st["scale"] = 0.86 + 0.14 * t
    elif fx == "type":
        st["alpha"] = min(1.0, t * 6)
        st["reveal"] = t
    elif fx == "glow":
        st["glow"] = (1 - t) * 1.2
        st["alpha"] = min(1.0, t * 2.2)
    elif fx == "none":
        st["alpha"] = 1.0 if t > 0 else 0.0
    return st


class SubtitleOverlay(QWidget):
    """One floating layer."""
    moved = Signal(list)          # [x, y] after the user drags it in edit mode

    def __init__(self, layer: str = "dialogue"):
        super().__init__(None, FLAGS | Qt.WindowTransparentForInput)
        self.layer = layer
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setWindowTitle(f"Arabize Game — {layer}")
        self.items: list[dict] = []
        self.style: dict = {}
        self.screen_obj = None
        self._t = 1.0             # effect progress 0..1
        self._leaving = False
        self._edit = False
        self._drag: QPoint | None = None
        self._ops = []
        self._h = 0.0
        self._anim = QVariantAnimation(self, startValue=0.0, endValue=1.0)
        self._anim.valueChanged.connect(self._on_t)
        self._anim.finished.connect(self._anim_done)
        self.excluded = False

    # ---------- public ----------
    def configure(self, style: dict, qscreen) -> None:
        self.style = dict(style)
        self.screen_obj = qscreen
        self._relayout()

    def show_items(self, items: list[dict], animate: bool = True) -> None:
        self._leaving = False
        self.items = items
        self._relayout()
        if not self.isVisible():
            self.show()
            self.excluded = exclude_from_capture(int(self.winId()))
        fx, ms = self.style.get("fx_in", "fade"), int(self.style.get("fx_ms", 260))
        if fx == "type":
            # typing speed follows the amount of text, so long lines do not crawl and short ones do not flash
            ms = int(min(1600, max(ms, render.text_length(self._ops) * 22)))
        if animate and fx != "none" and ms > 0:
            self._anim.stop()
            self._anim.setEasingCurve(QEasingCurve.Linear if fx == "type" else QEasingCurve.OutCubic)
            self._anim.setStartValue(0.0); self._anim.setEndValue(1.0); self._anim.setDuration(ms)
            self._t = 0.0
            self._anim.start()
        else:
            self._anim.stop(); self._t = 1.0
        self.update()

    def clear(self, animate: bool = True):
        fx, ms = self.style.get("fx_out", "fade"), int(self.style.get("fx_ms", 260))
        if not self.isVisible() or not self.items:
            self.items = []
            self.hide()
            return
        if animate and fx != "none" and ms > 0 and not self._edit:
            self._leaving = True
            self._anim.stop()
            self._anim.setEasingCurve(QEasingCurve.InCubic)
            self._anim.setStartValue(self._t); self._anim.setEndValue(0.0)
            self._anim.setDuration(int(ms * 0.8 * max(0.2, self._t)))
            self._anim.start()
        else:
            self.items = []
            self.hide()

    def set_edit_mode(self, on: bool) -> None:
        """Make the layer draggable (normally it ignores the mouse so the game gets every click)."""
        self._edit = on
        vis = self.isVisible()
        flags = FLAGS if on else (FLAGS | Qt.WindowTransparentForInput)
        self.setWindowFlags(flags)
        if on and not self.items:
            self.items = [{"kind": self.layer, "label": "", "tr": f"طبقة {LAYER_NAMES.get(self.layer, '')}: اسحبها إلى مكانها ثم اضغط Enter", "src": ""}]
        self._t = 1.0
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
        width = max(260, geo.width() * self.style.get("width_pct", 70) / 100)
        self._ops, h = render.layout(self.items or [{"tr": " "}], self.style, width)
        h = min(h, geo.height() * 0.6)
        self._h = h
        # room for the slide/zoom effects and the glow so nothing is clipped while animating
        m = int(self.style.get("font_size", 26) * 0.6)
        pos = self.style.get("custom_pos")
        if pos:
            x, y = pos[0] + m, pos[1] + m
        else:
            x, y = anchor_xy(geo, width, h, self.style.get("anchor", "bottom"), self.style.get("offset", 80))
        x = min(max(geo.x(), x), geo.x() + geo.width() - width)
        y = min(max(geo.y(), y), geo.y() + geo.height() - h)
        self._margin = m
        self.setGeometry(int(x - m), int(y - m), int(width + 2 * m), int(h + 2 * m))

    # ---------- painting ----------
    def _on_t(self, v):
        self._t = float(v)
        self.update()

    def _anim_done(self):
        if self._leaving:
            self._leaving = False
            self.items = []
            self.hide()

    def effect_state(self) -> dict:
        return effect_state(self.style, self._t, self._leaving)

    def paintEvent(self, _):
        p = QPainter(self)
        m = getattr(self, "_margin", 0)
        box = QRectF(m, m, self.width() - 2 * m, self.height() - 2 * m)
        if self.items:
            e = self.effect_state()
            p.save()
            c = box.center()
            p.translate(c.x(), c.y() + e["dy"])
            p.scale(e["scale"], e["scale"])
            p.translate(-c.x(), -c.y())
            render.paint(p, box, self.items, self.style, e["alpha"], self._ops, e["reveal"], e["glow"])
            p.restore()
        if self._edit:
            p.setRenderHint(QPainter.Antialiasing)
            p.setPen(QPen(QColor("#E7B964"), 2, Qt.DashLine))
            p.drawRoundedRect(box.adjusted(1, 1, -1, -1), 16, 16)
            f = QFont(); f.setPixelSize(12); p.setFont(f)
            p.drawText(box.toRect().adjusted(0, 0, 0, -4), Qt.AlignBottom | Qt.AlignHCenter, "وضع التحريك — Enter للحفظ، Esc للإلغاء")
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
            self.clear(animate=False)
        elif e.key() == Qt.Key_Escape:
            self.set_edit_mode(False)
            self.clear(animate=False)


class OverlayLayers(QObject):
    """All subtitle layers together. Same interface the controller used for the single overlay."""
    moved = Signal(str, list)     # layer, [x, y]

    def __init__(self):
        super().__init__()
        self.layers = {k: SubtitleOverlay(k) for k in styles.LAYER_IDS}
        for k, w in self.layers.items():
            w.moved.connect(lambda pos, k=k: self.moved.emit(k, pos))
        self.style: dict = {}
        self.split = True
        self.on = {k: True for k in styles.LAYER_IDS}
        self._last: dict[str, list] = {}

    def configure(self, style: dict, qscreen) -> None:
        self.style = dict(style)
        self.split = bool(style.get("layers_on", True))
        cfg = style.get("layers") or {}
        for k, w in self.layers.items():
            self.on[k] = k == "dialogue" or bool({**styles.DEFAULT_LAYERS[k], **cfg.get(k, {})}.get("on", True))
            w.configure(styles.layer_style(style, k, cfg), qscreen)

    def distribute(self, items: list[dict]) -> dict[str, list[dict]]:
        """Which items each layer shows. With layers off (or a layer switched off) text goes to the dialogue box."""
        out: dict[str, list[dict]] = {k: [] for k in styles.LAYER_IDS}
        for it in items:
            k = it.get("kind", "dialogue") if self.split else "dialogue"
            if k not in out or not self.on.get(k, True):
                k = "dialogue"
            out[k].append(it)
        return out

    def show_items(self, items: list[dict]) -> None:
        parts = self.distribute(items)
        for k, w in self.layers.items():
            its = parts[k]
            if its:
                # a layer whose text did not change keeps still instead of replaying its effect
                same = [(i.get("src"), i.get("tr")) for i in its] == [(i.get("src"), i.get("tr")) for i in self._last.get(k, [])]
                w.show_items(its, animate=not (same and w.isVisible()))
            elif w.isVisible():
                w.clear()
        self._last = parts

    def clear(self, animate: bool = True):
        for w in self.layers.values():
            w.clear(animate)
        self._last = {}

    def hide(self):
        for w in self.layers.values():
            w.hide()

    def isVisible(self) -> bool:
        return any(w.isVisible() for w in self.layers.values())

    @property
    def excluded(self) -> bool:
        return all(w.excluded for w in self.layers.values() if w.isVisible())

    def physical_rects(self) -> list[tuple[int, int, int, int]]:
        return [r for w in self.layers.values() if not w.excluded for r in [w.physical_rect()] if r]

    def set_edit_mode(self, on: bool, layer: str = "dialogue") -> None:
        self.layers[layer].set_edit_mode(on)
