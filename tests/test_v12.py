"""1.2: game dictionary, VR placement and in-headset controls, performance presets, error log, settings backup,
capture fallbacks and the self-playing intro."""
import json
import math

import pytest

from arabize.engines import Engine, Manager, Request, protect, restore, terms_in


# ------------------------------------------------------------------ dictionary
GL = (("Mara", "مارا"), ("Iron Sword", "السيف الحديدي"), ("Sword", "سيف"), ("Lumen", "لومين"))


def test_terms_found_longest_first_and_whole_words_only():
    t = "Captain Mara, take the iron sword to Lumen."
    assert [s for s, _ in terms_in(t, GL)] == ["Iron Sword", "Lumen", "Mara"]
    assert terms_in("Swordfish and Maranello", GL) == ()          # not inside other words


def test_protect_and_restore_survive_engine_noise():
    masked, mp = protect("Mara has the Iron Sword.", terms_in("Mara has the Iron Sword.", GL))
    assert "Mara" not in masked and "Sword" not in masked
    out = restore("لدى qxz 1 xxx Q X Z0.", mp)                    # spaces and lower case added by the engine
    assert "مارا" in out and "السيف الحديدي" in out


class Plain(Engine):
    id = "plain"; seen = []

    def translate(self, r):
        Plain.seen.append(r.text)
        return "ع: " + r.text, "en"


class Smart(Plain):
    id = "smart"; smart = True; got = []

    def translate(self, r):
        Smart.got.append(r.glossary)
        return "ع: " + r.text, "en"


def test_manager_uses_the_dictionary_with_plain_and_smart_engines(env_ctrl, monkeypatch):
    m = env_ctrl.manager
    monkeypatch.setattr(Manager, "_engines", lambda self: [Plain({})])
    r = m.translate(Request("Mara draws the Iron Sword", "en", "ar", "gaming", (), GL))
    assert "مارا" in r.text and "السيف الحديدي" in r.text
    assert "Mara" not in Plain.seen[-1]                              # the engine never saw the name
    # the same sentence without a dictionary is a different memory entry
    r2 = m.translate(Request("Mara draws the Iron Sword", "en", "ar", "gaming"))
    assert "Mara" in r2.text
    monkeypatch.setattr(Manager, "_engines", lambda self: [Smart({})])
    m.translate(Request("Lumen at dawn", "en", "ar", "gaming", (), GL))
    assert Smart.got[-1] == (("Lumen", "لومين"),)                   # only the terms that appear are sent


def test_glossary_reaches_the_live_pipeline(env_ctrl):
    from arabize.pipeline import LiveTranslator
    env_ctrl.settings.update_profile("glossary", [{"src": "Mara", "tr": "مارا", "kind": "character"}, {"src": "", "tr": "x"}])
    w = LiveTranslator(env_ctrl.settings, env_ctrl.store, env_ctrl.manager)
    seen = []
    w.manager = type("M", (), {"translate": lambda self, req: seen.append(req.glossary) or
                               type("R", (), {"text": req.text, "engine": "x", "source": "engine"})()})()
    w._translate_items([{"label": "", "src": "Mara waits"}], env_ctrl.settings.profile)
    assert seen[0] == (("Mara", "مارا"),)


# ------------------------------------------------------------------ VR placement
def _hmd(deg, pos=(0.0, 1.7, 0.0)):
    t = math.radians(deg)
    return [[math.cos(t), 0, math.sin(t), pos[0]], [0, 1, 0, pos[1]], [-math.sin(t), 0, math.cos(t), pos[2]]]


def test_panel_sits_in_front_and_faces_the_player():
    from arabize.vr import panel_target, pose_matrix
    for deg in (0, 35, -120):
        pos, yaw = panel_target(_hmd(deg), 1.5, -0.3, 0.0)
        h = _hmd(deg)
        fwd = (-h[0][2], -h[2][2])
        assert pos == pytest.approx([fwd[0] * 1.5, 1.4, fwd[1] * 1.5])
        m = pose_matrix(pos, yaw)
        for a, b in zip(m, h):                                         # same turn as the head (yaw only)
            assert a[:3] == pytest.approx(b[:3])


def test_side_offset_goes_to_the_right():
    from arabize.vr import panel_target
    pos, _ = panel_target(_hmd(0), 1.0, 0.0, 0.5)
    assert pos[0] == pytest.approx(0.5) and pos[2] == pytest.approx(-1.0)


def test_follow_ignores_small_head_moves_then_glides():
    from arabize.vr import Follower, panel_target
    f = Follower()
    p0, y0 = f.step(*panel_target(_hmd(0), 1.4, -0.3, 0), 0.016)
    for _ in range(30):                                   # small nods/turns: the panel stays exactly where it is
        p, y = f.step(*panel_target(_hmd(8), 1.4, -0.3, 0), 0.016)
    assert p == p0 and y == y0
    tgt = panel_target(_hmd(60), 1.4, -0.3, 0)
    steps = [f.step(*tgt, 0.016) for _ in range(5)]
    assert 0 < abs(steps[0][1] - y0) < abs(tgt[1] - y0) * 0.2      # starts moving gently, no jump
    for _ in range(300):
        p, y = f.step(*tgt, 0.016)
    assert y == pytest.approx(tgt[1], abs=0.03) and p == pytest.approx(tgt[0], abs=0.03)


