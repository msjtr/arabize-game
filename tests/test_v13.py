"""1.3: translation drawn on the game's own text, fast reading, VR fixes."""
import ctypes

import pytest

from arabize.overlay import place_items


def meas(it, font, width):
    return font * 1.6


def test_cover_centres_the_translation_on_the_source_text():
    it = {"abs": (1200, 300, 400, 40), "line_h": 40}
    (bx, by, w, h, font, _), = place_items([it], (0, 0, 1920, 1080), (0, 0), 1.0, "cover", meas)
    assert abs((bx + w / 2) - 1400) < 1 and abs((by + h / 2) - 320) < 1      # same centre as the English line
    assert w >= 400 and 30 <= font <= 40


def test_above_sits_over_the_line_or_below_when_there_is_no_room():
    top = {"abs": (800, 2, 300, 30), "line_h": 30}
    mid = {"abs": (800, 500, 300, 30), "line_h": 30}
    placed = {id(p[5]): p for p in place_items([top, mid], (0, 0, 1920, 1080), (0, 0), 1.0, "above", meas)}
    bx, by, w, h, *_ = placed[id(mid)]
    assert by + h <= 500
    bx, by, w, h, *_ = placed[id(top)]
    assert by >= 2 + 30                                                      # no room above: goes below


def test_high_dpi_and_second_monitor_map_to_logical_pixels():
    # a 4K TV at 150 % placed right of a 1080p monitor: Qt geometry (1920, 0, 2560, 1440), native origin (1920, 0)
    it = {"abs": (1920 + 1500, 900, 600, 60), "line_h": 60}
    (bx, by, w, h, *_), = place_items([it], (1920, 0, 2560, 1440), (1920, 0), 1.5, "cover", meas)
    assert abs(bx + w / 2 - (1920 + 1800 / 1.5)) < 1 and abs(by + h / 2 - 930 / 1.5) < 1


def test_boxes_never_overlap_and_stay_on_screen():
    a = {"abs": (900, 1040, 300, 36), "line_h": 36}
    b = {"abs": (920, 1050, 300, 36), "line_h": 36}
    c = {"abs": (1900, 500, 300, 36), "line_h": 36}
    pl = place_items([a, b, c], (0, 0, 1920, 1080), (0, 0), 1.0, "cover", meas)
    for bx, by, w, h, *_ in pl:
        assert bx >= 0 and by >= 0 and bx + w <= 1920 and by + h <= 1080 + 60
    (x1, y1, w1, h1, *_), (x2, y2, w2, h2, *_) = pl[0], pl[1]
    assert not (x1 < x2 + w2 and x2 < x1 + w1 and y1 < y2 + h2 and y2 < y1 + h1)


@pytest.fixture
def qapp():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_layers_switch_to_in_place_when_items_have_positions(qapp):
    from arabize.config import DEFAULT_PROFILE
    from arabize.overlay import OverlayLayers
    from PySide6.QtGui import QGuiApplication
    ov = OverlayLayers()
    st = dict(DEFAULT_PROFILE["display"]["screen"]); st["rtl"] = True
    ov.configure(st, QGuiApplication.primaryScreen())
    items = [{"kind": "dialogue", "label": "Mara", "label_tr": "مارا", "src": "Run!", "tr": "اركض!", "abs": (300, 400, 200, 40), "line_h": 40}]
    ov.show_items(items)
    assert ov.inplace.isVisible() and not any(w.isVisible() for w in ov.layers.values())
    assert ov.inplace.boxes
    # without positions (preview, sample text) the normal subtitle box is used
    ov.show_items([{"kind": "dialogue", "label": "", "src": "x", "tr": "تجربة"}])
    assert not ov.inplace.isVisible() and ov.layers["dialogue"].isVisible()
    st["place"] = "fixed"; ov.configure(st, QGuiApplication.primaryScreen())
    ov.show_items(items)
    assert not ov.inplace.isVisible()
    ov.clear(animate=False)


