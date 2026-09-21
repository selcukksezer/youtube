"""
Unit tests for Section 7 infrastructure items 426-440 (batch 26 audit).
Excluded: #436, #440-441 (manual upload / OAuth out of scope).
"""
import inspect
import os
import tempfile
import unittest
from unittest.mock import patch

import config
from api_models import validate_generated_plan_errors
from effects.pipeline import scramble_mp4_hash
from notifications import notify_render_error
from quota_manager import QuotaTracker
from subtitle_generator import SUBTITLE_PRESETS, create_karaoke_subtitles
from system_resilience import (
    clean_ai_system_preamble,
    get_ffmpeg_loglevel,
    smart_split_narration_for_shorts,
)
from voice.audio_dsp import normalize_ebu_r128


class TestSection7Items426440(unittest.TestCase):
    def test_excluded_upload_items_not_in_batch(self):
        excluded = {436, 440, 441}
        batch = set(range(426, 441)) - excluded
        self.assertEqual(batch, set(range(426, 436)) | {437, 438, 439})

    def test_item_426_notify_render_error(self):
        src = inspect.getsource(notify_render_error)
        self.assertIn("send_telegram_message", src)
        self.assertIn("send_discord_notification", src)
        worker_src = inspect.getsource(__import__("server_core.render_worker", fromlist=["process_video_task"]))
        self.assertIn("notify_render_error", worker_src)

    def test_item_427_ffmpeg_cancel_terminate(self):
        from render import ffmpeg_graph

        src = inspect.getsource(ffmpeg_graph.render_with_ffmpeg_graph)
        self.assertIn("proc.terminate()", src)
        from routers import video_router

        routes = [getattr(r, "path", "") for r in video_router.routes]
        self.assertIn("/api/video/cancel", routes)

    def test_item_428_clean_ai_system_preamble(self):
        raw = "İşte hazırladığım senaryo:\n\nMarcus Aurelius bilge bir imparatordur."
        cleaned = clean_ai_system_preamble(raw)
        self.assertEqual(cleaned, "Marcus Aurelius bilge bir imparatordur.")

    def test_item_429_scramble_mp4_hash(self):
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"fake-mp4-content")
            path = f.name
        try:
            size_before = os.path.getsize(path)
            self.assertTrue(scramble_mp4_hash(path))
            self.assertGreater(os.path.getsize(path), size_before)
        finally:
            os.remove(path)

    def test_item_430_smart_split_narration(self):
        long_text = "Marcus Aurelius bilge bir imparatordur. " * 40
        shortened, was_split = smart_split_narration_for_shorts(long_text, max_words=50)
        self.assertTrue(was_split)
        self.assertLessEqual(len(shortened.split()), 55)

    def test_item_431_pydantic_scene_schema(self):
        good = {
            "scenes": [
                {
                    "narration": "Bu tam bir cumle, on kelimelik siniri asar ve yeterli icerik tasir.",  # >= MIN_WORDS_PER_SCENE (10)
                    "duration": 3.0,
                    "search_queries": ["marble bust stoic"],
                }
            ]
        }
        self.assertEqual(validate_generated_plan_errors(good), [])
        bad = {"scenes": [{"search_queries": ["city night"]}]}
        self.assertTrue(validate_generated_plan_errors(bad))

    def test_item_432_bgm_cache_stub(self):
        import bgm_manager

        src = inspect.getsource(bgm_manager)
        self.assertIn("_BGM_RAM_CACHE", src)
        self.assertIn("cache_bgm_file", src)
        self.assertIn("get_cached_bgm_path", src)

    def test_item_433_subtitle_style_compiler(self):
        self.assertGreaterEqual(len(SUBTITLE_PRESETS), 3)
        src = inspect.getsource(create_karaoke_subtitles)
        self.assertIn("ass_header", src)
        self.assertIn("[V4+ Styles]", src)

    def test_item_434_token_quota_tracker(self):
        tracker = QuotaTracker()
        tracker.token_totals = {}
        tracker.record_token_usage("Gemini", prompt_tokens=120, completion_tokens=80)
        totals = tracker.token_totals.get("Gemini", {})
        self.assertEqual(totals.get("prompt"), 120)
        self.assertEqual(totals.get("completion"), 80)
        self.assertEqual(totals.get("total"), 200)
        src = inspect.getsource(QuotaTracker.record_token_usage)
        self.assertIn("token_totals", src)

    def test_item_435_channel_output_isolation(self):
        paths = config.channel_paths("Test Kanal TR")
        self.assertIn("output_dir", paths)
        self.assertIn("channels", paths["output_dir"])
        self.assertEqual(config.get_channel_output_dir("Test Kanal TR"), paths["output_dir"])

    def test_item_437_ffmpeg_loglevel(self):
        with patch.dict(os.environ, {"FFMPEG_DEBUG": "false"}, clear=False):
            self.assertEqual(get_ffmpeg_loglevel(), "error")
        with patch.dict(os.environ, {"FFMPEG_DEBUG": "true"}, clear=False):
            self.assertEqual(get_ffmpeg_loglevel(), "warning")

    def test_item_438_ebu_r128_normalizer(self):
        src = inspect.getsource(normalize_ebu_r128)
        self.assertIn("-14", src)
        self.assertIn("loudnorm", src)

    def test_item_439_encrypted_db_backup_present(self):
        import database

        self.assertTrue(hasattr(database, "encrypted_db_backup"))
        src = inspect.getsource(database.encrypted_db_backup).lower()
        self.assertIn("pbkdf2", src)
        self.assertIn("encrypted", src)


if __name__ == "__main__":
    unittest.main()
