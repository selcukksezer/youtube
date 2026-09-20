"""Render worker clip contract tests (P0-03)."""
import asyncio
import os
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from director.quality_gate import (
    clip_coverage_report,
    clip_uniqueness_report,
    format_duplicate_clips_error,
    format_missing_clips_error,
)
from render.ffmpeg_graph import render_with_ffmpeg_graph
from server_core.render_worker import (
    _fetch_scenes_parallel,
    _fetch_single_scene_visual,
    _gemini_image_circuit_open,
    _veo_circuit_open,
    _veo_render_allowed,
    _sweep_render_temp_files,
)
from system_resilience import verify_stock_video_integrity
from video_fetcher import fetch_scene_clip, reset_session_source_counts


class TestMultiSourceFetch(unittest.TestCase):
    @patch("system_resilience.verify_stock_video_integrity", return_value={"valid": True})
    @patch("video_fetcher.search_and_download")
    def test_fetch_scene_clip_retries_second_provider(self, mock_search, _mock_ffprobe):
        mock_search.side_effect = [None, "/tmp/s001_pixabay_42.mp4"]
        reset_session_source_counts()
        with tempfile.TemporaryDirectory() as tmp:
            result = fetch_scene_clip(["nature"], 1, tmp, target_duration=5)
        self.assertEqual(result, "/tmp/s001_pixabay_42.mp4")
        self.assertGreaterEqual(mock_search.call_count, 2)
        sources = {c.kwargs.get("preferred_source") for c in mock_search.call_args_list}
        self.assertGreaterEqual(len(sources), 2)

    @patch("system_resilience.verify_stock_video_integrity", return_value={"valid": True})
    @patch("video_fetcher.search_and_download")
    def test_fetch_scene_clip_defined_no_name_error(self, mock_search, _mock_ffprobe):
        mock_search.return_value = "/tmp/s000_pexels_1.mp4"
        reset_session_source_counts()
        with tempfile.TemporaryDirectory() as tmp:
            path = fetch_scene_clip(["city"], 0, tmp)
        self.assertTrue(path.endswith(".mp4"))

    @patch("system_resilience.verify_stock_video_integrity")
    @patch("video_fetcher.search_and_download")
    def test_fetch_scene_clip_rejects_sub720p_p1_16(self, mock_search, mock_integrity):
        mock_search.return_value = "/tmp/s000_pexels_1.mp4"
        mock_integrity.return_value = {"valid": False, "reason": "720p altı (640x360)"}
        reset_session_source_counts()
        with tempfile.TemporaryDirectory() as tmp:
            path = fetch_scene_clip(["city"], 0, tmp)
        self.assertIsNone(path)


class TestClipContract(unittest.TestCase):
    def test_clip_coverage_report_all_ok(self):
        clips = [{"path": f"/tmp/s{i:03d}.mp4", "duration": 3.0} for i in range(14)]
        report = clip_coverage_report(clips)
        self.assertTrue(report["complete"])
        self.assertEqual(report["ok"], 14)
        self.assertEqual(report["missing_indices"], [])

    def test_clip_coverage_report_partial_fail(self):
        clips = [{"path": "/tmp/s000.mp4", "duration": 3.0}]
        clips.extend({"path": None, "duration": 3.0} for _ in range(13))
        report = clip_coverage_report(clips)
        self.assertFalse(report["complete"])
        self.assertEqual(report["ok"], 1)
        self.assertEqual(len(report["missing_indices"]), 13)
        self.assertEqual(report["missing_indices"][0], 1)

    def test_format_missing_clips_error_lists_scenes(self):
        clips = [{"path": "/tmp/s000.mp4", "duration": 3.0}]
        clips.extend({"path": None, "duration": 3.0} for _ in range(13))
        report = clip_coverage_report(clips)
        msg = format_missing_clips_error(report)
        self.assertIn("1/14", msg)
        self.assertIn("Missing scenes (1-based): 2", msg)
        self.assertIn("single-clip repeat", msg)

    def test_clip_uniqueness_report_all_unique(self):
        with tempfile.TemporaryDirectory() as tmp:
            clips = []
            for i in range(3):
                path = os.path.join(tmp, f"s{i:03d}.mp4")
                with open(path, "wb") as f:
                    f.write(f"clip-{i}".encode())
                clips.append({"path": path, "duration": 3.0})
            report = clip_uniqueness_report(clips, min_unique=3)
            self.assertTrue(report["ok"])
            self.assertEqual(report["unique_hashes"], 3)

    def test_clip_uniqueness_report_duplicate_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "same.mp4")
            with open(path, "wb") as f:
                f.write(b"shared-bytes")
            clips = [{"path": path, "duration": 3.0}, {"path": path, "duration": 3.0}]
            report = clip_uniqueness_report(clips, min_unique=2)
            self.assertFalse(report["ok"])
            self.assertIn("duplicate_paths", report["issues"])
            msg = format_duplicate_clips_error(report)
            self.assertIn("Duplicate paths", msg)

    def test_clip_uniqueness_report_duplicate_content_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            path_a = os.path.join(tmp, "a.mp4")
            path_b = os.path.join(tmp, "b.mp4")
            payload = b"identical-stock-footage"
            for path in (path_a, path_b):
                with open(path, "wb") as f:
                    f.write(payload)
            clips = [{"path": path_a, "duration": 3.0}, {"path": path_b, "duration": 3.0}]
            report = clip_uniqueness_report(clips, min_unique=2)
            self.assertFalse(report["ok"])
            self.assertIn("duplicate_content_hash", report["issues"])
            self.assertIn("unique_hashes<2", report["issues"])
            msg = format_duplicate_clips_error(report)
            self.assertIn("Duplicate content hash", msg)

    def test_ffmpeg_graph_aborts_partial_clip_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            audio = os.path.join(tmp, "a.wav")
            out = os.path.join(tmp, "out.mp4")
            clip_path = os.path.join(tmp, "s000.mp4")
            with open(audio, "wb") as f:
                f.write(b"\x00" * 4096)
            with open(clip_path, "wb") as f:
                f.write(b"\x00" * 4096)

            clips = [{"path": clip_path, "duration": 3.0}]
            clips.extend({"path": None, "duration": 3.0} for _ in range(13))

            with patch("render.ffmpeg_graph.os.path.exists", return_value=True):
                result = render_with_ffmpeg_graph(clips, audio, out)
            self.assertEqual(result, "")


