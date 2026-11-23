"""Application controller: owns settings, memory, engines, the live loop, overlay, VR, hotkeys and tray."""
from __future__ import annotations

import threading

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QAction, QGuiApplication
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from .cache import Store
from .capture import Capturer
from .config import APP_NAME_AR, Settings
from .engines import Manager
from .hotkeys import Hotkeys
from .overlay import SubtitleOverlay
from .pipeline import LiveTranslator
from .platform_utils import IS_WIN, foreground_exe
from .screens import RegionSelector, qscreen_for
from .ui import icons, theme
from .vr import VRError, VRSubtitle


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
        self.overlay = SubtitleOverlay()
        self.overlay.moved.connect(self._overlay_moved)
        self.vr = VRSubtitle()
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
        self.apply_display()

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
        if code == "error" and "OCR" in msg:
            self.toast(msg, err=True)

    def _on_result(self, r: dict):
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
            rect = self.overlay.physical_rect()
            self.worker.set_exclusions([rect] if rect and not self.overlay.excluded else [])

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

    def toggle_overlay(self):
        self.overlay_hidden = not self.overlay_hidden
        if self.overlay_hidden:
            self.overlay.hide(); self.vr.hide()
            self.toast("أُخفيت الترجمة — اضغط الاختصار نفسه لإظهارها")
        else:
            if self.last_items:
                self._show(self.last_items)
            self.toast("ظهرت الترجمة")

    def edit_overlay_position(self):
        if self.prof["display"]["mode"] != "screen":
            self.toast("التحريك بالماوس متاح في وضع الشاشة", err=True); return
        self.overlay.set_edit_mode(True)

    def _overlay_moved(self, pos):
        self.settings.update_profile("display.screen.custom_pos", pos)
        self.toast("حُفظ مكان الترجمة لهذه اللعبة")
        self.profile_changed.emit()

    # ------------------------------------------------------------------ modes / VR
    def set_mode(self, mode: str):
        if mode == self.prof["display"]["mode"]:
            return
        if mode == "vr":
            if not self._start_vr():
                self.mode_changed.emit(); return
            self.overlay.clear()
        else:
            self.vr.stop()
        self.settings.update_profile("display.mode", mode)
        if self.last_items:
            self._show(self.last_items)
        self.toast("وضع الواقع الافتراضي مفعّل" if mode == "vr" else "وضع الشاشة مفعّل")
        self.mode_changed.emit()

    def _start_vr(self) -> bool:
        if self.vr.active:
            return True
        try:
            self.vr.start({**self.prof["display"]["vr"], "rtl": self.prof["lang"]["tgt"] in ("ar", "fa", "ur", "he")})
            return True
        except VRError as e:
            self.toast(str(e), err=True)
            return False

    def test_vr(self):
        if not self._start_vr():
            return
        self.vr.show_items([{"label": "Captain Mara", "label_tr": "القائدة مارا", "src": "Test", "tr": "هذه ترجمة تجريبية داخل النظارة"}])
        self.toast("أُرسلت ترجمة تجريبية إلى النظارة")
        if self.prof["display"]["mode"] != "vr":
            QTimer.singleShot(6000, lambda: (self.prof["display"]["mode"] != "vr") and self.vr.stop())

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
            self.vr.stop()
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
         "retranslate": self.retranslate}.get(action, lambda: None)()

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
        self.vr.stop()
        self.hotkeys.stop()
        self.store.close()
        QApplication.quit()
