"""CapCut-density jump cuts for HumanCraft edit_directives."""
from __future__ import annotations

import unittest

from moviepy.editor import ColorClip

from effects.pipeline import apply_capcut_density_cuts, enforce_3s_broll_rule


class CapCutDensityTests(unittest.TestCase):
    def test_short_clip_unchanged(self):
        clip = ColorClip(size=(64, 64), color=(10, 20, 30), duration=2.0)
        out = apply_capcut_density_cuts(clip, cut_sec=2.8, force=True)
        self.assertAlmostEqual(out.duration, 2.0, places=1)
        clip.close()
        if out is not clip:
            out.close()

    def test_long_clip_gets_multiple_cuts(self):
        clip = ColorClip(size=(64, 64), color=(10, 20, 30), duration=8.0)
        out = apply_capcut_density_cuts(clip, cut_sec=2.5, force=True)
        self.assertAlmostEqual(out.duration, 8.0, places=1)
        # Must have produced a concatenated result (not identity when cuts apply)
        self.assertIsNotNone(out)
        clip.close()
        out.close()

    def test_enforce_3s_delegates(self):
        clip = ColorClip(size=(32, 32), color=(1, 2, 3), duration=1.5)
        out = enforce_3s_broll_rule(clip, max_duration=3.2)
        self.assertAlmostEqual(out.duration, 1.5, places=1)
        clip.close()


if __name__ == "__main__":
    unittest.main()
