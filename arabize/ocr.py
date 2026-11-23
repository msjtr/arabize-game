"""Text recognition engines.

- "windows": Windows.Media.Ocr (built into Windows 10/11, lightest, uses installed language packs)
- "rapid":   RapidOCR / ONNX (bundled, works everywhere, strong on English)
- "auto":    Windows OCR when available, otherwise RapidOCR
"""
from __future__ import annotations

import sys
import threading
import time

import numpy as np

from .textproc import Line, clean


class OcrError(RuntimeError):
    pass


class BaseOcr:
    name = "base"

    def read(self, img_bgr: np.ndarray) -> list[Line]:
        raise NotImplementedError


def _prep(img: np.ndarray, min_h: int = 48, max_side: int = 2200, pad: int = 32) -> tuple[np.ndarray, float, int]:
    """Upscale tiny regions, downscale huge ones, and add a margin.

    The text detector misses lines that touch the image edge, which is exactly what a tight
    user-selected subtitle strip looks like, so every image gets a replicated border.
    """
    import cv2  # shipped with rapidocr
    h, w = img.shape[:2]
    scale = 1.0
    if h < min_h:
        scale = min(3.0, min_h / max(1, h))
    elif max(h, w) > max_side:
        scale = max_side / max(h, w)
    if abs(scale - 1.0) > 0.05:
        img = cv2.resize(img, (int(w * scale), int(h * scale)),
                         interpolation=cv2.INTER_CUBIC if scale > 1 else cv2.INTER_AREA)
    img = cv2.copyMakeBorder(img, pad, pad, pad, pad, cv2.BORDER_REPLICATE)
    return img, scale, pad


PERF_PRESETS = {
    # how often the screen is checked, how large the OCR detector looks, CPU threads
    "light": {"interval_ms": 600, "stable_ms": 300, "ocr_side": 960, "threads": 1},
    "balanced": {"interval_ms": 300, "stable_ms": 250, "ocr_side": 1280, "threads": 2},
    "high": {"interval_ms": 150, "stable_ms": 200, "ocr_side": 1600, "threads": 4},
}


def gpu_available() -> bool:
    """True when onnxruntime can run the OCR models on the graphics card through DirectML (any DX12 GPU)."""
    try:
        import onnxruntime as ort  # type: ignore
        return "DmlExecutionProvider" in ort.get_available_providers()
    except Exception:
        return False


GPU_ERROR = ""


def use_gpu(eng) -> bool:
    """Move RapidOCR's ONNX sessions to the graphics card (DirectML). Falls back to CPU; the reason is kept in GPU_ERROR."""
    global GPU_ERROR
    if not gpu_available():
        GPU_ERROR = "onnxruntime-directml غير مثبت"
        return False
    import onnxruntime as ort  # type: ignore
    moved = False
    seen = set()
    for part in vars(eng).values():
        for holder in (part, *vars(part).values()) if hasattr(part, "__dict__") else ():
            sess = getattr(holder, "session", None)
            if sess is None or not hasattr(sess, "_model_path") or id(sess) in seen:
                continue
            seen.add(id(sess))
            try:
                opt = ort.SessionOptions()
                opt.enable_mem_pattern = False          # required by DirectML
                opt.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
                holder.session = ort.InferenceSession(sess._model_path, sess_options=opt,
                                                      providers=["DmlExecutionProvider", "CPUExecutionProvider"])
                moved = moved or "DmlExecutionProvider" in holder.session.get_providers()
            except Exception as e:
                GPU_ERROR = str(e)[:300]
                continue
    if moved:
        GPU_ERROR = ""
    return moved


class RapidOcr(BaseOcr):
    name = "rapid"
    _engine = None
    _lock = threading.Lock()

    _cfg: tuple | None = None
    gpu_active = False

    def __init__(self, min_conf: float = 0.55, perf: dict | None = None):
        self.min_conf = min_conf
        p = {**PERF_PRESETS["balanced"], **(perf or {})}
        self.max_side = int(p["ocr_side"])
        cfg = (int(p["threads"]), self.max_side, bool(p.get("gpu")))
        with RapidOcr._lock:
            if RapidOcr._engine is None or RapidOcr._cfg != cfg:
                try:
                    from rapidocr_onnxruntime import RapidOCR  # type: ignore
                except Exception as e:  # pragma: no cover
                    raise OcrError(f"محرك القراءة RapidOCR غير متاح: {e}")
                eng = RapidOCR(intra_op_num_threads=cfg[0], inter_op_num_threads=1)
                # Default sizing scales the SHORT side up to 736px, which turns a thin subtitle strip
                # into a huge image (1.2 s). Capping the LONG side is ~13x faster on strips and
                # ~2x on full screens, with equal or better accuracy in our tests.
                try:
                    op = eng.text_detector.preprocess_op[0]
                    op.limit_type, op.limit_side_len = "max", cfg[1]
                except (AttributeError, IndexError):
                    pass
                eng.use_angle_cls = False  # game text is upright; skipping the rotation model saves time
                RapidOcr.gpu_active = use_gpu(eng) if cfg[2] else False
                RapidOcr._engine, RapidOcr._cfg = eng, cfg

    def read(self, img_bgr: np.ndarray) -> list[Line]:
        img, scale, pad = _prep(img_bgr, max_side=2200 if self.max_side >= 1280 else 1600)
        with RapidOcr._lock:
            result, _ = RapidOcr._engine(img)
        lines: list[Line] = []
        for pts, text, conf in result or []:
            conf = float(conf)
            text = clean(text)
            if not text or conf < self.min_conf:
                continue
            xs = [p[0] - pad for p in pts]; ys = [p[1] - pad for p in pts]
            x0, y0 = max(0.0, min(xs) / scale), max(0.0, min(ys) / scale)
            lines.append(Line(text, conf, x0, y0, (max(xs) / scale) - x0, (max(ys) / scale) - y0))
        return lines


