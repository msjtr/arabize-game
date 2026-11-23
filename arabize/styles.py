"""Subtitle looks: bundled fonts, effects, layers and ready-made templates.

Everything here is plain data so the overlay, the VR panel, the previews and the
tests all agree on what a template means.
"""
from __future__ import annotations

import copy
import json
import re
import uuid

# ---------------------------------------------------------------- fonts
# Only fonts that ship with the app (assets/fonts) and fully support Arabic.
# System font pickers list hundreds of Latin-only fonts that break Arabic shaping.
FONTS = [
    ("IBM Plex Sans Arabic", "بلكس", "واضح ومتوازن — الافتراضي"),
    ("Readex Pro", "ريدكس", "عريض ومريح للتلفزيون والمسافة البعيدة"),
    ("Tajawal", "تجوال", "خفيف وعصري"),
    ("Cairo", "القاهرة", "مضغوط، يناسب الجمل الطويلة"),
    ("Alexandria", "الإسكندرية", "عريض وقوي للعناوين والقوالب الحماسية"),
    ("Noto Naskh Arabic", "نسخ", "كلاسيكي، يناسب ألعاب القصص والخيال"),
]
FONT_FAMILIES = [f[0] for f in FONTS]
DEFAULT_FONT = "IBM Plex Sans Arabic"
UI_FONT = "IBM Plex Sans Arabic"
DISPLAY_FONT = "Alexandria"


def normalize_font(name: str | None) -> str:
    """Old settings may point at a system font or the removed Noto Sans/Kufi; map them to a bundled one."""
    if name in FONT_FAMILIES:
        return name
    return DEFAULT_FONT


# ---------------------------------------------------------------- effects
FX_IN = [
    ("fade", "ظهور تدريجي"),
    ("slide", "انزلاق للأعلى"),
    ("zoom", "تكبير"),
    ("type", "كتابة حرفاً حرفاً"),
    ("glow", "وميض متوهّج"),
    ("none", "بدون"),
]
FX_OUT = [
    ("fade", "اختفاء تدريجي"),
    ("slide", "انزلاق للأسفل"),
    ("zoom", "تصغير"),
    ("none", "بدون"),
]
TEXT_FX = [
    ("shadow", "ظل ناعم"),
    ("outline", "حدّ حول الحروف"),
    ("glow", "توهّج"),
    ("none", "بدون"),
]
BOXES = [
    ("glass", "زجاجي"),
    ("card", "بطاقة بحافة ملوّنة"),
    ("bar", "شريط بعرض الشاشة"),
    ("bubble", "فقاعة حوار"),
    ("none", "بدون خلفية"),
]

# ---------------------------------------------------------------- layers
# Each piece of on-screen text is sorted into a layer, and each layer has its own place on screen.
LAYERS = [
    ("dialogue", "الحوار", "كلام الشخصيات والسرد"),
    ("quest", "المهمة", "الهدف الحالي ودفتر المهام"),
    ("choices", "الخيارات", "خيارات الرد والقوائم"),
    ("other", "نصوص أخرى", "تعليمات وإشعارات وعناوين"),
]
LAYER_IDS = [k for k, *_ in LAYERS]
ANCHORS = [
    ("bottom", "أسفل الوسط"), ("bottom-right", "أسفل اليمين"), ("bottom-left", "أسفل اليسار"),
    ("center", "الوسط"), ("right", "يمين الوسط"), ("left", "يسار الوسط"),
    ("top", "أعلى الوسط"), ("top-right", "أعلى اليمين"), ("top-left", "أعلى اليسار"),
]
DEFAULT_LAYERS = {
    "dialogue": {"on": True, "anchor": "bottom", "offset": 80, "width_pct": 70, "scale": 1.0, "custom_pos": None},
    "quest": {"on": True, "anchor": "top-right", "offset": 40, "width_pct": 30, "scale": 0.8, "custom_pos": None},
    "choices": {"on": True, "anchor": "right", "offset": 60, "width_pct": 32, "scale": 0.9, "custom_pos": None},
    "other": {"on": True, "anchor": "top", "offset": 40, "width_pct": 50, "scale": 0.8, "custom_pos": None},
}

# ---------------------------------------------------------------- templates
# A template sets the look (font, colours, box, effects). It never touches capture or language settings.
LOOK_KEYS = ("font_family", "font_size", "bold", "color", "bg", "bg_opacity", "box", "text_fx", "accent",
             "fx_in", "fx_out", "fx_ms", "width_pct", "offset", "anchor", "align", "radius")

