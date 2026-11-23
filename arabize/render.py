"""One painter for the subtitle, shared by the on-screen overlay, the VR panel and previews."""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QImage, QPainter, QPainterPath, QPen, QTextOption

ACCENT = QColor("#E7B964")


RTL_LANGS = {"ar", "fa", "ur", "he"}


def _font(style: dict, size: float, bold: bool) -> QFont:
    f = QFont(style.get("font_family") or "Noto Sans Arabic")
    f.setFamilies([style.get("font_family") or "Noto Sans Arabic", "Noto Sans Arabic", "Segoe UI", "Arial"])
    f.setPixelSize(max(8, int(size)))
    f.setBold(bold)
    f.setStyleStrategy(QFont.PreferAntialias)
    return f


def layout(items: list[dict], style: dict, width: float) -> tuple[list[tuple], float]:
    """Measure the subtitle. Returns (draw ops, total height)."""
    size = style.get("font_size", 26)
    pad = size * 0.55
    inner = width - pad * 2
    opt_flags = Qt.TextWordWrap | Qt.AlignHCenter
    ops, y = [], pad
    shown = items[-int(style.get("max_lines", 4)):] if items else []
    for idx, it in enumerate(shown):
        if it.get("label"):
            f = _font(style, size * 0.62, True)
            fm = QFontMetricsF(f)
            r = fm.boundingRect(QRectF(0, 0, inner, 10_000), opt_flags, it.get("label_tr") or it["label"])
            ops.append(("label", f, QRectF(pad, y, inner, r.height()), it.get("label_tr") or it["label"]))
            y += r.height() + size * 0.08
        f = _font(style, size, style.get("bold", True))
        fm = QFontMetricsF(f)
        txt = it.get("tr") or it.get("src", "")
        r = fm.boundingRect(QRectF(0, 0, inner, 10_000), opt_flags, txt)
        ops.append(("text", f, QRectF(pad, y, inner, r.height()), txt))
        y += r.height()
        if style.get("show_original") and it.get("src"):
            f2 = _font(style, size * 0.5, False)
            r2 = QFontMetricsF(f2).boundingRect(QRectF(0, 0, inner, 10_000), opt_flags, it["src"])
            ops.append(("orig", f2, QRectF(pad, y + size * 0.1, inner, r2.height()), it["src"]))
            y += r2.height() + size * 0.1
        if idx < len(shown) - 1:
            y += size * 0.45
    return ops, y + pad


def paint(p: QPainter, rect: QRectF, items: list[dict], style: dict, alpha: float = 1.0, ops=None) -> None:
    if ops is None:
        ops, _ = layout(items, style, rect.width())
    p.save()
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.TextAntialiasing)
    p.setOpacity(max(0.0, min(1.0, alpha)))
    bg = QColor(style.get("bg", "#05080F"))
    bg.setAlphaF(max(0.0, min(1.0, style.get("bg_opacity", 72) / 100)))
    if bg.alpha() > 0:
        path = QPainterPath()
        path.addRoundedRect(rect, 16, 16)
        p.fillPath(path, bg)
        edge = QColor(ACCENT); edge.setAlpha(int(70 * bg.alphaF()))
        p.setPen(QPen(edge, 1.2)); p.drawPath(path)
    opt = QTextOption(Qt.AlignHCenter)
    opt.setWrapMode(QTextOption.WordWrap)
    opt.setTextDirection(Qt.RightToLeft if style.get("rtl", True) else Qt.LeftToRight)
    opt_orig = QTextOption(Qt.AlignHCenter)
    opt_orig.setWrapMode(QTextOption.WordWrap)
    opt_orig.setTextDirection(Qt.LeftToRight)
    color = QColor(style.get("color", "#FFFFFF"))
    for kind, font, r, txt in ops:
        r = QRectF(r.x() + rect.x(), r.y() + rect.y(), r.width(), r.height())
        p.setFont(font)
        if kind == "text":
            # soft shadow keeps text readable on bright game scenes even with a light background
            p.setPen(QColor(0, 0, 0, 200))
            for dx, dy in ((0, 2), (1.5, 1.5), (-1.5, 1.5)):
                p.drawText(r.translated(dx, dy), txt, opt)
            p.setPen(color)
        elif kind == "label":
            p.setPen(ACCENT)
        else:
            p.setPen(QColor(200, 205, 225, 190))
        p.drawText(r, txt, opt_orig if kind == "orig" else opt)
    p.restore()


def render_image(items: list[dict], style: dict, width: int) -> QImage:
    ops, h = layout(items, style, width)
    img = QImage(int(width), int(max(h, 10)), QImage.Format_RGBA8888)
    img.fill(Qt.transparent)
    p = QPainter(img)
    paint(p, QRectF(0, 0, width, h), items, style, 1.0, ops)
    p.end()
    return img
