"""Render worker clip contract tests (P0-03)."""
import asyncio
import os
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import config

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
    _compose_with_retry,
    _gemini_image_circuit_open,
    _get_render_thread_limits,
    _quality_report_allows_render,
    _veo_circuit_open,
    _veo_render_allowed,
    _sweep_render_temp_files,
)
from system_resilience import verify_stock_video_integrity
from video_fetcher import (
    fetch_scene_clip,
    fetch_selected_stock_video,
    reset_session_source_counts,
)


class TestScriptQualityGate(unittest.TestCase):
    def test_thermal_thread_limits_are_render_local(self):
        with patch.object(config, "RENDER_THREADS", 8), \
            patch.object(config, "FFMPEG_THREADS", 6):
            self.assertEqual(_get_render_thread_limits(), (8, 6))
            self.assertEqual(
                _get_render_thread_limits({"thermal_throttle_recommended": True}),
                (4, 4),
            )
            self.assertEqual(config.RENDER_THREADS, 8)
            self.assertEqual(config.FFMPEG_THREADS, 6)

    def test_hard_fail_report_cannot_be_softened_by_issue_name(self):
        for issue in (
            "word_count_out_of_band:84",
            "duration_out_of_band:37.99",
            "scene_0_words_below_7",
            "scene_0_queries_insufficient",
            "scene_0_visual_description_invalid",
        ):
            with self.subTest(issue=issue):
                self.assertFalse(
                    _quality_report_allows_render(
                        {"hard_fail": True, "issues": [issue]}
                    )
                )

    def test_advisory_report_remains_renderable(self):
        self.assertTrue(
            _quality_report_allows_render(
                {"hard_fail": False, "warnings": ["word_count_above_optimal:111"]}
            )
        )

    def test_explicit_draft_override_remains_available(self):
        self.assertTrue(
            _quality_report_allows_render(
                {"hard_fail": True, "issues": ["word_count_out_of_band:84"]},
                allow_draft_render=True,
            )
        )


class TestWorkflowRenderRetryIntegration(unittest.TestCase):
    def test_composition_retries_isolated_output_then_forces_cpu(self):
        with tempfile.TemporaryDirectory() as temp_dir, \
            patch.object(config, "USE_GPU_ACCELERATION", True, create=True):
            output_path = os.path.join(temp_dir, "render.mp4")
            calls = []
            progress_values = []

            def compose(_clips, _audio_path, _word_timings, attempt_path, *,
                        use_gpu_override, progress_callback):
                self.assertEqual(_clips, [])
                self.assertEqual(_audio_path, "audio.wav")
                self.assertEqual(_word_timings, [])
                calls.append((attempt_path, use_gpu_override))
                progress_callback(90 if len(calls) == 1 else 80)
                with open(attempt_path, "wb") as output:
                    output.write(b"PARTIAL" if len(calls) == 1 else b"RENDERED_VIDEO")
                return "" if len(calls) == 1 else attempt_path

            result = _compose_with_retry(
                compose, [], "audio.wav", [], output_path,
                progress_callback=progress_values.append,
            )

            self.assertEqual(result, output_path)
            self.assertEqual(progress_values, [90.0, 90.0])
            self.assertEqual(
                calls,
                [
                    (os.path.join(temp_dir, "render.attempt-001.mp4"), True),
                    (os.path.join(temp_dir, "render.attempt-002.mp4"), False),
                ],
            )
            with open(output_path, "rb") as rendered:
                self.assertEqual(rendered.read(), b"RENDERED_VIDEO")


class TestMultiSourceFetch(unittest.TestCase):
    @patch("system_resilience.verify_stock_video_integrity", return_value={"valid": True})
    @patch("video_fetcher.gather_scene_pools", return_value="/tmp/s001_pixabay_42.mp4")
    def test_fetch_scene_clip_uses_one_pool_gather(self, mock_gather, _mock_ffprobe):
        reset_session_source_counts()
        with tempfile.TemporaryDirectory() as tmp:
            result = fetch_scene_clip(["nature"], 1, tmp, target_duration=5)
        self.assertEqual(result, "/tmp/s001_pixabay_42.mp4")
        self.assertEqual(mock_gather.call_count, 1)

    @patch("system_resilience.verify_stock_video_integrity", return_value={"valid": True})
    @patch("video_fetcher.gather_scene_pools", return_value="/tmp/s000_pexels_1.mp4")
    def test_fetch_scene_clip_defined_no_name_error(self, mock_gather, _mock_ffprobe):
        reset_session_source_counts()
        with tempfile.TemporaryDirectory() as tmp:
            path = fetch_scene_clip(["city"], 0, tmp)
        self.assertTrue(path.endswith(".mp4"))
        self.assertEqual(mock_gather.call_count, 1)

    @patch("system_resilience.verify_stock_video_integrity")
    @patch("video_fetcher.gather_scene_pools", return_value="/tmp/s000_pexels_1.mp4")
    def test_fetch_scene_clip_rejects_sub720p_p1_16(self, mock_gather, mock_integrity):
        mock_integrity.return_value = {"valid": False, "reason": "720p altı (640x360)"}
        reset_session_source_counts()
        with tempfile.TemporaryDirectory() as tmp:
            path = fetch_scene_clip(["city"], 0, tmp)
        self.assertIsNone(path)
        self.assertEqual(mock_gather.call_count, 1)


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
    def setUp(self):
        from server_core import state
        state.current_render_state["cancel_requested"] = False
        state.cancel_requested = False

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

    def test_sweep_render_temp_files_preserves_active_ffgraph_jobs(self):
        with tempfile.TemporaryDirectory() as tmp:
            ffgraph = os.path.join(tmp, "ffgraph_test123")
            os.makedirs(ffgraph)
            with patch("tempfile.gettempdir", return_value=tmp):
                _sweep_render_temp_files("")
            self.assertTrue(os.path.isdir(ffgraph))


