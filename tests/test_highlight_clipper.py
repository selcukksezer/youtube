"""P8 clipper: overlap drop, word edge, subtitle gaps, 9:16 filter."""
import inspect
import os
import subprocess
import tempfile

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers.clipper_router import router
from services.highlight_clipper import (
    cut_ranges_vertical,
    inside_word,
    kept_timeline,
    select_highlights,
    snap_span,
    vertical_vf,
)
import server_core.render_worker as render_worker


def test_ten_minute_overlap_drops_lower_score():
    raw = [
        {"title": "A", "start_time": 100, "end_time": 160, "score": 90},
        {"title": "B", "start_time": 120, "end_time": 170, "score": 40},
    ]
    kept = select_highlights(raw, duration=600, num_clips=5)
    titles = [item["title"] for item in kept]
    assert titles == ["A"]
    assert kept[0]["end_time"] <= 600


def test_snap_does_not_start_inside_a_word():
    words = [
        {"w": "merhaba", "s": 10.0, "e": 10.5},
        {"w": "dunya", "s": 10.6, "e": 11.0},
    ]
    start, end = snap_span(10.2, 10.8, words, video_duration=600, min_duration=0.2)
    assert start <= 10.0
    assert end >= 11.0
    assert inside_word(start, words) is False
    assert inside_word(end, words) is False


def test_offset_is_pulled_out_of_a_word():
    words = [{"w": "kelime", "s": 20.0, "e": 20.8}]
    start, end = snap_span(20.0, 20.8, words, 600, start_ost_ms=500, end_ost_ms=-600, min_duration=0.2)
    assert inside_word(start, words) is False
    assert inside_word(end, words) is False


def test_deleted_subtitle_range_is_removed():
    segments = [
        {"id": "1", "start": 0, "end": 2},
        {"id": "2", "start": 2, "end": 5},
        {"id": "3", "start": 5, "end": 8},
    ]
    assert kept_timeline(segments, ["2"]) == [(0.0, 2.0), (5.0, 8.0)]


def test_vertical_filter_is_9_16():
    vf = vertical_vf(1920, 1080, crop_x=100)
    assert "crop=1080:1920:" in vf


def test_num_clips_caps_at_five():
    raw = [
        {"title": str(i), "start_time": i * 80, "end_time": i * 80 + 30, "score": 10 + i}
        for i in range(8)
    ]
    assert len(select_highlights(raw, duration=700, num_clips=9)) == 5


def test_narration_render_does_not_call_clipper():
    source = inspect.getsource(render_worker)
    assert "highlight_clipper" not in source
    assert "/api/clipper" not in source


def test_json_route_drops_overlap_without_render():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    response = client.post("/api/clipper", json={
        "render": False,
        "duration": 600,
        "num_clips": 3,
        "highlights": [
            {"title": "A", "start_time": 100, "end_time": 160, "score": 90},
            {"title": "B", "start_time": 120, "end_time": 170, "score": 40},
        ],
    })
    assert response.status_code == 200
    body = response.json()
    assert [item["title"] for item in body["highlights"]] == ["A"]


def test_cut_writes_vertical_frame():
    ffmpeg = "ffmpeg"
    try:
        import imageio_ffmpeg
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    with tempfile.TemporaryDirectory() as tmp:
        source = os.path.join(tmp, "wide.mp4")
        made = subprocess.run(
            [ffmpeg, "-y", "-f", "lavfi", "-i", "color=c=blue:s=320x180:d=1", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", source],
            capture_output=True,
            text=True,
        )
        if made.returncode != 0 or not os.path.isfile(source):
            pytest.skip(made.stderr[-200:] if made.stderr else "ffmpeg lavfi yok")
        out = os.path.join(tmp, "short.mp4")
        cut_ranges_vertical(source, [(0.0, 0.8)], out)
        probe = subprocess.run(
            [ffmpeg, "-hide_banner", "-i", out],
            capture_output=True,
            text=True,
        )
        assert "1080x1920" in (probe.stderr or "")
