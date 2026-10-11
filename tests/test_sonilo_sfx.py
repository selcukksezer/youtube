"""Opt-in Sonilo SFX preflight, render wiring, and output preservation tests."""

import importlib
import os
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

from fastapi import BackgroundTasks, HTTPException

import config
from api_models import VideoRenderRequest
from services import sonilo_sfx


class TestSoniloSfxService(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.video_path = os.path.join(self.temp_dir.name, "render.mp4")
        with open(self.video_path, "wb") as video_file:
            video_file.write(b"original video")

    def test_missing_key_rejects_before_external_request(self):
        with patch.object(config, "SONILO_API_KEY", ""), patch.object(
            sonilo_sfx.requests, "post"
        ) as post:
            with self.assertRaises(sonilo_sfx.SoniloSfxError):
                sonilo_sfx.add_ai_sfx_to_video(self.video_path)
        post.assert_not_called()

    def test_duration_limit_rejects_before_upload(self):
        with patch.object(config, "SONILO_API_KEY", "sonilo-test"), patch.object(
            sonilo_sfx, "_ffprobe_duration", return_value=181.0
        ), patch.object(sonilo_sfx, "_request_sfx_audio") as request_audio:
            with self.assertRaisesRegex(sonilo_sfx.SoniloSfxError, "180s"):
                sonilo_sfx.add_ai_sfx_to_video(self.video_path)
        request_audio.assert_not_called()

    def test_task_submission_authenticates_and_returns_task_id(self):
        response = Mock(status_code=202)
        response.json.return_value = {"task_id": "task-123"}
        with patch.object(
            sonilo_sfx.requests, "post", return_value=response
        ) as post:
            task_id = sonilo_sfx._submit_task(self.video_path, "sonilo-test-key")

        self.assertEqual(task_id, "task-123")
        args, kwargs = post.call_args
        self.assertEqual(
            args[0],
            f"{sonilo_sfx.API_BASE_URL}{sonilo_sfx.VIDEO_TO_SFX_PATH}",
        )
        self.assertEqual(
            kwargs["headers"]["Authorization"], "Bearer sonilo-test-key"
        )
        self.assertEqual(kwargs["files"]["video"][0], "render.mp4")

    def test_task_polling_waits_then_returns_success(self):
        processing = Mock(status_code=200)
        processing.json.return_value = {"status": "processing"}
        succeeded = Mock(status_code=200)
        succeeded.json.return_value = {
            "status": "succeeded",
            "audio": {"url": "https://cdn.example.test/sfx.m4a"},
        }
        with patch.object(
            sonilo_sfx.requests, "get", side_effect=[processing, succeeded]
        ) as get, patch.object(
            sonilo_sfx.time, "monotonic", side_effect=[100.0, 100.1]
        ), patch.object(sonilo_sfx.time, "sleep") as sleep:
            result = sonilo_sfx._poll_task("task-123", "sonilo-test-key")

        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(get.call_count, 2)
        self.assertEqual(
            get.call_args.kwargs["headers"]["Authorization"],
            "Bearer sonilo-test-key",
        )
        sleep.assert_called_once_with(sonilo_sfx.POLL_INTERVAL_SECONDS)

    def test_successful_mix_replaces_render_only_after_ffmpeg_output_exists(self):
        def fake_ffmpeg(command, **kwargs):
            with open(command[-1], "wb") as output_file:
                output_file.write(b"mixed video")
            return subprocess.CompletedProcess(command, 0, stdout=b"", stderr=b"")

        with patch.object(config, "SONILO_API_KEY", "sonilo-test"), patch.object(
            sonilo_sfx, "_ffprobe_duration", return_value=45.0
        ), patch.object(
            sonilo_sfx, "_ffprobe_streams", return_value=[{"codec_type": "audio"}]
        ), patch.object(
            sonilo_sfx, "_request_sfx_audio", return_value=b"sfx audio"
        ), patch.object(
            sonilo_sfx.imageio_ffmpeg, "get_ffmpeg_exe", return_value="ffmpeg"
        ), patch.object(
            sonilo_sfx.subprocess, "run", side_effect=fake_ffmpeg
        ) as run:
            sonilo_sfx.add_ai_sfx_to_video(self.video_path)

        with open(self.video_path, "rb") as video_file:
            self.assertEqual(video_file.read(), b"mixed video")
        command = run.call_args.args[0]
        self.assertIn("[0:a:0][sfx]amix=", command[command.index("-filter_complex") + 1])
        self.assertEqual(command[command.index("-c:v") + 1], "copy")
        self.assertEqual(os.listdir(self.temp_dir.name), ["render.mp4"])

    def test_ffmpeg_failure_preserves_original_and_cleans_temporary_files(self):
        with patch.object(config, "SONILO_API_KEY", "sonilo-test"), patch.object(
            sonilo_sfx, "_ffprobe_duration", return_value=45.0
        ), patch.object(
            sonilo_sfx, "_ffprobe_streams", return_value=[{"codec_type": "audio"}]
        ), patch.object(
            sonilo_sfx, "_request_sfx_audio", return_value=b"sfx audio"
        ), patch.object(
            sonilo_sfx.imageio_ffmpeg, "get_ffmpeg_exe", return_value="ffmpeg"
        ), patch.object(
            sonilo_sfx.subprocess,
            "run",
            return_value=subprocess.CompletedProcess(
                ["ffmpeg"], 1, stdout=b"", stderr=b"mix failed"
            ),
        ):
            with self.assertRaisesRegex(sonilo_sfx.SoniloSfxError, "mix failed"):
                sonilo_sfx.add_ai_sfx_to_video(self.video_path)

        with open(self.video_path, "rb") as video_file:
            self.assertEqual(video_file.read(), b"original video")
        self.assertEqual(os.listdir(self.temp_dir.name), ["render.mp4"])

    def test_unconfirmed_original_audio_prevents_replacement(self):
        with patch.object(config, "SONILO_API_KEY", "sonilo-test"), patch.object(
            sonilo_sfx, "_ffprobe_duration", return_value=45.0
        ), patch.object(
            sonilo_sfx, "_ffprobe_streams", return_value=[]
        ), patch.object(
            sonilo_sfx, "_request_sfx_audio", return_value=b"sfx audio"
        ), patch.object(sonilo_sfx.subprocess, "run") as run:
            with self.assertRaisesRegex(sonilo_sfx.SoniloSfxError, "audio track"):
                sonilo_sfx.add_ai_sfx_to_video(self.video_path)

        run.assert_not_called()
        with open(self.video_path, "rb") as video_file:
            self.assertEqual(video_file.read(), b"original video")
        self.assertEqual(os.listdir(self.temp_dir.name), ["render.mp4"])

    def test_download_never_sends_sonilo_api_key_to_result_host(self):
        response = Mock(status_code=200, content=b"sfx audio")
        with patch.object(sonilo_sfx.requests, "get", return_value=response) as get:
            self.assertEqual(
                sonilo_sfx._download_audio("https://cdn.example.test/sfx.m4a"),
                b"sfx audio",
            )
        self.assertNotIn("headers", get.call_args.kwargs)

    def test_result_audio_url_must_use_https(self):
        with self.assertRaises(sonilo_sfx.SoniloSfxError):
            sonilo_sfx._result_audio_url(
                {"audio": {"url": "http://localhost/sfx.m4a"}}, "task-1"
            )


class TestSoniloSfxWiring(unittest.TestCase):
    def test_render_request_defaults_ai_sfx_off(self):
        request = VideoRenderRequest(keyword="test")
        self.assertFalse(request.enable_sonilo_sfx)

    def test_render_api_requires_key_before_starting_job(self):
        video_router = importlib.import_module("routers.video_router")
        request = VideoRenderRequest(keyword="test", enable_sonilo_sfx=True)
        with patch.object(config, "SONILO_API_KEY", ""):
            with self.assertRaises(HTTPException) as raised:
                video_router.api_render_video(request, BackgroundTasks())
        self.assertEqual(raised.exception.status_code, 400)
        self.assertIn("Sonilo API Key", raised.exception.detail)

    def test_render_worker_skips_unchecked_option_and_logs_failure(self):
        render_worker = importlib.import_module("server_core.render_worker")
        with patch("services.sonilo_sfx.add_ai_sfx_to_video") as add_sfx:
            self.assertFalse(
                render_worker._apply_optional_sonilo_sfx(self.video_fixture(), False)
            )
            add_sfx.assert_not_called()

            add_sfx.side_effect = sonilo_sfx.SoniloSfxError("temporary failure")
            self.assertFalse(
                render_worker._apply_optional_sonilo_sfx(self.video_fixture(), True)
            )
            add_sfx.assert_called_once()

    @staticmethod
    def video_fixture() -> str:
        return os.path.join(tempfile.gettempdir(), "sonilo-sfx-render-test.mp4")

    def test_studio_payload_and_copy_explain_opt_in_upload(self):
        root = os.path.dirname(os.path.dirname(__file__))
        with open(
            os.path.join(root, "static", "js", "render-monitor.js"),
            encoding="utf-8",
        ) as render_file:
            render_js = render_file.read()
        with open(os.path.join(root, "static", "index.html"), encoding="utf-8") as html_file:
            html = html_file.read()
        self.assertIn("enable_sonilo_sfx:", render_js)
        self.assertIn("chk-enable-sonilo-sfx", render_js)
        self.assertIn("Sonilo’ya yüklenir", html)


if __name__ == "__main__":
    unittest.main()
