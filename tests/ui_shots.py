"""Launch the real app on a virtual display, drive it, and save screenshots of every screen."""
import os
import sys
import tempfile
import threading
import time
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tests"))
os.environ["ARABIZE_HOME"] = tempfile.mkdtemp(prefix="arabize-ui-")
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/shots"); OUT.mkdir(parents=True, exist_ok=True)

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QImage, QPixmap
from PySide6.QtWidgets import QApplication, QLabel

from conftest import Fake
from gameshots import dialogue_scene

srv = ThreadingHTTPServer(("127.0.0.1", 0), Fake); threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = f"http://127.0.0.1:{srv.server_address[1]}"

from arabize.app import Controller
from arabize.ui import theme
from arabize.ui.main_window import MainWindow

app = QApplication([])
theme.apply(app)
errors = []
sys.excepthook = lambda *a: errors.append(a)


def pump(s, until=None):
    end = time.time() + s
    while time.time() < end:
        app.processEvents(); time.sleep(0.02)
        if until and until():
            return True
    return False


def shot(name, widget=None):
    pm = (widget.grab() if widget else QGuiApplication.primaryScreen().grabWindow(0))
    pm.save(str(OUT / f"{name}.png"))


ctrl = Controller()
ctrl.manager.overrides_endpoint = {e: f"{BASE}/{e}" for e in ("google", "mymemory", "claude", "deepl")}
win = MainWindow(ctrl); ctrl.window = win
win.resize(1280, 820); win.show(); pump(0.8)
for i, page in enumerate(win.pages):
    win.go(i); pump(0.4); shot(f"page{i}", win)
win.adv.setChecked(True); win.go(2); pump(0.4); shot("page2_adv", win)
win.pages[2].t_vr.click(); pump(0.3); shot("page2_vr", win)
win.go(3); win.pages[3]._test(); pump(4, lambda: "✓" in win.pages[3].test_out.text()); shot("page3_tested", win)
win.adv.setChecked(False)

from arabize.ui.tutorial import Tutorial
t = Tutorial(win); t.show(); pump(0.3)
for i in range(10):
    t.go(i); pump(1.4); shot(f"tutorial{i}", t)
t.close()

# live session over a fake game on the whole virtual screen
game = QLabel(); game.setWindowFlags(Qt.FramelessWindowHint)
img, _ = dialogue_scene(); rgb = np.ascontiguousarray(img[:, :, ::-1])
game.setPixmap(QPixmap.fromImage(QImage(rgb.data, 1920, 1080, 1920 * 3, QImage.Format_RGB888).copy()))
game.setGeometry(0, 0, 1920, 1080); game.show()
win.showMinimized(); pump(0.6)
ctrl.settings.update_profile("capture.interval_ms", 200)
ctrl.start()
ok = pump(25, lambda: bool(ctrl.last_items))
pump(1.0)
shot("live_overlay")
print("live result:", ok, [(it.get("label_tr"), it["tr"]) for it in ctrl.last_items])
ctrl.settings.update_profile("display.screen.anchor", "top"); ctrl.settings.update_profile("display.screen.color", "#FFE14D")
ctrl.apply_display(); pump(0.6); shot("live_overlay_top")
win.showNormal(); win.go(0); pump(0.8); shot("home_running", win)
ctrl.stop(); pump(0.5)
print("errors:", errors)
ctrl.quit()
