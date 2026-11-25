"""Click-through subtitle windows that float above the game on any monitor/TV.

There is one window per layer (dialogue, quest, choices, other) so each kind of text can sit in its own place.
Each window plays the template's entrance and exit effects.
"""
from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QObject, QPoint, QPointF, QRectF, Qt, QTimer, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import QWidget

from . import render, styles
from .platform_utils import keep_on_top, set_capture_visible

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
        self._reserve = 0.0        # steady box: height kept for the subtitle so the window does not resize per line
        self._cy = 0.0             # where the text sits inside the steady box
        self._geo = None
        # a game entering fullscreen can push topmost windows down; raise the layer again while it shows text
        self._top = QTimer(self, interval=1500, timeout=lambda: self.isVisible() and keep_on_top(int(self.winId())))
        self._top.start()

    # ---------- public ----------
    def configure(self, style: dict, qscreen) -> None:
        self.style = dict(style)
        self.screen_obj = qscreen
        self._reserve = 0.0
        self._relayout()
        if self.isVisible():
            self._capture_mode()

    def _capture_mode(self):
        """Visible in screenshots/recordings, or hidden from every capture (the old behaviour)."""
        self.excluded = set_capture_visible(int(self.winId()), bool(self.style.get("recordable", True)))

    def show_items(self, items: list[dict], animate: bool = True) -> None:
        self._leaving = False
        self.items = items
        self._relayout()
        if not self.isVisible():
            self.show()
            self._capture_mode()
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
            self._capture_mode()
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
        box_h, self._cy = h, 0.0
        if self.style.get("steady", True) and not self._edit:
            # one window size for every line: reserve room for a few lines once, then only the text changes
            if not self._reserve:
                n = max(1, min(3, int(self.style.get("max_lines", 4))))
                sample = [{"kind": "dialogue", "label": "", "tr": "نص"} for _ in range(n)]
                self._reserve = min(geo.height() * 0.6, render.layout(sample, self.style, width)[1])
            self._reserve = max(self._reserve, h)
            box_h = self._reserve
            v = self.style.get("anchor", "bottom").partition("-")[0]
            if self.style.get("custom_pos") or v == "top":
                self._cy = 0.0
            elif v == "bottom":
                self._cy = box_h - h
            else:
                self._cy = (box_h - h) / 2
        # room for the slide/zoom effects and the glow so nothing is clipped while animating
        m = int(self.style.get("font_size", 26) * 0.6)
        pos = self.style.get("custom_pos")
        if pos:
            x, y = pos[0] + m, pos[1] + m
        else:
            x, y = anchor_xy(geo, width, box_h, self.style.get("anchor", "bottom"), self.style.get("offset", 80))
        x = min(max(geo.x(), x), geo.x() + geo.width() - width)
        y = min(max(geo.y(), y), geo.y() + geo.height() - box_h)
        self._margin = m
        g = (int(x - m), int(y - m), int(width + 2 * m), int(box_h + 2 * m))
        if g != self._geo or self.geometry().getRect() != g:
            self._geo = g
            self.setGeometry(*g)

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
        box = QRectF(m, m + self._cy, self.width() - 2 * m, self._h)
        if self._edit:
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


# ------------------------------------------------------------------ translation drawn on the game text itself
PLACES = [
    ("cover", "فوق النص الأصلي", "تظهر الترجمة مكان الكلام نفسه وتغطيه، أينما كان في الشاشة"),
    ("above", "أعلى النص الأصلي", "تظهر الترجمة فوق الكلام مباشرة، ويبقى الأصل ظاهراً تحتها"),
    ("fixed", "في مكان ثابت", "صندوق ترجمة في المكان الذي تختاره (أسفل الشاشة مثلاً) مع الطبقات"),
]


def native_rect(qs) -> tuple[float, float, float, float, float]:
    """(x, y, w, h, dpr) of a screen in physical pixels. Qt keeps a screen's top-left in native coordinates."""
    g = qs.geometry()
    d = qs.devicePixelRatio() or 1.0
    return g.x(), g.y(), g.width() * d, g.height() * d, d


def screen_for_point(px: float, py: float):
    screens = QGuiApplication.screens()
    for qs in screens:
        x, y, w, h, _ = native_rect(qs)
        if x <= px < x + w and y <= py < y + h:
            return qs
    return QGuiApplication.primaryScreen()


