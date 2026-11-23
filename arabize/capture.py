"""Screen capture (multi-monitor, region) and cheap change detection."""
from __future__ import annotations

import threading
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


class Capturer:
    """Grabs a monitor or a region of it. One mss instance per thread (mss is not thread-safe)."""

    def __init__(self):
        self._local = threading.local()

    def _sct(self):
        if mss is None:
            raise RuntimeError("مكتبة التقاط الشاشة mss غير مثبتة")
        s = getattr(self._local, "sct", None)
        if s is None:
            s = mss.MSS() if hasattr(mss, "MSS") else mss.mss()
            self._local.sct = s
        return s

    def monitors(self) -> list[Monitor]:
        mons = self._sct().monitors[1:]
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

    def grab(self, monitor_index: int, region: list[int] | None = None) -> tuple[np.ndarray, dict]:
        """Returns (BGR image, absolute bbox dict). region is relative to the monitor."""
        mon = self.monitor(monitor_index)
        if region:
            x, y, w, h = [int(v) for v in region]
            x = max(0, min(x, mon.width - 1)); y = max(0, min(y, mon.height - 1))
            w = max(8, min(w, mon.width - x)); h = max(8, min(h, mon.height - y))
            box = {"left": mon.left + x, "top": mon.top + y, "width": w, "height": h}
        else:
            box = {"left": mon.left, "top": mon.top, "width": mon.width, "height": mon.height}
        shot = self._sct().grab(box)
        img = np.asarray(shot)[:, :, :3]  # BGRA -> BGR (view, no copy)
        return np.ascontiguousarray(img), box


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
