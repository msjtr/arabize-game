"""1.4: speed and steadiness, calm service messages, recordable subtitles, in-game look, FPS / temperatures / specs."""
import threading
import time

import numpy as np
import pytest

from arabize import messages
from arabize.blend import contrast, sample_colors
from arabize.hud import hud_rows
from arabize.hwinfo import FrameCounter, frame_column, specs, specs_text
from arabize.overlay import steady_boxes


# ---------------------------------------------------------------- 3: messages that do not alarm the player
ALARM = ("خطر", "خطأ", "عطل", "فيروس", "HTTP", "Traceback", "Errno", "error", "Error")


@pytest.mark.parametrize("errors,network,internet,code", [
    ({"google": "تعذّر الاتصال: timed out"}, True, True, "offline"),
    ({"google": "تعذّر الاتصال: [Errno 11001] getaddrinfo failed"}, True, False, "offline"),
    ({"google": "HTTP 503: <html>Service Unavailable</html>", "mymemory": "HTTP 503: busy"}, False, None, "warn"),
    ({"google": "HTTP 429: Too Many Requests"}, False, None, "warn"),
    ({"claude": "المفتاح مرفوض أو منتهي (HTTP 401)"}, False, None, "warn"),
    ({}, False, None, "error"),
])
def test_service_trouble_is_explained_calmly(errors, network, internet, code):
    c, msg = messages.translate_failure(errors, network, internet)
    assert c == code
    assert msg and not any(w in msg for w in ALARM), msg
    if internet is False:
        assert msg == messages.NO_INTERNET
    if network and internet:
        assert "الإنترنت" not in msg            # the internet works: it is the service, not the player's connection


def test_engine_test_table_hides_raw_server_replies():
    assert messages.engine_test_error("HTTP 503: <html>…") == "الخدمة لا تستجيب مؤقتاً"
    assert "HTTP" not in messages.engine_test_error("HTTP 429: x")
    assert messages.engine_test_error("يحتاج مفتاح API") == "يحتاج مفتاح API"


def test_capture_hiccup_message_is_not_an_exception_dump():
    assert messages.capture_failure(RuntimeError("D3D11 device removed 0x887A0005")) == messages.CAPTURE_HICCUP


# ---------------------------------------------------------------- 7: the game's own colours
def _panel(bg=(60, 30, 20), fg=(240, 240, 240), noise=False):
    img = np.zeros((200, 600, 3), np.uint8); img[:] = bg
    if noise:
        img[:] = np.random.default_rng(1).integers(0, 255, img.shape, dtype=np.uint8)
    img[90:110:3, 100:500] = fg                 # "letters": thin strokes of the text colour
    img[90:110, 100:500:4] = fg
    return img


def test_colours_are_taken_from_the_game_panel():
    col = sample_colors(_panel(), (100, 88, 400, 24))
    assert col["bg"] == "#14 1E3C".replace(" ", "")      # BGR (60, 30, 20) -> RGB #141E3C
    assert col["fg"] == "#F0F0F0"
    assert col["flat"] is True


def test_busy_background_is_not_flat_and_text_stays_readable():
    col = sample_colors(_panel(noise=True), (100, 88, 400, 24))
    assert col["flat"] is False
    r = lambda h: tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
    assert contrast(r(col["fg"]), r(col["bg"])) >= 3.0


def test_unusable_boxes_are_skipped():
    assert sample_colors(_panel(), (590, 190, 2, 2)) is None
    assert sample_colors(None, (0, 0, 10, 10)) is None


# ---------------------------------------------------------------- 2: steadiness
def test_ocr_jitter_keeps_the_box_still_but_real_moves_follow():
    it = {"key": "hello"}
    prev = {"hello": (100.0, 200.0, 400.0, 50.0, 30.0, it)}
    jitter = steady_boxes([(103.0, 198.0, 408.0, 52.0, 31.0, it)], prev)[0]
    assert jitter[:5] == (100.0, 200.0, 400.0, 50.0, 30.0)
    moved = steady_boxes([(400.0, 600.0, 400.0, 50.0, 30.0, it)], prev)[0]
    assert moved[:2] == (400.0, 600.0)
    new = steady_boxes([(103.0, 198.0, 408.0, 52.0, 31.0, {"key": "other"})], prev)[0]
    assert new[:2] == (103.0, 198.0)


