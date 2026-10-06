"""
Tests for Chapter 28.8 / Section 2.1 (Item 8):
reference_repos/short-video-maker evolution:
- services/structured_logger.py: JSONLogFormatter, StructuredLoggerAdapter, secret redaction
- render/render_limits.py: RenderLimits, RenderConcurrencyGate
- effects/audio_visualizer.py: build_waveform_filter, is_visualizer_recommended_for_niche
"""

import json
import logging
import os
import time
import unittest
from unittest.mock import patch, MagicMock

from services.structured_logger import (
    JSONLogFormatter,
    TextLogFormatter,
    StructuredLoggerAdapter,
    get_structured_logger,
)
from render.render_limits import (
    RenderLimits,
    RenderConcurrencyGate,
)
from effects.audio_visualizer import (
    build_waveform_filter,
    render_standalone_waveform,
    is_visualizer_recommended_for_niche,
)


class TestStructuredLogger(unittest.TestCase):
    def test_json_formatter_structure_and_redaction(self):
        formatter = JSONLogFormatter(sanitize=True)
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Processing with key sk-1234567890abcdef and token=secret123",
            args=(),
            exc_info=None,
        )
        record.task_id = "task-999"
        record.api_key = "sensitive_secret_val"

        formatted = formatter.format(record)
        data = json.loads(formatted)

        self.assertEqual(data["level"], "INFO")
        self.assertEqual(data["logger"], "test_logger")
        self.assertIn("timestamp", data)
        self.assertTrue(data["timestamp"].endswith("Z"))
        self.assertIn("[REDACTED]", data["message"])
        self.assertNotIn("sk-1234567890abcdef", data["message"])
        self.assertEqual(data["context"]["task_id"], "task-999")
        self.assertEqual(data["context"]["api_key"], "[REDACTED]")

    def test_adapter_binding(self):
        raw_logger = logging.getLogger("adapter_test")
        adapter = StructuredLoggerAdapter(raw_logger, {"initial": "val"})
        bound = adapter.bind(scene_idx=3, niche="podcast")
        self.assertEqual(bound.extra["initial"], "val")
        self.assertEqual(bound.extra["scene_idx"], 3)
        self.assertEqual(bound.extra["niche"], "podcast")


class TestRenderLimitsAndConcurrencyGate(unittest.TestCase):
    def test_render_limits_defaults(self):
        self.assertEqual(RenderLimits.DEFAULT_FPS, 30)
        self.assertEqual(RenderLimits.VERTICAL_WIDTH, 1080)
        self.assertEqual(RenderLimits.VERTICAL_HEIGHT, 1920)
        self.assertGreaterEqual(RenderLimits.MAX_CONCURRENT_RENDERS, 1)

    def test_concurrency_gate_sync(self):
        gate = RenderConcurrencyGate(max_concurrency=2)
        metrics_initial = gate.get_metrics()
        self.assertEqual(metrics_initial["active_renders"], 0)
        self.assertEqual(metrics_initial["available_slots"], 2)

        with gate.acquire_slot_sync(task_id="t1"):
            m = gate.get_metrics()
            self.assertEqual(m["active_renders"], 1)
            self.assertEqual(m["available_slots"], 1)

        m_after = gate.get_metrics()
        self.assertEqual(m_after["active_renders"], 0)
        self.assertEqual(m_after["total_served"], 1)

    def test_concurrency_gate_timeout(self):
        gate = RenderConcurrencyGate(max_concurrency=1)
        with gate.acquire_slot_sync(task_id="t1"):
            # Attempting second acquire should time out quickly
            with self.assertRaises(TimeoutError):
                with gate.acquire_slot_sync(task_id="t2", timeout=0.05):
                    pass


class TestAudioVisualizer(unittest.TestCase):
    def test_is_visualizer_recommended_for_niche(self):
        self.assertTrue(is_visualizer_recommended_for_niche("podcast_debate"))
        self.assertTrue(is_visualizer_recommended_for_niche("stoic_quotes"))
        self.assertTrue(is_visualizer_recommended_for_niche("philosophy"))
        self.assertFalse(is_visualizer_recommended_for_niche("minecraft_parkour"))

    def test_build_waveform_filter_line(self):
        flt, tag = build_waveform_filter(
            audio_tag="1:a",
            video_tag="0:v",
            width=1080,
            height=160,
            y_pos=1400,
            mode="line",
            color="#00D7FF",
        )
        self.assertEqual(tag, "out_wave")
        self.assertIn("showwaves=s=1080x160:mode=line:colors=0x00D7FF@0.85", flt)
        self.assertIn("format=yuva420p", flt)
        self.assertIn("overlay=x=(W-w)/2:y=1400", flt)

    def test_build_waveform_filter_frequency_bars(self):
        flt, tag = build_waveform_filter(
            audio_tag="0:a",
            video_tag="0:v",
            mode="frequency_bars",
            color="0xFFD700",
        )
        self.assertIn("showfreqs=s=1080x160:mode=bar", flt)
        self.assertIn("colors=0xFFD700@0.85", flt)

    @patch("os.path.isfile", return_value=True)
    @patch("subprocess.run")
    def test_render_standalone_waveform_cmd(self, mock_run, mock_isfile):
        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_run.return_value = mock_res

        with patch("os.path.getsize", return_value=5000):
            out = render_standalone_waveform(
                audio_path="assets/speech.wav",
                output_path="assets/wave.webm",
                duration=5.0,
            )
        self.assertEqual(out, "assets/wave.webm")
        cmd = mock_run.call_args[0][0]
        cmd_str = " ".join(cmd)
        self.assertIn("libvpx-vp9", cmd_str)
        self.assertIn("yuva420p", cmd_str)
        self.assertIn("-t 5.000", cmd_str)

    @patch("os.path.exists", return_value=True)
    @patch("subprocess.Popen")
    def test_ffmpeg_graph_audio_visualizer_wiring(self, mock_popen, mock_exists):
        from render.ffmpeg_graph import render_with_ffmpeg_graph
        mock_proc = MagicMock()
        mock_proc.poll.return_value = 0
        mock_proc.returncode = 0
        mock_proc.stdout.readline.return_value = ""
        mock_proc.stderr.read.return_value = ""
        mock_popen.return_value = mock_proc

        clips = [
            {"path": "c1.mp4", "duration": 4.0, "narration": "Podcast introsu"},
        ]
        with patch("render.ffmpeg_graph._probe_has_audio", return_value=True), \
             patch("render.ffmpeg_graph.os.path.getsize", return_value=204800):
            res = render_with_ffmpeg_graph(
                clips=clips,
                audio_path="speech.wav",
                output_path="out.mp4",
                enable_audio_visualizer=True,
                audio_visualizer_mode="line",
                audio_visualizer_color="0x00D7FF",
            )
            self.assertEqual(res, "out.mp4")
            cmd = mock_popen.call_args[0][0]
            cmd_str = " ".join(cmd)
            self.assertIn("showwaves", cmd_str)
            self.assertIn("format=yuva420p", cmd_str)
            self.assertIn("vwave", cmd_str)

    def test_api_models_visualizer_fields(self):
        from api_models import VideoRenderRequest
        req = VideoRenderRequest(
            keyword="Felsefe Podcast",
            enable_audio_visualizer=True,
            audio_visualizer_mode="frequency_bars",
            audio_visualizer_color="0xFFD700",
        )
        self.assertTrue(req.enable_audio_visualizer)
        self.assertEqual(req.audio_visualizer_mode, "frequency_bars")
        self.assertEqual(req.audio_visualizer_color, "0xFFD700")


if __name__ == "__main__":
    unittest.main()
