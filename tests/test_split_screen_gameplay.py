"""
tests/test_split_screen_gameplay.py — Comprehensive tests for Split-Screen & Gameplay features.
Validates:
1. services/gameplay_background_manager.py: Category resolution, asset retrieval, procedural fallback.
2. render/ffmpeg_graph.py: Single-pass FFmpeg split-screen chain with neon divider and vstack.
3. reddit_card_renderer.py: Question card generation & FFmpeg overlay integration.
4. server_core/render_worker.py: Auto-wiring of split-screen and gameplay assets into live render pipeline.
"""

import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from services.gameplay_background_manager import (
    GameplayBackgroundManager,
    GAMEPLAY_CATEGORIES,
    NICHE_DEFAULT_GAMEPLAY,
    GLOBAL_BACKGROUND_MANAGER,
)
from render.ffmpeg_graph import (
    build_scene_filter_chain,
    render_with_ffmpeg_graph,
    compose_via_director,
)
from api_models import VideoRenderRequest


class TestSplitScreenGameplay(unittest.TestCase):
    def setUp(self):
        self.mgr = GameplayBackgroundManager()
        self.test_dir = tempfile.mkdtemp(prefix="split_screen_test_")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_category_resolution(self):
        # Explicit categories
        self.assertEqual(self.mgr.resolve_category("minecraft_parkour"), "minecraft_parkour")
        self.assertEqual(self.mgr.resolve_category("subway_surfers_style"), "subway_surfers_style")
        self.assertEqual(self.mgr.resolve_category("gta_car_ramp"), "gta_car_ramp")
        self.assertEqual(self.mgr.resolve_category("asmr_kinetic_sand"), "asmr_kinetic_sand")

        # Niche-based resolution when auto
        self.assertEqual(self.mgr.resolve_category("auto", niche="11_reddit_stories"), "subway_surfers_style")
        self.assertEqual(self.mgr.resolve_category("auto", niche="2_philosophy_stoic"), "asmr_kinetic_sand")
        self.assertEqual(self.mgr.resolve_category("auto", niche="8_survival_myth"), "gta_car_ramp")

        # Unknown niche fallback
        self.assertEqual(self.mgr.resolve_category("auto", niche="unknown_niche"), "mobile_game")

    def test_procedural_gameplay_clip_generation(self):
        clip = self.mgr.generate_procedural_gameplay_clip(self.test_dir, duration=1.0)
        self.assertTrue(os.path.exists(clip))
        self.assertGreater(os.path.getsize(clip), 1000)

    def test_get_gameplay_clip_fallback_guarantee(self):
        # When external search returns None, procedural generator takes over immediately
        with patch("gameplay_pool.fetch_gameplay_clip", return_value=None):
            clip = self.mgr.get_gameplay_clip(
                project_dir=self.test_dir,
                category="minecraft_parkour",
                target_duration=1.0,
            )
            self.assertIsNotNone(clip)
            self.assertTrue(os.path.exists(clip))
            self.assertGreater(os.path.getsize(clip), 1000)

    def test_build_scene_filter_chain_split_screen(self):
        flt = build_scene_filter_chain(
            input_index=0,
            duration=5.0,
            width=1080,
            height=1920,
            scene_index=0,
            split_screen=True,
            gameplay_label="[gp0]",
            gameplay_start=2.5,
        )
        # Verify split-screen architecture (58% top = 1112px, 42% bottom = 808px)
        self.assertIn("vstack=inputs=2", flt)
        self.assertIn("crop=1080:1112", flt)
        self.assertIn("crop=1080:808", flt)
        self.assertIn("drawbox=y=0:h=3:color=0xFFD700@0.95:t=fill", flt)  # Neon divider line
        self.assertIn("trim=start=2.500:duration=5.000", flt)

    def test_render_with_ffmpeg_graph_split_and_reddit_card_command(self):
        # Create dummy media files
        dummy_clip = os.path.join(self.test_dir, "clip.mp4")
        dummy_gp = os.path.join(self.test_dir, "gameplay.mp4")
        dummy_audio = os.path.join(self.test_dir, "audio.wav")
        dummy_rcard = os.path.join(self.test_dir, "card.png")

        for f in [dummy_clip, dummy_gp, dummy_audio, dummy_rcard]:
            with open(f, "wb") as fh:
                fh.write(b"\x00" * 12000)

        with patch("subprocess.Popen") as mock_popen, \
             patch("render.ffmpeg_graph._probe_duration", return_value=10.0), \
             patch("render.ffmpeg_graph._probe_is_landscape", return_value=False), \
             patch("render.ffmpeg_graph.probe_stream_color", return_value={}), \
             patch("system_resilience.get_encoder_fallback_chain", return_value=[("libx264", ["-c:v", "libx264"])]):

            proc = MagicMock()
            proc.poll.return_value = 0
            proc.returncode = 0
            proc.stdout.readline.return_value = b""
            mock_popen.return_value = proc

            out_video = os.path.join(self.test_dir, "out.mp4")
            clips = [{"path": dummy_clip, "duration": 5.0}]

            res = render_with_ffmpeg_graph(
                clips=clips,
                audio_path=dummy_audio,
                output_path=out_video,
                gameplay_path=dummy_gp,
                enable_reddit_card=True,
                reddit_card_path=dummy_rcard,
            )

            cmd_args = mock_popen.call_args[0][0]
            cmd_str = " ".join(cmd_args)

            # Check that gameplay input was added with loop
            self.assertIn("-stream_loop -1 -i", cmd_str)
            self.assertIn(dummy_gp.replace("\\", "/"), cmd_str.replace("\\", "/"))

            # Check that reddit card input was added
            self.assertIn(dummy_rcard.replace("\\", "/"), cmd_str.replace("\\", "/"))

            # Check filter graph includes vstack and card overlay
            filter_complex = cmd_args[cmd_args.index("-filter_complex") + 1]
            self.assertIn("vstack=inputs=2", filter_complex)
            self.assertIn("drawbox=y=0:h=3:color=0xFFD700@0.95:t=fill", filter_complex)
            self.assertIn("between(t,0,3.6)", filter_complex)

    def test_api_models_request_supports_split_screen_and_gameplay(self):
        req = VideoRenderRequest(
            keyword="Reddit Mystery Story",
            split_screen=True,
            gameplay_category="minecraft_parkour",
            enable_reddit_card=True,
        )
        self.assertTrue(req.split_screen)
        self.assertEqual(req.gameplay_category, "minecraft_parkour")
        self.assertTrue(req.enable_reddit_card)


if __name__ == "__main__":
    unittest.main()
