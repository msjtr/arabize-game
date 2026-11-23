"""Templates, fonts, layers and effects."""
import json

import pytest
from PySide6.QtWidgets import QApplication

from arabize import styles
from arabize.textproc import classify


@pytest.fixture(scope="module")
def app():
    a = QApplication.instance() or QApplication([])
    from arabize.ui import theme
    theme.load_fonts()
    return a


# ------------------------------------------------------------------ fonts
def test_bundled_fonts_cover_arabic(app):
    from PySide6.QtGui import QFontDatabase, QFontInfo, QFont
    fams = set(QFontDatabase.families())
    for fam in styles.FONT_FAMILIES:
        assert fam in fams, f"{fam} is not bundled"
        assert QFontDatabase.WritingSystem.Arabic in QFontDatabase.writingSystems(fam), fam
        assert QFontInfo(QFont(fam)).family() == fam


def test_old_and_unknown_fonts_are_migrated(tmp_path):
    from arabize.config import Settings
    old = {"profiles": {"default": {"display": {"screen": {"font_family": "Arial", "fade_ms": 0, "font_size": 33},
                                                "vr": {"font_family": "Noto Sans Arabic"}}}}}
    p = tmp_path / "settings.json"; p.write_text(json.dumps(old), encoding="utf-8")
    s = Settings(p)
    scr = s.profile["display"]["screen"]
    assert scr["font_family"] == styles.DEFAULT_FONT and s.profile["display"]["vr"]["font_family"] == styles.DEFAULT_FONT
    assert scr["font_size"] == 33                      # the user's own choice is kept
    assert scr["fx_in"] == "none" and "fade_ms" not in scr
    assert scr["template"] == "custom" and scr["layers"]["quest"]["anchor"] == "top-right"


# ------------------------------------------------------------------ templates
def test_every_template_is_complete_and_valid():
    for tid, t in styles.TEMPLATES.items():
        assert t["name"] and t["desc"]
        assert set(t["look"]) == set(styles.LOOK_KEYS), tid
        assert styles.sanitize_look(t["look"]) == t["look"], tid
        assert t["look"]["font_family"] in styles.FONT_FAMILIES


def test_controller_templates(env_ctrl):
    c = env_ctrl
    c.settings.update_profile("display.screen.custom_pos", [10, 10])
    assert c.apply_template("tv")
    scr = c.prof["display"]["screen"]
    assert scr["template"] == "tv" and scr["font_size"] == 42 and scr["box"] == "bar" and scr["custom_pos"] is None
    assert c.prof["display"]["vr"]["font_family"] == "Readex Pro"
    assert c.prof["capture"]["full"] is True            # a template never touches capture settings
    c.settings.update_profile("display.screen.color", "#123456")
    tid = c.save_template("قالبي الأحمر")
    assert c.templates()[tid]["look"]["color"] == "#123456" and not c.templates()[tid]["builtin"]
    dump = c.export_templates()
    assert c.delete_template(tid) and tid not in c.templates()
    assert c.import_templates(dump) == 1
    assert not c.apply_template("does-not-exist")


def test_import_rejects_bad_values():
    bad = {"templates": {"x": {"name": "شرير", "look": {"color": "red; drop", "font_size": 9999, "box": "explode",
                                                       "font_family": "Comic Sans", "fx_in": "slide", "evil": 1}},
                         "y": "not a template"}}
    out = styles.import_templates(json.dumps(bad))
    (tid, t), = out.items()
    assert tid.startswith("my-")
    assert t["look"] == {"font_size": 90, "font_family": styles.DEFAULT_FONT, "fx_in": "slide"}
    with pytest.raises(ValueError):
        styles.import_templates("{not json")


# ------------------------------------------------------------------ layers
def test_classify_dialogue_quest_choices():
    items = [{"label": "QUEST", "src": "Reach the old lighthouse", "box": (1300, 60, 280, 60)},
             {"label": "Captain Mara", "src": "We leave at dawn. Bring your sword.", "box": (300, 700, 1000, 80)},
             {"label": "", "src": "I'm in.", "box": (1200, 400, 200, 30)},
             {"label": "", "src": "Not today.", "box": (1200, 440, 200, 30)},
             {"label": "", "src": "Tell me more about the ship.", "box": (1200, 480, 300, 30)},
             {"label": "", "src": "Press E to interact", "box": (700, 990, 200, 30)}]
    assert classify(items) == ["quest", "dialogue", "choices", "choices", "choices", "other"]
    # numbered menu and a header-only quest line
    assert classify([{"label": "", "src": "1. Attack"}, {"label": "", "src": "2. Run away"}]) == ["choices", "choices"]
    assert classify([{"label": "", "src": "Objective", "box": (10, 10, 90, 20)},
                     {"label": "", "src": "Find the key before sunset", "box": (10, 34, 260, 20)}]) == ["quest", "quest"]
    # narration without a speaker is still the dialogue layer
    assert classify([{"label": "", "src": "The storm swallowed the village before anyone could warn them."}]) == ["dialogue"]


