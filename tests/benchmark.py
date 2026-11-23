"""Performance with default settings: idle CPU, OCR time, and text-appears -> subtitle-shown latency."""
import os
import sys
import tempfile
import threading
import time
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tests"))
os.environ["ARABIZE_HOME"] = tempfile.mkdtemp(prefix="arabize-bench-")

import numpy as np
import psutil
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QApplication, QLabel

from conftest import Fake
from gameshots import choices_scene, dialogue_scene, small_subtitle

srv = ThreadingHTTPServer(("127.0.0.1", 0), Fake); threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = f"http://127.0.0.1:{srv.server_address[1]}"
from arabize.cache import Store
from arabize.config import Settings
from arabize.engines import Manager
from arabize.pipeline import LiveTranslator

app = QApplication([])
proc = psutil.Process()


def pump(s, until=None):
    end = time.time() + s
    while time.time() < end:
        app.processEvents(); time.sleep(0.01)
        if until and until():
            return True
    return False


def show(label, bgr):
    rgb = np.ascontiguousarray(bgr[:, :, ::-1])
    label.setPixmap(QPixmap.fromImage(QImage(rgb.data, rgb.shape[1], rgb.shape[0], rgb.shape[1] * 3, QImage.Format_RGB888).copy()))


def run(mode: str):
    s = Settings(Path(os.environ["ARABIZE_HOME"]) / f"{mode}.json"); st = Store(Path(os.environ["ARABIZE_HOME"]) / f"{mode}.db")
    m = Manager(s, st); m.overrides_endpoint = {e: f"{BASE}/{e}" for e in ("google", "mymemory")}
    if mode == "region":
        s.update_profile("capture.full", False); s.update_profile("capture.region", [200, 600, 1520, 460])
    game = QLabel(); game.setWindowFlags(Qt.FramelessWindowHint); game.setGeometry(0, 0, 1920, 1080)
    scenes = [dialogue_scene(seed=i)[0] if i % 2 == 0 else choices_scene(seed=i)[0] for i in range(6)]
    show(game, scenes[0]); game.show(); pump(0.5)
    lt = LiveTranslator(s, st, m); res = []
    lt.result.connect(lambda r: res.append((time.perf_counter(), r)))
    lt.start(); pump(20, lambda: res)
    # idle: same picture for 10 s
    proc.cpu_percent(None); pump(10)
    idle = proc.cpu_percent(None)
    # latency: new text appears, time until translation is emitted
    lats, ocrs = [], []
    for img in scenes[1:]:
        n = len(res); t0 = time.perf_counter(); show(game, img)
        pump(20, lambda: len(res) > n)
        lats.append((res[-1][0] - t0) * 1000); ocrs.append(res[-1][1]["ms"]["ocr"])
        pump(0.6)
    lt.stop(); lt.wait(5000); game.close()
    return idle, lats, ocrs


for mode in ("full", "region"):
    idle, lats, ocrs = run(mode)
    print(f"{mode:7s} idle CPU {idle:5.1f}% of one core | OCR {np.median(ocrs):.0f} ms median | "
          f"text-on-screen -> translation {np.median(lats):.0f} ms median ({min(lats):.0f}-{max(lats):.0f})")
print(f"memory {proc.memory_info().rss / 1_048_576:.0f} MB | cores {os.cpu_count()}")
