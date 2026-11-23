import time

import numpy as np

from arabize.capture import ChangeDetector
from arabize.config import Settings
from arabize.engines import AllEnginesFailed, Request
from arabize.textproc import Line, TextTracker, group_lines, is_noise, normalize_key, similarity
from conftest import Fake


# ---------- text ----------
def test_normalize_and_similarity():
    assert normalize_key("  “Halt!”  Who goes   there? ") == normalize_key('"halt" who goes there')
    assert similarity("Halt! Who goes there?", "Halt! Who goes there") > 0.95
    assert similarity("Open the gate", "Close the door") < 0.7


def test_noise_filter():
    assert is_noise("12") and is_noise("--") and is_noise("") and is_noise("|||")
    assert not is_noise("Go")


def test_group_lines_paragraph_and_separate_menu():
    lines = [Line("The guard looks at you", .9, 100, 500, 400, 30),
             Line("with suspicion.", .9, 100, 534, 200, 30),
             Line("Inventory", .9, 1500, 80, 160, 26)]
    blocks = group_lines(lines)
    texts = sorted(b.text for b in blocks)
    assert texts == ["Inventory", "The guard looks at you with suspicion."]


def test_tracker_skips_repeats_and_ocr_jitter():
    t = TextTracker()
    assert t.is_new(["Halt! Who goes there?"])
    assert not t.is_new(["Halt! Who goes there?"])
    assert not t.is_new(["Halt! Who goes there"])          # OCR jitter
    assert t.is_new(["You may pass, traveler."])
    assert not t.is_new([])


# ---------- change detection ----------
def test_change_detector_fires_once_after_text_settles():
    cd = ChangeDetector(sensitivity=3, stable_ms=200)
    blank = np.zeros((200, 600, 3), np.uint8)
    text = blank.copy(); text[80:120, 50:500] = 255
    t = 0.0
    fired = []
    for img in [blank, blank, blank]:          # first frame forced read
        fired.append(cd.update(img, t)); t += .1
    assert fired.count(True) == 1
    fired = [cd.update(text, t)]; t += .1     # change starts
    for _ in range(4):
        fired.append(cd.update(text, t)); t += .1
    assert fired.count(True) == 1 and fired[0] is False  # only after it settled
    assert not any(cd.update(text, t + i) for i in range(3))  # no repeat while still


# ---------- settings & profiles ----------
def test_profiles_roundtrip(tmp_path):
    s = Settings(tmp_path / "s.json")
    pid = s.add_profile("Elden Ring", "eldenring.exe")
    s.set_active(pid)
    s.update_profile("display.screen.font_size", 34)
    s2 = Settings(tmp_path / "s.json")
    assert s2.profile_id == pid and s2.profile["display"]["screen"]["font_size"] == 34
    assert s2.profile_for_exe("EldenRing.exe") == pid
    assert s2.data["profiles"]["default"]["display"]["screen"]["font_size"] == 26
    assert s2.delete_profile(pid) and s2.profile_id == "default"
    assert not s2.delete_profile("default")


def test_broken_settings_file_recovers(tmp_path):
    p = tmp_path / "s.json"; p.write_text("{not json", encoding="utf-8")
    s = Settings(p)
    assert s.profile["lang"]["tgt"] == "ar"


# ---------- engines: real response formats ----------
def test_google_format(env):
    s, st, m = env
    r = m.translate(Request("Halt! Who goes there?", "auto", "ar"))
    assert r.text == "قف! من هناك؟" and r.engine == "google" and r.detected == "en"


def test_memory_prevents_second_request(env):
    s, st, m = env
    m.translate(Request("Halt! Who goes there?", "auto", "ar"))
    r = m.translate(Request("  halt!  who goes there? ", "auto", "ar"))
    assert r.source.startswith("cache") and Fake.calls["google"] == 1


def test_retry_then_success(env):
    s, st, m = env
    Fake.mode["google"] = "flaky"
    r = m.translate(Request("Open the gate", "auto", "ar"))
    assert r.engine == "google" and Fake.calls["google"] == 2


def test_fallback_to_next_engine(env):
    s, st, m = env
    Fake.mode["google"] = "500"
    r = m.translate(Request("Open the gate", "auto", "ar"))
    assert r.engine == "mymemory" and r.text == "م:Open the gate"
    assert Fake.calls["google"] == 3   # 1 try + 2 retries


def test_circuit_breaker_rests_failing_engine(env):
    s, st, m = env
    Fake.mode["google"] = "500"
    for i in range(3):
        m.translate(Request(f"line {i} text", "auto", "ar"))
    before = Fake.calls["google"]
    m.translate(Request("another line text", "auto", "ar"))
    assert Fake.calls["google"] == before  # rested, went straight to MyMemory
    assert m.engine_state()["google"] == "rest"


def test_all_fail_reports_network(env):
    s, st, m = env
    Fake.mode["google"] = "drop"; Fake.mode["mymemory"] = "drop"
    try:
        m.translate(Request("Open the gate", "auto", "ar"))
        assert False
    except AllEnginesFailed as e:
        assert e.network and set(e.errors) == {"google", "mymemory"}


def test_claude_and_deepl_formats(env):
    s, st, m = env
    s.data["engines"].update({"order": ["claude", "deepl"], "enabled": {"claude": True, "deepl": True},
                              "claude_key": "sk-test", "deepl_key": "k:fx"})
    r = m.translate(Request("Halt! Who goes there?", "auto", "ar", context=("Guard: Stop.",)))
    assert r.engine == "claude" and r.text == "قف! من هناك؟" and r.detected == "en"
    Fake.mode["claude"] = "401"
    r = m.translate(Request("New text here", "auto", "ar"))
    assert r.engine == "deepl" and r.text == "د:New text here"
    assert Fake.calls["claude"] == 2   # 401 is not retried


def test_manual_override_wins(env):
    s, st, m = env
    hid = st.add_history("default", "Halt! Who goes there?", "قف! من هناك؟", "google", "en", "ar")
    st.edit_history(hid, "توقف! من القادم؟")
    r = m.translate(Request("Halt! Who goes there?", "auto", "ar"))
    assert r.text == "توقف! من القادم؟" and r.source == "manual"
    assert st.history()[0]["engine"] == "manual"


def test_diagnostics(env):
    s, st, m = env
    rows = {r["id"]: r for r in m.test_engines()}
    assert rows["google"]["ok"] and rows["google"]["text"] == "اضغط أي زر لمتابعة مغامرتك."
    assert rows["mymemory"]["ok"] and not rows["claude"]["ok"] and rows["claude"]["error"]


# ---------- hotkeys / VR / render ----------
def test_hotkey_conversion():
    from arabize.hotkeys import to_pynput
    assert to_pynput("Ctrl+Shift+T") == "<ctrl>+<shift>+t"
    assert to_pynput("Alt+F8") == "<alt>+<f8>"
    assert to_pynput("") is None and to_pynput("Ctrl+") is None


def test_vr_reports_missing_steamvr_cleanly():
    from arabize.vr import VRError, VRSubtitle
    v = VRSubtitle()
    try:
        v.start({"distance_m": 1.4})
        v.stop()
    except VRError as e:
        assert "SteamVR" in str(e) or "OpenVR" in str(e)
    assert not v.active
