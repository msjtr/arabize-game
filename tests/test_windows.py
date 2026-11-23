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
    ov.configure({"font_size": 26}, app.primaryScreen())
    ov.show_items([{"label": "", "tr": "اختبار", "src": ""}])
    app.processEvents()
    assert ov.excluded  # SetWindowDisplayAffinity(WDA_EXCLUDEFROMCAPTURE) succeeded
    ov.close()
