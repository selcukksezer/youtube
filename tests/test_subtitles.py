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

    def test_all_16_subtitle_presets_defined(self):
        """Chapter 4.5: All 16 predefined subtitle presets must exist and have required fields."""
        expected_16 = [
            "capcut_yellow", "cyber_green", "red_fire", "clean_white",
            "high_contrast_retention", "tiktok_bold", "mrbeast_style",
            "cinematic_minimal", "crypto_gold", "luxury_elegance",
            "horror_blood", "history_sepia", "space_neon_blue",
            "fitness_punch", "psychology_violet", "wisdom_emerald"
        ]
        for name in expected_16:
            self.assertIn(name, SUBTITLE_PRESETS, f"Missing preset: {name}")
            preset = SUBTITLE_PRESETS[name]
            self.assertIn("highlight_color", preset)
            self.assertIn("font_name", preset)
            self.assertIn("font_size", preset)

    def test_get_niche_subtitle_preset_mapping(self):
        """Chapter 4.5: Niches map to contextual subtitle presets."""
        from subtitle_generator import get_niche_subtitle_preset
        crypto = get_niche_subtitle_preset("crypto_finance")
        self.assertEqual(crypto["font_name"], "Montserrat")
        self.assertEqual(crypto["highlight_color"], "#FFCC00")
        self.assertEqual(crypto["stroke_color"], "#1A1400")
        self.assertFalse(crypto.get("glow"))

        horror = get_niche_subtitle_preset("dark_horror_cases")
        self.assertEqual(horror["highlight_color"], "#CC0000")

        wisdom = get_niche_subtitle_preset("stoic_philosophy")
        self.assertEqual(wisdom["highlight_color"], "#2ECC71")


    def test_karaoke_seamless_transitions_and_natural_durations(self):
        """Karaoke highlight smoothly transitions to next word without gaps or artificial 0.40s cap."""
        timings = [
            {"text": "Modern", "offset": 0.10, "duration": 0.68},
            {"text": "dünyanın", "offset": 0.78, "duration": 0.54},
            {"text": "açıklayamadığı", "offset": 1.32, "duration": 0.85},
        ]
        test_ass = "output/test_sync.ass"
        os.makedirs("output", exist_ok=True)
        try:
            create_karaoke_subtitles(timings, test_ass, style_opts=SUBTITLE_PRESETS["capcut_yellow"])
            with open(test_ass, "r", encoding="utf-8") as f:
                lines = [l for l in f.readlines() if l.startswith("Dialogue:")]
            self.assertEqual(len(lines), 3)
            # Line 0 should start at 0:00:00.10 and end at line 1 start 0:00:00.78
            self.assertIn("0:00:00.10,0:00:00.78", lines[0])
            # Line 1 should start at 0:00:00.78 and end at line 2 start 0:00:01.32
            self.assertIn("0:00:00.78,0:00:01.32", lines[1])
            # Line 2 should preserve natural long duration (> 0.40s)
            self.assertTrue(lines[2].startswith("Dialogue: 0,0:00:01.32,0:00:02.17"))
        finally:
            if os.path.exists(test_ass):
                os.remove(test_ass)

    def test_tts_estimate_word_timings_weighted(self):
        """Weighted estimation gives longer words and punctuated words more time than short words."""
        from tts_engine import _estimate_word_timings
        text = "Modern açıklayamadığı ve olay."
        durations = _estimate_word_timings(text, duration_sec=4.0)
        self.assertEqual(len(durations), 4)
        word_map = {w["text"]: w["duration"] for w in durations}
        # 'açıklayamadığı' (14 chars) must have significantly larger duration than 've' (2 chars)
        self.assertGreater(word_map["açıklayamadığı"], word_map["ve"] * 2.5)
        # Total span should equal duration_sec
        total_time = durations[-1]["offset"] + durations[-1]["duration"]
        self.assertAlmostEqual(total_time, 4.0, delta=0.1)

    def test_preset_ass_border_outline_and_shadow(self):
        """4.5: box, zero outline, and 45° shadow reach the ASS file."""
        os.makedirs("output", exist_ok=True)
        words = [{"text": "Altin", "offset": 0.0, "duration": 0.4}]
        cases = {
            "capcut_yellow": ("1", "4"),
            "cinematic_minimal": ("1", "0"),
            "mrbeast_style": ("3", "5"),
        }
        for key, (border, outline) in cases.items():
            path = f"output/test_preset_{key}.ass"
            try:
                create_karaoke_subtitles(words, path, style_opts=SUBTITLE_PRESETS[key])
                with open(path, encoding="utf-8") as f:
                    style = next(line for line in f if line.startswith("Style: K,"))
                fields = style.strip().split(",")
                self.assertEqual(fields[15], border, key)
                self.assertEqual(fields[16], outline, key)
                self.assertEqual(fields[-1], "1", key)
                self.assertNotEqual(fields[-2], "1", key)
            finally:
                if os.path.exists(path):
                    os.remove(path)
        path = "output/test_preset_crypto.ass"
        try:
            create_karaoke_subtitles(words, path, style_opts=SUBTITLE_PRESETS["crypto_gold"])
            with open(path, encoding="utf-8") as f:
                body = f.read()
            self.assertIn(hex_to_ass_color("#FFCC00"), body)
            self.assertNotIn("\\xshad", body)
        finally:
            if os.path.exists(path):
                os.remove(path)
        path = "output/test_preset_tiktok.ass"
        try:
            create_karaoke_subtitles(words, path, style_opts=SUBTITLE_PRESETS["tiktok_bold"])
            with open(path, encoding="utf-8") as f:
                body = f.read()
            self.assertIn(hex_to_ass_color("#FFE600"), body)
            self.assertNotIn("\\1a&HFF&", body)
            self.assertNotIn("\\blur", body)
        finally:
            if os.path.exists(path):
                os.remove(path)


if __name__ == "__main__":
    unittest.main()