class WindowsOcr(BaseOcr):  # pragma: no cover - needs Windows
    """Windows.Media.Ocr through the winsdk package."""
    name = "windows"

    def __init__(self, lang: str = "en", min_conf: float = 0.0):
        if sys.platform != "win32":
            raise OcrError("Windows OCR يعمل على ويندوز فقط")
        try:
            self.ns = _winrt_ns()
            OcrEngine = self.ns.media_ocr.OcrEngine
            Language = self.ns.globalization.Language
        except Exception as e:
            raise OcrError(f"Windows OCR غير متاح: {e}")
        tag = {"zh-CN": "zh-Hans", "zh-TW": "zh-Hant"}.get(lang, lang)
        eng = None
        if lang and lang != "auto":
            try:
                if OcrEngine.is_language_supported(Language(tag)):
                    eng = OcrEngine.try_create_from_language(Language(tag))
            except Exception:
                eng = None
        self.engine = eng or OcrEngine.try_create_from_user_profile_languages()
        if self.engine is None:
            raise OcrError("لا توجد حزمة لغة OCR مثبتة في ويندوز")

    def read(self, img_bgr: np.ndarray) -> list[Line]:
        import asyncio
        im = self.ns.imaging
        SoftwareBitmap, BitmapPixelFormat, BitmapAlphaMode = im.SoftwareBitmap, im.BitmapPixelFormat, im.BitmapAlphaMode
        DataWriter = self.ns.streams.DataWriter

        img, scale, pad = _prep(img_bgr)
        h, w = img.shape[:2]
        bgra = np.dstack([img, np.full((h, w), 255, np.uint8)]).tobytes()

        async def run():
            writer = DataWriter()
            writer.write_bytes(bgra)
            buf = writer.detach_buffer()
            bmp = SoftwareBitmap.create_copy_from_buffer(buf, BitmapPixelFormat.BGRA8, w, h, BitmapAlphaMode.PREMULTIPLIED)
            return await self.engine.recognize_async(bmp)

        res = asyncio.run(run())
        lines: list[Line] = []
        for ln in res.lines:
            words = list(ln.words)
            if not words:
                continue
            xs0 = [wd.bounding_rect.x for wd in words]; ys0 = [wd.bounding_rect.y for wd in words]
            xs1 = [wd.bounding_rect.x + wd.bounding_rect.width for wd in words]
            ys1 = [wd.bounding_rect.y + wd.bounding_rect.height for wd in words]
            text = clean(ln.text)
            if text:
                lines.append(Line(text, 1.0, max(0.0, (min(xs0) - pad) / scale), max(0.0, (min(ys0) - pad) / scale),
                                  (max(xs1) - min(xs0)) / scale, (max(ys1) - min(ys0)) / scale))
        return lines


def _winrt_ns():  # pragma: no cover - Windows only
    """Windows Runtime bindings: the maintained 'winrt-*' packages, or the older 'winsdk' bundle."""
    import importlib
    import types
    for root in ("winrt", "winsdk"):
        try:
            return types.SimpleNamespace(
                media_ocr=importlib.import_module(f"{root}.windows.media.ocr"),
                globalization=importlib.import_module(f"{root}.windows.globalization"),
                imaging=importlib.import_module(f"{root}.windows.graphics.imaging"),
                streams=importlib.import_module(f"{root}.windows.storage.streams"))
        except ImportError:
            continue
    raise ImportError("winrt / winsdk not installed")


def create_ocr(kind: str = "auto", lang: str = "en", min_conf: float = 0.55, perf: dict | None = None) -> BaseOcr:
    errors = []
    order = {"auto": ["windows", "rapid"], "windows": ["windows", "rapid"], "rapid": ["rapid"]}.get(kind, ["rapid"])
    for k in order:
        try:
            return WindowsOcr(lang, min_conf) if k == "windows" else RapidOcr(min_conf, perf)
        except OcrError as e:
            errors.append(str(e))
    raise OcrError("؛ ".join(errors))


def timed_read(ocr: BaseOcr, img: np.ndarray) -> tuple[list[Line], float]:
    t = time.perf_counter()
    lines = ocr.read(img)
    return lines, (time.perf_counter() - t) * 1000
