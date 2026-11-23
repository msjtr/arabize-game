"""Screen capture (multi-monitor, region) and cheap change detection."""
from __future__ import annotations

import sys
import threading
import time
from dataclasses import dataclass

import numpy as np

try:
    import mss  # type: ignore
except Exception:  # pragma: no cover
    mss = None


@dataclass
class Monitor:
    index: int        # 1-based, matches the settings file
    left: int
    top: int
    width: int
    height: int
    primary: bool = False

    @property
    def label(self) -> str:
        tag = " (الرئيسية)" if self.primary else ""
        return f"الشاشة {self.index}{tag} — {self.width}×{self.height}"


METHODS = [
    ("auto", "تلقائي (الأفضل)", "يستخدم DXGI، ويرجع لطريقة النظام القديمة إن لم يعمل"),
    ("window", "نافذة اللعبة فقط (مثل OBS)", "يلتقط نافذة اللعبة نفسها حتى لو غطّتها نوافذ أخرى أو كانت على شاشة ثانية"),
    ("dxgi", "الشاشة عبر DXGI", "سريع، ويعمل مع ألعاب ملء الشاشة"),
    ("gdi", "طريقة النظام القديمة", "للأجهزة القديمة فقط؛ قد تظهر بعض الألعاب سوداء"),
]


class CaptureError(RuntimeError):
    pass


class _GdiSource:
    """mss (GDI BitBlt). Works everywhere, but DirectX games in fullscreen can come out black."""
    name = "gdi"

    def __init__(self):
        if mss is None:
            raise CaptureError("مكتبة التقاط الشاشة mss غير مثبتة")
        self.sct = mss.MSS() if hasattr(mss, "MSS") else mss.mss()

    def monitors(self) -> list[dict]:
        return list(self.sct.monitors[1:])

    def grab(self, box: dict) -> np.ndarray:
        return np.ascontiguousarray(np.asarray(self.sct.grab(box))[:, :, :3])

    def close(self):
        try:
            self.sct.close()
        except Exception:
            pass


class _DxgiSource:  # pragma: no cover - Windows only, exercised by tests/test_windows.py on real Windows
    """DXGI Desktop Duplication: reads what the GPU shows on a monitor, fullscreen games included.
    Returns the previous frame when nothing changed on screen, which costs almost nothing."""
    name = "dxgi"

    def __init__(self, mon: Monitor, count: int):
        try:
            from windows_capture import DxgiDuplicationSession  # type: ignore
        except Exception as e:
            raise CaptureError(f"DXGI غير متاح: {e}")
        self.mon = mon
        self.session = None
        # the library numbers monitors in the same order as Windows; confirm by size, then try the others
        order = [mon.index] + [i for i in range(1, count + 1) if i != mon.index]
        for i in order:
            try:
                sess = DxgiDuplicationSession(i)
                fr = None
                for _ in range(6):
                    fr = sess.acquire_frame(timeout_ms=50)
                    if fr is not None:
                        break
                if fr is not None and (fr.width, fr.height) == (mon.width, mon.height):
                    self.session, self.last = sess, fr.to_bgr().copy()
                    break
            except Exception:
                continue
        if self.session is None:
            raise CaptureError("تعذّر بدء DXGI لهذه الشاشة")

    def grab(self, box: dict) -> np.ndarray:
        try:
            fr = self.session.acquire_frame(timeout_ms=0)
        except Exception:
            self.session.recreate()      # display mode changed, game switched to fullscreen, etc.
            fr = None
        if fr is not None:
            self.last = fr.to_bgr().copy()
        x, y = box["left"] - self.mon.left, box["top"] - self.mon.top
        return np.ascontiguousarray(self.last[y:y + box["height"], x:x + box["width"]])

    def close(self):
        self.session = None


class _WindowSource:  # pragma: no cover - Windows only
    """Windows Graphics Capture of one window (the same API OBS uses for window capture). It sees the game
    even when other windows are on top of it. Frames arrive on the library's thread; we keep the latest."""
    name = "window"

    def __init__(self, hwnd: int):
        try:
            from windows_capture import WindowsCapture  # type: ignore
        except Exception as e:
            raise CaptureError(f"التقاط النافذة غير متاح: {e}")
        self.hwnd = hwnd
        self._lock = threading.Lock()
        self._frame: np.ndarray | None = None
        self._closed = False
        cap = WindowsCapture(cursor_capture=False, draw_border=False, window_hwnd=int(hwnd), minimum_update_interval=50)

        @cap.event
        def on_frame_arrived(frame, control):
            if self._closed:
                control.stop(); return
            img = np.ascontiguousarray(frame.frame_buffer[:, :, :3])
            with self._lock:
                self._frame = img

        @cap.event
        def on_closed():
            self._closed = True

        self.control = cap.start_free_threaded()
        t0 = time.monotonic()
        while self._frame is None and time.monotonic() - t0 < 2.0 and not self._closed:
            time.sleep(0.02)
        if self._frame is None:
            self.close()
            raise CaptureError("لم تصل صورة من نافذة اللعبة")

    @property
    def alive(self) -> bool:
        return not self._closed

    def grab(self, box: dict) -> np.ndarray:
        with self._lock:
            img = self._frame
        x, y = box.get("wx", 0), box.get("wy", 0)
        return np.ascontiguousarray(img[y:y + box["height"], x:x + box["width"]])

    def size(self) -> tuple[int, int]:
        with self._lock:
            h, w = self._frame.shape[:2]
        return w, h

    def close(self):
        self._closed = True
        try:
            self.control.stop()
        except Exception:
            pass