TEMPLATES: dict[str, dict] = {
    "cinema": {
        "name": "سينمائي", "desc": "حروف بيضاء بحدّ أسود بدون صندوق، مثل ترجمة الأفلام",
        "look": {"font_family": "IBM Plex Sans Arabic", "font_size": 30, "bold": True, "color": "#FFFFFF", "bg": "#000000",
                 "bg_opacity": 0, "box": "none", "text_fx": "outline", "accent": "#F6DCA0", "fx_in": "fade", "fx_out": "fade",
                 "fx_ms": 240, "width_pct": 76, "offset": 64, "anchor": "bottom", "align": "center", "radius": 14},
    },
    "dialogue": {
        "name": "صندوق حوار", "desc": "بطاقة زجاجية بحافة ذهبية واسم المتحدث فوق الكلام",
        "look": {"font_family": "IBM Plex Sans Arabic", "font_size": 26, "bold": True, "color": "#FFFFFF", "bg": "#0A0E1F",
                 "bg_opacity": 80, "box": "card", "text_fx": "shadow", "accent": "#E7B964", "fx_in": "slide", "fx_out": "fade",
                 "fx_ms": 280, "width_pct": 68, "offset": 80, "anchor": "bottom", "align": "center", "radius": 18},
    },
    "hud": {
        "name": "واجهة تقنية", "desc": "شريط داكن بلون سماوي، يظهر النص كأنه يُكتب",
        "look": {"font_family": "Readex Pro", "font_size": 25, "bold": False, "color": "#E8FBFF", "bg": "#03121A",
                 "bg_opacity": 78, "box": "card", "text_fx": "glow", "accent": "#5CE1E6", "fx_in": "type", "fx_out": "fade",
                 "fx_ms": 520, "width_pct": 64, "offset": 72, "anchor": "bottom", "align": "start", "radius": 6},
    },
    "tv": {
        "name": "تلفزيون", "desc": "خط كبير وتباين عالٍ يُقرأ من الكنبة على شاشة بعيدة",
        "look": {"font_family": "Readex Pro", "font_size": 42, "bold": True, "color": "#FFFFFF", "bg": "#000000",
                 "bg_opacity": 86, "box": "bar", "text_fx": "outline", "accent": "#FFD45E", "fx_in": "fade", "fx_out": "fade",
                 "fx_ms": 200, "width_pct": 100, "offset": 0, "anchor": "bottom", "align": "center", "radius": 0},
    },
    "minimal": {
        "name": "بسيط", "desc": "صغير وشفاف لا يغطي اللعبة",
        "look": {"font_family": "Tajawal", "font_size": 22, "bold": True, "color": "#F4F4F6", "bg": "#000000",
                 "bg_opacity": 42, "box": "glass", "text_fx": "shadow", "accent": "#C9D0EA", "fx_in": "fade", "fx_out": "fade",
                 "fx_ms": 180, "width_pct": 56, "offset": 48, "anchor": "bottom", "align": "center", "radius": 12},
    },
    "classic": {
        "name": "كلاسيكي", "desc": "خط نسخ بلون الرقّ، لألعاب القصص والخيال",
        "look": {"font_family": "Noto Naskh Arabic", "font_size": 28, "bold": True, "color": "#FFF1D2", "bg": "#1B1209",
                 "bg_opacity": 84, "box": "card", "text_fx": "shadow", "accent": "#D9A441", "fx_in": "zoom", "fx_out": "fade",
                 "fx_ms": 320, "width_pct": 66, "offset": 76, "anchor": "bottom", "align": "center", "radius": 10},
    },
    "bubble": {
        "name": "فقاعة", "desc": "فقاعة حوار بيضاء بنص داكن مثل القصص المصوّرة",
        "look": {"font_family": "Cairo", "font_size": 25, "bold": True, "color": "#121212", "bg": "#FFFFFF",
                 "bg_opacity": 94, "box": "bubble", "text_fx": "none", "accent": "#E4572E", "fx_in": "zoom", "fx_out": "zoom",
                 "fx_ms": 260, "width_pct": 58, "offset": 70, "anchor": "bottom", "align": "center", "radius": 26},
    },
    "neon": {
        "name": "نيون", "desc": "حروف متوهّجة بلون وردي لألعاب الأكشن والسباق",
        "look": {"font_family": "Alexandria", "font_size": 28, "bold": True, "color": "#FFFFFF", "bg": "#0B0216",
                 "bg_opacity": 35, "box": "none", "text_fx": "glow", "accent": "#FF4FD8", "fx_in": "glow", "fx_out": "fade",
                 "fx_ms": 360, "width_pct": 70, "offset": 70, "anchor": "bottom", "align": "center", "radius": 14},
    },
}
DEFAULT_TEMPLATE = "dialogue"


def template_ids() -> list[str]:
    return list(TEMPLATES)


def all_templates(custom: dict | None) -> dict[str, dict]:
    out = {k: {**v, "builtin": True} for k, v in TEMPLATES.items()}
    for k, v in (custom or {}).items():
        out[k] = {**v, "builtin": False}
    return out


def look_of(style: dict) -> dict:
    return {k: copy.deepcopy(style[k]) for k in LOOK_KEYS if k in style}


