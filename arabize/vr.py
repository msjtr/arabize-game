"""VR mode: the subtitle as a floating panel inside the headset (SteamVR / OpenVR overlay).

Works with any headset that runs through SteamVR (Valve Index, HTC Vive, Meta Quest via Link/Air Link
or Virtual Desktop, Pico via Streaming Assistant, Windows MR via SteamVR). The panel follows the head
at the distance/height chosen in the VR settings.
"""
from __future__ import annotations

import ctypes

from . import render


class VRError(RuntimeError):
    pass


class VRSubtitle:
    KEY = "arabize.game.subtitle"

    def __init__(self):
        self.ovr = None
        self.overlay = None
        self.handle = None
        self.style: dict = {}
        self._buf = None

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
            openvr.init(openvr.VRApplication_Overlay)
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
        o = self.ovr
        self.overlay.setOverlayWidthInMeters(self.handle, float(style.get("width_m", 1.1)))
        m = o.HmdMatrix34_t()
        for i in range(3):
            for j in range(4):
                m.m[i][j] = 1.0 if i == j else 0.0
        m.m[1][3] = float(style.get("height_m", -0.35))      # up/down from the eyes
        m.m[2][3] = -abs(float(style.get("distance_m", 1.4)))  # in front of the face
        self.overlay.setOverlayTransformTrackedDeviceRelative(self.handle, o.k_unTrackedDeviceIndex_Hmd, m)

    def show_items(self, items: list[dict]) -> None:
        if not self.active:
            return
        st = dict(self.style)
        img = render.render_image(items, st, 1400)
        w, h = img.width(), img.height()
        self._buf = ctypes.create_string_buffer(bytes(img.constBits())[: w * h * 4])
        self.overlay.setOverlayRaw(self.handle, ctypes.cast(self._buf, ctypes.c_void_p), w, h, 4)
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
