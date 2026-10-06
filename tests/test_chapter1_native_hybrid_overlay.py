"""
Unit tests for Chapter 1.1 & 1.2: Native FFmpeg FilterComplex Hybrid UI Overlays.
Verifies transparent PNG generation for hybrid niches (Items 276-345) and single-pass
FFmpeg graph routing, eliminating MoviePy CPU bottleneck and memory leaks.
"""
import os
import tempfile
import unittest
from unittest.mock import Mock, patch
from PIL import Image

from effects.hybrid_overlay import is_native_hybrid_supported, create_hybrid_ui_overlay_png
from render.ffmpeg_graph import _needs_moviepy_composer, compose_via_director


class TestNativeHybridOverlay(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp(prefix="test_hybrid_")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_is_native_hybrid_supported_all_types(self):
        supported_specs = [
            {"ui_type": "imessage"},
            {"ui_type": "ios_notification"},
            {"ui_type": "split_choice"},
            {"ui_type": "interactive_quiz"},
            {"ui_type": "tweet_card"},
            {"ui_type": "search_bar"},
            {"ui_type": "subtitle_bar"},
            {"overlay": "neon_frame"},
            {"overlay": "hybrid_frame"},
            {"overlay": "epic_vignette"},
            {"overlay": "soft_vignette"},
            {"overlay": "countdown_wheel"},
            {"overlay": "eq_bar"},
        ]
        for spec in supported_specs:
            self.assertTrue(
                is_native_hybrid_supported(spec),
                f"Expected {spec} to be supported natively"
            )

        self.assertFalse(is_native_hybrid_supported({}))
        self.assertFalse(is_native_hybrid_supported({"ui_type": "unknown_future_xyz"}))

    def test_create_ios_notification_png(self):
        spec = {
            "ui_type": "imessage",
            "header": "Tarih Grubu",
            "body": "Sezar: Brutus sen de mi?",
        }
        out_png = os.path.join(self.tmp_dir, "imessage.png")
        info = create_hybrid_ui_overlay_png(spec, width=1080, height=1920, total_duration=25.0, out_path=out_png)

        self.assertIsNotNone(info)
        self.assertTrue(os.path.exists(out_png))
        self.assertGreater(os.path.getsize(out_png), 500)
        self.assertEqual(info["png_path"], out_png)
        self.assertEqual(info["start_time"], 0.6)
        self.assertIn("between(t,0.60,", info["enable_expr"])
        self.assertEqual(info["x_expr"], "(W-w)/2")

        with Image.open(out_png) as img:
            self.assertEqual(img.mode, "RGBA")
            self.assertEqual(img.size, (960, 160))

    def test_create_split_choice_png(self):
        spec = {
            "ui_type": "split_choice",
            "header": "Kırmızı Hap",
            "body": "Mavi Hap",
        }
        out_png = os.path.join(self.tmp_dir, "split_choice.png")
        info = create_hybrid_ui_overlay_png(spec, width=1080, height=1920, total_duration=30.0, out_path=out_png)

        self.assertIsNotNone(info)
        self.assertTrue(os.path.exists(out_png))
        self.assertEqual(info["start_time"], 1.0)
        self.assertIn("between(t,1.00,", info["enable_expr"])

        with Image.open(out_png) as img:
            self.assertEqual(img.mode, "RGBA")
            self.assertEqual(img.size, (920, 280))

    def test_create_search_bar_png(self):
        spec = {
            "ui_type": "search_bar",
            "header": "GİZLİ DOSYA",
            "body": "Kozmik sinyal arandı...",
        }
        out_png = os.path.join(self.tmp_dir, "search.png")
        info = create_hybrid_ui_overlay_png(spec, width=1080, height=1920, total_duration=20.0, out_path=out_png)

        self.assertIsNotNone(info)
        self.assertTrue(os.path.exists(out_png))
        with Image.open(out_png) as img:
            self.assertEqual(img.mode, "RGBA")
            self.assertEqual(img.size, (920, 140))

    def test_create_neon_frame_png(self):
        spec = {
            "overlay": "neon_frame",
            "label": "CYBERPUNK STOIC",
        }
        out_png = os.path.join(self.tmp_dir, "neon.png")
        info = create_hybrid_ui_overlay_png(spec, width=1080, height=1920, total_duration=15.0, out_path=out_png)

        self.assertIsNotNone(info)
        self.assertTrue(os.path.exists(out_png))
        self.assertEqual(info["start_time"], 0.0)
        self.assertEqual(info["duration"], 15.0)
        self.assertEqual(info["x_expr"], "0")
        self.assertEqual(info["y_expr"], "0")

        with Image.open(out_png) as img:
            self.assertEqual(img.mode, "RGBA")
            self.assertEqual(img.size, (1080, 1920))

    def test_needs_moviepy_composer_native_bypass(self):
        # Default with hybrid overlay returns True unless native is enabled
        self.assertTrue(_needs_moviepy_composer({"hybrid_render_overlay": {"ui_type": "imessage"}}))

        # Explicitly enabling native hybrid routes to FFmpeg (returns False)
        self.assertFalse(_needs_moviepy_composer({
            "hybrid_render_overlay": {"ui_type": "imessage"},
            "enable_native_hybrid": True,
        }))

        # If force_moviepy is True, always returns True
        self.assertTrue(_needs_moviepy_composer({
            "hybrid_render_overlay": {"ui_type": "imessage"},
            "enable_native_hybrid": True,
            "force_moviepy": True,
        }))

    def test_compose_via_director_routes_to_ffmpeg_when_native_enabled(self):
        clips = [{"path": "clip1.mp4", "duration": 4.0}]
        mock_ffmpeg = Mock(return_value="output.mp4")
        mock_composer = Mock(return_value="legacy_moviepy.mp4")

        with patch("render.ffmpeg_graph.render_with_ffmpeg_graph", mock_ffmpeg), \
             patch("video_composer.compose_video", mock_composer):

            res = compose_via_director(
                clips, "voice.wav", [], "output.mp4",
                hybrid_render_overlay={"ui_type": "imessage", "header": "Test"},
                enable_native_hybrid=True,
            )

            self.assertEqual(res, "output.mp4")
            self.assertEqual(mock_ffmpeg.call_count, 1)
            self.assertEqual(mock_composer.call_count, 0)
            # Verify hybrid_render_overlay was passed to render_with_ffmpeg_graph
            call_kwargs = mock_ffmpeg.call_args[1]
            self.assertEqual(call_kwargs.get("hybrid_render_overlay"), {"ui_type": "imessage", "header": "Test"})

    def test_render_with_ffmpeg_graph_injects_hybrid_overlay_command(self):
        """Verifies that render_with_ffmpeg_graph adds PNG loop input and overlay filter."""
        from render.ffmpeg_graph import render_with_ffmpeg_graph
        import subprocess

        clip_path = os.path.join(self.tmp_dir, "s01.mp4")
        with open(clip_path, "wb") as f:
            f.write(b"\x00" * 1024)
        audio_path = os.path.join(self.tmp_dir, "voice.wav")
        with open(audio_path, "wb") as f:
            f.write(b"\x00" * 1024)

        captured_cmd = []

        class MockPopen:
            def __init__(self, cmd, *args, **kwargs):
                nonlocal captured_cmd
                captured_cmd = cmd
                self.returncode = 0
                self.stdout = Mock()
                self.stdout.readline = Mock(side_effect=[""])
                self.stderr = Mock()
                self.stderr.readline = Mock(side_effect=["frame=100 time=00:00:04.00", ""])
                # Create fake output file >= 100KB
                out_path = cmd[-1]
                with open(out_path, "wb") as f:
                    f.write(b"\x00" * 150000)

            def poll(self):
                return 0

            def wait(self, timeout=None):
                return 0

            def kill(self):
                pass

            def terminate(self):
                pass

        def mock_run(cmd, *args, **kwargs):
            res = Mock()
            res.returncode = 0
            res.stderr = "Duration: 00:00:04.00"
            res.stdout = ""
            return res

        with patch("subprocess.run", side_effect=mock_run), \
             patch("subprocess.Popen", side_effect=MockPopen), \
             patch("render.ffmpeg_graph.probe_stream_color", return_value="bt709"), \
             patch("render.ffmpeg_graph.color_convert_filter", return_value=""), \
             patch("system_resilience.get_encoder_fallback_chain", return_value=[(["-c:v", "libx264"], "CPU")]), \
             patch("render.ffmpeg_graph.os.path.exists", return_value=True):

            out_video = os.path.join(self.tmp_dir, "final.mp4")
            res = render_with_ffmpeg_graph(
                [{"path": clip_path, "duration": 4.0}],
                audio_path,
                out_video,
                hybrid_render_overlay={"ui_type": "imessage", "header": "Tarih"},
            )

            self.assertEqual(res, out_video)
            self.assertTrue(len(captured_cmd) > 0)
            fc_idx = captured_cmd.index("-filter_complex")
            fc = captured_cmd[fc_idx + 1]
            self.assertIn("vhybrid", fc)
            self.assertIn("hy_rgba", fc)
            self.assertIn("overlay=x=(W-w)/2", fc)


if __name__ == "__main__":
    unittest.main()
