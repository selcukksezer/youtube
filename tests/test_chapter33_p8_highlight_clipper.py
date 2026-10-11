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
from unittest.mock import patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from routers.clipper_router import router
from routers.video_router import api_clipper_analyze
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
from services.youtube_clipper import YouTubeClipperService
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

    def test_api_clipper_rejects_description_only_highlight_timing(self):
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        with patch(
            "services.youtube_clipper.youtube_clipper.extract_youtube_info",
            return_value={"duration": 120.0, "description": "Video description without timestamps."},
        ), patch(
            "services.youtube_clipper.youtube_clipper.fetch_subtitles_or_transcribe",
            return_value=[],
        ):
            response = client.post("/api/clipper", json={
                "url": "https://youtube.com/watch?v=example",
                "render": False,
            })

        self.assertEqual(response.status_code, 422)
        self.assertIn("zaman", response.json()["detail"].lower())

    def test_video_router_clipper_rejects_description_only_timing(self):
        with patch(
            "services.youtube_clipper.youtube_clipper.extract_youtube_info",
            return_value={"duration": 120.0, "description": "Description has no timing."},
        ), patch(
            "services.youtube_clipper.youtube_clipper.fetch_subtitles_or_transcribe",
            return_value=[],
        ):
            with self.assertRaises(HTTPException) as raised:
                api_clipper_analyze({"url": "https://youtube.com/watch?v=example"})

        self.assertEqual(raised.exception.status_code, 422)

    def test_video_router_clipper_returns_only_transcript_grounded_suggestions(self):
        captions = [
            {
                "start": 10.0,
                "end": 16.0,
                "text": "This real transcript contains enough source words for this selected moment.",
            }
        ]
        suggestions = [
            {
                "title": "Grounded moment",
                "start_time": 0.0,
                "end_time": 30.0,
                "score": 80,
            },
            {
                "title": "Unsupported moment",
                "start_time": 60.0,
                "end_time": 90.0,
                "score": 99,
            },
        ]

        with patch(
            "services.youtube_clipper.youtube_clipper.extract_youtube_info",
            return_value={"duration": 120.0, "description": ""},
        ), patch(
            "services.youtube_clipper.youtube_clipper.fetch_subtitles_or_transcribe",
            return_value=captions,
        ) as transcribe, patch(
            "services.youtube_clipper.youtube_clipper.detect_highlights_with_llm",
            return_value=suggestions,
        ):
            result = api_clipper_analyze({
                "url": "https://youtube.com/watch?v=example",
                "hotwords": "OpenAI GPT-5",
            })

        transcribe.assert_called_once_with(
            "https://youtube.com/watch?v=example",
            "",
            hotwords="OpenAI GPT-5",
        )
        self.assertEqual(
            [item["title"] for item in result["highlights"]],
            ["Grounded moment"],
        )
        self.assertEqual(result["highlights"][0]["transcript_word_count"], 11)

    def test_api_clipper_surfaces_ai_failure_without_fake_highlights(self):
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        with patch(
            "services.youtube_clipper.youtube_clipper.extract_youtube_info",
            return_value={"duration": 120.0, "description": ""},
        ), patch(
            "services.youtube_clipper.youtube_clipper.fetch_subtitles_or_transcribe",
            return_value=[{"start": 1.0, "end": 2.0, "text": "A real transcript."}],
        ), patch(
            "services.youtube_clipper.youtube_clipper.detect_highlights_with_llm",
            side_effect=RuntimeError("provider unavailable"),
        ):
            response = client.post("/api/clipper", json={
                "url": "https://youtube.com/watch?v=example",
                "render": False,
            })

        self.assertEqual(response.status_code, 502)
        self.assertIn("provider unavailable", response.json()["detail"])

    def test_api_clipper_returns_only_transcript_grounded_suggestions(self):
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        captions = [
            {
                "start": 10.0,
                "end": 16.0,
                "text": "This real transcript contains enough source words for this selected moment.",
            }
        ]
        suggestions = [
            {
                "title": "Grounded moment",
                "start_time": 0.0,
                "end_time": 30.0,
                "score": 80,
            },
            {
                "title": "Unsupported moment",
                "start_time": 60.0,
                "end_time": 90.0,
                "score": 99,
            },
        ]

        with patch(
            "services.youtube_clipper.youtube_clipper.extract_youtube_info",
            return_value={"duration": 120.0, "description": ""},
        ), patch(
            "services.youtube_clipper.youtube_clipper.fetch_subtitles_or_transcribe",
            return_value=captions,
        ) as transcribe, patch(
            "services.youtube_clipper.youtube_clipper.detect_highlights_with_llm",
            return_value=suggestions,
        ):
            response = client.post(
                "/api/clipper",
                data={
                    "url": "https://youtube.com/watch?v=example",
                    "render": "false",
                    "hotwords": "OpenAI GPT-5",
                },
                files={"placeholder": ("", b"")},
            )

        self.assertEqual(response.status_code, 200)
        transcribe.assert_called_once_with(
            "https://youtube.com/watch?v=example",
            "",
            hotwords="OpenAI GPT-5",
        )
        highlights = response.json()["highlights"]
        self.assertEqual([item["title"] for item in highlights], ["Grounded moment"])
        self.assertEqual(highlights[0]["transcript_word_count"], 11)
        self.assertIn("real transcript", highlights[0]["transcript_excerpt"])

    def test_api_clipper_analyzes_uploaded_local_video_without_url(self):
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        transcript = [
            {"start": 20.0, "end": 35.0, "text": "A surprising fact changes everything."},
            {"start": 35.0, "end": 55.0, "text": "Here is the evidence and the unexpected result."},
        ]
        suggestion = {
            "title": "The surprising result",
            "start_time": 20.0,
            "end_time": 55.0,
            "score": 88,
        }
        with patch("routers.clipper_router._resolve_source", return_value="local.mp4"), \
             patch("render.pipeline_audit._ffprobe_duration", return_value=90.0), \
             patch(
                 "services.youtube_clipper.youtube_clipper.fetch_subtitles_or_transcribe",
                 return_value=transcript,
             ) as transcribe, \
             patch(
                 "services.youtube_clipper.youtube_clipper.detect_highlights_with_llm",
                 return_value=[suggestion],
             ), \
             patch(
                 "services.youtube_clipper.youtube_clipper.ground_highlights_in_transcript",
                 side_effect=lambda highlights, subs: highlights if subs == transcript else [],
             ):
            response = client.post("/api/clipper", json={
                "source_path": "local.mp4",
                "render": False,
                "num_clips": 1,
                "hotwords": "OpenAI GPT-5",
            })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["highlights_count"], 1)
        self.assertEqual(response.json()["highlights"][0]["title"], "The surprising result")
        transcribe.assert_called_once_with(
            "",
            "local.mp4",
            hotwords="OpenAI GPT-5",
        )

    def test_local_clipper_reports_unreadable_video_duration(self):
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)
        with patch("routers.clipper_router._resolve_source", return_value="local.mp4"), \
             patch("render.pipeline_audit._ffprobe_duration", return_value=-1.0), \
             patch("services.youtube_clipper.youtube_clipper.fetch_subtitles_or_transcribe") as transcribe:
            response = client.post("/api/clipper", json={
                "source_path": "local.mp4",
                "render": False,
            })

        self.assertEqual(response.status_code, 422)
        self.assertIn("süresi okunamadı", response.json()["detail"])
        transcribe.assert_not_called()

    def test_api_clipper_rejects_invalid_transcription_hotwords(self):
        app = FastAPI()
        app.include_router(router)
        client = TestClient(app)

        with patch(
            "services.youtube_clipper.youtube_clipper.extract_youtube_info",
            return_value={"duration": 120.0},
        ), patch(
            "services.youtube_clipper.youtube_clipper.fetch_subtitles_or_transcribe"
        ) as transcribe:
            for hotwords in (["GPT-5"], "x" * 501):
                response = client.post(
                    "/api/clipper",
                    json={
                        "url": "https://youtube.com/watch?v=example",
                        "hotwords": hotwords,
                        "render": False,
                    },
                )
                self.assertEqual(response.status_code, 400)

        transcribe.assert_not_called()


