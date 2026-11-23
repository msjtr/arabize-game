"""System-wide keyboard shortcuts that work while the game has focus."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal

_SPECIAL = {"ctrl": "<ctrl>", "control": "<ctrl>", "shift": "<shift>", "alt": "<alt>", "meta": "<cmd>", "win": "<cmd>",
            "space": "<space>", "tab": "<tab>", "esc": "<esc>", "escape": "<esc>", "enter": "<enter>", "return": "<enter>",
            "home": "<home>", "end": "<end>", "pgup": "<page_up>", "pgdown": "<page_down>", "ins": "<insert>", "del": "<delete>",
            "up": "<up>", "down": "<down>", "left": "<left>", "right": "<right>"}


def to_pynput(seq: str) -> str | None:
    """'Ctrl+Shift+T' -> '<ctrl>+<shift>+t'; 'F8' -> '<f8>'."""
    if not seq:
        return None
    out = []
    for part in seq.replace(" ", "").split("+"):
        k = part.lower()
        if not k:
            return None
        if k in _SPECIAL:
            out.append(_SPECIAL[k])
        elif k.startswith("f") and k[1:].isdigit():
            out.append(f"<{k}>")
        elif len(k) == 1:
            out.append(k)
        else:
            return None
    return "+".join(out)


class Hotkeys(QObject):
    triggered = Signal(str)
    failed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._listener = None

    def apply(self, mapping: dict[str, str]) -> list[str]:
        """Start listening. Returns the actions whose shortcut could not be registered."""
        self.stop()
        bad, combos = [], {}
        for action, seq in mapping.items():
            k = to_pynput(seq)
            if not k or k in combos:
                bad.append(action)
                continue
            combos[k] = (lambda a=action: self.triggered.emit(a))
        try:
            from pynput import keyboard  # imported late: needs a desktop session
            self._listener = keyboard.GlobalHotKeys(combos)
            self._listener.daemon = True
            self._listener.start()
        except Exception as e:
            self.failed.emit(f"تعذّر تفعيل الاختصارات العامة: {e}")
            return list(mapping)
        return bad

    def stop(self):
        if self._listener is not None:
            try:
                self._listener.stop()
            except Exception:
                pass
            self._listener = None
