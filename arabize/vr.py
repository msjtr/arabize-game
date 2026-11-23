"""VR mode: the subtitle as a floating panel inside the headset (SteamVR / OpenVR overlay).

Works with any headset that runs through SteamVR (Valve Index, HTC Vive, Meta Quest via Link/Air Link
or Virtual Desktop, Pico via Streaming Assistant, Windows MR via SteamVR). The panel follows the head
at the distance/height chosen in the VR settings.
"""
from __future__ import annotations

import ctypes
import math

from . import render

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


class VRSubtitle:
    KEY = "arabize.game.subtitle"

    def __init__(self):
        self.ovr = None
        self.overlay = None
        self.system = None
        self.handle = None
        self.style: dict = {}
        self._buf = None
        self.hidden = False
        self.follower = Follower()
        self.world_pose: tuple[list[float], float] | None = None

    @property
    def active(self) -> bool:
        return self.handle is not None

    def start(self, style: dict) -> None:
        try:
            import openvr  # type: ignore
        except Exception as e:
            raise VRError(f"مكتبة OpenVR غير مثبتة: {e}")
        self.ovr = openvr
        try:
            self.system = openvr.init(openvr.VRApplication_Overlay)
        except Exception as e:
            raise VRError("لم يُعثر على SteamVR. شغّل SteamVR والنظارة متصلة ثم أعد المحاولة. "
                          f"(التفاصيل: {e})")
        self.overlay = openvr.IVROverlay()
        try:
            self.handle = self.overlay.createOverlay(self.KEY, "Arabize Game")
        except Exception:
            self.handle = self.overlay.findOverlay(self.KEY)
        self.apply_style(style)
        self.overlay.showOverlay(self.handle)

    def apply_style(self, style: dict) -> None:
        self.style = dict(style)
        if not self.active:
            return
        self.overlay.setOverlayWidthInMeters(self.handle, float(style.get("width_m", 1.1)))
        if style.get("placement", "head") == "head":
            self._place_head()
        else:
            self.update_pose(0.0, recenter=self.world_pose is None)

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
            poses = self.system.getDeviceToAbsoluteTrackingPose(self.ovr.TrackingUniverseStanding, 0, 1)
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
        self.overlay.setOverlayTransformAbsolute(self.handle, self.ovr.TrackingUniverseStanding, self._matrix(pose_matrix(pos, yaw)))

    def recenter(self):
        self.world_pose = None
        self.follower.pos = None
        if not self.active:
            return
        if self.style.get("placement", "head") == "head":
            self._place_head()
        else:
            self.update_pose(0.0, recenter=True)

    def set_hidden(self, hidden: bool) -> None:
        self.hidden = hidden
        if not self.active:
            return
        try:
            (self.overlay.hideOverlay if hidden else self.overlay.showOverlay)(self.handle)
        except Exception:
            pass

    def show_items(self, items: list[dict]) -> None:
        if not self.active:
            return
        st = dict(self.style)
        img = render.render_image(items, st, 1400)
        w, h = img.width(), img.height()
        self._buf = ctypes.create_string_buffer(bytes(img.constBits())[: w * h * 4])
        self.overlay.setOverlayRaw(self.handle, ctypes.cast(self._buf, ctypes.c_void_p), w, h, 4)
        if not self.hidden:
            self.overlay.showOverlay(self.handle)

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