@pytest.fixture
def qapp():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_subtitle_box_keeps_one_size_between_lines(qapp):
    from arabize.overlay import SubtitleOverlay
    ov = SubtitleOverlay()
    ov.configure({"font_size": 26, "anchor": "bottom", "offset": 80, "width_pct": 70, "max_lines": 4, "steady": True,
                  "recordable": True}, qapp.primaryScreen())
    ov.show_items([{"label": "", "tr": "سطر قصير", "src": "a"}], animate=False)
    g1 = ov.geometry().getRect()
    ov.show_items([{"label": "مارا", "tr": "سطر أطول قليلاً من الأول", "src": "b"},
                   {"label": "", "tr": "وسطر ثانٍ", "src": "c"}], animate=False)
    g2 = ov.geometry().getRect()
    ov.show_items([{"label": "", "tr": "قصير", "src": "d"}], animate=False)
    g3 = ov.geometry().getRect()
    assert g1 == g2 == g3
    ov.close()


def test_without_steady_the_box_follows_the_text(qapp):
    from arabize.overlay import SubtitleOverlay
    ov = SubtitleOverlay()
    ov.configure({"font_size": 26, "anchor": "bottom", "steady": False}, qapp.primaryScreen())
    ov.show_items([{"label": "", "tr": "سطر", "src": "a"}], animate=False)
    h1 = ov.height()
    ov.show_items([{"label": "", "tr": "سطر", "src": "a"}, {"label": "", "tr": "سطر", "src": "b"}], animate=False)
    assert ov.height() > h1
    ov.close()


# ---------------------------------------------------------------- 4: recordable subtitles
def test_cover_needs_a_reader_that_cannot_see_the_subtitle(qapp):
    from arabize.overlay import OverlayLayers
    lay = OverlayLayers()
    lay.configure({"font_size": 26, "place": "cover", "recordable": True, "blend": True}, qapp.primaryScreen())
    items = [{"key": "k", "label": "", "src": "Hello", "tr": "مرحبا", "abs": (400, 300, 300, 40), "line_h": 40,
              "game_bg": "#202020", "game_fg": "#FFFFFF", "game_flat": True}]
    lay.ocr_blind = False                     # screen capture: it would read our window back
    lay.show_items(items)
    assert lay.inplace.mode == "above"
    lay.ocr_blind = True                      # the game window itself is read (like OBS): cover is safe
    lay.show_items(items)
    assert lay.inplace.mode == "cover" and lay.physical_rects() == []
    assert lay.inplace.blends(items[0])
    st = lay.inplace._item_style(30, items[0])
    assert st["bg"] == "#202020" and st["color"] == "#FFFFFF" and st["box"] == "none"
    lay.clear(); lay.hide()


def test_recordable_switches_capture_to_the_game_window(monkeypatch):
    from arabize import pipeline
    prof = {"capture": {"method": "auto"}, "display": {"screen": {"recordable": True}}}
    monkeypatch.setattr(pipeline, "IS_WIN", True)
    assert pipeline.LiveTranslator._method(prof) == "window"
    prof["display"]["screen"]["recordable"] = False
    assert pipeline.LiveTranslator._method(prof) == "auto"
    prof["capture"]["method"] = "dxgi"; prof["display"]["screen"]["recordable"] = True
    assert pipeline.LiveTranslator._method(prof) == "dxgi"          # a method the user picked is kept