def test_layers_distribute_and_switch_off(app):
    from arabize.overlay import OverlayLayers
    from arabize.config import DEFAULT_PROFILE
    from PySide6.QtGui import QGuiApplication
    ov = OverlayLayers()
    st = dict(DEFAULT_PROFILE["display"]["screen"])
    ov.configure(st, QGuiApplication.primaryScreen())
    parts = ov.distribute(styles.SAMPLE_ITEMS)
    assert [len(parts[k]) for k in ("dialogue", "quest", "choices", "other")] == [1, 1, 2, 0]
    st["layers"] = {**st["layers"], "choices": {**st["layers"]["choices"], "on": False}}
    ov.configure(st, QGuiApplication.primaryScreen())
    assert len(ov.distribute(styles.SAMPLE_ITEMS)["dialogue"]) == 3
    ov.configure({**st, "layers_on": False}, QGuiApplication.primaryScreen())
    assert len(ov.distribute(styles.SAMPLE_ITEMS)["dialogue"]) == 4
    # each layer is placed where its anchor says
    ov.configure(dict(DEFAULT_PROFILE["display"]["screen"]), QGuiApplication.primaryScreen())
    ov.show_items(styles.SAMPLE_ITEMS)
    geo = QGuiApplication.primaryScreen().geometry()
    q, d, ch = ov.layers["quest"].geometry(), ov.layers["dialogue"].geometry(), ov.layers["choices"].geometry()
    assert q.center().y() < geo.center().y() < d.center().y()        # quest on top, dialogue at the bottom
    assert q.center().x() > geo.center().x() and ch.center().x() > geo.center().x()  # both on the right
    assert not ov.layers["other"].isVisible()
    ov.clear(animate=False)
    assert not ov.isVisible()


def test_anchor_positions():
    from PySide6.QtCore import QRect
    from arabize.overlay import anchor_xy
    g = QRect(0, 0, 1000, 500)
    assert anchor_xy(g, 100, 50, "bottom", 10) == (450, 440)
    assert anchor_xy(g, 100, 50, "top-right", 10) == (890, 10)
    assert anchor_xy(g, 100, 50, "left", 10) == (10, 225)
    assert anchor_xy(g, 100, 50, "center", 10) == (450, 225)


# ------------------------------------------------------------------ rendering & effects
def _opaque(img):
    return sum(1 for x in range(0, img.width(), 7) for y in range(0, img.height(), 5) if img.pixelColor(x, y).alpha() > 40)


def test_every_template_and_text_effect_draws(app):
    from arabize import render
    for tid, t in styles.TEMPLATES.items():
        for kind in ("dialogue", "quest", "choices"):
            st = {**t["look"], "rtl": True}
            img = render.render_image([{**styles.SAMPLE_ITEMS[1], "kind": kind}], st, 900)
            assert img.height() > 40 and _opaque(img) > 20, (tid, kind)
    st = {**styles.TEMPLATES["cinema"]["look"], "rtl": True}
    full = _opaque(render.render_image(styles.SAMPLE_ITEMS[1:2], st, 900))
    half = _opaque(render.render_image(styles.SAMPLE_ITEMS[1:2], st, 900, reveal=0.4))
    assert 0 < half < full                              # typewriter shows part of the text


def test_effect_states():
    from arabize.overlay import effect_state
    base = {"font_size": 30}
    assert effect_state({**base, "fx_in": "slide"}, 0)["dy"] > 0 and effect_state({**base, "fx_in": "slide"}, 1)["dy"] == 0
    assert effect_state({**base, "fx_in": "zoom"}, 0)["scale"] < 1
    assert effect_state({**base, "fx_in": "type"}, 0.5)["reveal"] == 0.5
    assert effect_state({**base, "fx_in": "glow"}, 0)["glow"] > 0
    assert effect_state({**base, "fx_out": "fade"}, 0.3, leaving=True)["alpha"] == pytest.approx(0.3)


def test_overlay_plays_entrance_and_exit(app):
    import time
    from PySide6.QtGui import QGuiApplication
    from arabize.overlay import SubtitleOverlay
    from arabize.config import DEFAULT_PROFILE
    ov = SubtitleOverlay("dialogue")
    ov.configure({**DEFAULT_PROFILE["display"]["screen"], "fx_in": "slide", "fx_out": "fade", "fx_ms": 200},
                 QGuiApplication.primaryScreen())
    ov.show_items(styles.SAMPLE_ITEMS[1:2])
    assert ov._t < 0.5
    end = time.time() + 0.6
    while time.time() < end:
        app.processEvents()
    assert ov._t == 1.0 and ov.isVisible()
    ov.clear()
    end = time.time() + 0.6
    while time.time() < end:
        app.processEvents()
    assert not ov.isVisible() and not ov.items


def test_icons_3d_render(app):
    from arabize.ui import icons
    from arabize import icons3d
    for name in icons3d.GLYPHS:
        pm = icons.tile(name, "gold", 32)
        img = pm.toImage()
        assert img.pixelColor(img.width() // 2, img.height() // 2).alpha() == 255, name
    assert icons3d.tile_svg("vr", "violet", uid="a") != icons3d.tile_svg("vr", "violet", uid="b")
