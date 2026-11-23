"""OS-specific helpers. Every function degrades gracefully off Windows."""
from __future__ import annotations

import ctypes
import sys

IS_WIN = sys.platform == "win32"
WDA_EXCLUDEFROMCAPTURE = 0x11


def exclude_from_capture(win_id: int) -> bool:
    """Hide our subtitle window from screen capture (Windows 10 2004+), so OCR never reads it."""
    if not IS_WIN:
        return False
    try:
        return bool(ctypes.windll.user32.SetWindowDisplayAffinity(ctypes.c_void_p(int(win_id)), WDA_EXCLUDEFROMCAPTURE))
    except Exception:
        return False


def foreground_exe() -> str | None:
    """Executable name of the window in front (the game), e.g. 'eldenring.exe'."""
    if not IS_WIN:
        return None
    try:
        import psutil
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if not pid.value:
            return None
        return psutil.Process(pid.value).name()
    except Exception:
        return None


def foreground_title() -> str:
    if not IS_WIN:
        return ""
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        n = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(n + 1)
        user32.GetWindowTextW(hwnd, buf, n + 1)
        return buf.value
    except Exception:
        return ""


_PROC = None


def process_usage() -> tuple[float, float]:
    """(cpu % of one core since the previous call, memory MB) of this app."""
    global _PROC
    try:
        import psutil
        if _PROC is None:
            _PROC = psutil.Process()
            _PROC.cpu_percent(interval=None)
        return _PROC.cpu_percent(interval=None), _PROC.memory_info().rss / 1_048_576
    except Exception:
        return 0.0, 0.0
