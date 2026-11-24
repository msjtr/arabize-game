"""VR mode: the subtitle as a floating panel inside the headset (SteamVR / OpenVR overlay).

Works with any headset that runs through SteamVR (Valve Index, HTC Vive, Meta Quest via Link/Air Link
or Virtual Desktop, Pico via Streaming Assistant, Windows MR via SteamVR). The panel follows the head
at the distance/height chosen in the VR settings.
"""
from __future__ import annotations

import ctypes
import math

from . import render
from .logs import log

PLACEMENTS = [
    ("head", "أمام عينك دائماً", "ثابتة في مجال الرؤية، تتحرك مع رأسك"),
    ("follow", "تتبعك بنعومة", "تبقى في مكانها وأنت تلتفت قليلاً، ثم تلحقك بهدوء بدون اهتزاز"),
    ("world", "ثابتة في المكان", "تبقى في نقطة محددة في الغرفة أو اللعبة؛ «توسيط» يعيدها أمامك"),
]


# ------------------------------------------------------------------ pose math (pure Python, unit tested)
def flat_yaw(m) -> float:
    """Heading of a 3x4 pose matrix around the vertical axis (radians). OpenVR looks down -Z."""
    fx, fz = -m[0][2], -m[2][2]
    return math.atan2(fx, -fz)


def panel_target(hmd, distance: float, height: float, side: float) -> tuple[list[float], float]:
    """Where a panel should float for this head pose: in front at eye level (+height), turned to face the player.
    Only the heading is used, so looking up/down does not tilt or bob the panel."""
    yaw = flat_yaw(hmd)
    px, py, pz = hmd[0][3], hmd[1][3], hmd[2][3]
    fwd = (math.sin(yaw), -math.cos(yaw))           # x, z
    right = (math.cos(yaw), math.sin(yaw))
    pos = [px + fwd[0] * distance + right[0] * side, py + height, pz + fwd[1] * distance + right[1] * side]
    return pos, yaw


def pose_matrix(pos, yaw) -> list[list[float]]:
    """3x4 matrix that turns the panel to face the player (its +Z points back at them) and moves it to pos.
    That is a rotation around Y by -yaw: the same turn as the head, without its pitch and roll."""
    c, s_ = math.cos(yaw), math.sin(yaw)
    return [[c, 0.0, -s_, pos[0]], [0.0, 1.0, 0.0, pos[1]], [s_, 0.0, c, pos[2]]]


def angle_diff(a: float, b: float) -> float:
    return (a - b + math.pi) % (2 * math.pi) - math.pi


class Follower:
    """Lazy follow: the panel stays put while the head moves a little (no jitter), and glides back in front
    once the player turns more than start_deg or walks more than start_m away."""

    def __init__(self, start_deg: float = 22.0, start_m: float = 0.35, tau: float = 0.35):
        self.start, self.start_m, self.tau = math.radians(start_deg), start_m, tau
        self.pos: list[float] | None = None
        self.yaw = 0.0
        self.moving = False

    def step(self, target_pos, target_yaw, dt: float) -> tuple[list[float], float]:
        if self.pos is None:
            self.pos, self.yaw = list(target_pos), target_yaw
            return self.pos, self.yaw
        dyaw = angle_diff(target_yaw, self.yaw)
        dist = math.dist(self.pos, target_pos)
        if not self.moving and (abs(dyaw) > self.start or dist > self.start_m):
            self.moving = True
        if self.moving:
            k = 1.0 - math.exp(-max(0.0, dt) / self.tau)
            self.pos = [a + (b - a) * k for a, b in zip(self.pos, target_pos)]
            self.yaw += dyaw * k
            if abs(angle_diff(target_yaw, self.yaw)) < math.radians(1.5) and math.dist(self.pos, target_pos) < 0.02:
                self.moving = False
        return self.pos, self.yaw


class VRError(RuntimeError):
    pass


class VRNotRunning(VRError):
    """SteamVR is installed but not running yet: start it and try again shortly."""


# ------------------------------------------------------------------ helpers around SteamVR / OpenXR
def _init_error_name(e) -> str:
    return type(e).__name__