def place_items(items, geo, origin, dpr, mode, measure, scale=1.0, natural=None):
    """Where each translation goes, in logical pixels of one screen.

    items carry "abs" = the source text's physical rectangle and "line_h" = its line height. measure(item, font_px,
    width) -> height. "cover" centres the translation on the source text (hiding it); "above" puts it just above
    (or below when there is no room). Boxes never overlap each other and never leave the screen."""
    placed = []
    for it in sorted(items, key=lambda i: (i["abs"][1], i["abs"][0])):
        ax, ay, aw, ah = it["abs"]
        x = geo[0] + (ax - origin[0]) / dpr
        y = geo[1] + (ay - origin[1]) / dpr
        w, h = aw / dpr, ah / dpr
        lh = (it.get("line_h") or ah) / dpr
        font = max(14.0, min(64.0, lh * 0.8 * scale))        # OCR boxes include ascenders: ~1.25x the type size
        width = max(w + font * 1.2, font * 6)
        if natural:     # as wide as the Arabic needs on one line, up to 1.6x the English line, then wrap
            width = max(width, min(natural(it, font) + font * 1.6, max(w * 1.6, font * 14)))
        width = min(geo[2] - 16, width)
        bh = measure(it, font, width)
        bx = x + w / 2 - width / 2
        if mode == "above":
            by = y - bh - font * 0.25
            if by < geo[1] + 4:
                by = y + h + font * 0.25
        else:                                   # cover: at least the whole English block, centred on it
            width = max(width, min(geo[2] - 16, w + font * 0.8))
            bh = max(bh, h + font * 0.5)
            by = y + h / 2 - bh / 2
        bx = min(max(geo[0] + 4, bx), geo[0] + geo[2] - width - 4)
        by = min(max(geo[1] + 4, by), geo[1] + geo[3] - bh - 4)
        for px, py, pw, ph, _, _ in placed:      # keep boxes apart: push down below one that is in the way
            if bx < px + pw and px < bx + width and by < py + ph and py < by + bh:
                by = py + ph + 4
        placed.append((bx, by, width, bh, font, it))
    return placed


def steady_boxes(boxes: list[tuple], prev: dict[str, tuple]) -> list[tuple]:
    """The same line read again a few pixels off (OCR jitter) keeps its previous box and font size, so the Arabic
    stays still on the game text instead of trembling; a real move or a new line takes the new box."""
    out = []
    for b in boxes:
        bx, by, w, h, f, it = b
        old = prev.get(it.get("key") or it.get("src", ""))
        if old:
            ox, oy, ow, oh, of, _ = old
            near = abs(bx - ox) <= max(10, ow * 0.04) and abs(by - oy) <= max(8, oh * 0.25)
            same_size = abs(w - ow) <= max(14, ow * 0.12) and abs(h - oh) <= max(8, oh * 0.2) and abs(f - of) <= of * 0.12
            if near and same_size:
                b = (ox, oy, ow, oh, of, it)
        out.append(b)
    return out