class TestGeminiCircuitStockOnly(unittest.TestCase):
    def setUp(self):
        from server_core import state
        state.current_render_state["cancel_requested"] = False
        state.cancel_requested = False

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


class TestSelectedSceneStockVideo(unittest.TestCase):
    def setUp(self):
        from server_core import state
        state.current_render_state["cancel_requested"] = False
        state.cancel_requested = False

    @patch("server_core.render_worker.fetch_scene_clip")
    @patch("server_core.render_worker.fetch_selected_stock_video")
    def test_existing_local_selected_video_keeps_priority(self, mock_selected, mock_search):
        with tempfile.TemporaryDirectory() as project_dir:
            local_path = os.path.join(project_dir, "selected.mp4")
            with open(local_path, "wb") as clip_file:
                clip_file.write(b"selected local clip")
            scene = {
                "duration": 4.0,
                "selected_video": {"path": local_path},
            }

            index, clip, path = _fetch_single_scene_visual(0, scene, {}, project_dir, 4)

        self.assertEqual((index, path), (0, local_path))
        self.assertEqual(clip["path"], local_path)
        mock_selected.assert_not_called()
        mock_search.assert_not_called()

    @patch("server_core.render_worker.fetch_scene_clip", return_value="/tmp/search.mp4")
    @patch("server_core.render_worker.fetch_selected_stock_video", return_value="/tmp/selected.mp4")
    def test_remote_selected_video_is_used_before_stock_search(self, mock_selected, mock_search):
        scene = {
            "duration": 4.0,
            "search_queries": ["unrelated query"],
            "scene_description": "selected subject",
            "selected_video": {
                "id": "px_12345",
                "source": "pexels",
                "kind": "video",
                "url": "https://videos.pexels.com/video-files/12345/video.mp4",
            },
        }

        index, clip, path = _fetch_single_scene_visual(0, scene, {}, "/tmp", 4)

        self.assertEqual((index, path), (0, "/tmp/selected.mp4"))
        self.assertEqual(clip["path"], "/tmp/selected.mp4")
        mock_selected.assert_called_once()
        mock_search.assert_not_called()

    @patch("server_core.render_worker._gemini_image_circuit_open", return_value=True)
    @patch("server_core.render_worker.fetch_scene_clip", return_value="/tmp/search.mp4")
    def test_nonvideo_selection_falls_back_to_scene_search(self, mock_search, _circuit):
        scene = {
            "duration": 4.0,
            "search_queries": ["mosque sunrise"],
            "scene_description": "mosque at sunrise",
            "selected_video": {
                "id": "ov_123",
                "source": "openverse",
                "kind": "image",
                "url": "https://example.com/image.jpg",
            },
        }

        _index, _clip, path = _fetch_single_scene_visual(0, scene, {}, "/tmp", 4)

        self.assertEqual(path, "/tmp/search.mp4")
        mock_search.assert_called_once()

    def test_image_selection_is_rejected_without_downloading(self):
        with patch("video_fetcher.requests.get") as mock_get:
            result = fetch_selected_stock_video(
                {
                    "id": "ov_123",
                    "source": "openverse",
                    "kind": "image",
                    "url": "https://example.com/image.jpg",
                },
                0,
                tempfile.gettempdir(),
            )

        self.assertIsNone(result)
        mock_get.assert_not_called()

    def test_untrusted_selected_video_url_is_rejected_without_downloading(self):
        with patch("video_fetcher.requests.get") as mock_get:
            result = fetch_selected_stock_video(
                {
                    "id": "px_123",
                    "source": "pexels",
                    "kind": "video",
                    "url": "https://example.com/video.mp4",
                },
                0,
                tempfile.gettempdir(),
            )

        self.assertIsNone(result)
        mock_get.assert_not_called()

    @patch("visuals.fetch.add_manifest_entry")
    @patch("system_resilience.verify_stock_video_integrity", return_value={"valid": True})
    @patch("database.record_source_asset")
    @patch("database.source_asset_was_used", return_value=False)
    @patch("database.is_stock_blocklisted", return_value=False)
    def test_downloads_selected_video_and_records_license_manifest(
        self, _blocklisted, _already_used, mock_record_source,
        _integrity, mock_manifest,
    ):
        class FakeResponse:
            status_code = 200
            is_redirect = False
            headers = {"Content-Length": "12000"}

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return None

            def raise_for_status(self):
                return None

            def iter_content(self, _chunk_size):
                yield b"x" * 12000

        with tempfile.TemporaryDirectory() as project_dir, patch(
            "video_fetcher.requests.get", return_value=FakeResponse()
        ) as mock_get:
            result = fetch_selected_stock_video(
                {
                    "id": "px_123",
                    "source": "pexels",
                    "kind": "video",
                    "url": "https://videos.pexels.com/video-files/123/video.mp4",
                    "title": "Selected stock clip",
                    "source_url": "https://www.pexels.com/video/123/",
                },
                2,
                project_dir,
                target_duration=4,
            )

            self.assertTrue(result and os.path.isfile(result))
            mock_get.assert_called_once()
            self.assertFalse(mock_get.call_args.kwargs["allow_redirects"])
            manifest = mock_manifest.call_args.args[0]
            self.assertEqual(manifest["source"], "pexels")
            self.assertEqual(manifest["source_url"], "https://www.pexels.com/video/123/")
            self.assertEqual(manifest["license"]["license"], "pexels")
            self.assertTrue(manifest["sha256"])
            mock_record_source.assert_called_once()


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