def init_message(e) -> str:
    n = _init_error_name(e)
    if "HmdNotFound" in n:
        return ("SteamVR يعمل لكن لا يرى النظارة. لنظارات Meta Quest: شغّل تطبيق Meta Quest Link على الكمبيوتر، "
                "وفعّل Link من داخل النظارة، ثم شغّل SteamVR.")
    if "InstallationNotFound" in n or "VRClientDLLNotFound" in n or "PathRegistryNotFound" in n:
        return "SteamVR غير مثبت. ثبّته مجاناً من Steam (ابحث عن SteamVR) ثم أعد المحاولة."
    if "NoServerForBackgroundApp" in n:
        return "SteamVR غير مشغّل. أشغّله الآن…"
    return f"تعذّر الاتصال بـ SteamVR ({n})"


def launch_steamvr() -> bool:
    """Ask Steam to start SteamVR (app 250820)."""
    import os
    import sys
    if sys.platform != "win32":
        return False
    try:
        os.startfile("steam://rungameid/250820")  # type: ignore[attr-defined]
        return True
    except OSError:
        return False


def openxr_runtime() -> str | None:
    """Which runtime OpenXR games will use: 'steamvr', 'meta', 'wmr', 'other' or None (unknown)."""
    import sys
    if sys.platform != "win32":
        return None
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Khronos\OpenXR\1") as k:
            path = str(winreg.QueryValueEx(k, "ActiveRuntime")[0]).lower()
    except OSError:
        return None
    if "steamvr" in path or "steamxr" in path:
        return "steamvr"
    if "oculus" in path or "meta" in path:
        return "meta"
    if "mixedreality" in path:
        return "wmr"
    return "other"


OPENXR_HINT = ("ألعاب الواقع الافتراضي على Meta Quest Link تعمل الآن عبر برنامج Meta، فلا تظهر لوحة الترجمة داخلها. "
               "لتظهر: افتح SteamVR ← الإعدادات ← OpenXR ← «اجعل SteamVR مشغّل OpenXR»، ثم شغّل اللعبة من جديد.")


