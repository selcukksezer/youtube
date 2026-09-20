"""
Unit tests for Karaoke Subtitles & Presets (Items 42, 43, 93)
"""
import re
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

    def test_ass_uppercase_for_capcut_preset(self):
        """CapCut preset renders all subtitle words in uppercase."""
        timings = [
            {"text": "dünyanın", "offset": 0.0, "duration": 0.3},
            {"text": "en", "offset": 0.3, "duration": 0.2},
            {"text": "büyük", "offset": 0.5, "duration": 0.3},
        ]
        test_ass = "output/test_upper.ass"
        os.makedirs("output", exist_ok=True)
        try:
            create_karaoke_subtitles(timings, test_ass, style_opts=SUBTITLE_PRESETS["capcut_yellow"])
            with open(test_ass, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("DÜNYANIN", content)
            self.assertIn("BÜYÜK", content)
            self.assertNotIn("dünyanın", content)
        finally:
            if os.path.exists(test_ass):
                os.remove(test_ass)

    def test_glow_tags_for_capcut_preset(self):
        """CapCut preset adds neon glow ASS override tags on active word."""
        timings = [{"text": "test", "offset": 0.0, "duration": 0.5}]
        test_ass = "output/test_glow.ass"
        os.makedirs("output", exist_ok=True)
        try:
            create_karaoke_subtitles(timings, test_ass, style_opts=SUBTITLE_PRESETS["capcut_yellow"])
            with open(test_ass, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn(r"\blur3", content)
            self.assertIn(r"\shad2", content)
            self.assertIn(r"\be1", content)
        finally:
            if os.path.exists(test_ass):
                os.remove(test_ass)

    def test_max_four_words_per_dialogue_line(self):
        """Items 206/265: at most 4 words per karaoke dialogue line."""
        timings = [
            {"text": f"kelime{i}", "offset": i * 0.25, "duration": 0.25}
            for i in range(10)
        ]
        test_ass = "output/test_words.ass"
        os.makedirs("output", exist_ok=True)
        try:
            create_karaoke_subtitles(timings, test_ass, style_opts=SUBTITLE_PRESETS["capcut_yellow"])
            with open(test_ass, "r", encoding="utf-8") as f:
                content = f.read()
            for line in content.splitlines():
                if not line.startswith("Dialogue:"):
                    continue
                text_part = line.split(",,")[-1]
                plain = re.sub(r"\{[^}]*\}", "", text_part)
                words = [w for w in plain.split() if w.strip()]
                self.assertLessEqual(len(words), 4, f"Too many words in line: {plain}")
        finally:
            if os.path.exists(test_ass):
                os.remove(test_ass)

    def test_preset_includes_font_and_layout_defaults(self):
        """Presets expose font_name, uppercase, glow, y_position."""
        capcut = SUBTITLE_PRESETS["capcut_yellow"]
        self.assertEqual(capcut["font_name"], "Anton")
        self.assertTrue(capcut["uppercase"])
        self.assertTrue(capcut["glow"])
        self.assertAlmostEqual(capcut["y_position"], 0.75)

if __name__ == "__main__":
    unittest.main()