def apply_template(style: dict, look: dict) -> dict:
    """Return the screen style with the template's look applied. Position the user dragged is reset."""
    out = dict(style)
    out.update(copy.deepcopy(look))
    out["font_family"] = normalize_font(out.get("font_family"))
    out["custom_pos"] = None
    return out


def vr_from_look(vr: dict, look: dict) -> dict:
    """The VR panel follows the template's font and colours, but keeps its own size and distance."""
    out = dict(vr)
    for k in ("font_family", "color", "bg", "accent", "text_fx", "bold", "fx_in", "fx_out", "fx_ms"):
        if k in look:
            out[k] = look[k]
    out["bg_opacity"] = max(60, int(look.get("bg_opacity", 80)))   # a floating panel always needs a background
    out["box"] = "glass" if look.get("box") in ("none", "bar") else look.get("box", "glass")
    return out


_ID = re.compile(r"[^a-z0-9_-]+")


def new_template_id(name: str) -> str:
    base = _ID.sub("", (name or "").lower())[:16]
    return f"my-{base or 'tpl'}-{uuid.uuid4().hex[:6]}"


def export_templates(custom: dict) -> str:
    return json.dumps({"app": "arabize-game", "kind": "templates", "version": 1, "templates": custom},
                      ensure_ascii=False, indent=2)


def import_templates(text: str) -> dict:
    """Parse an exported file. Unknown keys are dropped and values are checked so a bad file cannot break the overlay."""
    data = json.loads(text)
    items = data.get("templates", data) if isinstance(data, dict) else {}
    out = {}
    for tid, t in (items or {}).items():
        if not isinstance(t, dict) or not isinstance(t.get("look"), dict):
            continue
        look = {k: v for k, v in t["look"].items() if k in LOOK_KEYS}
        if not look:
            continue
        look = sanitize_look(look)
        key = tid if str(tid).startswith("my-") else new_template_id(t.get("name", ""))
        out[key] = {"name": str(t.get("name") or "قالب مستورد")[:40], "desc": str(t.get("desc") or "")[:120], "look": look}
    return out


_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


def sanitize_look(look: dict) -> dict:
    ok = dict(look)
    keys_choice = {"box": BOXES, "text_fx": TEXT_FX, "fx_in": FX_IN, "fx_out": FX_OUT, "anchor": ANCHORS}
    for k, choices in keys_choice.items():
        if k in ok and ok[k] not in [c[0] for c in choices]:
            ok.pop(k)
    for k in ("color", "bg", "accent"):
        if k in ok and not (isinstance(ok[k], str) and _HEX.match(ok[k])):
            ok.pop(k)
    rng = {"font_size": (12, 90), "bg_opacity": (0, 100), "fx_ms": (0, 2000), "width_pct": (20, 100),
           "offset": (0, 800), "radius": (0, 40)}
    for k, (lo, hi) in rng.items():
        if k in ok:
            try:
                ok[k] = int(min(hi, max(lo, float(ok[k]))))
            except (TypeError, ValueError):
                ok.pop(k)
    if "align" in ok and ok["align"] not in ("center", "start"):
        ok.pop("align")
    if "bold" in ok:
        ok["bold"] = bool(ok["bold"])
    if "font_family" in ok:
        ok["font_family"] = normalize_font(ok["font_family"])
    return ok


def layer_style(style: dict, layer: str, layers: dict) -> dict:
    """The full style one layer is drawn with: the template look plus that layer's place and size."""
    cfg = {**DEFAULT_LAYERS.get(layer, DEFAULT_LAYERS["dialogue"]), **(layers or {}).get(layer, {})}
    st = dict(style)
    if layer == "dialogue":
        # the dialogue layer IS the main subtitle: it uses the template's own position and size
        if cfg.get("custom_pos"):
            st["custom_pos"] = cfg["custom_pos"]
        return st
    st["anchor"] = cfg["anchor"]
    st["offset"] = cfg["offset"]
    st["width_pct"] = cfg["width_pct"]
    st["font_size"] = max(12, int(style.get("font_size", 26) * float(cfg.get("scale", 1.0))))
    st["custom_pos"] = cfg.get("custom_pos")
    if layer == "choices":
        st["align"] = "start"
        if st.get("box") == "bar":
            st["box"] = "glass"
    if layer in ("quest", "other") and st.get("box") == "bar":
        st["box"] = "glass"
    return st


# ---------------------------------------------------------------- sample text for previews
SAMPLE_ITEMS = [
    {"kind": "quest", "label": "QUEST", "label_tr": "المهمة", "src": "Reach the old lighthouse", "tr": "اذهب إلى المنارة القديمة"},
    {"kind": "dialogue", "label": "Captain Mara", "label_tr": "القائدة مارا", "src": "We leave at dawn. Bring your sword.",
     "tr": "سننطلق عند الفجر. أحضر سيفك."},
    {"kind": "choices", "label": "", "src": "I'm in.", "tr": "أنا معك."},
    {"kind": "choices", "label": "", "src": "Not today.", "tr": "ليس اليوم."},
]
