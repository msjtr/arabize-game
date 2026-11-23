"""Synthetic but realistic game screenshots for OCR tests (1920x1080, varied fonts/backgrounds)."""
from __future__ import annotations

import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONTS = {
    "poppins": ["/usr/share/fonts/truetype/google-fonts/Poppins-Medium.ttf", "C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf"],
    "poppins_b": ["/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf", "C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf"],
    "serif": ["/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", "C:/Windows/Fonts/georgiab.ttf", "C:/Windows/Fonts/timesbd.ttf"],
    "sans": ["/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", "C:/Windows/Fonts/arial.ttf"],
}


def _font(name, size):
    for path in FONTS[name]:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def scene_bg(w=1920, h=1080, seed=1):
    """Painterly game-like background: sky gradient, hills, noise, bloom."""
    rnd = random.Random(seed)
    y = np.linspace(0, 1, h)[:, None]
    top = np.array([rnd.randint(10, 60), rnd.randint(20, 80), rnd.randint(60, 130)])
    bot = np.array([rnd.randint(90, 200), rnd.randint(60, 140), rnd.randint(40, 90)])
    img = (top * (1 - y) + bot * y)[:, :, None].repeat(w, 1).reshape(h, w, 3) if False else None
    grad = (top[None, None, :] * (1 - y[..., None]) + bot[None, None, :] * y[..., None])
    img = np.broadcast_to(grad, (h, w, 3)).astype(np.float32).copy()
    img += np.random.default_rng(seed).normal(0, 9, (h, w, 3))
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    for k in range(3):
        base = int(h * (0.55 + 0.12 * k))
        pts = [(0, h)] + [(x, base - int(80 * np.sin(x / (180 + 60 * k) + seed + k))) for x in range(0, w + 40, 40)] + [(w, h)]
        c = 25 + 18 * k
        d.polygon(pts, fill=(c, c - 5, c + 10))
    return im.filter(ImageFilter.GaussianBlur(1.2))


def dialogue_scene(seed=1):
    im = scene_bg(seed=seed).convert("RGBA")
    ov = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    d.rounded_rectangle([260, 800, 1660, 1010], 18, fill=(0, 0, 0, 175))
    im = Image.alpha_composite(im, ov); d = ImageDraw.Draw(im)
    d.text((300, 815), "Captain Mara", font=_font("poppins_b", 34), fill=(255, 200, 90))
    d.text((300, 870), "We leave at dawn. If you want to come with us,", font=_font("poppins", 36), fill=(245, 245, 245))
    d.text((300, 922), "bring your sword and meet me at the docks.", font=_font("poppins", 36), fill=(245, 245, 245))
    d.text((1460, 60), "QUEST", font=_font("serif", 26), fill=(255, 220, 120))
    d.text((1300, 100), "Reach the old lighthouse", font=_font("sans", 28), fill=(255, 255, 255))
    expected = {"dialogue": "We leave at dawn. If you want to come with us, bring your sword and meet me at the docks.",
                "speaker": "Captain Mara", "quest": "Reach the old lighthouse"}
    return np.asarray(im.convert("RGB"))[:, :, ::-1].copy(), expected


def choices_scene(seed=2):
    im = scene_bg(seed=seed); d = ImageDraw.Draw(im)
    opts = ["I will help you.", "What is in it for me?", "Leave me alone."]
    for i, o in enumerate(opts):
        y = 640 + i * 70
        d.rounded_rectangle([700, y, 1220, y + 54], 10, fill=(10, 14, 30))
        d.text((730, y + 8), o, font=_font("poppins", 30), fill=(230, 230, 230))
    return np.asarray(im)[:, :, ::-1].copy(), {"choices": opts}


def small_subtitle(seed=3):
    """Small 20px subtitle without a box, over a bright busy area — the hard case."""
    im = scene_bg(seed=seed); d = ImageDraw.Draw(im)
    txt = "Stay close to me, the bridge will not hold for long."
    f = _font("sans", 22)
    for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
        d.text((660 + dx, 980 + dy), txt, font=f, fill=(0, 0, 0))
    d.text((660, 980), txt, font=f, fill=(255, 255, 255))
    return np.asarray(im)[:, :, ::-1].copy(), {"subtitle": txt}
