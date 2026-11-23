import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_vr_texture_renders_arabic(app):
    from arabize import render
    from arabize.ui import theme
    theme.load_fonts()
    img = render.render_image([{"label": "x", "label_tr": "القائدة مارا", "tr": "سننطلق عند الفجر. أحضر سيفك."}],
                              {"font_size": 44, "bg_opacity": 80, "font_family": "IBM Plex Sans Arabic"}, 1400)
    assert img.width() == 1400 and img.height() > 80
    # the panel is not empty: some opaque pixels exist
    assert any(img.pixelColor(x, img.height() // 2).alpha() > 0 for x in range(0, 1400, 20))
