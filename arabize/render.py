"""One painter for the subtitle, shared by the on-screen layers, the VR panel, previews and template cards.

The style dict decides the look (see styles.py): font, colours, box ("glass", "card", "bar", "bubble", "none"),
text effect ("shadow", "outline", "glow", "none"), alignment and accent colour. Items carry a "kind"
(dialogue / quest / choices / other) which changes how a line is introduced (speaker name, quest header, bullet).
"""
from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QColor, QFont, QFontMetricsF, QImage, QLinearGradient, QPainter, QPainterPath, QPen,
                           QPolygonF, QTextOption)

from .styles import DEFAULT_FONT
from .textproc import _QUEST

ACCENT = QColor("#E7B964")
RTL_LANGS = {"ar", "fa", "ur", "he"}
QUEST_HEAD = "المهمة"
BULLET = "◆"


def _font(style: dict, size: float, bold: bool) -> QFont:
    fam = style.get("font_family") or DEFAULT_FONT
    f = QFont(fam)
    f.setFamilies([fam, DEFAULT_FONT, "Segoe UI", "Tahoma", "Arial"])
    f.setPixelSize(max(8, int(size)))
    f.setBold(bold)
    f.setStyleStrategy(QFont.PreferAntialias)
    return f


def _pad(style: dict, size: float) -> tuple[float, float]:
    box = style.get("box", "glass")
    if box == "none":
        return size * 0.25, size * 0.2
    if box == "bar":
        return size * 0.9, size * 0.45
    return size * 0.7, size * 0.5


def tail_height(style: dict) -> float:
    return style.get("font_size", 26) * 0.55 if style.get("box") == "bubble" else 0.0


def _align(style: dict, rtl: bool) -> Qt.AlignmentFlag:
    if style.get("align") == "start":
        return Qt.AlignRight if rtl else Qt.AlignLeft
    return Qt.AlignHCenter


def layout(items: list[dict], style: dict, width: float) -> tuple[list[tuple], float]:
    """Measure the subtitle. Returns (draw ops, total height including a bubble's tail)."""
    size = style.get("font_size", 26)
    padx, pady = _pad(style, size)
    inner = max(40.0, width - padx * 2)
    rtl = style.get("rtl", True)
    al = _align(style, rtl)
    flags = Qt.TextWordWrap | al
    ops, y = [], pady
    shown = items[-int(style.get("max_lines", 4)):] if items else []
    last_kind = None
    for idx, it in enumerate(shown):
        kind = it.get("kind", "dialogue")
        head = it.get("label_tr") or it.get("label") or ""
        if kind == "quest":
            generic = not it.get("label") or _QUEST.match(it.get("label", ""))
            head = f"{BULLET}  {QUEST_HEAD}" if generic else f"{BULLET}  {head}"
        if kind == "choices":
            head = ""
        if head and not (kind == "quest" and last_kind == "quest"):
            f = _font(style, size * 0.62, True)
            r = QFontMetricsF(f).boundingRect(QRectF(0, 0, inner, 10_000), flags, head)
            ops.append(("label", f, QRectF(padx, y, inner, r.height()), head, al))
            y += r.height() + size * 0.1
        if kind == "quest" and not it.get("label") and _QUEST.match(it.get("src", "")) and len(it.get("src", "").split()) <= 3:
            last_kind = kind          # a bare "QUEST" header line: the header above already says it
            continue
        f = _font(style, size, style.get("bold", True))
        txt = it.get("tr") or it.get("src", "")
        if kind == "choices":
            txt = f"{BULLET}  {txt}"
        r = QFontMetricsF(f).boundingRect(QRectF(0, 0, inner, 10_000), flags, txt)
        ops.append(("text", f, QRectF(padx, y, inner, r.height()), txt, al))
        y += r.height()
        if style.get("show_original") and it.get("src"):
            f2 = _font(style, size * 0.5, False)
            r2 = QFontMetricsF(f2).boundingRect(QRectF(0, 0, inner, 10_000), Qt.TextWordWrap | al, it["src"])
            ops.append(("orig", f2, QRectF(padx, y + size * 0.1, inner, r2.height()), it["src"], al))
            y += r2.height() + size * 0.1
        if idx < len(shown) - 1:
            y += size * (0.22 if kind == "choices" and shown[idx + 1].get("kind") == "choices" else 0.45)
        last_kind = kind
    return ops, y + pady + tail_height(style)


def _box_path(style: dict, rect: QRectF) -> QPainterPath:
    box = style.get("box", "glass")
    path = QPainterPath()
    if box == "bar":
        path.addRect(rect)
        return path
    rad = float(style.get("radius", 16))
    if box == "bubble":
        th = tail_height(style)
        body = rect.adjusted(0, 0, 0, -th)
        path.addRoundedRect(body, rad, rad)
        cx = body.center().x()
        tail = QPainterPath()
        tail.addPolygon(QPolygonF([QPointF(cx - th * 0.9, body.bottom() - 1), QPointF(cx + th * 0.9, body.bottom() - 1),
                                   QPointF(cx + th * 0.2, body.bottom() + th)]))
        return path.united(tail)
    path.addRoundedRect(rect, rad, rad)
    return path