# ------------------------------------------------------------------ VR against a stand-in SteamVR
class FakeOVR:
    """Enough of pyopenvr to drive VRSubtitle: SteamVR off/on, overlay calls recorded, a quit event."""


    VRApplication_Background, VRApplication_Overlay = 3, 2
    VREvent_Quit, VREvent_DriverRequestedQuit = 700, 704
    TrackingUniverseStanding = 1
    k_unTrackedDeviceIndex_Hmd = 0

    def __init__(self):
        import types
        self.running = False
        self.calls = []
        self.events = []

        class InitError(Exception):
            pass

        class InitError_Init_NoServerForBackgroundApp(InitError):
            pass

        self.error_code = types.SimpleNamespace(InitError=InitError, NoServer=InitError_Init_NoServerForBackgroundApp)
        ovr = self

        class Overlay:
            def __getattr__(self, name):
                def f(*a):
                    ovr.calls.append((name, a))
                    return 7 if name in ("createOverlay", "findOverlay") else None
                return f
        self._Overlay = Overlay

        class System:
            def pollNextEvent(self, ev):
                if ovr.events:
                    ev.eventType = ovr.events.pop(0); return True
                return False

            def acknowledgeQuit_Exiting(self):
                ovr.calls.append(("ack", ()))

            def getDeviceToAbsoluteTrackingPose(self, *a):
                return a[2]
        self._System = System

    def isRuntimeInstalled(self):
        return True

    def init(self, kind):
        if not self.running:
            raise self.error_code.NoServer("no server")
        return self._System()

    def shutdown(self):
        self.calls.append(("shutdown", ()))

    def IVROverlay(self):
        return self._Overlay()

    class VREvent_t:
        eventType = 0

    class HmdMatrix34_t:
        def __init__(self):
            self.m = [[0.0] * 4 for _ in range(3)]

    class TrackedDevicePose_t(ctypes.Structure):
        _fields_ = [("bPoseIsValid", ctypes.c_bool)]


def test_vr_waits_for_steamvr_uploads_the_picture_and_lets_go_on_quit(qapp, monkeypatch):
    import ctypes
    import sys
    from arabize.vr import VRNotRunning, VRSubtitle
    fake = FakeOVR()
    monkeypatch.setitem(sys.modules, "openvr", fake)
    v = VRSubtitle()
    with pytest.raises(VRNotRunning):
        v.start({"width_m": 1.1})
    fake.running = True
    v.start({"width_m": 1.1, "placement": "head"})
    assert v.active
    v.show_items([{"label": "", "src": "Run!", "tr": "اركض!"}])
    raw = [a for n, a in fake.calls if n == "setOverlayRaw"][-1]
    buf, w, h, bpp = raw[1:]
    assert isinstance(buf, ctypes.Array) and len(buf) == w * h * 4 and bpp == 4   # the pixels, not a pointer to them
    assert any(b != 0 for b in bytes(buf)[: w * h * 4: 97])
    fake.events.append(fake.VREvent_Quit)
    assert v.poll() == "quit" and not v.active and ("ack", ()) in fake.calls


def test_controller_starts_steamvr_and_connects_when_it_is_ready(env_ctrl, monkeypatch):
    import sys
    import arabize.app as appmod
    fake = FakeOVR()
    monkeypatch.setitem(sys.modules, "openvr", fake)
    launched = []
    monkeypatch.setattr(appmod, "launch_steamvr", lambda: launched.append(1) or True)
    c = env_ctrl
    c.set_mode("vr")
    assert launched and c.vr_wait.isActive() and c.prof["display"]["mode"] == "vr"
    fake.running = True
    c._vr_retry()
    assert c.vr.active and not c.vr_wait.isActive() and c.vr_events.isActive()
    fake.events.append(fake.VREvent_Quit)
    c._vr_events()
    assert not c.vr.active and c.vr_wait.isActive()        # waits to reconnect when SteamVR comes back
    c.vr_wait.stop()