def test_in_headset_shortcuts(env_ctrl):
    c = env_ctrl
    assert not c.vr_adjust("vr_nearer")                     # screen mode: ignored
    c.settings.update_profile("display.mode", "vr")
    d0 = c.prof["display"]["vr"]["distance_m"]
    assert c.vr_adjust("vr_nearer") and c.prof["display"]["vr"]["distance_m"] == pytest.approx(d0 - 0.1)
    for _ in range(60):
        c.vr_adjust("vr_left")
    assert c.prof["display"]["vr"]["side_m"] == pytest.approx(-1.5)   # clamped
    assert c.vr_adjust("vr_placement") and c.prof["display"]["vr"]["placement"] == "follow"
    assert c.vr_adjust("vr_placement") and c.prof["display"]["vr"]["placement"] == "world"
    assert c.vr_adjust("vr_center")
    hk = c.settings.data["hotkeys"]
    assert hk["vr_left"] == "Ctrl+Shift+Left" and len(set(hk.values())) == len(hk)   # no clashing shortcuts


def test_every_shortcut_parses():
    from arabize.config import DEFAULT_HOTKEYS
    from arabize.hotkeys import to_pynput
    for k, v in DEFAULT_HOTKEYS.items():
        assert to_pynput(v), k


# ------------------------------------------------------------------ performance + GPU
def test_performance_presets_rebuild_the_reader():
    from arabize.ocr import PERF_PRESETS, RapidOcr, gpu_available
    from arabize.textproc import group_lines, similarity
    from gameshots import dialogue_scene
    img, exp = dialogue_scene()
    for name in ("light", "high", "balanced"):
        o = RapidOcr(perf={**PERF_PRESETS[name], "gpu": False})
        assert RapidOcr._cfg[1] == PERF_PRESETS[name]["ocr_side"]
        blocks = group_lines(o.read(img))
        assert max(similarity(b.text, exp["dialogue"]) for b in blocks) > 0.8, name
    assert isinstance(gpu_available(), bool)


# ------------------------------------------------------------------ error log + backup
def test_error_log_and_report(tmp_path, monkeypatch):
    monkeypatch.setenv("ARABIZE_HOME", str(tmp_path))
    from arabize import logs
    logs._ready = False
    path = logs.setup()
    logs.log.error("test failure %s", 42)
    for h in logs.log.handlers:
        h.flush()
    assert path.exists() and "test failure 42" in path.read_text(encoding="utf-8")
    rep = logs.report()
    assert "Arabize Game" in rep and "test failure 42" in rep
    for h in list(logs.log.handlers):
        logs.log.removeHandler(h); h.close()
    logs._ready = False


def test_settings_backup_round_trip_keeps_keys_private(env_ctrl, tmp_path):
    from arabize.config import Settings
    s = env_ctrl.settings
    s.data["engines"]["claude_key"] = "sk-secret"
    s.add_profile("Elden Ring", "eldenring.exe") if hasattr(s, "add_profile") else env_ctrl.add_game("Elden Ring", "eldenring.exe")
    s.update_profile("glossary", [{"src": "Tarnished", "tr": "الملطّخ", "kind": "character"}])
    text = s.export_text()
    assert "sk-secret" not in text
    other = Settings(tmp_path / "other.json")
    other.data["engines"]["claude_key"] = "sk-mine"
    n = other.import_text(text)
    assert n >= 2 and other.data["engines"]["claude_key"] == "sk-mine"
    assert any(g["src"] == "Tarnished" for p in other.data["profiles"].values() for g in p.get("glossary", []))
    with pytest.raises(ValueError):
        other.import_text(json.dumps({"kind": "templates"}))


# ------------------------------------------------------------------ capture fallbacks
def test_capture_falls_back_when_windows_apis_are_missing():
    import sys
    from arabize.capture import Capturer
    try:
        cap = Capturer("window")
        img, box = cap.grab(1, None, None)          # no game window: uses the screen
    except Exception as e:
        pytest.skip(f"no screen to capture here: {e}")
    assert img.ndim == 3 and img.shape[2] == 3 and box["width"] > 0
    assert cap.active in ("dxgi", "gdi") if sys.platform == "win32" else cap.active == "gdi"
    cap.close()


# ------------------------------------------------------------------ intro video
def test_intro_plays_by_itself():
    from PySide6.QtWidgets import QApplication
    from arabize.ui import theme
    from arabize.ui.tutorial import STEPS, Tutorial
    app = QApplication.instance() or QApplication([])
    theme.load_fonts()
    t = Tutorial()
    assert t.autoplay and t.i == 0
    t._elapsed = t.step_seconds() - 0.01
    t._advance()
    assert t.i == 1                                   # moved on without a click
    t._toggle_play(); t._elapsed = 999; t._advance()
    assert t.i == 1                                   # paused
    for i in range(len(STEPS)):
        assert 7.0 <= t.step_seconds(i) <= 25.0
    t.close()