class TestYoutubeTranscriptFallback(unittest.TestCase):
    def test_local_whisper_fallback_groups_timed_words(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            video_path = os.path.join(temp_dir, "local.mp4")
            with open(video_path, "wb") as handle:
                handle.write(b"video")
            service = YouTubeClipperService(download_dir=temp_dir, output_dir=temp_dir)
            fake_youtube = patch(
                "services.youtube_clipper.yt_dlp.YoutubeDL"
            )
            with fake_youtube as youtube_dl, patch(
                "services.youtube_clipper.importlib.util.find_spec",
                return_value=object(),
            ), patch(
                "subtitle_generator._transcribe_whisper_words",
                return_value=[
                    {"text": "Hello", "offset": 0.0, "duration": 0.2},
                    {"text": "world.", "offset": 0.25, "duration": 0.3},
                    {"text": "Another", "offset": 1.0, "duration": 0.2},
                    {"text": "line.", "offset": 1.25, "duration": 0.3},
                ],
            ) as transcribe:
                youtube_dl.return_value.__enter__.return_value.extract_info.return_value = {
                    "id": "no-captions",
                    "language": "en",
                }
                segments = service.fetch_subtitles_or_transcribe(
                    "https://youtube.com/watch?v=example",
                    video_path,
                    hotwords="OpenAI GPT-5",
                )

        self.assertEqual(
            segments,
            [
                {"start": 0.0, "end": 0.55, "text": "Hello world."},
                {"start": 1.0, "end": 1.55, "text": "Another line."},
            ],
        )
        transcribe.assert_called_once_with(
            video_path,
            language="en",
            initial_prompt="OpenAI GPT-5",
        )

    def test_uploaded_local_video_skips_youtube_subtitle_lookup(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            video_path = os.path.join(temp_dir, "local.mp4")
            with open(video_path, "wb") as handle:
                handle.write(b"video")
            service = YouTubeClipperService(download_dir=temp_dir, output_dir=temp_dir)
            with patch(
                "services.youtube_clipper.yt_dlp.YoutubeDL"
            ) as youtube_dl, patch(
                "services.youtube_clipper.importlib.util.find_spec",
                return_value=object(),
            ), patch(
                "subtitle_generator._transcribe_whisper_words",
                return_value=[
                    {"text": "Local", "offset": 0.0, "duration": 0.3},
                    {"text": "transcript.", "offset": 0.35, "duration": 0.45},
                ],
            ) as transcribe:
                segments = service.fetch_subtitles_or_transcribe("", video_path)

        self.assertEqual(
            segments,
            [{"start": 0.0, "end": 0.8, "text": "Local transcript."}],
        )
        youtube_dl.assert_not_called()
        transcribe.assert_called_once_with(video_path, language="tr")

    def test_uploaded_local_video_reports_missing_optional_whisper(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            video_path = os.path.join(temp_dir, "local.mp4")
            with open(video_path, "wb") as handle:
                handle.write(b"video")
            service = YouTubeClipperService(download_dir=temp_dir, output_dir=temp_dir)
            with patch(
                "services.youtube_clipper.importlib.util.find_spec",
                return_value=None,
            ):
                with self.assertRaisesRegex(RuntimeError, "faster-whisper"):
                    service.fetch_subtitles_or_transcribe("", video_path)

    def test_whisper_transcriber_uses_initial_prompt(self):
        import sys
        from types import ModuleType, SimpleNamespace
        from unittest.mock import MagicMock

        import subtitle_generator

        model = MagicMock()
        model.transcribe.return_value = (
            [SimpleNamespace(words=[SimpleNamespace(word="OpenAI", start=0.0, end=0.4)])],
            None,
        )
        faster_whisper = ModuleType("faster_whisper")
        setattr(faster_whisper, "WhisperModel", MagicMock(return_value=model))
        environment = {
            "WHISPER_MODEL": "small",
            "WHISPER_DEVICE": "cpu",
            "WHISPER_COMPUTE": "int8",
        }
        with patch.dict(sys.modules, {"faster_whisper": faster_whisper}), patch.dict(
            os.environ, environment
        ), patch.object(subtitle_generator, "_WHISPER_MODEL", model), patch.object(
            subtitle_generator, "_WHISPER_MODEL_KEY", ("small", "cpu", "int8")
        ):
            subtitle_generator._transcribe_whisper_words(
                "voice.wav",
                language="en",
                initial_prompt="OpenAI GPT-5",
            )

        self.assertEqual(model.transcribe.call_args.kwargs["initial_prompt"], "OpenAI GPT-5")

    def test_missing_optional_whisper_does_not_download_a_video(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            service = YouTubeClipperService(download_dir=temp_dir, output_dir=temp_dir)
            with patch(
                "services.youtube_clipper.yt_dlp.YoutubeDL"
            ) as youtube_dl, patch(
                "services.youtube_clipper.importlib.util.find_spec",
                return_value=None,
            ), patch.object(service, "download_video") as download:
                youtube_dl.return_value.__enter__.return_value.extract_info.return_value = {
                    "id": "no-captions",
                }
                segments = service.fetch_subtitles_or_transcribe(
                    "https://youtube.com/watch?v=example",
                    "",
                )

        self.assertEqual(segments, [])
        download.assert_not_called()

    def test_url_whisper_fallback_downloads_only_when_model_is_available(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            video_path = os.path.join(temp_dir, "source.mp4")
            with open(video_path, "wb") as handle:
                handle.write(b"video")
            service = YouTubeClipperService(download_dir=temp_dir, output_dir=temp_dir)
            with patch(
                "services.youtube_clipper.yt_dlp.YoutubeDL"
            ) as youtube_dl, patch(
                "services.youtube_clipper.importlib.util.find_spec",
                return_value=object(),
            ), patch.object(service, "download_video", return_value=video_path) as download, patch(
                "subtitle_generator._transcribe_whisper_words",
                return_value=[{"text": "Grounded.", "offset": 2.0, "duration": 0.5}],
            ):
                youtube_dl.return_value.__enter__.return_value.extract_info.return_value = {
                    "id": "no-captions",
                }
                segments = service.fetch_subtitles_or_transcribe(
                    "https://youtube.com/watch?v=example",
                    "",
                )

        self.assertEqual(segments, [{"start": 2.0, "end": 2.5, "text": "Grounded."}])
        download.assert_called_once_with("https://youtube.com/watch?v=example")


if __name__ == "__main__":
    unittest.main()
