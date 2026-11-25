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


def set_capture_visible(win_id: int, visible: bool) -> bool:
    """visible=True: screenshots and recordings show the window (normal). False: hidden from every capture.
    Returns True when the window is now hidden from capture."""
    if not IS_WIN:
        return False
    if not visible:
        return exclude_from_capture(win_id)
    try:
        ctypes.windll.user32.SetWindowDisplayAffinity(ctypes.c_void_p(int(win_id)), 0)   # WDA_NONE
    except Exception:
        pass
    return False


def is_admin() -> bool:
    if not IS_WIN:
        try:
            import os
            return os.geteuid() == 0
        except Exception:
            return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def restart_as_admin() -> bool:
    """Start this program again with administrator rights (Windows asks the user). True if the request was made."""
    if not IS_WIN:
        return False
    try:
        import subprocess
        exe = sys.executable
        args = "" if getattr(sys, "frozen", False) else subprocess.list2cmdline(sys.argv)
        return int(ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, args, None, 1)) > 32
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


def keep_on_top(win_id: int) -> bool:
    """Re-assert always-on-top. A game switching to fullscreen can push other topmost windows down;
    overlays like the Xbox Game Bar re-raise themselves the same way."""
    if not IS_WIN:
        return False
    try:
        HWND_TOPMOST, SWP_NOSIZE, SWP_NOMOVE, SWP_NOACTIVATE, SWP_SHOWWINDOW = -1, 0x1, 0x2, 0x10, 0x40
        return bool(ctypes.windll.user32.SetWindowPos(ctypes.c_void_p(int(win_id)), ctypes.c_void_p(HWND_TOPMOST), 0, 0, 0, 0,
                                                      SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE | SWP_SHOWWINDOW))
    except Exception:
        return False


def find_game_window(exe: str | None = None) -> tuple[int, str] | None:
    """(hwnd, exe) of the game: the foreground window, or the largest visible window of exe if given."""
    if not IS_WIN:
        return None
    try:
        import psutil
        user32 = ctypes.windll.user32
        own_pid = __import__("os").getpid()

        def exe_of(h):
            pid = ctypes.c_ulong(); user32.GetWindowThreadProcessId(h, ctypes.byref(pid))
            if not pid.value or pid.value == own_pid:
                return None
            try:
                return psutil.Process(pid.value).name()
            except Exception:
                return None

        if not exe:
            h = user32.GetForegroundWindow()
            e = exe_of(h) if h else None
            return (int(h), e) if e else None
        best, best_area = None, 0
        EnumProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

        def cb(h, _):
            nonlocal best, best_area
            if user32.IsWindowVisible(h) and (exe_of(h) or "").lower() == exe.lower():
                r = window_rect(h)
                if r and r[2] * r[3] > best_area:
                    best, best_area = int(h), r[2] * r[3]
            return True
        user32.EnumWindows(EnumProc(cb), 0)
        return (best, exe) if best else None
    except Exception:
        return None


def window_rect(hwnd: int) -> tuple[int, int, int, int] | None:
    """Screen rectangle (x, y, w, h) of a window as it is drawn (without the invisible resize border)."""
    if not IS_WIN:
        return None
    try:
        class RECT(ctypes.Structure):
            _fields_ = [("l", ctypes.c_long), ("t", ctypes.c_long), ("r", ctypes.c_long), ("b", ctypes.c_long)]
        r = RECT()
        DWMWA_EXTENDED_FRAME_BOUNDS = 9
        if ctypes.windll.dwmapi.DwmGetWindowAttribute(ctypes.c_void_p(int(hwnd)), DWMWA_EXTENDED_FRAME_BOUNDS,
                                                      ctypes.byref(r), ctypes.sizeof(r)) != 0:
            ctypes.windll.user32.GetWindowRect(ctypes.c_void_p(int(hwnd)), ctypes.byref(r))
        return r.l, r.t, r.r - r.l, r.b - r.t
    except Exception:
        return None


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
