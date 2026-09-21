"""
Unit tests for Section 4 retention overlays (Items 211, 212).
"""
import unittest
import numpy as np
from moviepy.editor import ColorClip

import config
from effects.motion import apply_censored_blur_bait
from effects.overlays import apply_neon_countdown_overlay, generate_neon_countdown_overlay


class TestSection4Items211212(unittest.TestCase):
    def test_item_211_censored_blur_bait(self):
        clip = ColorClip(size=(720, 1280), color=(80, 120, 200), duration=4.0)
        baited = apply_censored_blur_bait(clip, reveal_after=3.0)
        self.assertEqual(baited.size, (720, 1280))
        frame_blurred = baited.get_frame(0.5)
        frame_revealed = baited.get_frame(3.5)
        self.assertFalse(np.array_equal(frame_blurred, frame_revealed))

    def test_item_212_neon_countdown_overlay(self):
        overlay = generate_neon_countdown_overlay(1080, 1920, duration=3.0, fps=30.0)
        self.assertAlmostEqual(overlay.duration, 3.0, places=1)
        frame_three = overlay.get_frame(0.2)
        frame_one = overlay.get_frame(2.5)
        self.assertFalse(np.array_equal(frame_three, frame_one))

    def test_item_212_apply_neon_countdown_overlay(self):
        prev = getattr(config, "RENDER_SAFE_MODE", True)
        config.RENDER_SAFE_MODE = False
        try:
            clip = ColorClip(size=(720, 1280), color=(20, 20, 40), duration=5.0)
            clip.fps = 30
            out = apply_neon_countdown_overlay(clip, duration=3.0, position="top_right")
            self.assertEqual(out.duration, 5.0)
            self.assertEqual(out.size, (720, 1280))
            self.assertGreater(len(out.clips), 1)
        finally:
            config.RENDER_SAFE_MODE = prev


if __name__ == "__main__":
    unittest.main()
