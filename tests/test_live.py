"""End-to-end: a fake game window on a virtual display, the real live loop reading it."""
import time

import numpy as np
import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QApplication, QLabel

from arabize.overlay import SubtitleOverlay
from arabize.pipeline import LiveTranslator
from arabize.platform_utils import process_usage
from arabize.screens import qscreen_for
from conftest import Fake
from gameshots import choices_scene, dialogue_scene


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def show_game(label, bgr):
    rgb = np.ascontiguousarray(bgr[:, :, ::-1])
    qi = QImage(rgb.data, rgb.shape[1], rgb.shape[0], rgb.shape[1] * 3, QImage.Format_RGB888).copy()
    label.setPixmap(QPixmap.fromImage(qi))


def pump(app, secs, until=None):
    end = time.time() + secs
    while time.time() < end:
        app.processEvents()
        if until and until():
            return True
        time.sleep(0.02)
    return False


def test_live_loop_reads_translates_dedupes_and_follows_changes(app, env):
    s, st, m = env
    s.update_profile("capture.interval_ms", 150)
    game = QLabel(); game.setWindowFlags(Qt.FramelessWindowHint); game.setGeometry(0, 0, 1920, 1080)
    img1, _ = dialogue_scene(); show_game(game, img1); game.show()
    pump(app, 0.5)

    lt = LiveTranslator(s, st, m)
    results, statuses, metrics = [], [], []
    lt.result.connect(results.append); lt.status.connect(lambda c, t: statuses.append(c)); lt.metrics.connect(metrics.append)
    lt.start()
    assert pump(app, 20, lambda: len(results) >= 1), statuses
    r = results[0]
    srcs = [it["src"] for it in r["items"]]
    print("\nfirst read:", srcs, "engine:", r["engine"], "ms:", r["ms"])
    assert any("lighthouse" in x for x in srcs)
    assert any(it["label"] == "Captain Mara" and it["label_tr"] for it in r["items"])
    assert all(it["tr"] for it in r["items"])

    # same screen for 2 s -> no new translation requests
    calls = Fake.calls["google"]
    pump(app, 2.0)
    assert len(results) == 1 and Fake.calls["google"] == calls

    # new dialogue choices appear -> translated once
    img2, exp = choices_scene(); show_game(game, img2)
    assert pump(app, 20, lambda: len(results) >= 2), statuses
    srcs2 = [it["src"] for it in results[1]["items"]]
    print("second read:", srcs2, "ms:", results[1]["ms"])
    assert sum(1 for c in exp["choices"] if any(c.rstrip(".?") in x for x in srcs2)) == 3

    # overlay over the game is not read back by OCR
    ov = SubtitleOverlay()
    ov.configure(s.profile["display"]["screen"], qscreen_for(1))
    ov.show_items([{"label": "", "tr": "Hidden test subtitle text", "src": ""}])
    pump(app, 0.3)
    lt.set_exclusions([ov.physical_rect()])
    lt.trigger()
    assert pump(app, 20, lambda: len(results) >= 3)
    assert not any("Hidden test subtitle" in it["src"] for it in results[2]["items"])

    # resource use while idle on an unchanged screen
    pump(app, 3.0)
    lt.stop(); lt.wait(5000); pump(app, 0.3)
    cpu = [x["cpu"] for x in metrics[-2:]]
    print("idle cpu % (one core):", cpu, "mem MB:", round(metrics[-1]["mem"]))
    assert "stopped" in statuses
    assert st.history()[0]["translation"]
    game.close(); ov.close()


def test_offline_then_recovers(app, env):
    s, st, m = env
    s.update_profile("capture.interval_ms", 150)
    LiveTranslator.RETRY_OFFLINE_S = 0.5
    for k in Fake.mode:
        Fake.mode[k] = "drop"
    game = QLabel(); game.setWindowFlags(Qt.FramelessWindowHint); game.setGeometry(0, 0, 1920, 1080)
    img, _ = choices_scene(seed=9); show_game(game, img); game.show(); pump(app, 0.4)
    lt = LiveTranslator(s, st, m)
    results, statuses = [], []
    lt.result.connect(results.append); lt.status.connect(lambda c, t: statuses.append(c))
    lt.start()
    assert pump(app, 20, lambda: "offline" in statuses)
    for k in Fake.mode:
        Fake.mode[k] = "ok"
    m._rest_until.clear()
    assert pump(app, 20, lambda: len(results) >= 1), statuses
    lt.stop(); lt.wait(5000); game.close()