class VRSubtitle:
    KEY = "arabize.game.subtitle"

    def __init__(self):
        self.ovr = None
        self.overlay = None
        self.system = None
        self.handle = None
        self.style: dict = {}
        self._buf = None
        self._files = 0
        self._raw_ok = True
        self.hidden = False
        self.follower = Follower()
        self.world_pose: tuple[list[float], float] | None = None
        self._pose = None

    @property
    def active(self) -> bool:
        return self.handle is not None

    def start(self, style: dict) -> None:
        try:
            import openvr  # type: ignore
        except Exception as e:
            raise VRError(f"مكتبة OpenVR غير موجودة في هذه النسخة: {e}")
        self.ovr = openvr
        try:
            installed = openvr.isRuntimeInstalled()
        except Exception:
            installed = True
        if not installed:
            raise VRError("SteamVR غير مثبت. ثبّته مجاناً من Steam (ابحث عن SteamVR) ثم أعد المحاولة.")
        # 1) is SteamVR already running? (a background check never starts it and answers at once)
        try:
            openvr.init(openvr.VRApplication_Background)
            openvr.shutdown()
        except openvr.error_code.InitError as e:
            if "NoServerForBackgroundApp" in _init_error_name(e):
                raise VRNotRunning(init_message(e))
            raise VRError(init_message(e))
        # 2) connect as an overlay
        try:
            self.system = openvr.init(openvr.VRApplication_Overlay)
        except openvr.error_code.InitError as e:
            raise VRError(init_message(e))
        except Exception as e:
            raise VRError(f"تعذّر الاتصال بـ SteamVR: {e}")
        self.overlay = openvr.IVROverlay()
        try:
            self.handle = self.overlay.createOverlay(self.KEY, "Arabize Game")
        except Exception:
            self.handle = self.overlay.findOverlay(self.KEY)     # left over from an earlier run
        self._pose = (openvr.TrackedDevicePose_t * 1)()
        try:
            self.overlay.setOverlaySortOrder(self.handle, 200)    # above other overlays
            self.overlay.setOverlayAlpha(self.handle, 1.0)
        except Exception:
            pass
        self.apply_style(style)

    def apply_style(self, style: dict) -> None:
        self.style = dict(style)
        if not self.active:
            return
        try:
            self.overlay.setOverlayWidthInMeters(self.handle, float(style.get("width_m", 1.1)))
            if style.get("placement", "head") == "head":
                self._place_head()
            else:
                self.update_pose(0.0, recenter=self.world_pose is None)
        except Exception as e:
            log.warning("VR style: %s", e)

    def _matrix(self, rows):
        m = self.ovr.HmdMatrix34_t()
        for i in range(3):
            for j in range(4):
                m.m[i][j] = float(rows[i][j])
        return m

    def _place_head(self):
        st = self.style
        rows = [[1, 0, 0, float(st.get("side_m", 0.0))], [0, 1, 0, float(st.get("height_m", -0.35))],
                [0, 0, 1, -abs(float(st.get("distance_m", 1.4)))]]
        self.overlay.setOverlayTransformTrackedDeviceRelative(self.handle, self.ovr.k_unTrackedDeviceIndex_Hmd, self._matrix(rows))

    def hmd_pose(self):
        """Current head pose as a 3x4 list, or None while the headset is not tracked."""
        try:
            poses = self.system.getDeviceToAbsoluteTrackingPose(self.ovr.TrackingUniverseStanding, 0, self._pose)
            p = poses[0]
            if not p.bPoseIsValid:
                return None
            m = p.mDeviceToAbsoluteTracking
            return [[m.m[i][j] for j in range(4)] for i in range(3)]
        except Exception:
            return None

    def update_pose(self, dt: float, recenter: bool = False) -> None:
        """Called ~60 times a second by the controller in "follow" and "world" placements."""
        if not self.active or self.style.get("placement", "head") == "head":
            return
        hmd = self.hmd_pose()
        if hmd is None:
            return
        st = self.style
        pos, yaw = panel_target(hmd, float(st.get("distance_m", 1.4)), float(st.get("height_m", -0.35)), float(st.get("side_m", 0.0)))
        if st.get("placement") == "world":
            if recenter or self.world_pose is None:
                self.world_pose = (pos, yaw)
            pos, yaw = self.world_pose
        else:
            if recenter:
                self.follower.pos = None
            pos, yaw = self.follower.step(pos, yaw, dt)
        try:
            self.overlay.setOverlayTransformAbsolute(self.handle, self.ovr.TrackingUniverseStanding, self._matrix(pose_matrix(pos, yaw)))
        except Exception:
            pass

    def recenter(self):
        self.world_pose = None
        self.follower.pos = None
        if not self.active:
            return
        if self.style.get("placement", "head") == "head":
            self._place_head()
        else:
            self.update_pose(0.0, recenter=True)

    def poll(self) -> str | None:
        """Read SteamVR's messages. Returns "quit" when SteamVR is closing (we let go at once so it can exit)."""
        if not self.active:
            return None
        ev = self.ovr.VREvent_t()
        try:
            while self.system.pollNextEvent(ev):
                if ev.eventType in (self.ovr.VREvent_Quit, getattr(self.ovr, "VREvent_DriverRequestedQuit", -1)):
                    try:
                        self.system.acknowledgeQuit_Exiting()
                    except Exception:
                        pass
                    self.stop()
                    return "quit"
        except Exception as e:
            log.warning("VR poll: %s", e)
        return None

    def set_hidden(self, hidden: bool) -> None:
        self.hidden = hidden
        if not self.active:
            return
        try:
            (self.overlay.hideOverlay if hidden else self.overlay.showOverlay)(self.handle)
        except Exception:
            pass

    def _upload(self, img) -> None:
        w, h = img.width(), img.height()
        if self._raw_ok:
            try:
                # the buffer itself (not a pointer to it): pyopenvr passes byref(buffer) to SteamVR
                self._buf = ctypes.create_string_buffer(bytes(img.constBits())[: w * h * 4], w * h * 4)
                self.overlay.setOverlayRaw(self.handle, self._buf, w, h, 4)
                return
            except Exception as e:
                log.warning("VR raw upload failed, using an image file instead: %s", e)
                self._raw_ok = False
        import os
        import tempfile
        self._files += 1
        path = os.path.join(tempfile.gettempdir(), f"arabize_vr_{self._files % 3}.png")
        img.save(path, "PNG")
        self.overlay.setOverlayFromFile(self.handle, path)

    def show_items(self, items: list[dict]) -> None:
        if not self.active:
            return
        st = dict(self.style)
        img = render.render_image(items, st, 1400)
        if img.height() > 1080:                 # SteamVR's limit for one overlay picture
            img = img.copy(0, img.height() - 1080, img.width(), 1080)
        try:
            self._upload(img)
            if not self.hidden:
                self.overlay.showOverlay(self.handle)
        except Exception as e:
            log.warning("VR show failed: %s", e)

    def hide(self) -> None:
        if self.active:
            try:
                self.overlay.hideOverlay(self.handle)
            except Exception:
                pass

    def stop(self) -> None:
        if self.active:
            try:
                self.overlay.destroyOverlay(self.handle)
            except Exception:
                pass
            try:
                self.ovr.shutdown()
            except Exception:
                pass
        self.handle = None
