"""
Unit tests for Karaoke Subtitles & Presets (Items 42, 43, 93)
"""
import unittest, os
from subtitle_generator import (
    create_karaoke_subtitles, create_srt_file,
    SUBTITLE_PRESETS, hex_to_ass_color
)

class TestSubtitles(unittest.TestCase):
    def test_presets_exist(self):
        """Verify all subtitle presets are defined with highlight colors."""
        self.assertIn("capcut_yellow", SUBTITLE_PRESETS)
        self.assertIn("cyber_green", SUBTITLE_PRESETS)
        self.assertIn("red_fire", SUBTITLE_PRESETS)
        self.assertIn("clean_white", SUBTITLE_PRESETS)

    def test_hex_to_ass_color(self):
        """Verify hex to ASS format conversion."""
        res = hex_to_ass_color("#FF0000") # Red
        self.assertEqual(res, "&H000000FF&")

    def test_create_karaoke_subtitles_file(self):
        """Verify ASS file is written with events."""
        timings = [
            {"text": "Bunu", "offset": 0.0, "duration": 0.3},
            {"text": "asla", "offset": 0.3, "duration": 0.4},
            {"text": "unutmayın!", "offset": 0.7, "duration": 0.5}
        ]
        test_ass = "output/test_sample.ass"
        os.makedirs("output", exist_ok=True)
        try:
            create_karaoke_subtitles(timings, test_ass, style_opts=SUBTITLE_PRESETS["capcut_yellow"])
            self.assertTrue(os.path.exists(test_ass))
            with open(test_ass, "r", encoding="utf-8") as f:
                content = f.read()
                self.assertIn("[V4+ Styles]", content)
                self.assertIn("Dialogue:", content)
        finally:
            if os.path.exists(test_ass):
                os.remove(test_ass)

if __name__ == "__main__":
    unittest.main()
