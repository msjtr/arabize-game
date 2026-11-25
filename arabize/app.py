"""Application controller: owns settings, memory, engines, the live loop, overlay, VR, hotkeys and tray."""
from __future__ import annotations

import threading
import time

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QAction, QGuiApplication
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from .cache import Store
from .capture import Capturer
from .config import APP_NAME_AR, Settings
from .engines import Manager
from .hotkeys import Hotkeys
from .hud import PerfHud
from .hwinfo import FpsMeter, Sensors
from . import styles
from .overlay import OverlayLayers
from .pipeline import LiveTranslator
from .platform_utils import IS_WIN, foreground_exe, restart_as_admin
from .screens import RegionSelector, qscreen_for
from .ui import icons, theme
from .logs import log
from .vr import OPENXR_HINT, VRError, VRNotRunning, VRSubtitle, launch_steamvr, openxr_runtime


SAMPLE_ITEMS = styles.SAMPLE_ITEMS


class Controller(QObject):
    status = Signal(str, str)
    result = Signal(dict)
    metrics = Signal(dict)
    running_changed = Signal(bool)
    mode_changed = Signal()
    profile_changed = Signal()
    capture_updated = Signal()
    engines_tested = Signal(list)
    game_changed = Signal(str)
    toast_signal = Signal(str, bool)

    def __init__(self, settings: Settings | None = None, store: Store | None = None):
        super().__init__()
        self.settings = settings or Settings()
        self.store = store or Store()
        self.manager = Manager(self.settings, self.store)
        self.worker: LiveTranslator | None = None
        self.overlay = OverlayLayers()
        self.overlay.moved.connect(self._overlay_moved)
        self.vr = VRSubtitle()
        self.vr_timer = QTimer(self, interval=16); self.vr_timer.timeout.connect(self._vr_tick)
        self.vr_events = QTimer(self, interval=250); self.vr_events.timeout.connect(self._vr_events)
        self.vr_wait = QTimer(self, interval=3000); self.vr_wait.timeout.connect(self._vr_retry)
        self._vr_wait_until = 0.0
        self._xr_warned = False
        self._vr_test_until = 0.0
        self._vr_t = time.monotonic()
        self.overlay_hidden = False
        self.last_items: list[dict] = []
        self.quitting = False
        self.window = None
        self.tray: QSystemTrayIcon | None = None
        self.hotkeys = Hotkeys(self)
        self.hotkeys.triggered.connect(self._hotkey)
        self.hotkeys.failed.connect(lambda m: self.toast(m, err=True))
        self._game = None
        self.game_timer = QTimer(self); self.game_timer.timeout.connect(self._watch_game); self.game_timer.start(2000)
        # performance readout: live readings and the game's frame rate, only while someone looks at them
        self.sensors = Sensors()
        self.fps = FpsMeter()
        self.hud = PerfHud(self._hud_source)
        self.apply_display()
        if self.settings.get("hud.on"):
            QTimer.singleShot(1500, lambda: self.set_hud(True, quiet=True))

    # ------------------------------------------------------------------ helpers
    @property
    def prof(self) -> dict:
        return self.settings.profile

    def toast(self, text: str, err: bool = False):
        self.toast_signal.emit(text, err)

    def tray_available(self) -> bool:
        return self.tray is not None and QSystemTrayIcon.isSystemTrayAvailable()

    def toast_tray(self, text: str):
        if self.tray_available():
            self.tray.showMessage(APP_NAME_AR, text, QSystemTrayIcon.Information, 3000)

    def monitors(self):
        return Capturer().monitors()

    @property
    def running(self) -> bool:
        return self.worker is not None and self.worker.isRunning()

    # ------------------------------------------------------------------ live translation
    def start(self):
        if self.running:
            return
        if self.prof["display"]["mode"] == "vr" and not self._start_vr():
            return
        w = LiveTranslator(self.settings, self.store, self.manager)
        w.status.connect(self.status)
        w.status.connect(self._on_status)
        w.result.connect(self._on_result)
        w.cleared.connect(self._on_cleared)
        w.metrics.connect(self.metrics)
        self.worker = w
        w.start()
        self.running_changed.emit(True)
        self._update_tray()

    def stop(self):
        if self.worker:
            self.worker.stop()
            self.worker.wait(4000)
            self.worker = None
        self.overlay.clear()
        self.vr.hide()
        self.running_changed.emit(False)
        self.status.emit("stopped", "متوقف")
        self._update_tray()

    def toggle(self):
        self.stop() if self.running else self.start()

    def restart_if_running(self):
        if self.running:
            self.stop(); self.start()

    def retranslate(self):
        if not self.running:
            self.start()
        elif self.worker:
            self.worker.trigger()

    def _on_status(self, code, msg):
        if code == "error":
            self.toast(msg, err=True)

    def _on_result(self, r: dict):
        # the reader takes its picture from the game window itself: our windows are not in it
        self.overlay.ocr_blind = r.get("capture") == "window"
        self.last_items = r["items"]
        self._show(self.last_items)
        self.result.emit(r)

    def _on_cleared(self):
        self.last_items = []
        self.overlay.clear()
        self.vr.hide()

    def _show(self, items):
        if self.prof["display"]["mode"] == "vr":
            self.vr.show_items(items)
            return
        if self.overlay_hidden or not items:
            return
        self.overlay.show_items(items)
        if self.worker:
            self.worker.set_exclusions(self.overlay.physical_rects())

    # ------------------------------------------------------------------ display
    def apply_display(self):
        st = dict(self.prof["display"]["screen"])
        st["rtl"] = self.prof["lang"]["tgt"] in ("ar", "fa", "ur", "he")
        screens = QGuiApplication.screens()
        idx = st.get("monitor", 1)
        qs = screens[idx - 1] if 1 <= idx <= len(screens) else QGuiApplication.primaryScreen()
        self.overlay.configure(st, qs)
        if self.overlay.isVisible() and self.last_items:
            self.overlay.show_items(self.last_items)
        if self.vr.active:
            self.vr.apply_style({**self.prof["display"]["vr"], "rtl": st["rtl"]})
            if self.last_items:
                self.vr.show_items(self.last_items)
        self._vr_timer_sync()

    # ------------------------------------------------------------------ VR panel: follow / world placement, in-headset controls
    def _vr_timer_sync(self):
        need = self.vr.active and self.prof["display"]["vr"].get("placement", "head") != "head"
        if need and not self.vr_timer.isActive():
            self._vr_t = time.monotonic(); self.vr_timer.start()
        elif not need and self.vr_timer.isActive():
            self.vr_timer.stop()

    def _vr_tick(self):
        now = time.monotonic()
        dt, self._vr_t = now - self._vr_t, now
        self.vr.update_pose(dt)

    VR_STEPS = {"vr_left": ("side_m", -0.05), "vr_right": ("side_m", 0.05), "vr_up": ("height_m", 0.05),
                "vr_down": ("height_m", -0.05), "vr_nearer": ("distance_m", -0.1), "vr_farther": ("distance_m", 0.1),
                "vr_bigger": ("width_m", 0.1), "vr_smaller": ("width_m", -0.1)}
    VR_LIMITS = {"side_m": (-1.5, 1.5), "height_m": (-1.0, 1.0), "distance_m": (0.5, 4.0), "width_m": (0.4, 3.0)}
    VR_NAMES = {"side_m": "يمين/يسار", "height_m": "الارتفاع", "distance_m": "المسافة", "width_m": "العرض"}

    def vr_adjust(self, action: str) -> bool:
        """In-headset controls. Returns False when VR mode is not on (the shortcut is then ignored)."""
        if self.prof["display"]["mode"] != "vr":
            return False
        v = self.prof["display"]["vr"]
        if action in self.VR_STEPS:
            key, step = self.VR_STEPS[action]
            lo, hi = self.VR_LIMITS[key]
            val = round(min(hi, max(lo, float(v.get(key, 0.0)) + step)), 2)
            self.settings.update_profile(f"display.vr.{key}", val)
            msg = f"{self.VR_NAMES[key]}: {val:+.2f} م" if key in ("side_m", "height_m") else f"{self.VR_NAMES[key]}: {val:.1f} م"
        elif action == "vr_center":
            self.vr.recenter(); msg = "أُعيدت اللوحة أمامك"
        elif action == "vr_placement":
            from .vr import PLACEMENTS
            ids = [k for k, *_ in PLACEMENTS]
            nxt = ids[(ids.index(v.get("placement", "head")) + 1) % len(ids)] if v.get("placement", "head") in ids else "head"
            self.settings.update_profile("display.vr.placement", nxt)
            self.vr.recenter()
            msg = next(t for k, t, _ in PLACEMENTS if k == nxt)
        else:
            return False
        self.apply_display()
        self.vr_feedback(msg)
        self.profile_changed.emit()
        return True

    def vr_feedback(self, msg: str):
        """Show what changed inside the headset for a moment, then the subtitle again."""
        if not self.vr.active:
            return
        self.vr.show_items([{"kind": "other", "label": "", "tr": msg, "src": ""}])
        QTimer.singleShot(1200, lambda: self.vr.active and self.vr.show_items(self.last_items or [{"kind": "other", "label": "", "tr": "·", "src": ""}]))

    # ------------------------------------------------------------------ translation size (shortcut, works in game)
    SIZE_LIMITS = {"screen": (12, 80), "vr": (20, 90)}

    def adjust_size(self, step: int) -> int:
        """Make the translation bigger (+) or smaller (-) from inside the game. Saved for this game."""
        mode = "vr" if self.prof["display"]["mode"] == "vr" else "screen"
        lo, hi = self.SIZE_LIMITS[mode]
        cur = int(self.prof["display"][mode].get("font_size", 26))
        val = max(lo, min(hi, cur + step * (4 if mode == "vr" else 2)))
        self.settings.update_profile(f"display.{mode}.font_size", val)
        self.apply_display()
        if mode == "screen" and self.last_items and not self.overlay_hidden:
            self.overlay.show_items(self.last_items)
        self.profile_changed.emit()
        msg = f"حجم الترجمة: {val}"
        if mode == "vr":
            self.vr_feedback(msg)
        else:
            self.toast(msg)
        return val

    # ------------------------------------------------------------------ performance readout (FPS, temperatures, ping)
    def _hud_source(self):
        ping = self.manager.ping()
        return (self.settings.get("hud", {}) or {}, self.sensors.data, self.fps.current(), self.fps.state, ping)

    def _device_page_open(self) -> bool:
        w = self.window
        return bool(w and w.isVisible() and type(w.stack.currentWidget()).__name__ == "DevicePage")

    def set_hud(self, on: bool, quiet: bool = False):
        self.settings.set("hud.on", bool(on))
        if bool(on) == self.hud.isVisible():
            return
        if on:
            self.sensors.start()
            if (self.settings.get("hud", {}) or {}).get("fps", True):
                self.fps.start()
            self.hud.recordable = bool(self.prof["display"]["screen"].get("recordable", True))
            self.hud.start()
            if not quiet:
                self.toast("ظهر مؤشر الأداء — اضغط الاختصار نفسه لإخفائه")
        else:
            self.hud.stop()
            if not self._device_page_open():
                self.fps.stop()
            self.sensors.stop()
            if not quiet:
                self.toast("أُخفي مؤشر الأداء")

    def toggle_hud(self):
        self.set_hud(not self.hud.isVisible())

    def restart_admin(self):
        """FPS needs administrator rights: start again elevated (Windows asks), then close this copy."""
        if restart_as_admin():
            self.quit()
        else:
            self.toast("لم يُعِد ويندوز التشغيل كمسؤول — اضغط بزر الماوس الأيمن على البرنامج واختر «تشغيل كمسؤول»", err=True)

    def toggle_overlay(self):
        self.overlay_hidden = not self.overlay_hidden
        self.vr.set_hidden(self.overlay_hidden)
        if self.overlay_hidden:
            self.overlay.hide()
            self.toast("أُخفيت الترجمة — اضغط الاختصار نفسه لإظهارها")
        else:
            if self.last_items:
                self._show(self.last_items)
            self.toast("ظهرت الترجمة")

    def edit_overlay_position(self, layer: str = "dialogue"):
        if self.prof["display"]["mode"] != "screen":
            self.toast("التحريك بالماوس متاح في وضع الشاشة", err=True); return
        self.overlay.set_edit_mode(True, layer)

    def _overlay_moved(self, layer, pos):
        if layer == "dialogue":
            self.settings.update_profile("display.screen.custom_pos", pos)
        else:
            self.settings.update_profile(f"display.screen.layers.{layer}.custom_pos", pos)
        self.toast("حُفظ مكان الطبقة لهذه اللعبة")
        self.apply_display()
        self.profile_changed.emit()

    # ------------------------------------------------------------------ templates
    def templates(self) -> dict:
        return styles.all_templates(self.settings.get("templates", {}))

    def apply_template(self, tid: str) -> bool:
        t = self.templates().get(tid)
        if not t:
            return False
        disp = self.prof["display"]
        self.settings.update_profile("display.screen", {**styles.apply_template(disp["screen"], t["look"]), "template": tid})
        self.settings.update_profile("display.vr", styles.vr_from_look(disp["vr"], t["look"]))
        self.apply_display()
        self.profile_changed.emit()
        if self.overlay.isVisible() or self.running:
            self._show(self.last_items or [])
        return True

    def save_template(self, name: str, desc: str = "") -> str:
        tid = styles.new_template_id(name)
        custom = dict(self.settings.get("templates", {}) or {})
        custom[tid] = {"name": name.strip()[:40] or "قالبي", "desc": desc.strip()[:120],
                       "look": styles.look_of(self.prof["display"]["screen"])}
        self.settings.set("templates", custom)
        self.settings.update_profile("display.screen.template", tid)
        self.profile_changed.emit()
        return tid

    def delete_template(self, tid: str) -> bool:
        custom = dict(self.settings.get("templates", {}) or {})
        if tid not in custom:
            return False
        del custom[tid]
        self.settings.set("templates", custom)
        if self.prof["display"]["screen"].get("template") == tid:
            self.settings.update_profile("display.screen.template", "custom")
        self.profile_changed.emit()
        return True

    def import_templates(self, text: str) -> int:
        new = styles.import_templates(text)
        custom = dict(self.settings.get("templates", {}) or {}); custom.update(new)
        self.settings.set("templates", custom)
        self.profile_changed.emit()
        return len(new)

    def export_templates(self) -> str:
        return styles.export_templates(self.settings.get("templates", {}) or {})

    def preview_effect(self):
        """Replay the entrance effect on screen with sample text so the user sees the template in the real game."""
        if self.prof["display"]["mode"] != "screen":
            return
        sample = self.last_items or SAMPLE_ITEMS
        self.overlay._last = {}
        self.overlay.show_items(sample)
        if not self.running:
            QTimer.singleShot(4200, lambda: (not self.running) and self.overlay.clear())

    # ------------------------------------------------------------------ modes / VR
    def set_mode(self, mode: str):
        if mode == self.prof["display"]["mode"]:
            return
        if mode == "vr":
            if not self._start_vr():
                self.mode_changed.emit(); return
            self.overlay.clear()
        else:
            (self.vr.stop(), self._vr_timer_sync())
        self.settings.update_profile("display.mode", mode)
        if self.last_items:
            self._show(self.last_items)
        self.toast("وضع الواقع الافتراضي مفعّل" if mode == "vr" else "وضع الشاشة مفعّل")
        self.mode_changed.emit()

    def _start_vr(self, launch: bool = True) -> bool:
        """Connect to SteamVR. If it is not running yet, start it and keep trying in the background (True = connected
        or on the way)."""
        if self.vr.active:
            return True
        try:
            self.vr.start({**self.prof["display"]["vr"], "rtl": self.prof["lang"]["tgt"] in ("ar", "fa", "ur", "he")})
        except VRNotRunning:
            if not self.vr_wait.isActive():
                started = launch and launch_steamvr()
                self.toast("يشغّل SteamVR الآن… ستظهر الترجمة في النظارة حين يجهز" if started
                           else "شغّل SteamVR وسأتصل به تلقائياً حين يعمل")
                self._vr_wait_until = time.monotonic() + 180
                self.vr_wait.start()
            return True
        except VRError as e:
            log.warning("VR start: %s", e)
            self.toast(str(e), err=True)
            return False
        self._vr_connected()
        return True

    def _vr_connected(self):
        self.vr_wait.stop()
        self.vr_events.start()
        self._vr_timer_sync()
        self.vr.set_hidden(self.overlay_hidden)
        if self.last_items:
            self.vr.show_items(self.last_items)
        if openxr_runtime() == "meta" and not self._xr_warned:
            self._xr_warned = True
            QTimer.singleShot(2500, lambda: self.toast(OPENXR_HINT))
        log.info("VR connected")

    def _vr_retry(self):
        wanted = self.prof["display"]["mode"] == "vr" or time.monotonic() < self._vr_test_until
        if self.vr.active or not wanted or time.monotonic() > self._vr_wait_until:
            self.vr_wait.stop()
            return
        try:
            self.vr.start({**self.prof["display"]["vr"], "rtl": self.prof["lang"]["tgt"] in ("ar", "fa", "ur", "he")})
        except VRNotRunning:
            return
        except VRError as e:              # running now but something else is wrong (e.g. headset not found yet)
            log.info("VR not ready: %s", e)
            return
        self.toast("اتصلت بـ SteamVR — الترجمة تظهر الآن داخل النظارة")
        self._vr_connected()
        if self.prof["display"]["mode"] != "vr" and time.monotonic() < self._vr_test_until:
            self._vr_test_until = 0.0
            self.test_vr()

    def _vr_events(self):
        if not self.vr.active:
            self.vr_events.stop()
            return
        if self.vr.poll() == "quit":
            self.vr_events.stop(); self._vr_timer_sync()
            if self.prof["display"]["mode"] == "vr":
                self.toast("أُغلق SteamVR — سأعيد الاتصال تلقائياً حين يعمل من جديد")
                self._vr_wait_until = time.monotonic() + 3600
                self.vr_wait.start()

    def test_vr(self):
        self._vr_test_until = time.monotonic() + 120
        if not self._start_vr():
            return
        if not self.vr.active:
            return                         # SteamVR is starting; the panel appears once connected
        self.vr.show_items([{"label": "Captain Mara", "label_tr": "القائدة مارا", "src": "Test", "tr": "هذه ترجمة تجريبية داخل النظارة"}])
        self.toast("أُرسلت ترجمة تجريبية إلى النظارة")
        if self.prof["display"]["mode"] != "vr":
            QTimer.singleShot(6000, lambda: (self.prof["display"]["mode"] != "vr") and (self.vr.stop(), self._vr_timer_sync()))

    # ------------------------------------------------------------------ capture region
    def select_region(self):
        if self.window:
            self.window.showMinimized()
        mon = self.prof["capture"]["monitor"]
        QTimer.singleShot(350, lambda: self._open_selector(mon))

    def _open_selector(self, mon):
        qs = qscreen_for(mon)
        cur = None if self.prof["capture"]["full"] else self.prof["capture"]["region"]
        self.overlay.hide()
        self._sel = RegionSelector(qs, cur)
        self._sel.selected.connect(self._region_chosen)
        self._sel.cancelled.connect(self._region_cancel)
        self._sel.showFullScreen(); self._sel.activateWindow()

    def _region_chosen(self, rect):
        self.settings.update_profile("capture.region", rect)
        self.settings.update_profile("capture.full", False)
        self.capture_changed()
        self.toast(f"حُددت المنطقة {rect[2]}×{rect[3]} — ستُقرأ هذه المنطقة فقط")
        self._region_cancel()

    def _region_cancel(self):
        if self.window:
            self.window.showNormal(); self.window.activateWindow()
        if self.last_items and not self.overlay_hidden:
            self._show(self.last_items)

    def use_full_screen(self):
        self.settings.update_profile("capture.full", True)
        self.capture_changed()
        self.toast("سيُقرأ النص من الشاشة كاملة")

    def capture_changed(self):
        if self.worker:
            self.worker.reset_text(); self.worker.trigger()
        self.capture_updated.emit()
        self.profile_changed.emit()

    # ------------------------------------------------------------------ engines
    def test_engines(self):
        def run():
            rows = self.manager.test_engines(tgt=self.prof["lang"]["tgt"])
            self.engines_tested.emit(rows)
        threading.Thread(target=run, daemon=True).start()

    def edit_translation(self, history_id: int, text: str, last: dict):
        self.store.edit_history(history_id, text)
        if len(last["items"]) == 1:
            self.store.set_override(last["items"][0]["src"], self.prof["lang"]["tgt"], text.split(": ", 1)[-1] if last["items"][0]["label"] else text)
            last["items"][0]["tr"] = text.split(": ", 1)[-1] if last["items"][0]["label"] else text
            self._show(last["items"])
        self.toast("حُفظ تعديلك وسيُستخدم كلما ظهر هذا النص")

    # ------------------------------------------------------------------ games / profiles
    def _watch_game(self):
        exe = foreground_exe()
        if not exe or exe == self._game or exe.lower().startswith(("arabize", "python")):
            return
        self._game = exe
        self.game_changed.emit(exe)
        if self.settings.data.get("auto_profile"):
            pid = self.settings.profile_for_exe(exe)
            if pid and pid != self.settings.profile_id:
                self.switch_profile(pid, auto=True)

    def switch_profile(self, pid: str, auto: bool = False):
        if not pid or not self.settings.set_active(pid):
            return
        was_vr = self.vr.active
        self.apply_display()
        if self.prof["display"]["mode"] != "vr" and was_vr:
            (self.vr.stop(), self._vr_timer_sync())
        self.profile_changed.emit(); self.mode_changed.emit()
        self.restart_if_running()
        self.toast(("تم التبديل تلقائياً إلى إعدادات: " if auto else "إعدادات: ") + self.prof["name"])

    def add_game(self, name: str, exe: str):
        pid = self.settings.add_profile(name, exe)
        self.switch_profile(pid)

    def running_games(self) -> list[str]:
        try:
            import psutil
        except Exception:
            return []
        skip = {"explorer.exe", "svchost.exe", "system", "idle", "systemd", "python.exe", "pythonw.exe", "steamwebhelper.exe",
                "chrome.exe", "msedge.exe", "discord.exe", "conhost.exe", "runtimebroker.exe", "searchhost.exe", "dwm.exe"}
        names = set()
        for p in psutil.process_iter(["name", "memory_info"]):
            try:
                n = p.info["name"] or ""
                if n.lower() in skip or not n:
                    continue
                if IS_WIN and not n.lower().endswith(".exe"):
                    continue
                if p.info["memory_info"] and p.info["memory_info"].rss > 150 * 1_048_576:   # games are heavy
                    names.add(n)
            except Exception:
                continue
        return sorted(names, key=str.lower)

    # ------------------------------------------------------------------ hotkeys / tray / tutorial
    def apply_hotkeys(self) -> list[str]:
        return self.hotkeys.apply(self.settings.data["hotkeys"])

    def _hotkey(self, action: str):
        {"toggle": self.toggle, "region": self.select_region, "hide": self.toggle_overlay,
         "mode": lambda: self.set_mode("screen" if self.prof["display"]["mode"] == "vr" else "vr"),
         "retranslate": self.retranslate, "size_up": lambda: self.adjust_size(+1),
         "size_down": lambda: self.adjust_size(-1), "hud": self.toggle_hud}.get(action, lambda: self.vr_adjust(action))()

    def setup_tray(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray = QSystemTrayIcon(theme.app_icon(), self)
        self.tray.setToolTip(APP_NAME_AR)
        m = QMenu()
        self.act_toggle = QAction("ابدأ الترجمة", m); self.act_toggle.triggered.connect(self.toggle); m.addAction(self.act_toggle)
        for t, fn in (("تحديد منطقة", self.select_region), ("إخفاء/إظهار الترجمة", self.toggle_overlay), ("فتح النافذة", self.show_window)):
            a = QAction(t, m); a.triggered.connect(fn); m.addAction(a)
        m.addSeparator()
        q = QAction("خروج", m); q.triggered.connect(self.quit); m.addAction(q)
        self._tray_menu = m
        self.tray.setContextMenu(m)
        self.tray.activated.connect(lambda r: self.show_window() if r == QSystemTrayIcon.Trigger else None)
        self.tray.show()

    def _update_tray(self):
        if self.tray:
            self.act_toggle.setText("إيقاف الترجمة" if self.running else "ابدأ الترجمة")
            self.tray.setToolTip(f"{APP_NAME_AR} — {'تعمل' if self.running else 'متوقفة'}")

    def show_window(self):
        if self.window:
            self.window.showNormal(); self.window.raise_(); self.window.activateWindow()

    def show_tutorial(self):
        from .ui.tutorial import Tutorial
        t = Tutorial(self.window)
        t.action.connect(self._tutorial_action)
        t.finished_tutorial.connect(lambda: self.settings.set("first_run", False))
        t.show()
        self._tutorial = t

    def _tutorial_action(self, name: str):
        if name == "region":
            self.select_region(); return
        if self.window:
            self.window.go_name(name)
            if name == "engines":
                self.window.pages[3]._test()

    def quit(self):
        self.quitting = True
        self.stop()
        (self.vr.stop(), self._vr_timer_sync())
        self.hotkeys.stop()
        self.hud.stop(); self.fps.stop(); self.sensors.stop(force=True)
        self.store.close()
        QApplication.quit()
