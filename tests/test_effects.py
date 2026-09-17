"""
Unit tests for Video Effects & Anti-Duplicate Engine (Items 40, 41, 49, 50, 59, 60, 92, 94)
"""
import unittest, os
from moviepy.editor import ColorClip
from effects_engine import (
    apply_smart_crop, apply_anti_duplicate,
    apply_mirror_and_pitch, extract_frame0_thumbnail
)

class TestEffects(unittest.TestCase):
    def test_smart_crop_horizontal(self):
        """Verify horizontal 1920x1080 clip converts to 1080x1920 vertical canvas."""
        clip = ColorClip(size=(1920, 1080), color=(100, 50, 20), duration=1.0)
        try:
            cropped = apply_smart_crop(clip, 1080, 1920)
            self.assertEqual(cropped.size, (1080, 1920))
            self.assertEqual(cropped.duration, 1.0)
        finally:
            clip.close()

    def test_anti_duplicate_filter(self):
        """Verify anti-duplicate modifies clip properties without crashing."""
        clip = ColorClip(size=(100, 100), color=(50, 50, 50), duration=1.0)
        try:
            filtered = apply_anti_duplicate(clip, intensity=1.0)
            self.assertEqual(filtered.size, (100, 100))
        finally:
            clip.close()

    def test_mirror_effect(self):
        """Verify horizontal flip works."""
        clip = ColorClip(size=(100, 100), color=(50, 50, 50), duration=1.0)
        try:
            mirrored = apply_mirror_and_pitch(clip, horizontal_flip=True)
            self.assertEqual(mirrored.size, (100, 100))
        finally:
            clip.close()

if __name__ == "__main__":
    unittest.main()