class TestParallelStockFetch(unittest.IsolatedAsyncioTestCase):
    @patch("server_core.render_worker._gemini_image_circuit_open", return_value=True)
    @patch("server_core.render_worker.fetch_scene_clip")
    async def test_parallel_scene_fetch_uses_gather_p1_13(self, mock_fetch, _circuit):
        per_scene = 0.03

        def _slow_fetch(*_args, **_kwargs):
            time.sleep(per_scene)
            return "/tmp/fake.mp4"

        mock_fetch.side_effect = _slow_fetch
        scenes = [
            {"duration": 3.0, "search_queries": ["nature"], "scene_description": "test"}
            for _ in range(14)
        ]
        t0 = time.time()
        results = await _fetch_scenes_parallel(scenes, {}, "/tmp", 14)
        elapsed = time.time() - t0
        serial_estimate = 14 * per_scene
        self.assertEqual(len(results), 14)
        self.assertEqual(mock_fetch.call_count, 14)
        self.assertLess(elapsed, serial_estimate * 0.85)


class TestVeoSparsePolicy(unittest.TestCase):
    @patch("server_core.render_worker.config")
    def test_veo_blocked_without_paid_quota_p3_31(self, mock_cfg):
        mock_cfg.USE_GEMINI_VIDEO_GEN = True
        mock_cfg.GEMINI_API_KEY = "test-key"
        mock_cfg.GEMINI_VEO_PAID_QUOTA = False
        mock_cfg.GEMINI_VEO_PREVIEW_ONLY = True
        mock_cfg.GEMINI_VIDEO_MODEL = "veo-3.1-fast-generate-preview"
        with patch("server_core.render_worker._veo_circuit_open", return_value=False):
            self.assertFalse(_veo_render_allowed())

    @patch("system_resilience.circuit_breaker")
    def test_veo_circuit_open_helper_p3_31(self, mock_cb):
        mock_cb.can_execute.return_value = False
        self.assertTrue(_veo_circuit_open())

    def test_sweep_render_temp_files_p3_35(self):
        with tempfile.TemporaryDirectory() as tmp:
            ffgraph = os.path.join(tmp, "ffgraph_test123")
            os.makedirs(ffgraph)
            with patch("tempfile.gettempdir", return_value=tmp):
                _sweep_render_temp_files("")
            self.assertFalse(os.path.exists(ffgraph))


class TestGeminiCircuitStockOnly(unittest.TestCase):
    @patch("server_core.render_worker._gemini_image_circuit_open", return_value=True)
    @patch("server_core.render_worker.generate_ai_image_clip")
    @patch("server_core.render_worker.fetch_scene_clip", return_value="/tmp/stock.mp4")
    def test_circuit_open_skips_ai_forces_stock_p1_17(self, mock_stock, mock_ai, _circuit):
        scene = {
            "duration": 3.0,
            "search_queries": ["marble bust"],
            "scene_description": "stoic statue",
            "visual_intent": {},
            "narration": "test",
        }
        _i, _clip, path = _fetch_single_scene_visual(2, scene, {}, "/tmp", 14)
        mock_ai.assert_not_called()
        mock_stock.assert_called_once()
        self.assertEqual(path, "/tmp/stock.mp4")

    @patch("system_resilience.circuit_breaker")
    def test_gemini_circuit_open_helper_p1_17(self, mock_cb):
        mock_cb.can_execute.return_value = False
        self.assertTrue(_gemini_image_circuit_open())


class TestFfprobeIntegrity(unittest.TestCase):
    def test_verify_rejects_zero_byte_p1_16(self):
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            path = tmp.name
        try:
            result = verify_stock_video_integrity(path)
            self.assertFalse(result["valid"])
            self.assertIn("0 bayt", result["reason"])
        finally:
            os.remove(path)


if __name__ == "__main__":
    unittest.main()
