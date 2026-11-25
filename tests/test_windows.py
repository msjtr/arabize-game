"""Windows-only checks (skipped elsewhere): capture exclusion, foreground game detection, Windows OCR."""
import sys

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows only")


def test_foreground_exe_does_not_crash():
    from arabize.platform_utils import foreground_exe
    exe = foreground_exe()
    assert exe is None or exe.lower().endswith(".exe")


def test_windows_ocr_reads_game_text():
    from arabize.ocr import OcrError, WindowsOcr
    from arabize.textproc import group_lines, similarity
    from gameshots import dialogue_scene
    try:
        ocr = WindowsOcr("en")
    except OcrError as e:
        pytest.skip(f"Windows OCR language pack not installed on this machine: {e}")
    img, exp = dialogue_scene()
    blocks = group_lines(ocr.read(img))
    assert max(similarity(b.text, exp["dialogue"]) for b in blocks) > 0.85


def test_overlay_excluded_from_capture():
    from PySide6.QtWidgets import QApplication
    from arabize.overlay import SubtitleOverlay
    app = QApplication.instance() or QApplication([])
    ov = SubtitleOverlay()
    ov.configure({"font_size": 26, "recordable": False}, app.primaryScreen())
    ov.show_items([{"label": "", "tr": "اختبار", "src": ""}])
    app.processEvents()
    assert ov.excluded  # SetWindowDisplayAffinity(WDA_EXCLUDEFROMCAPTURE) succeeded
    ov.configure({"font_size": 26, "recordable": True}, app.primaryScreen())
    app.processEvents()
    assert not ov.excluded  # visible to screenshots and recordings again
    ov.close()


# ---------------------------------------------------------------- capture methods (DXGI, game window, GDI)
def _show_scene(app, title="Arabize Test Game"):
    """A window that shows a game dialogue screenshot, standing in for a game."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QImage, QPixmap
    from PySide6.QtWidgets import QLabel
    from gameshots import dialogue_scene
    import time
    img, exp = dialogue_scene()
    h, w = img.shape[:2]
    rgb = img[:, :, ::-1].copy()
    q = QImage(rgb.data, w, h, w * 3, QImage.Format_RGB888).copy()
    lab = QLabel(); lab.setWindowTitle(title); lab.setWindowFlags(Qt.FramelessWindowHint)
    scr = app.primaryScreen().geometry()
    lab.setPixmap(QPixmap.fromImage(q).scaled(min(w, scr.width()), min(h, scr.height()), Qt.KeepAspectRatio))
    lab.move(scr.x(), scr.y()); lab.show(); lab.raise_(); lab.activateWindow()
    t = time.time()
    while time.time() - t < 1.0:
        app.processEvents()
    return lab, exp


def _read(img):
    from arabize.ocr import RapidOcr
    from arabize.textproc import group_lines
    return " ".join(b.text for b in group_lines(RapidOcr().read(img)))


def test_dxgi_capture_reads_the_screen_and_skips_our_overlay():
    from PySide6.QtWidgets import QApplication
    from arabize.capture import Capturer
    from arabize.overlay import SubtitleOverlay
    from arabize.textproc import similarity
    app = QApplication.instance() or QApplication([])
    lab, exp = _show_scene(app)
    ov = SubtitleOverlay(); ov.configure({"font_size": 40, "anchor": "top", "offset": 20, "width_pct": 60, "recordable": False}, app.primaryScreen())
    ov.show_items([{"label": "", "tr": "OVERLAYMARKER", "src": ""}]); app.processEvents()
    cap = Capturer("dxgi")
    img, box = cap.grab(1)
    try:
        if cap.active != "dxgi":
            pytest.skip(f"DXGI duplication not available on this machine: {cap.note}")
        text = _read(img)
        assert similarity(text, exp["dialogue"]) > 0.3 or "dawn" in text.lower(), text
        assert "OVERLAYMARKER" not in text.upper()
    finally:
        cap.close(); ov.close(); lab.close()


def test_window_capture_sees_the_game_even_when_covered():
    import ctypes
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QLabel
    from arabize.capture import Capturer
    app = QApplication.instance() or QApplication([])
    lab, exp = _show_scene(app, "Arabize Covered Game")
    cover = QLabel("COVER WINDOW"); cover.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
    cover.setStyleSheet("background:#ff00ff;font-size:60px"); cover.setGeometry(lab.geometry()); cover.show()
    for _ in range(30):
        app.processEvents()
    hwnd = int(lab.winId())
    cap = Capturer("window")
    try:
        img, box = cap.grab(1, None, (hwnd, "python.exe"))
        if cap.active != "window":
            pytest.skip(f"Windows Graphics Capture not available here: {cap.note}")
        text = _read(img).lower()
        assert "dawn" in text or "captain" in text, text
        assert "cover" not in text
        assert box["width"] > 200 and box["height"] > 100
    finally:
        cap.close(); cover.close(); lab.close()


def test_keep_on_top_and_find_window():
    from PySide6.QtWidgets import QApplication, QWidget
    from arabize.platform_utils import keep_on_top, window_rect
    app = QApplication.instance() or QApplication([])
    w = QWidget(); w.resize(300, 200); w.show(); app.processEvents()
    assert keep_on_top(int(w.winId()))
    r = window_rect(int(w.winId()))
    assert r and r[2] >= 290 and r[3] >= 190
    w.close()


def test_ocr_on_the_graphics_card():
    from arabize.ocr import PERF_PRESETS, RapidOcr, gpu_available
    from arabize.textproc import group_lines, similarity
    from gameshots import dialogue_scene
    if not gpu_available():
        pytest.skip("onnxruntime-directml not installed")
    import arabize.ocr as ocrmod
    o = RapidOcr(perf={**PERF_PRESETS["balanced"], "gpu": True})
    if not RapidOcr.gpu_active:
        RapidOcr(perf={**PERF_PRESETS["balanced"], "gpu": False})
        pytest.skip(f"DirectML could not start on this machine (CI runners have no GPU): {ocrmod.GPU_ERROR}")
    img, exp = dialogue_scene()
    blocks = group_lines(o.read(img))
    assert max(similarity(b.text, exp["dialogue"]) for b in blocks) > 0.8
    RapidOcr(perf={**PERF_PRESETS["balanced"], "gpu": False})   # back to CPU for the other tests


def test_in_place_cover_is_hidden_from_the_reader():
    """The translation painted over the game text must not be read back, or the English would 'disappear'."""
    import time
    from PySide6.QtWidgets import QApplication
    from arabize.capture import Capturer
    from arabize.overlay import InPlaceOverlay
    app = QApplication.instance() or QApplication([])
    lab, exp = _show_scene(app)
    cap = Capturer("auto")
    img, box = cap.grab(1)
    text0 = _read(img)
    ov = InPlaceOverlay(); ov.configure({"font_size": 26, "bg": "#000000", "box": "card", "rtl": False, "recordable": False}, "cover")
    # cover the whole screen's middle with an opaque plate that says OVERLAYMARKER
    ov.show_items([{"label": "", "src": "x", "tr": "OVERLAYMARKER OVERLAYMARKER", "abs": (200, 200, 1400, 600), "line_h": 60}])
    for _ in range(10):
        app.processEvents(); time.sleep(0.03)
    try:
        assert ov.excluded
        img, box = cap.grab(1)
        text1 = _read(img)
        assert "OVERLAYMARKER" not in text1.upper()
    finally:
        cap.close(); ov.close(); lab.close()
