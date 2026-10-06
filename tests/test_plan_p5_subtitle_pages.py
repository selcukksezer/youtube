"""P5 acceptance: preset pages, isolated word effects, and render time bounds."""
import re
from pathlib import Path

import pytest

from subtitle_generator import (
    SUBTITLE_PRESETS,
    create_karaoke_subtitles,
    hex_to_ass_color,
    merge_studio_subtitle_opts,
)


def spoken_events(path):
    return [
        line.split(",", 9)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.startswith("Dialogue: 0,")
    ]


def seconds(value):
    hours, minutes, secs = value.split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(secs)


@pytest.mark.parametrize("preset", SUBTITLE_PRESETS)
def test_selected_preset_keeps_four_word_pages_after_craft(tmp_path, preset):
    words = "Bir, iki üç dört beş altı yedi sekiz dokuz".split()
    timings = [
        {"text": word, "offset": i * 0.4, "duration": 0.4}
        for i, word in enumerate(words)
    ]
    opts = merge_studio_subtitle_opts(
        preset, font_size=54, y_position=0.8,
        craft_opts={"max_words_per_line": 3, "max_words_per_frame": 3},
    )
    path = tmp_path / "pages.ass"
    create_karaoke_subtitles(timings, path, style_opts=opts)
    events = spoken_events(path)
    assert len(events) == len(words)
    expected = [words[:4]] * 4 + [words[4:8]] * 4 + [words[8:]]
    for event, page in zip(events, expected):
        plain = re.sub(r"{[^}]*}", "", event[9])
        text = " ".join(page)
        assert plain == (text.upper() if opts["uppercase"] else text)
        active_color = r"\c" + hex_to_ass_color(opts["highlight_color"])
        assert event[9].count(active_color) == 1
    assert opts["font_size"] == 54
    assert opts["y_position"] == 0.8


def test_glow_bounce_and_bold_reset_before_next_inactive_word(tmp_path):
    path = tmp_path / "reset.ass"
    timings = [
        {"text": word, "offset": i * 0.4, "duration": 0.4}
        for i, word in enumerate(["önce", "şimdi", "sonra", "biter"])
    ]
    create_karaoke_subtitles(timings, path, style_opts=SUBTITLE_PRESETS["capcut_yellow"])
    first = spoken_events(path)[0][9]
    assert r"\blur3" in first
    assert r"\t(0,70,\fscx115\fscy115)" in first
    closing = first.split("önce".upper(), 1)[1].split(" " + "şimdi".upper(), 1)[0]
    assert r"\r" in closing, "ASS transforms and glow must not leak to inactive words"
    assert r"\b0" not in closing, "Inactive words must retain the preset's bold setting"


def test_fast_words_do_not_overlap_or_overrun_video(tmp_path):
    path = tmp_path / "fast.ass"
    timings = [
        {"text": word, "offset": i * 0.05, "duration": 0.05}
        for i, word in enumerate(["bir", "iki", "üç", "dört", "beş"])
    ]
    create_karaoke_subtitles(
        timings, path, max_dur=0.23, style_opts=SUBTITLE_PRESETS["capcut_yellow"],
    )
    events = spoken_events(path)
    assert len(events) == 5
    for i, event in enumerate(events):
        start, end = seconds(event[1]), seconds(event[2])
        assert start < end <= 0.23
        if i + 1 < len(events):
            assert end <= seconds(events[i + 1][1]), "Only one word may be active at a time"


def test_long_pause_starts_a_new_page(tmp_path):
    path = tmp_path / "pause.ass"
    timings = [
        {"text": "önce", "offset": 0.0, "duration": 0.3},
        {"text": "sonra", "offset": 3.0, "duration": 0.3},
    ]
    create_karaoke_subtitles(timings, path, style_opts=SUBTITLE_PRESETS["capcut_yellow"])
    events = spoken_events(path)
    assert "SONRA" not in events[0][9]
    assert "ÖNCE" not in events[1][9]
    assert seconds(events[0][2]) < 1.0


def test_studio_exposes_all_presets_and_four_word_preview():
    root = Path(__file__).resolve().parents[1]
    html = (root / "static/index.html").read_text(encoding="utf-8")
    dropdown = re.search(r"<select id=.select-subtitle-preset.[^>]*>(.*?)</select>", html, re.S)
    assert dropdown is not None
    options = re.findall(r"<option value=.([^>]+?).>", dropdown.group(1))
    assert len(options) == len(SUBTITLE_PRESETS) == 16
    assert set(options) == set(SUBTITLE_PRESETS)

    stage = re.search(r"<div class=.subtitle-stage. id=.sub-stage.>(.*?)</div>", html, re.S)
    assert stage is not None
    words = re.findall(r"<span class=.([^>]+?).>([^<]+)</span>", stage.group(1))
    assert len(words) == 4
    assert sum("active-word" in classes for classes, _ in words) == 1
    assert all(len(word.split()) == 1 for _, word in words)

    monitor = (root / "static/js/render-monitor.js").read_text(encoding="utf-8")
    assert "subtitle_preset: selectSubPreset.value" in monitor
    assert "subtitle_font_size: parseInt(subRangeSize" in monitor
    assert "subtitle_y_position: parseFloat(subRangeY" in monitor