# ---------------------------------------------------------------- 1/8: speed and connection
def test_one_connection_is_shared_by_all_threads_and_ping_is_measured(env):
    from arabize import engines
    from arabize.engines import Request
    from conftest import Fake
    s, st, m = env
    engines._IDLE.clear(); engines.LATENCY.clear()
    Fake.protocol_version = "HTTP/1.1"            # like the real services: the connection stays open
    out = []

    def one(t):
        out.append(m.translate(Request(t, "en", "ar"), use_memory=False).text)
    th = [threading.Thread(target=one, args=(f"line {i}",)) for i in range(3)]
    for t in th:
        t.start()
    for t in th:
        t.join()
    try:
        assert len(out) == 3
        assert sum(len(v) for v in engines._IDLE.values()) >= 1     # kept open for the next line, whatever thread
        before = sum(len(v) for v in engines._IDLE.values())
        one("again")                                                 # reuses an idle connection: no new one
        assert sum(len(v) for v in engines._IDLE.values()) == before
    finally:
        Fake.protocol_version = "HTTP/1.0"
        engines._IDLE.clear()
    assert "google" in m.ping() and m.ping()["google"] >= 0
    assert m.HEDGE_S <= 0.6


def test_warmup_opens_connections_before_the_first_line(env):
    from arabize import engines
    s, st, m = env
    engines._IDLE.clear()
    m.warmup()
    t0 = time.time()
    while time.time() - t0 < 3 and not engines._IDLE:
        time.sleep(0.02)
    assert engines._IDLE


def test_size_shortcut_changes_and_clamps(env_ctrl):
    c = env_ctrl
    c.settings.update_profile("display.screen.font_size", 26)
    assert c.adjust_size(+1) == 28
    assert c.adjust_size(-1) == 26
    c.settings.update_profile("display.screen.font_size", 80)
    assert c.adjust_size(+1) == 80
    assert "size_up" in c.settings.data["hotkeys"] and "hud" in c.settings.data["hotkeys"]


# ---------------------------------------------------------------- 9/10/11: FPS, temperatures, specs
def test_frame_counter_reads_presentmon_rows():
    v1 = ["Application", "ProcessID", "SwapChainAddress", "Runtime", "MsBetweenPresents", "MsBetweenDisplayChange"]
    v2 = ["Application", "ProcessID", "SwapChainAddress", "PresentRuntime", "FrameTime", "CPUBusy"]
    assert frame_column(v1) == 4 and frame_column(v2) == 4 and frame_column(["x"]) is None
    fc = FrameCounter()
    assert fc.header(v1)
    now = 100.0
    for i in range(90):
        fc.add(["game.exe", "1", "0xA", "DXGI", "16.667", "16.6"], now - 1.4 + i * (1 / 60))
    fc.add(["game.exe", "1", "0xB", "DXGI", "100.0", "100"], now)       # a second, slower swap chain
    fc.add(["game.exe", "1", "0xA", "DXGI", "NA", "NA"], now)
    assert fc.fps(now) == 60


def test_specs_describe_this_machine():
    s = specs()
    for k in ("os", "cpu", "cores", "threads", "gpus", "ram_gb", "drives"):
        assert k in s
    assert s["cpu"] and s["threads"] >= 1 and s["ram_gb"] > 0
    txt = specs_text(s)
    assert "المعالج" in txt and "الذاكرة" in txt


def test_hud_rows_show_what_is_known_and_say_why_fps_is_missing():
    cfg = {"fps": True, "cpu_temp": True, "cpu": True, "gpu_temp": True, "ram": True, "ping": True}
    sensors = {"cpu": 35.2, "cpu_temp": 71.0, "gpu_temp": None, "gpu_load": None, "ram_used_gb": 9.1, "ram_total_gb": 16.0,
               "ram_pct": 57}
    rows = {r[0]: r for r in hud_rows(cfg, sensors, None, "need_admin", {"google": 84})}
    assert rows["FPS"][1] == "يحتاج مسؤول"
    assert rows["CPU"][1] == "71°C  35%"
    assert "GPU" not in rows
    assert rows["RAM"][1] == "9.1/16 GB" and rows["PING"][1] == "84 ms"
    rows = {r[0]: r for r in hud_rows(cfg, sensors, 144, "running", {})}
    assert rows["FPS"][1] == "144" and "PING" not in rows


def test_device_page_and_hud_run(env_ctrl, qapp):
    from arabize.ui.main_window import MainWindow
    c = env_ctrl
    w = MainWindow(c); c.window = w
    w.go_name("device")
    page = w.pages[7]
    assert page.title_text == "الجهاز والأداء"
    page._tick()
    assert "المعالج" in page.spec_lbl.text()
    c.set_hud(True, quiet=True)
    c.hud.refresh()
    assert c.hud.rows and c.hud.isVisible()
    c.set_hud(False, quiet=True)
    assert not c.hud.isVisible()
    w.go(0)
    for i in range(len(w.pages)):
        w.go(i)
    w.close()


