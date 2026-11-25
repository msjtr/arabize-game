"""Settings, per-game profiles and on-disk locations.

Everything is stored as JSON in the user's data folder:
  Windows: %APPDATA%\\ArabizeGame
  other:   ~/.config/ArabizeGame
ARABIZE_HOME overrides the folder (used by tests and portable installs).
"""
from __future__ import annotations

import copy
import json
import os
import sys
import threading
from pathlib import Path

from . import styles

APP_NAME_AR = "عرب لعبتك"
APP_NAME_EN = "Arabize Game"
APP_VERSION = "1.4.0"


def data_dir() -> Path:
    env = os.environ.get("ARABIZE_HOME")
    if env:
        p = Path(env)
    elif sys.platform == "win32":
        p = Path(os.environ.get("APPDATA", Path.home())) / "ArabizeGame"
    else:
        p = Path.home() / ".config" / "ArabizeGame"
    p.mkdir(parents=True, exist_ok=True)
    return p


LANGUAGES = [
    ("auto", "اكتشاف تلقائي"), ("ar", "العربية"), ("en", "English"), ("fr", "Français"),
    ("es", "Español"), ("de", "Deutsch"), ("it", "Italiano"), ("pt", "Português"),
    ("tr", "Türkçe"), ("ru", "Русский"), ("ja", "日本語"), ("ko", "한국어"),
    ("zh-CN", "中文 (简体)"), ("zh-TW", "中文 (繁體)"), ("pl", "Polski"), ("id", "Bahasa Indonesia"),
]
LANG_NAMES_EN = {
    "ar": "Arabic", "en": "English", "fr": "French", "es": "Spanish", "de": "German", "it": "Italian",
    "pt": "Portuguese", "tr": "Turkish", "ru": "Russian", "ja": "Japanese", "ko": "Korean",
    "zh-CN": "Simplified Chinese", "zh-TW": "Traditional Chinese", "pl": "Polish", "id": "Indonesian",
}

ENGINE_INFO = {
    "google": {"name": "Google (مجاني)", "needs_key": False},
    "mymemory": {"name": "MyMemory (مجاني)", "needs_key": False},
    "claude": {"name": "Claude (ذكي، يحتاج مفتاح API)", "needs_key": True},
    "deepl": {"name": "DeepL (يحتاج مفتاح API)", "needs_key": True},
}

DEFAULT_HOTKEYS = {
    "toggle": "Ctrl+Shift+T",       # start / stop live translation
    "region": "Ctrl+Shift+R",       # select a screen region
    "hide": "Ctrl+Shift+H",         # hide / show the subtitle
    "mode": "Ctrl+Shift+V",         # switch screen <-> VR
    "retranslate": "Ctrl+Shift+E",  # translate what is on screen now
    "size_up": "Ctrl+Shift+U",      # bigger translation text (screen or headset), saved for this game
    "size_down": "Ctrl+Shift+J",    # smaller translation text
    "hud": "Ctrl+Shift+F",          # show / hide the performance readout (FPS, CPU temperature, ping)
    # inside the headset (VR mode): move, size and place the panel without taking the headset off
    "vr_left": "Ctrl+Shift+Left", "vr_right": "Ctrl+Shift+Right", "vr_up": "Ctrl+Shift+Up", "vr_down": "Ctrl+Shift+Down",
    "vr_nearer": "Ctrl+Shift+PgUp", "vr_farther": "Ctrl+Shift+PgDown",
    "vr_bigger": "Ctrl+Shift+Home", "vr_smaller": "Ctrl+Shift+End",
    "vr_center": "Ctrl+Shift+C", "vr_placement": "Ctrl+Shift+P",
}

