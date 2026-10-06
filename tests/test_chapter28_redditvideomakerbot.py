"""
Tests for Chapter 28.16 / Section 2.2 (Madde 14):
reference_repos2/RedditVideoMakerBot evolution:
- services/gameplay_background_manager.py: GameplayBackgroundManager, safe intervals, anti-repetition, filter
- reddit_card_renderer.py: generate_transparent_reddit_card_png, build_reddit_card_ffmpeg_filter
"""

import os
import unittest
from PIL import Image

from services.gameplay_background_manager import (
    GameplayBackgroundManager,
    GLOBAL_BACKGROUND_MANAGER,
)
from reddit_card_renderer import (
    generate_transparent_reddit_card_png,
    build_reddit_card_ffmpeg_filter,
)


class TestRedditVideoMakerBotBackgroundManager(unittest.TestCase):
    def setUp(self):
        self.mgr = GameplayBackgroundManager()

    def test_short_background_triggers_loop_mode(self):
        # 15s background video, 45s required clip length
        start, end, needs_loop = self.mgr.get_safe_background_interval(video_length=15.0, target_clip_length=45.0)
        self.assertTrue(needs_loop)
        self.assertEqual(start, 0.0)

    def test_long_background_returns_valid_interval(self):
        # 600s background video, 40s clip
        start, end, needs_loop = self.mgr.get_safe_background_interval(video_length=600.0, target_clip_length=40.0)
        self.assertFalse(needs_loop)
        self.assertGreaterEqual(start, 0.0)
        self.assertLessEqual(end, 600.0)
        self.assertAlmostEqual(end - start, 40.0, places=2)

    def test_anti_repetition_history_tracking(self):
        # Multiple requests should record distinct intervals
        intervals = []
        for _ in range(5):
            s, e, loop = self.mgr.get_safe_background_interval(video_length=1200.0, target_clip_length=30.0)
            intervals.append((s, e))

        self.assertEqual(len(self.mgr.used_history), 5)
        # Verify not all start times are identical
        starts = [x[0] for x in intervals]
        self.assertGreater(len(set(starts)), 1)

    def test_build_extract_background_filter(self):
        filt_normal = self.mgr.build_extract_background_filter(start_time=12.5, duration=30.0, needs_loop=False)
        self.assertIn("trim=start=12.50:duration=30.00", filt_normal)
        self.assertIn("scale=1080:1920", filt_normal)

        filt_loop = self.mgr.build_extract_background_filter(start_time=0.0, duration=45.0, needs_loop=True)
        self.assertIn("loop=loop=-1", filt_loop)


class TestRedditCardRenderer(unittest.TestCase):
    def test_generate_transparent_reddit_card_png(self):
        output_png = "test_reddit_card_tmp.png"
        try:
            path = generate_transparent_reddit_card_png(
                title="What is the most bizarre fact you know that sounds completely fake?",
                subreddit="AskReddit",
                author="u/DeepCuriosity",
                upvotes="42.8k",
                comments="3.4k",
                output_path=output_png,
                card_width=940,
            )
            self.assertTrue(os.path.exists(path))
            with Image.open(path) as img:
                self.assertEqual(img.mode, "RGBA")
                self.assertEqual(img.width, 940)
                self.assertGreater(img.height, 200)
        finally:
            if os.path.exists(output_png):
                os.remove(output_png)

    def test_build_reddit_card_ffmpeg_filter(self):
        filter_str = build_reddit_card_ffmpeg_filter(
            card_png_path="assets/card.png",
            display_duration=3.5,
            fade_duration=0.35,
            y_pos=600,
        )
        self.assertIn("fade=t=in:st=0:d=0.35:alpha=1", filter_str)
        self.assertIn("fade=t=out:st=3.15:d=0.35:alpha=1", filter_str)
        self.assertIn("overlay=(W-w)/2:600:enable='between(t,0,3.50)'", filter_str)

    def test_ffmpeg_graph_gameplay_start_seconds_integration(self):
        from render.ffmpeg_graph import gameplay_start_seconds
        start = gameplay_start_seconds(clip_duration=300.0, need=45.0, scene_index=0)
        self.assertGreaterEqual(start, 0.0)
        self.assertLessEqual(start, 255.0)

    def test_ffmpeg_graph_gameplay_loop_when_short(self):
        from render.ffmpeg_graph import gameplay_start_seconds
        # When background clip is shorter than need (10s < 45s), start must be 0.0 without crashing
        start = gameplay_start_seconds(clip_duration=10.0, need=45.0, scene_index=0)
        self.assertEqual(start, 0.0)


if __name__ == "__main__":
    unittest.main()
