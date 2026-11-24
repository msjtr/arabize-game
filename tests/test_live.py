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


def _screen_size(app):
    g = app.primaryScreen().geometry()
    return g.width(), g.height()


def test_live_loop_reads_translates_dedupes_and_follows_changes(app, env):
    if _screen_size(app)[0] < 1920:
        pytest.skip("needs a 1920x1080 screen")
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

    def got_choices():
        return results and sum(1 for c in exp["choices"] if any(c.rstrip(".?") in it["src"] for it in results[-1]["items"])) == 3
    assert pump(app, 20, got_choices), statuses
    srcs2 = [it["src"] for it in results[-1]["items"]]
    print("second read:", srcs2, "ms:", results[-1]["ms"])
    # the previous dialogue gives way to the new text instead of lingering beside it
    assert not any("We leave at dawn" in x for x in srcs2) or any("We leave at dawn" in x for x in exp.get("lines", []))
    n_after_choices = len(results)

    # overlay over the game is not read back by OCR
    ov = SubtitleOverlay()
    ov.configure(s.profile["display"]["screen"], qscreen_for(1))
    ov.show_items([{"label": "", "tr": "Hidden test subtitle text", "src": ""}])
    pump(app, 0.3)
    lt.set_exclusions([ov.physical_rect()])
    lt.trigger()
    assert pump(app, 20, lambda: len(results) > n_after_choices)
    assert not any("Hidden test subtitle" in it["src"] for it in results[-1]["items"])

    # resource use while idle on an unchanged screen
    pump(app, 3.0)
    lt.stop(); lt.wait(5000); pump(app, 0.3)
    cpu = [x["cpu"] for x in metrics[-2:]]
    print("idle cpu % (one core):", cpu, "mem MB:", round(metrics[-1]["mem"]))
    assert "stopped" in statuses
    assert st.history()[0]["translation"]
    game.close(); ov.close()


def test_offline_then_recovers(app, env):
    if _screen_size(app)[0] < 1920:
        pytest.skip("needs a 1920x1080 screen")
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


# ------------------------------------------------------------------ fast text over a moving scene
def _frame(text, phase, w=1600, h=900):
    from PIL import Image, ImageDraw
    from gameshots import _font
    y = np.linspace(0, 1, h)[:, None, None]
    x = np.linspace(0, 1, w)[None, :, None]
    # a scene that never stands still: drifting light bands and a moving sun (like water, clouds or a camera pan)
    bands = 0.5 + 0.5 * np.sin((x * 9 + y * 4 + phase * 0.7) * np.pi)
    base = np.concatenate([30 + 50 * y + 40 * bands, 40 + 60 * y + 30 * bands, 90 + 80 * (1 - y) + 20 * bands], axis=2)
    im = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)[:, :, ::-1].copy())
    d = ImageDraw.Draw(im)
    cx = int((phase * 37) % w)
    d.ellipse([cx, 90, cx + 120, 210], fill=(240, 220, 170))
    if text:
        f = _font("poppins", 40 if w >= 1400 else 30)
        tw = d.textlength(text, font=f)
        d.rounded_rectangle([w / 2 - tw / 2 - 30, h - 190, w / 2 + tw / 2 + 30, h - 110], 14, fill=(12, 14, 28))
        d.text((w / 2 - tw / 2, h - 175), text, font=f, fill=(255, 255, 255))
    return np.asarray(im)[:, :, ::-1].copy()


def _seen_lines(results):
    return {it["src"] for r in results for it in r["items"] if it.get("tr")}


def test_fast_lines_over_a_moving_scene_are_all_translated(app, env):
    """Dialogue lines that stay < 1 s each while the background keeps moving (the case that used to be skipped)."""
    s, st, m = env
    Fake.mode["google"] = "slow"                 # 350 ms per request, like a real server
    s.update_profile("capture.interval_ms", 150)
    lines = ["The bridge is out.", "Take the north road.", "Hurry, they are coming!", "Hide behind the wagon.", "Now run to the gate!"]
    W, H = min(1600, _screen_size(app)[0]), min(900, _screen_size(app)[1])
    game = QLabel(); game.setWindowFlags(Qt.FramelessWindowHint); game.setGeometry(0, 0, W, H)
    show_game(game, _frame("", 0, W, H)); game.show(); pump(app, 0.4)
    lt = LiveTranslator(s, st, m)
    results, statuses, metrics = [], [], []
    lt.result.connect(results.append); lt.status.connect(lambda c, t: statuses.append(c)); lt.metrics.connect(metrics.append)
    lt.start(); pump(app, 1.2)
    t0 = time.time(); phase = 0
    shown_at, first_tr = {}, {}
    for ln in lines + [""]:
        shown_at[ln] = time.time()
        end = time.time() + (0.9 if ln else 3.0)
        while time.time() < end:                  # ~12 fps background animation while the line is up
            phase += 1
            show_game(game, _frame(ln, phase, W, H))
            pump(app, 0.08)
            for src in _seen_lines(results):
                for want in lines:
                    if want.rstrip(".!") in src and want not in first_tr:
                        first_tr[want] = time.time() - shown_at[want]
    lt.stop(); lt.wait(5000); game.close()
    Fake.mode["google"] = "ok"
    print("\nscreen-to-translation per line (s):", {k: round(v, 2) for k, v in first_tr.items()})
    print("ocr ms:", round(metrics[-1]["ocr_ms"]) if metrics else None, "| reads:", metrics[-1]["reads"] if metrics else None)
    assert set(first_tr) == set(lines), f"missed: {set(lines) - set(first_tr)}"


def test_typewriter_line_is_translated_in_full(app, env):
    s, st, m = env
    s.update_profile("capture.interval_ms", 150)
    full = "Captain, the storm will reach the harbour before sunset."
    W, H = min(1600, _screen_size(app)[0]), min(900, _screen_size(app)[1])
    game = QLabel(); game.setWindowFlags(Qt.FramelessWindowHint); game.setGeometry(0, 0, W, H)
    show_game(game, _frame("", 0, W, H)); game.show(); pump(app, 0.4)
    lt = LiveTranslator(s, st, m)
    results = []
    lt.result.connect(results.append)
    lt.start(); pump(app, 1.2)
    for n in range(4, len(full) + 1, 3):          # letters appear one group at a time, ~25 letters per second
        show_game(game, _frame(full[:n], n, W, H)); pump(app, 0.12)
    show_game(game, _frame(full, 999, W, H))
    assert pump(app, 15, lambda: results and any("before sunset" in it["src"] and it["tr"] for it in results[-1]["items"]))
    final = [it for it in results[-1]["items"] if "sunset" in it["src"]][0]
    print("\ntypewriter final:", final["src"], "->", final["tr"], "| google calls:", Fake.calls["google"])
    assert final["tr"].rstrip(".").endswith("before sunset") and Fake.calls["google"] <= 8   # not one request per letter
    lt.stop(); lt.wait(5000); game.close()
