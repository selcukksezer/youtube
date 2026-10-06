"""
Unit and integration tests for Plan Item P8: Uzun videodan Shorts kesici (Highlight Clipper).
References:
- anil_matcha_shorts_generator: dedupe_highlights, time clamping.
- FunClip: video_clip start_ost/end_ost offsets in milliseconds.
- autoclip: edit_video_by_subtitle_deletion subtitle removal and timeline merge.
- openshorts: dedupe_overlapping with ratio=0.5 against shorter clip.
- Chapter 33 P1: face_cover_crop_x integration in vertical_vf.
"""
import inspect
import os
import subprocess
import tempfile
import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers.clipper_router import router
from services.highlight_clipper import (
    clamp_span,
    cut_ranges_vertical,
    dedupe_overlapping,
    inside_word,
    kept_timeline,
    normalize_words,
    select_highlights,
    snap_span,
    vertical_vf,
)
import server_core.render_worker as render_worker


class TestHighlightClipperLogic(unittest.TestCase):
    def test_ten_minute_overlap_drops_lower_scoring_clip(self):
        # 10-minute video (600s), two overlapping suggestions (100-160 and 120-170)
        # Higher score (90) must be kept, lower score (40) must be dropped
        candidates = [
            {"title": "High Virality", "start_time": 100.0, "end_time": 160.0, "score": 90},
            {"title": "Low Virality", "start_time": 120.0, "end_time": 170.0, "score": 40},
        ]
        kept = select_highlights(candidates, duration=600.0, num_clips=5)
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]["title"], "High Virality")
        self.assertLessEqual(kept[0]["end_time"], 600.0)

    def test_openshorts_shorter_span_dedupe_prevents_long_window_hiding_duplicate(self):
        # Long window (100-300s, score 50) and short duplicate inside (120-160s, score 95)
        # Under anil's old rule (checking 0.5 * candidate only), the short clip might not trigger 50% of the 200s window.
        # Under openshorts shorter-span rule, the overlap is 100% of the short span, so duplicate is caught.
        candidates = [
            {"title": "Long Window", "start_time": 100.0, "end_time": 300.0, "score": 50},
            {"title": "Short Peak", "start_time": 120.0, "end_time": 160.0, "score": 95},
        ]
        kept = select_highlights(candidates, duration=600.0, num_clips=5)
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]["title"], "Short Peak")

    def test_snap_span_does_not_start_inside_a_word(self):
        words = [
            {"w": "harika", "s": 15.0, "e": 15.6},
            {"w": "felsefe", "s": 15.7, "e": 16.4},
        ]
        # Start requested at 15.3 (inside "harika") -> must snap to lead before 15.0
        start, end = snap_span(15.3, 16.0, words, video_duration=300.0, min_duration=0.2)
        self.assertLessEqual(start, 15.0)
        self.assertGreaterEqual(end, 16.4)
        self.assertFalse(inside_word(start, words))
        self.assertFalse(inside_word(end, words))

    def test_funclip_offsets_pulled_out_of_word_interiors(self):
        words = [{"w": "kelime", "s": 30.0, "e": 31.0}]
        # Shift with millisecond offsets landing inside word boundary
        start, end = snap_span(
            30.0, 31.0, words, video_duration=300.0,
            start_ost_ms=400, end_ost_ms=-500, min_duration=0.2,
        )
        self.assertFalse(inside_word(start, words))
        self.assertFalse(inside_word(end, words))

    def test_autoclip_subtitle_deletion_merges_surviving_ranges(self):
        segments = [
            {"id": "s1", "start": 0.0, "end": 4.0},
            {"id": "s2", "start": 4.0, "end": 7.0},
            {"id": "s3", "start": 7.0, "end": 12.0},
            {"id": "s4", "start": 15.0, "end": 20.0},
        ]
        # Deleting s2 removes 4-7, leaving 0-4 and 7-12, 15-20
        # Touching survivor ranges (0-4 and 7-12 are separated; if touching they merge)
        timeline = kept_timeline(segments, deleted_ids=["s2"])
        self.assertEqual(timeline, [(0.0, 4.0), (7.0, 12.0), (15.0, 20.0)])

    def test_clip_capping_between_one_and_five(self):
        raw = [
            {"title": f"clip_{i}", "start_time": i * 50.0, "end_time": (i + 1) * 50.0, "score": 20 + i}
            for i in range(10)
        ]
        # Requests 8 clips -> must be capped at 5
        self.assertEqual(len(select_highlights(raw, duration=600.0, num_clips=8)), 5)
        # Requests 0 clips -> clamped to at least 1
        self.assertEqual(len(select_highlights(raw, duration=600.0, num_clips=0)), 1)

    def test_vertical_vf_is_strict_9_16(self):
        vf = vertical_vf(1920, 1080, crop_x=120)
        self.assertIn("crop=1080:1920:", vf)
        self.assertIn("setsar=1", vf)


class TestClipperIsolationAndApi(unittest.TestCase):
    def test_narration_render_does_not_invoke_clipper(self):
        source = inspect.getsource(render_worker)
        self.assertNotIn("highlight_clipper", source)
        self.assertNotIn("/api/clipper", source)

    def test_api_clipper_suggestion_endpoint_without_render(self):
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        res = client.post("/api/clipper", json={
            "render": False,
            "duration": 600.0,
            "num_clips": 3,
            "highlights": [
                {"title": "High Virality", "start_time": 100.0, "end_time": 160.0, "score": 90},
                {"title": "Low Virality", "start_time": 120.0, "end_time": 170.0, "score": 40},
            ],
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["highlights_count"], 1)
        self.assertEqual(data["highlights"][0]["title"], "High Virality")


if __name__ == "__main__":
    unittest.main()