def test_new_options_appear_in_old_settings(tmp_path):
    import json
    from arabize.config import Settings
    p = tmp_path / "s.json"
    p.write_text(json.dumps({"profiles": {"default": {"display": {"screen": {"font_size": 30}}}},
                             "hotkeys": {"toggle": "F8"}}), encoding="utf-8")
    s = Settings(p)
    scr = s.profile["display"]["screen"]
    assert scr["font_size"] == 30 and scr["blend"] and scr["steady"] and scr["recordable"]
    assert s.data["hotkeys"]["toggle"] == "F8" and s.data["hotkeys"]["size_up"]
    assert s.data["hud"]["on"] is False


# ---------------------------------------------------------------- on real Windows (CI)
win = pytest.mark.skipif(__import__("sys").platform != "win32", reason="Windows only")


@win
def test_recordable_subtitle_is_in_screenshots_but_not_in_what_is_read(qapp):
    """Recorders (DXGI, like Game Bar / OBS display capture) see the translation; the reader, which takes the game
    window itself, does not — so the Arabic can cover the English and still be recorded."""
    import sys
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
    from test_windows import _read, _show_scene
    from arabize.capture import Capturer
    from arabize.overlay import InPlaceOverlay
    lab, exp = _show_scene(qapp, "Arabize Recordable Game")
    ov = InPlaceOverlay()
    ov.configure({"font_size": 26, "bg": "#000000", "box": "card", "rtl": False, "recordable": True}, "cover")
    ov.show_items([{"label": "", "src": "x", "tr": "OVERLAYMARKER OVERLAYMARKER", "abs": (200, 200, 1400, 500), "line_h": 60}])
    for _ in range(20):
        qapp.processEvents(); time.sleep(0.03)
    screen, game = Capturer("dxgi"), Capturer("window")
    try:
        assert not ov.excluded
        img, _ = screen.grab(1)
        if screen.active == "dxgi":
            assert "OVERLAYMARKER" in _read(img).upper()          # a screenshot / recording shows the translation
        img, _ = game.grab(1, None, (int(lab.winId()), "python.exe"))
        if game.active != "window":
            pytest.skip(f"Windows Graphics Capture not available here: {game.note}")
        assert "OVERLAYMARKER" not in _read(img).upper()          # the reader never sees it
    finally:
        screen.close(); game.close(); ov.close(); lab.close()


@win
def test_windows_sensors_and_specs():
    from arabize.hwinfo import Sensors, specs
    s = specs()
    assert "Windows" in s["os"] and s["cpu"] != "غير معروف" and s["drives"]
    sen = Sensors(); sen.start()
    try:
        t0 = time.time()
        while time.time() - t0 < 25 and (sen.data["ram_pct"] is None or (sen.data["cpu_temp"] is None and not sen.temp_note)):
            time.sleep(0.25)
        assert sen.data["ram_pct"] is not None and sen.data["cpu"] is not None
        assert sen.data["cpu_temp"] is not None or sen.temp_note       # a reading, or the reason there is none
        print("\ncpu temp:", sen.data["cpu_temp"], sen.data["cpu_temp_src"], sen.temp_note, "gpu:", sen.data["gpu_temp"])
    finally:
        sen.stop(force=True)


@win
def test_presentmon_is_bundled_and_starts(qapp):
    from arabize.hwinfo import FpsMeter, presentmon_path
    from arabize.platform_utils import is_admin
    if presentmon_path() is None:
        pytest.skip("PresentMon not downloaded for this run")
    m = FpsMeter()
    m.start()
    try:
        t0 = time.time()
        while time.time() - t0 < 10 and m.state in ("off",):
            time.sleep(0.1)
        if not is_admin():
            assert m.state == "need_admin"
            return
        # nothing in front presents frames on a build machine; the meter must wait or run, never fail
        time.sleep(4)
        assert m.state in ("waiting", "running"), m.state
    finally:
        m.stop()
