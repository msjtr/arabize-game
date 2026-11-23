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

APP_NAME_AR = "عرب لعبتك"
APP_NAME_EN = "Arabize Game"
APP_VERSION = "1.0.0"


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
    },
    "ocr": {"engine": "auto", "min_conf": 0.55},
    "lang": {"src": "auto", "tgt": "ar"},
    "translate": {"style": "gaming"},
    "display": {
        "mode": "screen",           # "screen" or "vr"
        "screen": {
            "monitor": 1, "anchor": "bottom", "offset": 80, "width_pct": 70,
            "custom_pos": None,     # [x, y] in logical pixels after the user drags it
            "font_family": "Noto Sans Arabic", "font_size": 26, "bold": True,
            "color": "#FFFFFF", "bg": "#05080F", "bg_opacity": 72,
            "show_original": False, "max_lines": 4, "fade_ms": 220,
        },
        "vr": {
            "distance_m": 1.4, "width_m": 1.1, "height_m": -0.35,
            "font_size": 44, "color": "#FFFFFF", "bg": "#05080F", "bg_opacity": 80,
            "show_original": False,
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
        "timeout_s": 8,
    },
    "profiles": {"default": DEFAULT_PROFILE},
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
        data = deep_merge(DEFAULT_SETTINGS, raw)
        # every profile is completed with defaults so new options appear after updates
        data["profiles"] = {k: deep_merge(DEFAULT_PROFILE, v) for k, v in data["profiles"].items()}
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


def _slug(s: str) -> str:
    out = "".join(ch.lower() if ch.isalnum() else "-" for ch in s).strip("-")
    while "--" in out:
        out = out.replace("--", "-")
    return out or "game"
