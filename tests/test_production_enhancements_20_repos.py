"""
Unit and integration tests for 20-Repo Master Plan Production Enhancements:
1. Paket 1: ASS Dynamic Karaoke Bounce/Pop Subtitle Tags
2. Paket 2: Smart Fit & Fill Gaussian Blur for Horizontal Assets
3. Paket 4: Smooth Cosine Ease-in-out Ken Burns Camera Curves
4. Paket 5: Manifest Deduplication & Single Source Integrity
"""

import os
import unittest
from unittest.mock import patch, MagicMock

from render.ffmpeg_graph import (
    cheap_pan_filter,
    build_scene_filter_chain,
    _probe_is_landscape,
)
from subtitle_generator import (
    _active_word_tags,
    create_karaoke_subtitles,
)
from effects.kinetic_subtitle_pager import KineticPage, KineticWord


class TestProductionEnhancements20Repos(unittest.TestCase):

    def test_cheap_pan_filter_uses_cosine_ease_in_out(self):
        """Paket 4: cheap_pan_filter uses smooth cosine ease-in-out curves."""
        filt_0 = cheap_pan_filter(1080, 1920, duration=4.0, scene_index=0)
        filt_1 = cheap_pan_filter(1080, 1920, duration=4.0, scene_index=1)
        filt_2 = cheap_pan_filter(1080, 1920, duration=4.0, scene_index=2)
        filt_3 = cheap_pan_filter(1080, 1920, duration=4.0, scene_index=3)

        # Check for smooth cosine ease-in-out expression
        for f in (filt_0, filt_1, filt_2, filt_3):
            self.assertIn("cos(PI*", f)
            self.assertIn("min(t\\,", f)
            self.assertIn("scale=", f)
            self.assertIn("crop=", f)

    def test_build_scene_filter_chain_fit_and_fill(self):
        """Paket 2: fit_and_fill splits stream, blurs background, and fits foreground."""
        chain_normal = build_scene_filter_chain(
            input_index=0, duration=3.0, width=1080, height=1920, scene_index=0, fit_and_fill=False
        )
        self.assertNotIn("boxblur", chain_normal)
        self.assertIn("scale=1080:1920:force_original_aspect_ratio=increase", chain_normal)

        chain_blur = build_scene_filter_chain(
            input_index=0, duration=3.0, width=1080, height=1920, scene_index=0, fit_and_fill=True
        )
        self.assertIn("boxblur=25:5", chain_blur)
        self.assertIn("force_original_aspect_ratio=decrease", chain_blur)
        self.assertIn("overlay=(W-w)/2:(H-h)/2", chain_blur)

    def test_probe_is_landscape(self):
        """Paket 2: _probe_is_landscape identifies horizontal videos correctly."""
        self.assertFalse(_probe_is_landscape(""))
        self.assertFalse(_probe_is_landscape("nonexistent_file.mp4"))

        # Mock ffmpeg probe returning 1920x1080 (landscape)
        mock_res_land = MagicMock()
        mock_res_land.stderr = "Stream #0:0: Video: h264, yuv420p, 1920x1080 [SAR 1:1 DAR 16:9], 30 fps"
        with patch("subprocess.run", return_value=mock_res_land), patch("os.path.exists", return_value=True):
            self.assertTrue(_probe_is_landscape("dummy_16_9.mp4"))

        # Mock ffmpeg probe returning 1080x1920 (portrait)
        mock_res_vert = MagicMock()
        mock_res_vert.stderr = "Stream #0:0: Video: h264, yuv420p, 1080x1920 [SAR 1:1 DAR 9:16], 30 fps"
        with patch("subprocess.run", return_value=mock_res_vert), patch("os.path.exists", return_value=True):
            self.assertFalse(_probe_is_landscape("dummy_9_16.mp4"))

    def test_active_word_tags_bounce_animation(self):
        """Paket 1: _active_word_tags includes ASS scale pop animation tags."""
        open_tag, close_tag = _active_word_tags("&H00D7FF&", "&H00FFFFFF&", glow=True, word="test", bounce=True)
        self.assertIn(r"\t(0,70,\fscx115\fscy115)", open_tag)
        self.assertIn(r"\t(70,140,\fscx106\fscy106)", open_tag)
        self.assertIn(r"\fscx100\fscy100", close_tag)

        # When bounce is False, tag should not include \t scale pop
        open_tag_nobounce, _ = _active_word_tags("&H00D7FF&", "&H00FFFFFF&", glow=False, word="test", bounce=False)
        self.assertNotIn(r"\t(0,70,\fscx115\fscy115)", open_tag_nobounce)

    def test_kinetic_page_to_ass_dialogue_bounce(self):
        """Paket 1: KineticPage supports optional bounce pop in to_ass_dialogue."""
        page = KineticPage(
            page_index=0,
            start_ms=0,
            end_ms=1000,
            words=[KineticWord("Hello", 0, 500), KineticWord("World", 500, 1000)],
        )
        ass_normal = page.to_ass_dialogue(bounce=False)
        self.assertNotIn(r"\fscx115", ass_normal)
        self.assertIn(r"{\k50}Hello", ass_normal)

        ass_bounce = page.to_ass_dialogue(bounce=True)
        self.assertIn(r"\fscx115", ass_bounce)
        self.assertIn(r"{\k50\t(0,70,\fscx115\fscy115)", ass_bounce)


if __name__ == "__main__":
    unittest.main()