class InPlaceOverlay(QWidget):
    """One transparent, click-through window over the whole game screen. Each translation is painted exactly where
    its English line is: in the middle of the screen, on the right, on a sign... wherever the game wrote it."""

    def __init__(self):
        super().__init__(None, FLAGS | Qt.WindowTransparentForInput)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setWindowTitle("Arabize Game — in place")
        self.style: dict = {}
        self.mode = "cover"
        self.qs = None
        self.boxes: list = []
        self.excluded = False
        self._shown_once = False
        self._prev: dict[str, tuple] = {}     # key -> last box, so OCR jitter does not make the Arabic wobble
        self._top = QTimer(self, interval=1500, timeout=lambda: self.isVisible() and keep_on_top(int(self.winId())))
        self._top.start()

    def configure(self, style: dict, mode: str) -> None:
        self.style, self.mode = dict(style), mode
        if self.isVisible():
            self.excluded = set_capture_visible(int(self.winId()), bool(self.style.get("recordable", True)))
            self.update()

    def blends(self, it: dict | None) -> bool:
        return bool(self.mode == "cover" and self.style.get("blend", True) and it and it.get("game_bg"))

    def _item_style(self, font: float, it: dict | None = None) -> dict:
        st = dict(self.style)
        st.update(font_size=font, max_lines=12, show_original=False, align="center")
        if self.mode == "cover":
            # hide the original completely so only Arabic is read
            st["bg_opacity"] = 100
            if st.get("box") in ("none", "bar", "bubble"):
                st["box"] = "card"
            st["radius"] = min(int(st.get("radius", 16)), 10)
            if self.blends(it):
                # in the game's own colours, on the game's own background: reads like an official localisation
                st.update(box="none", bg=it["game_bg"], color=it["game_fg"], accent=it["game_fg"],
                          text_fx="none" if it.get("game_flat") else "shadow")
        return st

    def _measure(self, it, font, width):
        _, h = render.layout([it], self._item_style(font, it), width)
        return h

    def _natural(self, it, font):
        from PySide6.QtGui import QFontMetricsF
        st = self._item_style(font, it)
        fm = QFontMetricsF(render._font(st, font, st.get("bold", True)))
        return max(fm.horizontalAdvance(it.get("tr", "")), fm.horizontalAdvance(it.get("label_tr", "") or "") * 0.8)

    def show_items(self, items: list[dict]) -> None:
        items = [i for i in items if i.get("abs")]
        if not items:
            self.clear(); return
        a = items[0]["abs"]
        qs = screen_for_point(a[0] + a[2] / 2, a[1] + a[3] / 2)
        if qs is not self.qs:
            self.qs = qs
            self.setGeometry(qs.geometry())
        g = qs.geometry()
        x, y, _, _, d = native_rect(qs)
        scale = float(self.style.get("font_size", 26)) / 26.0
        placed = place_items(items, (g.x(), g.y(), g.width(), g.height()), (x, y), d, self.mode, self._measure, scale,
                             self._natural)
        self.boxes = steady_boxes([(bx - g.x(), by - g.y(), w, h, f, it) for bx, by, w, h, f, it in placed], self._prev)
        self._prev = {b[5].get("key") or b[5].get("src", ""): b for b in self.boxes}
        if not self.isVisible():
            self.show()
            self.excluded = set_capture_visible(int(self.winId()), bool(self.style.get("recordable", True)))
            keep_on_top(int(self.winId()))
        self.update()

    def clear(self, animate: bool = True):
        self.boxes = []
        self._prev = {}
        if self.isVisible():
            self.update()
            self.hide()

    def physical_rects(self) -> list[tuple[int, int, int, int]]:
        if not self.isVisible() or not self.qs:
            return []
        g = self.qs.geometry()
        x0, y0, _, _, d = native_rect(self.qs)
        return [(int(x0 + bx * d), int(y0 + by * d), int(w * d), int(h * d)) for bx, by, w, h, _, _ in self.boxes]

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        for bx, by, w, h, f, it in self.boxes:
            st = self._item_style(f, it)
            ops, hh = render.layout([it], st, w)
            if self.mode == "cover":       # a solid plate over the whole English block, then the subtitle centred on it
                bg = QColor(st.get("bg", "#0A0E1F")); bg.setAlpha(255)
                rad = float(st.get("radius", 10))
                p.setPen(Qt.NoPen)
                if self.blends(it):        # soft edges melt into the game's background instead of a hard card
                    feather = max(3, min(10, int(f * 0.35)))
                    for i in range(feather, 0, -1):
                        c = QColor(bg); c.setAlpha(64)
                        p.setBrush(c)
                        p.drawRoundedRect(QRectF(bx - i, by - i, w + 2 * i, h + 2 * i), rad + i, rad + i)
                p.setBrush(bg)
                p.drawRoundedRect(QRectF(bx, by, w, h), rad, rad)
            render.paint(p, QRectF(bx, by + max(0.0, (h - hh) / 2), w, hh), [it], st, 1.0, ops)
        p.end()


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
        self.inplace = InPlaceOverlay()
        self.place = "fixed"
        # True when the text reader takes its picture from the game window itself (like OBS): our windows are not in
        # that picture, so they can cover the English and still show in recordings
        self.ocr_blind = False

    def configure(self, style: dict, qscreen) -> None:
        self.style = dict(style)
        self.split = bool(style.get("layers_on", True))
        self.place = style.get("place", "cover")
        self.inplace.configure(style, self.place)
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

    def in_place(self, items) -> bool:
        return self.place in ("cover", "above") and bool(items) and all(i.get("abs") for i in items)

    def show_items(self, items: list[dict]) -> None:
        if self.in_place(items):
            for w in self.layers.values():
                if w.isVisible():
                    w.clear(animate=False)
            self._last = {}
            mode = self.place
            if mode == "cover" and not self.reader_cant_see_us():
                # the text reader would see our window: covering the English would hide it from the reader too,
                # so the translation goes just above it instead
                mode = "above"
            if mode != self.inplace.mode:
                self.inplace.configure(self.style, mode)
            self.inplace.show_items(items)
            return
        if self.inplace.isVisible():
            self.inplace.clear()
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

    def reader_cant_see_us(self) -> bool:
        """The screen picture the text is read from does not contain our subtitle windows."""
        if self.ocr_blind:
            return True
        if self.style.get("recordable", True):
            return False
        return self.inplace.excluded if self.inplace.isVisible() else True

    def clear(self, animate: bool = True):
        for w in self.layers.values():
            w.clear(animate)
        self.inplace.clear()
        self._last = {}

    def hide(self):
        for w in self.layers.values():
            w.hide()
        self.inplace.hide()

    def isVisible(self) -> bool:
        return any(w.isVisible() for w in self.layers.values()) or self.inplace.isVisible()

    @property
    def excluded(self) -> bool:
        ws = [w for w in list(self.layers.values()) + [self.inplace] if w.isVisible()]
        return all(w.excluded for w in ws)

    def physical_rects(self) -> list[tuple[int, int, int, int]]:
        if self.ocr_blind:
            return []
        out = [r for w in self.layers.values() if not w.excluded for r in [w.physical_rect()] if r]
        if not self.inplace.excluded:
            out += self.inplace.physical_rects()
        return out

    def set_edit_mode(self, on: bool, layer: str = "dialogue") -> None:
        self.layers[layer].set_edit_mode(on)