DEFAULT_PROFILE = {
    "name": "الإعدادات العامة",
    "exe": "",                      # e.g. "eldenring.exe" — empty for the default profile
    "capture": {
        "monitor": 1,               # 1-based index into the system's monitors
        "full": True,               # True = whole monitor, False = region below
        "region": None,             # [x, y, w, h] in physical pixels, relative to the monitor
        "interval_ms": 300,         # how often the region is checked for changes
        "stable_ms": 250,           # text must stay still this long before it is read
        "sensitivity": 3.0,         # mean pixel change (0-255) that counts as "new text"
        "method": "auto",           # auto | dxgi | window (the game window, like OBS) | gdi
    },
    "ocr": {"engine": "auto", "min_conf": 0.55},
    "lang": {"src": "auto", "tgt": "ar"},
    "translate": {"style": "gaming"},
    # this game's dictionary: names of characters, weapons, places... -> the translation to always use
    "glossary": [],                 # [{"src": "Mara", "tr": "مارا", "kind": "character"}]
    "display": {
        "mode": "screen",           # "screen" or "vr"
        "screen": {
            "monitor": 1, "anchor": "bottom", "offset": 80, "width_pct": 70,
            "place": "cover",       # cover / above: on the game's own text wherever it is; fixed: the subtitle box
            "blend": True,          # cover: use the game's own colours, so the Arabic looks like part of the game
            "steady": True,         # the subtitle box keeps one size and place instead of resizing with every line
            "recordable": True,     # the translation shows in screenshots and recordings (Game Bar, OBS, Discord)
            "custom_pos": None,     # [x, y] in logical pixels after the user drags it
            "font_family": styles.DEFAULT_FONT, "font_size": 26, "bold": True,
            "color": "#FFFFFF", "bg": "#0A0E1F", "bg_opacity": 80,
            "show_original": False, "max_lines": 4,
            # look (set together by a template, each can still be changed by hand)
            "template": styles.DEFAULT_TEMPLATE,
            "box": "card", "text_fx": "shadow", "accent": "#E7B964", "align": "center", "radius": 18,
            "fx_in": "slide", "fx_out": "fade", "fx_ms": 280,
            # layers: dialogue / quest / choices / other text each get their own place on screen
            "layers_on": True,
            "layers": styles.DEFAULT_LAYERS,
        },
        "vr": {
            "distance_m": 1.4, "width_m": 1.1, "height_m": -0.35, "side_m": 0.0,
            "placement": "head",    # head (fixed in view) | follow (lazy, smooth) | world (fixed in the room)
            "font_size": 44, "color": "#FFFFFF", "bg": "#0A0E1F", "bg_opacity": 80,
            "show_original": False, "font_family": styles.DEFAULT_FONT, "bold": True,
            "box": "card", "text_fx": "shadow", "accent": "#E7B964", "fx_in": "fade", "fx_out": "fade", "fx_ms": 240,
        },
    },
}

DEFAULT_SETTINGS = {
    "version": 1,
    "first_run": True,
    "ui_mode": "simple",            # "simple" or "advanced"
    "active_profile": "default",
    "auto_profile": True,           # switch profile when a known game is in front
    "minimize_to_tray": True,
    "hotkeys": DEFAULT_HOTKEYS,
    "engines": {
        "order": ["google", "mymemory", "claude", "deepl"],
        "enabled": {"google": True, "mymemory": True, "claude": False, "deepl": False},
        "claude_key": "", "claude_model": "claude-haiku-5-5",
        "deepl_key": "", "mymemory_email": "",
        "timeout_s": 6,
    },
    "profiles": {"default": DEFAULT_PROFILE},
    "templates": {},                # the user's own saved looks: id -> {name, desc, look}
    "performance": {"preset": "balanced", "gpu": False},   # light | balanced | high; gpu = OCR on the graphics card
    # performance readout over the game: which readings, and in which corner
    "hud": {"on": False, "corner": "top-left", "fps": True, "cpu_temp": True, "gpu_temp": True, "cpu": True,
            "ram": True, "ping": True, "scale": 100},
}


