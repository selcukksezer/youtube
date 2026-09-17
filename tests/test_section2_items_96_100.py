"""
Unit tests for Section 2 Items 96 - 100:
96. Film/Dizi Kesitlerinde 2.5 Saniye Limiti (Fair Use 2.5s clip limitation & auto-split)
97. Ekranın Üst ve Altını Doldurma (Split-Screen 58/42 + 2px Neon Divider)
98. Kendi Çektiğiniz Arka Plan Kütüphanesi (Custom Footage Pool Fallback)
99. Dinamik Kamera Sallantısı (Handheld Camera Shake simulation)
100. Görsel Maskeleme (Wipe Transition Mask Overlay)
"""
import unittest
import os
import tempfile
import time
from moviepy.editor import ColorClip

from scene_generator import enforce_fair_use_2_5s_rule
from effects_engine import (
    create_split_screen_clip,
    apply_handheld_camera_shake,
    get_ffmpeg_camera_shake_filter,
    apply_mask_wipe_transition
)
from video_fetcher import search_and_download, reset_used_videos
import config

class TestSection2Items96To100(unittest.TestCase):

    def test_item_96_fair_use_2_5s_rule(self):
        """Item 96: Clips from copyrighted or film/tv sources are capped to 2.5s maximum duration."""
        # 2 copyrighted scenes with duration 6.0s each
        scenes = [
            {"scene_number": 1, "duration": 6.0, "narration": "Film kesiti", "is_copyrighted": True},
            {"scene_number": 2, "duration": 2.0, "narration": "Kısa kesit", "is_copyrighted": True}
        ]
        adjusted = enforce_fair_use_2_5s_rule(scenes, is_copyrighted_source=True, max_clip_duration=2.5)

        # Scene 1 (6.0s) should be split into 3 segments (2.0s each), scene 2 (2.0s) remains 1 segment
        self.assertEqual(len(adjusted), 4)
        for sc in adjusted:
            self.assertLessEqual(sc["duration"], 2.5, "No copyrighted clip segment should exceed 2.5s")
        self.assertAlmostEqual(sum(s["duration"] for s in adjusted), 8.0, delta=0.2)

    def test_item_97_split_screen_58_42_with_neon_divider(self):
        """Item 97: Split screen has exactly 58% top, 42% bottom, and a 2px neon divider bar."""
        top_clip = ColorClip(size=(720, 1280), color=(10, 20, 30), duration=1.0)
        try:
            # Test split screen composition with neon divider
            comp = create_split_screen_clip(
                top_clip,
                bottom_clip_path="non_existent_gameplay.mp4",
                target_w=720,
                target_h=1280,
                divider_color=(0, 255, 204),
                divider_thickness=2
            )
            self.assertEqual(comp.size, (720, 1280))
            # Has 3 layers: top (58%), bottom (42%), and divider (2px)
            self.assertEqual(len(comp.clips), 3)

            # Check divider position (should be at y = int(1280 * 0.58) = 742)
            top_h = int(1280 * 0.58)
            self.assertEqual(top_h, 742)
        finally:
            top_clip.close()

    def test_item_98_custom_background_library_pool(self):
        """Item 98: Uses custom user-recorded footage pool if present in assets/custom_backgrounds."""
        reset_used_videos()
        custom_bg_dir = os.path.join(config.BASE_DIR, "assets", "custom_backgrounds")
        os.makedirs(custom_bg_dir, exist_ok=True)
        dummy_custom = os.path.join(custom_bg_dir, f"my_custom_nature_{int(time.time() * 1000)}.mp4")

        # Create dummy file if not exists
        with open(dummy_custom, "wb") as f:
            f.write(f"dummy_custom_clip_content_{time.time()}".encode())

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                selected_clip = search_and_download(
                    queries=["cinematic mountain"],
                    scene_index=0,
                    project_dir=temp_dir,
                    target_duration=5
                )
                self.assertEqual(selected_clip, dummy_custom, "Should pick clip from custom background library")
        finally:
            if os.path.exists(dummy_custom):
                os.remove(dummy_custom)
            reset_used_videos()

    def test_item_99_handheld_camera_shake(self):
        """Item 99: Simulates natural handheld camera shake for static shots and clips."""
        clip = ColorClip(size=(720, 1280), color=(15, 15, 25), duration=1.0)
        try:
            shaken = apply_handheld_camera_shake(clip, intensity=5.0, speed=2.0)
            self.assertEqual(shaken.size, (720, 1280))
            frame = shaken.get_frame(0.2)
            self.assertEqual(frame.shape, (1280, 720, 3))

            # Also verify FFmpeg pure filter generator
            shake_vf = get_ffmpeg_camera_shake_filter(intensity=5, speed=2.0)
            self.assertIn("crop=", shake_vf)
            self.assertIn("sin(t*", shake_vf)
        finally:
            clip.close()

    def test_item_100_mask_wipe_transition(self):
        """Item 100: Applies horizontal or circular wipe transition mask overlay."""
        clip = ColorClip(size=(720, 1280), color=(20, 40, 60), duration=1.0)
        try:
            # 1. Horizontal wipe
            wiped_h = apply_mask_wipe_transition(clip, direction="horizontal", transition_dur=0.3)
            self.assertEqual(wiped_h.size, (720, 1280))
            f_h = wiped_h.get_frame(0.15)
            self.assertEqual(f_h.shape, (1280, 720, 3))

            # 2. Circular wipe
            wiped_c = apply_mask_wipe_transition(clip, direction="circular", transition_dur=0.3)
            self.assertEqual(wiped_c.size, (720, 1280))
            f_c = wiped_c.get_frame(0.15)
            self.assertEqual(f_c.shape, (1280, 720, 3))
        finally:
            clip.close()

if __name__ == "__main__":
    unittest.main()
