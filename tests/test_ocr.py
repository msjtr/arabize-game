import time

import pytest

from arabize.ocr import RapidOcr
from arabize.textproc import group_lines, similarity
from gameshots import choices_scene, dialogue_scene, small_subtitle


@pytest.fixture(scope="module")
def ocr():
    return RapidOcr(min_conf=0.55)


def best(blocks, want):
    return max((similarity(b.text, want) for b in blocks), default=0)


def test_dialogue_quest_and_speaker(ocr):
    img, exp = dialogue_scene()
    t = time.perf_counter(); lines = ocr.read(img); ms = (time.perf_counter() - t) * 1000
    blocks = group_lines(lines)
    print(f"\nfull-screen OCR {ms:.0f} ms, {len(lines)} lines:", [b.text for b in blocks])
    print("labels:", [(b.label, b.text) for b in blocks])
    assert best(blocks, exp["dialogue"]) > 0.9
    assert best(blocks, exp["quest"]) > 0.9
    assert any(similarity(b.label, exp["speaker"]) > 0.9 for b in blocks)


def test_choices_stay_separate(ocr):
    img, exp = choices_scene()
    blocks = group_lines(ocr.read(img))
    for c in exp["choices"]:
        assert best(blocks, c) > 0.9, (c, [b.text for b in blocks])


def test_small_subtitle_region(ocr):
    img, exp = small_subtitle()
    region = img[950:1040, 500:1500]           # user-selected subtitle strip
    t = time.perf_counter(); blocks = group_lines(ocr.read(region)); ms = (time.perf_counter() - t) * 1000
    print(f"\nregion OCR {ms:.0f} ms:", [b.text for b in blocks])
    assert best(blocks, exp["subtitle"]) > 0.9
    assert ms < 1500
