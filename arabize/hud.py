"""A small performance readout in a corner of the game: FPS, CPU temperature and use, GPU temperature, RAM, ping.

Click-through and always on top like the subtitle. Shown and hidden with a shortcut (Ctrl+Shift+F by default).
"""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QGuiApplication, QPainter
from PySide6.QtWidgets import QWidget

from .platform_utils import keep_on_top, set_capture_visible
from .styles import DEFAULT_FONT

FLAGS = Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.WindowDoesNotAcceptFocus | Qt.WindowTransparentForInput
CORNERS = [("top-left", "أعلى اليسار"), ("top-right", "أعلى اليمين"), ("bottom-left", "أسفل اليسار"), ("bottom-right", "أسفل اليمين")]


def temp_color(t: float | None) -> str:
    if t is None:
        return "#C9D0EA"
    return "#6FE3B0" if t < 70 else ("#FFD166" if t < 85 else "#FF7A6B")


def fps_color(f: float | None) -> str:
    if f is None:
        return "#C9D0EA"
    return "#6FE3B0" if f >= 55 else ("#FFD166" if f >= 30 else "#FF7A6B")


def hud_rows(cfg: dict, sensors: dict, fps: float | None, fps_state: str, ping: dict[str, int]) -> list[tuple[str, str, str]]:
    """(label, value, colour) rows for the readout, in the order the player reads them."""
    rows = []
    if cfg.get("fps", True):
        if fps is not None:
            rows.append(("FPS", f"{fps:.0f}", fps_color(fps)))
        else:
            rows.append(("FPS", {"need_admin": "يحتاج مسؤول", "missing": "—", "waiting": "…", "running": "…"}.get(fps_state, "—"),
                         "#C9D0EA"))
    if cfg.get("cpu_temp", True) or cfg.get("cpu", True):
        parts = []
        t = sensors.get("cpu_temp")
        if cfg.get("cpu_temp", True):
            parts.append(f"{t:.0f}°C" if t is not None else "—°C")
        if cfg.get("cpu", True) and sensors.get("cpu") is not None:
            parts.append(f"{sensors['cpu']:.0f}%")
        rows.append(("CPU", "  ".join(parts), temp_color(t)))
    if cfg.get("gpu_temp", True) and (sensors.get("gpu_temp") is not None or sensors.get("gpu_load") is not None):
        g = sensors.get("gpu_temp")
        parts = [f"{g:.0f}°C"] if g is not None else []
        if sensors.get("gpu_load") is not None:
            parts.append(f"{sensors['gpu_load']:.0f}%")
        rows.append(("GPU", "  ".join(parts), temp_color(g)))
    if cfg.get("ram", True) and sensors.get("ram_used_gb") is not None:
        rows.append(("RAM", f"{sensors['ram_used_gb']:.1f}/{sensors['ram_total_gb']:.0f} GB",
                     "#FFD166" if (sensors.get("ram_pct") or 0) > 90 else "#E6EAF8"))
    if cfg.get("ping", True) and ping:
        ms = min(ping.values())
        rows.append(("PING", f"{ms} ms", "#6FE3B0" if ms < 150 else ("#FFD166" if ms < 400 else "#FF7A6B")))
    return rows


class PerfHud(QWidget):
    def __init__(self, source):
        """source() -> (cfg, sensors dict, fps, fps_state, ping dict)."""
        super().__init__(None, FLAGS)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setWindowTitle("Arabize Game — HUD")
        self.setLayoutDirection(Qt.LeftToRight)       # numbers and units read left to right, like any game overlay
        self.source = source
        self.rows: list = []
        self.recordable = True
        self._tick = QTimer(self, interval=1000, timeout=self.refresh)
        self._top = QTimer(self, interval=1500, timeout=lambda: self.isVisible() and keep_on_top(int(self.winId())))

    def start(self):
        self.refresh()
        self.show()
        set_capture_visible(int(self.winId()), self.recordable)
        keep_on_top(int(self.winId()))
        self._tick.start(); self._top.start()

    def stop(self):
        self._tick.stop(); self._top.stop()
        self.hide()

    def refresh(self):
        cfg, sensors, fps, state, ping = self.source()
        self.rows = hud_rows(cfg, sensors, fps, state, ping)
        self._place(cfg)
        self.update()

    def _font(self, cfg, bold=False) -> QFont:
        f = QFont(DEFAULT_FONT); f.setFamilies([DEFAULT_FONT, "Segoe UI", "Arial"])
        f.setPixelSize(int(15 * int(cfg.get("scale", 100)) / 100)); f.setBold(bold)
        return f

    def _place(self, cfg):
        fm = QFontMetricsF(self._font(cfg, True))
        lh = fm.height() * 1.25
        w = max([fm.horizontalAdvance(f"{a}   {b}") for a, b, _ in self.rows] or [80]) + 28
        h = lh * max(1, len(self.rows)) + 16
        scr = QGuiApplication.primaryScreen().geometry()
        corner = cfg.get("corner", "top-left")
        x = scr.x() + 12 if corner.endswith("left") else scr.x() + scr.width() - w - 12
        y = scr.y() + 12 if corner.startswith("top") else scr.y() + scr.height() - h - 12
        self.setGeometry(int(x), int(y), int(w), int(h))
        self._lh = lh

    def paintEvent(self, _):
        if not self.rows:
            return
        cfg = self.source()[0]
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing); p.setLayoutDirection(Qt.LeftToRight)
        p.setPen(Qt.NoPen); p.setBrush(QColor(8, 11, 24, 170))
        p.drawRoundedRect(QRectF(0, 0, self.width(), self.height()), 10, 10)
        fb, fr = self._font(cfg, True), self._font(cfg)
        y = 8.0
        for label, value, color in self.rows:
            r = QRectF(12, y, self.width() - 24, self._lh)
            p.setFont(fb); p.setPen(QColor("#8A92B6")); p.drawText(r, Qt.AlignLeft | Qt.AlignVCenter, label)
            p.setFont(fb if label == "FPS" else fr); p.setPen(QColor(color)); p.drawText(r, Qt.AlignRight | Qt.AlignVCenter, "\u2066" + value + "\u2069")
            y += self._lh
        p.end()