def deep_merge(base: dict, extra: dict) -> dict:
    """Return base updated with extra, recursively; unknown keys in extra are kept."""
    out = copy.deepcopy(base)
    for k, v in (extra or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


class Settings:
    """Thread-safe settings store with per-game profiles."""

    def __init__(self, path: Path | None = None):
        self.path = path or (data_dir() / "settings.json")
        self._lock = threading.RLock()
        self.data = self._load()

    # ---------- io ----------
    def _load(self) -> dict:
        raw = {}
        if self.path.exists():
            try:
                raw = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                bad = self.path.with_suffix(".broken.json")
                try:
                    self.path.replace(bad)
                except OSError:
                    pass
                raw = {}
        return self._normalize(raw)

    # ---------- backup ----------
    SECRET_KEYS = ("claude_key", "deepl_key")

    def export_text(self, include_keys: bool = False) -> str:
        """All settings (every game, templates, dictionary, shortcuts) as one file. API keys are left out unless asked."""
        with self._lock:
            data = copy.deepcopy(self.data)
        if not include_keys:
            for k in self.SECRET_KEYS:
                data.get("engines", {}).pop(k, None)
        return json.dumps({"app": "arabize-game", "kind": "settings", "version": APP_VERSION, "settings": data},
                          ensure_ascii=False, indent=2)

    def import_text(self, text: str) -> int:
        """Replace the settings with an exported file. Keys missing from the file keep their current values.
        Returns how many game profiles were imported. Raises ValueError for a file that is not a settings export."""
        doc = json.loads(text)
        raw = doc.get("settings") if isinstance(doc, dict) and doc.get("kind") == "settings" else None
        if not isinstance(raw, dict) or not isinstance(raw.get("profiles"), dict):
            raise ValueError("الملف ليس نسخة إعدادات من عرب لعبتك")
        with self._lock:
            eng = raw.setdefault("engines", {})
            for k in self.SECRET_KEYS:                     # keep this PC's keys if the file has none
                if not eng.get(k) and self.data.get("engines", {}).get(k):
                    eng[k] = self.data["engines"][k]
            raw["first_run"] = False
            self.data = self._normalize(raw)
            self.save()
        return len(self.data["profiles"])

    def _normalize(self, raw: dict) -> dict:
        if not isinstance(raw, dict):
            raw = {}
        data = deep_merge(DEFAULT_SETTINGS, raw)
        # every profile is completed with defaults so new options appear after updates
        raw_profiles = raw.get("profiles") if isinstance(raw.get("profiles"), dict) else {}
        data["hotkeys"] = {**DEFAULT_HOTKEYS, **(raw.get("hotkeys") or {})}   # new shortcuts appear for old installs
        data["profiles"] = {k: _migrate_profile(deep_merge(DEFAULT_PROFILE, v), raw_profiles.get(k) or {})
                            for k, v in data["profiles"].items()}
        if "default" not in data["profiles"]:
            data["profiles"]["default"] = copy.deepcopy(DEFAULT_PROFILE)
        if data["active_profile"] not in data["profiles"]:
            data["active_profile"] = "default"
        data["hotkeys"] = deep_merge(DEFAULT_HOTKEYS, data.get("hotkeys", {}))
        return data

    def save(self) -> None:
        with self._lock:
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(self.path)

    # ---------- profiles ----------
    @property
    def profile_id(self) -> str:
        return self.data["active_profile"]

    @property
    def profile(self) -> dict:
        with self._lock:
            return self.data["profiles"][self.data["active_profile"]]

    def set_active(self, pid: str) -> bool:
        with self._lock:
            if pid in self.data["profiles"] and pid != self.data["active_profile"]:
                self.data["active_profile"] = pid
                self.save()
                return True
            return False

    def profile_for_exe(self, exe: str | None) -> str | None:
        if not exe:
            return None
        exe = exe.lower()
        for pid, p in self.data["profiles"].items():
            if p.get("exe") and p["exe"].lower() == exe:
                return pid
        return None

    def add_profile(self, name: str, exe: str = "", copy_from: str | None = None) -> str:
        with self._lock:
            base = self.data["profiles"].get(copy_from or self.profile_id, DEFAULT_PROFILE)
            prof = copy.deepcopy(base)
            prof["name"] = name.strip() or exe or "لعبة"
            prof["exe"] = exe.strip()
            pid = _slug(prof["exe"] or prof["name"])
            n, cand = 2, pid
            while cand in self.data["profiles"]:
                cand = f"{pid}-{n}"
                n += 1
            self.data["profiles"][cand] = prof
            self.save()
            return cand

    def delete_profile(self, pid: str) -> bool:
        with self._lock:
            if pid == "default" or pid not in self.data["profiles"]:
                return False
            del self.data["profiles"][pid]
            if self.data["active_profile"] == pid:
                self.data["active_profile"] = "default"
            self.save()
            return True

    def update_profile(self, path: str, value) -> None:
        """Set a value in the active profile by dotted path, e.g. 'display.screen.font_size'."""
        with self._lock:
            node = self.profile
            keys = path.split(".")
            for k in keys[:-1]:
                node = node.setdefault(k, {})
            node[keys[-1]] = value
            self.save()

    def get(self, path: str, default=None):
        node = self.data
        for k in path.split("."):
            if not isinstance(node, dict) or k not in node:
                return default
            node = node[k]
        return node

    def set(self, path: str, value) -> None:
        with self._lock:
            node = self.data
            keys = path.split(".")
            for k in keys[:-1]:
                node = node.setdefault(k, {})
            node[keys[-1]] = value
            self.save()


def _migrate_profile(prof: dict, raw: dict) -> dict:
    """Bring a profile saved by an older version up to date without losing the user's choices."""
    scr, vr = prof["display"]["screen"], prof["display"]["vr"]
    raw_scr = (raw.get("display") or {}).get("screen") or {}
    # 1.0 had a single "fade_ms"; it becomes the effect speed
    if "fade_ms" in raw_scr and "fx_ms" not in raw_scr:
        scr["fx_ms"] = int(raw_scr["fade_ms"]) or 0
        scr["fx_in"] = scr["fx_out"] = "fade" if scr["fx_ms"] else "none"
    scr.pop("fade_ms", None)
    if raw_scr and "template" not in raw_scr:
        scr["template"] = "custom"          # an old profile keeps its look; no built-in template is "selected"
    scr["font_family"] = styles.normalize_font(scr.get("font_family"))
    vr["font_family"] = styles.normalize_font(vr.get("font_family"))
    return prof


def _slug(s: str) -> str:
    out = "".join(ch.lower() if ch.isalnum() else "-" for ch in s).strip("-")
    while "--" in out:
        out = out.replace("--", "-")
    return out or "game"