class Capturer:
    """Grabs a monitor, a region of it, or the game window. One instance per thread.

    method: "auto" (DXGI, falling back to GDI), "dxgi", "gdi", or "window" (the game window via Windows Graphics
    Capture, falling back to auto). self.active tells which one is really in use."""

    def __init__(self, method: str = "auto"):
        self.method = method
        self._gdi: _GdiSource | None = None
        self._dxgi: dict[int, _DxgiSource] = {}
        self._win: _WindowSource | None = None
        self._failed: set[str] = set()
        self.active = "gdi"
        self.note = ""

    # ---------- monitors ----------
    def _gdi_src(self) -> _GdiSource:
        if self._gdi is None:
            self._gdi = _GdiSource()
        return self._gdi

    def monitors(self) -> list[Monitor]:
        mons = self._gdi_src().monitors()
        out = []
        for i, m in enumerate(mons, 1):
            out.append(Monitor(i, m["left"], m["top"], m["width"], m["height"], primary=(m["left"] == 0 and m["top"] == 0)))
        if out and not any(m.primary for m in out):
            out[0].primary = True
        return out

    def monitor(self, index: int) -> Monitor:
        mons = self.monitors()
        if not mons:
            raise RuntimeError("لم يُعثر على أي شاشة")
        return mons[index - 1] if 1 <= index <= len(mons) else mons[0]

    # ---------- grabbing ----------
    def grab(self, monitor_index: int, region: list[int] | None = None, game: tuple[int, str] | None = None
             ) -> tuple[np.ndarray, dict]:
        """Returns (BGR image, absolute bbox dict). region is relative to the monitor.
        game=(hwnd, exe) is used by the "window" method."""
        if self.method == "window" and not region and "window" not in self._failed:
            got = self._grab_window(game)
            if got is not None:
                return got
        mon = self.monitor(monitor_index)
        if region:
            x, y, w, h = [int(v) for v in region]
            x = max(0, min(x, mon.width - 1)); y = max(0, min(y, mon.height - 1))
            w = max(8, min(w, mon.width - x)); h = max(8, min(h, mon.height - y))
            box = {"left": mon.left + x, "top": mon.top + y, "width": w, "height": h}
        else:
            box = {"left": mon.left, "top": mon.top, "width": mon.width, "height": mon.height}
        if self.method in ("auto", "dxgi", "window") and "dxgi" not in self._failed and sys.platform == "win32":
            try:
                src = self._dxgi.get(mon.index)
                if src is None or (src.mon.width, src.mon.height, src.mon.left, src.mon.top) != (mon.width, mon.height, mon.left, mon.top):
                    src = self._dxgi[mon.index] = _DxgiSource(mon, len(self.monitors()))
                img = src.grab(box)
                if img.size:
                    self.active = "dxgi"
                    return img, box
            except Exception as e:
                self._failed.add("dxgi"); self.note = str(e)
        self.active = "gdi"
        return self._gdi_src().grab(box), box

    def _grab_window(self, game):
        from .platform_utils import window_rect
        if not game:
            return None
        hwnd = game[0]
        try:
            if self._win is None or self._win.hwnd != hwnd or not self._win.alive:
                if self._win is not None:
                    self._win.close()
                self._win = _WindowSource(hwnd)
            rect = window_rect(hwnd)
            if not rect:
                return None
            fw, fh = self._win.size()
            # the captured frame is the window as drawn; place it on the screen rectangle of the window
            box = {"left": rect[0], "top": rect[1], "width": min(fw, rect[2]), "height": min(fh, rect[3]), "wx": 0, "wy": 0}
            img = self._win.grab(box)
            if not img.size:
                return None
            self.active = "window"
            return img, {k: box[k] for k in ("left", "top", "width", "height")}
        except Exception as e:
            self.note = str(e)
            self._failed.add("window")
            return None

    def close(self):
        for s in list(self._dxgi.values()):
            s.close()
        self._dxgi.clear()
        if self._win is not None:
            self._win.close()
        if self._gdi is not None:
            self._gdi.close()


def thumb(img: np.ndarray, width: int = 192) -> np.ndarray:
    """Tiny grayscale copy used only to compare frames (cheap)."""
    h, w = img.shape[:2]
    step = max(1, w // width)
    small = img[::step, ::step]
    return (small[..., 0].astype(np.uint16) * 29 + small[..., 1].astype(np.uint16) * 150
            + small[..., 2].astype(np.uint16) * 77 >> 8).astype(np.int16)


class ChangeDetector:
    """Says when the picture changed and then settled — the moment to run OCR.

    States: idle -> changing -> (stable for stable_ms) -> fire once -> idle.
    """

    def __init__(self, sensitivity: float = 3.0, stable_ms: int = 250):
        self.sensitivity = sensitivity
        self.stable_ms = stable_ms
        self.prev: np.ndarray | None = None
        self.changing = False
        self.still_since = 0.0
        self.force = True  # first frame is always read

    def diff(self, t: np.ndarray) -> float:
        if self.prev is None or self.prev.shape != t.shape:
            return 255.0
        return float(np.abs(t - self.prev).mean())

    def update(self, img: np.ndarray, now: float) -> bool:
        t = thumb(img)
        d = self.diff(t)
        self.prev = t
        if d >= self.sensitivity:
            self.changing = True
            self.still_since = now
            return False
        if self.force:
            self.force = False
            self.changing = False
            return True
        if self.changing and (now - self.still_since) * 1000 >= self.stable_ms:
            self.changing = False
            return True
        return False

    def trigger(self) -> None:
        self.force = True
