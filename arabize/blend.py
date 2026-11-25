"""Colours of the game's own text, so the Arabic can replace it and look like part of the game.

For each block of text the frame is sampled around the block (the panel or sky behind the words) and inside it
(the letters). The translation is then drawn on a plate of the background colour, in the text colour, at the
original size: the English is gone and the Arabic sits where it was, in the game's own colours.
"""
from __future__ import annotations

import numpy as np


def _hex(rgb) -> str:
    r, g, b = (int(max(0, min(255, v))) for v in rgb)
    return f"#{r:02X}{g:02X}{b:02X}"


def _lum(rgb) -> float:
    def ch(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(a, b) -> float:
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def sample_colors(img: np.ndarray, box) -> dict | None:
    """img: BGR frame; box: (x, y, w, h) of a text block inside img.
    Returns {"bg": "#RRGGBB", "fg": "#RRGGBB", "flat": bool} or None when the box is unusable.
    flat = the background around the text is one even colour (a dialogue panel), not a busy scene."""
    if img is None or img.ndim != 3:
        return None
    H, W = img.shape[:2]
    x, y, w, h = (int(v) for v in box)
    if w < 4 or h < 4 or x >= W or y >= H:
        return None
    pad = max(3, min(24, int(h * 0.3)))
    x0, y0, x1, y1 = max(0, x - pad), max(0, y - pad), min(W, x + w + pad), min(H, y + h + pad)
    outer = img[y0:y1, x0:x1]
    mask = np.ones(outer.shape[:2], bool)
    ix0, iy0 = x - x0, y - y0
    mask[max(0, iy0):max(0, iy0) + h, max(0, ix0):max(0, ix0) + w] = False
    ring = outer[mask]
    if ring.size < 12:
        return None
    step = max(1, len(ring) // 4000)
    ring = ring[::step].astype(np.int32)
    bg = np.median(ring, axis=0)
    spread = float(np.abs(ring - bg).sum(axis=1).mean())
    inner = img[y:min(H, y + h), x:min(W, x + w)].reshape(-1, 3)
    istep = max(1, len(inner) // 6000)
    inner = inner[::istep].astype(np.int32)
    dist = np.abs(inner - bg).sum(axis=1)
    n = max(3, int(len(inner) * 0.12))
    far = inner[np.argsort(dist)[-n:]]
    fg = np.median(far, axis=0)
    bg_rgb, fg_rgb = bg[::-1], fg[::-1]          # BGR -> RGB
    if contrast(fg_rgb, bg_rgb) < 3.0:           # unreadable pair: plain white or black on that background
        fg_rgb = (255, 255, 255) if _lum(bg_rgb) < 0.4 else (16, 16, 16)
    return {"bg": _hex(bg_rgb), "fg": _hex(fg_rgb), "flat": spread < 36.0}