def _paint_box(p: QPainter, rect: QRectF, style: dict) -> None:
    box = style.get("box", "glass")
    if box == "none":
        return
    bg = QColor(style.get("bg", "#0A0E1F"))
    bg.setAlphaF(max(0.0, min(1.0, style.get("bg_opacity", 72) / 100)))
    if bg.alpha() == 0:
        return
    accent = QColor(style.get("accent", "#E7B964"))
    path = _box_path(style, rect)
    p.fillPath(path, bg)
    if box in ("glass", "card", "bubble"):
        # soft light from above gives the box depth
        g = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        hl = QColor(255, 255, 255, int(28 * bg.alphaF())); g.setColorAt(0, hl)
        g.setColorAt(0.45, QColor(255, 255, 255, 0))
        p.fillPath(path, g)
    if box == "glass":
        p.setPen(QPen(QColor(255, 255, 255, int(40 * bg.alphaF())), 1.0)); p.drawPath(path)
    elif box == "card":
        edge = QColor(accent); edge.setAlpha(int(150 * bg.alphaF()))
        p.setPen(QPen(edge, 1.4)); p.drawPath(path)
        # a short accent bar on the reading side
        bar_h = min(rect.height() - 16, 46)
        x = rect.right() - 7 if style.get("rtl", True) else rect.left() + 3
        p.setPen(Qt.NoPen); p.setBrush(accent)
        p.drawRoundedRect(QRectF(x, rect.center().y() - bar_h / 2, 4, bar_h), 2, 2)
    elif box == "bar":
        edge = QColor(accent); edge.setAlpha(int(160 * bg.alphaF()))
        p.setPen(QPen(edge, 2)); p.drawLine(rect.topLeft(), rect.topRight())
    elif box == "bubble":
        edge = QColor(accent); edge.setAlpha(int(200 * bg.alphaF()))
        p.setPen(QPen(edge, 2.2)); p.drawPath(path)


_RING = [(math.cos(a * math.pi / 8), math.sin(a * math.pi / 8)) for a in range(16)]


def _draw_text(p: QPainter, r: QRectF, txt: str, opt: QTextOption, color: QColor, style: dict, size: float, glow: float):
    fx = style.get("text_fx", "shadow")
    if fx == "outline":
        rad = max(1.4, size * 0.07)
        p.setPen(QColor(0, 0, 0, 235))
        for dx, dy in _RING[::2]:
            p.drawText(r.translated(dx * rad, dy * rad), txt, opt)
        p.setPen(QColor(0, 0, 0, 120))
        p.drawText(r.translated(0, rad * 1.6), txt, opt)
    elif fx == "glow" or glow > 0:
        c = QColor(style.get("accent", "#E7B964"))
        strength = (0.55 if fx == "glow" else 0.0) + glow
        for rad, a in ((size * 0.16, 26), (size * 0.09, 46)):
            c.setAlpha(int(min(255, a * strength * 1.6)))
            p.setPen(c)
            for dx, dy in _RING[::2]:
                p.drawText(r.translated(dx * rad, dy * rad), txt, opt)
        if fx != "glow":
            p.setPen(QColor(0, 0, 0, 170)); p.drawText(r.translated(0, 2), txt, opt)
    elif fx == "shadow":
        p.setPen(QColor(0, 0, 0, 200))
        for dx, dy in ((0, 2), (1.5, 1.5), (-1.5, 1.5)):
            p.drawText(r.translated(dx, dy), txt, opt)
    p.setPen(color)
    p.drawText(r, txt, opt)


def text_length(ops) -> int:
    return sum(len(o[3]) for o in ops if o[0] in ("text", "label"))


def paint(p: QPainter, rect: QRectF, items: list[dict], style: dict, alpha: float = 1.0, ops=None,
          reveal: float = 1.0, glow: float = 0.0) -> None:
    """Draw the subtitle into rect. reveal (0..1) shows only the start of the text (typewriter effect),
    glow (0..1) adds an extra accent halo (flash-in effect)."""
    if ops is None:
        ops, _ = layout(items, style, rect.width())
    p.save()
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.TextAntialiasing)
    p.setOpacity(max(0.0, min(1.0, alpha)))
    _paint_box(p, rect, style)
    rtl = style.get("rtl", True)
    color = QColor(style.get("color", "#FFFFFF"))
    accent = QColor(style.get("accent", "#E7B964"))
    size = style.get("font_size", 26)
    budget = text_length(ops) * max(0.0, min(1.0, reveal)) if reveal < 1.0 else None
    for kind, font, r, txt, al in ops:
        if budget is not None and kind in ("text", "label"):
            if budget <= 0:
                continue
            if len(txt) > budget:
                txt = txt[: int(budget)]
            budget -= len(txt)
        elif budget is not None and kind == "orig" and budget <= 0:
            continue
        r = QRectF(r.x() + rect.x(), r.y() + rect.y(), r.width(), r.height())
        opt = QTextOption(al)
        opt.setWrapMode(QTextOption.WordWrap)
        opt.setTextDirection(Qt.LeftToRight if kind == "orig" or not rtl else Qt.RightToLeft)
        if kind == "orig":
            # the original (usually Latin) line keeps its own direction; alignment mirrors for start-aligned layouts
            opt.setAlignment(Qt.AlignHCenter if al == Qt.AlignHCenter else (Qt.AlignRight if rtl else Qt.AlignLeft))
        p.setFont(font)
        if kind == "text":
            _draw_text(p, r, txt, opt, color, style, size, glow)
        elif kind == "label":
            if style.get("text_fx") == "outline" or style.get("box") == "none":
                p.setPen(QColor(0, 0, 0, 200)); p.drawText(r.translated(0, 1.5), txt, opt)
            p.setPen(accent)
            p.drawText(r, txt, opt)
        else:
            dim = QColor(color); dim.setAlpha(175)
            p.setPen(dim)
            p.drawText(r, txt, opt)
    p.restore()


def render_image(items: list[dict], style: dict, width: int, reveal: float = 1.0) -> QImage:
    ops, h = layout(items, style, width)
    img = QImage(int(width), int(max(h, 10)), QImage.Format_RGBA8888)
    img.fill(Qt.transparent)
    p = QPainter(img)
    paint(p, QRectF(0, 0, width, h), items, style, 1.0, ops, reveal)
    p.end()
    return img
