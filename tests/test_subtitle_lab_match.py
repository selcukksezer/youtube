"""Lab cards and ASS burn-in share static/js/subtitle-style-tokens.json."""
import os
import tempfile
import unittest

import config
from subtitle_generator import (
    SUBTITLE_STYLE_TOKENS,
    create_karaoke_subtitles,
    hex_to_ass_color,
    merge_studio_subtitle_opts,
)

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _style_fields(content: str):
    line = next(row for row in content.splitlines() if row.startswith("Style: K,"))
    return line.strip().split(",")


class TestSubtitleLabMatch(unittest.TestCase):
    def test_card_highlights_match_shared_tokens(self):
        html_path = os.path.join(_ROOT, "static", "index.html")
        with open(html_path, encoding="utf-8") as handle:
            html = handle.read()
        js_path = os.path.join(_ROOT, "static", "js", "audio-media.js")
        with open(js_path, encoding="utf-8") as handle:
            script = handle.read()
        self.assertIn("subtitle-style-tokens.json", script)
        self.assertNotIn("SUBTITLE_LAB_COLORS", script)
        for key, token in SUBTITLE_STYLE_TOKENS.items():
            marker = f'data-preset="{key}"'
            start = html.find(marker)
            self.assertGreaterEqual(start, 0, key)
            chunk = html[start:start + 700]
            self.assertIn(token["highlight_color"], chunk, key)

    def test_capcut_and_mrbeast_ass_fields_match_preview_tokens(self):
        play_h = int(config.get_target_resolution()[1])
        scale = play_h / 1920.0
        craft = {
            "color": "#FFFFFF",
            "highlight_color": "#FFD700",
            "stroke_color": "#000000",
            "stroke_width": 5,
            "font_size": 40,
            "font_name": "Anton",
            "uppercase": True,
            "glow": True,
            "bold": False,
            "y_position": 0.52,
            "human_craft": True,
            "allow_mid_frame": True,
        }
        samples = {
            "capcut_yellow": [
                {"text": "bunu", "offset": 0.0, "duration": 0.3},
                {"text": "asla", "offset": 0.3, "duration": 0.3},
                {"text": "unutmayin", "offset": 0.6, "duration": 0.4},
            ],
            "mrbeast_style": [
                {"text": "bu", "offset": 0.0, "duration": 0.3},
                {"text": "fark", "offset": 0.3, "duration": 0.4},
            ],
        }
        cyber = merge_studio_subtitle_opts(
            "cyber_green", font_size=54, y_position=0.8, craft_opts=craft,
        )
        self.assertEqual(cyber["highlight_color"], "#00FF66")
        self.assertEqual(cyber["y_position"], 0.8)
        self.assertTrue(cyber["glow"])

        for key, words in samples.items():
            token = SUBTITLE_STYLE_TOKENS[key]
            opts = merge_studio_subtitle_opts(
                key, font_size=54, y_position=0.8, craft_opts=craft,
            )
            self.assertEqual(opts["color"], token["color"])
            self.assertEqual(opts["highlight_color"], token["highlight_color"])
            self.assertEqual(opts["stroke_color"], token["stroke_color"])
            self.assertEqual(opts["stroke_width"], token["stroke_width"])
            self.assertEqual(bool(opts.get("glow")), bool(token.get("glow")))
            self.assertEqual(bool(opts.get("box")), bool(token.get("box")))
            self.assertEqual(bool(opts.get("bold", True)), bool(token.get("bold", True)))
            self.assertEqual(opts["font_size"], 54)
            self.assertEqual(opts["y_position"], 0.8)
            self.assertTrue(opts["honor_y_position"])

            handle = tempfile.NamedTemporaryFile(suffix=".ass", delete=False)
            path = handle.name
            handle.close()
            try:
                create_karaoke_subtitles(words, path, style_opts=opts)
                with open(path, encoding="utf-8") as ass_file:
                    content = ass_file.read()
            finally:
                if os.path.exists(path):
                    os.remove(path)

            fields = _style_fields(content)
            expected_font = str(max(18, int(54 * scale)))
            expected_outline = (
                "0" if int(token["stroke_width"]) <= 0
                else str(max(1, int(float(token["stroke_width"]) * scale)))
            )
            expected_margin = str(int(round((1.0 - 0.8) * play_h)))
            self.assertEqual(fields[2], expected_font, key)
            self.assertEqual(fields[3], hex_to_ass_color(token["color"]), key)
            self.assertEqual(fields[4], hex_to_ass_color(token["highlight_color"]), key)
            self.assertEqual(fields[5], hex_to_ass_color(token["stroke_color"]), key)
            self.assertEqual(fields[7], "-1" if token.get("bold", True) else "0", key)
            self.assertEqual(fields[15], "3" if token.get("box") else "1", key)
            self.assertEqual(fields[16], expected_outline, key)
            self.assertEqual(fields[17], "0", key)
            self.assertEqual(fields[21], expected_margin, key)
            if token.get("box"):
                self.assertEqual(fields[6], hex_to_ass_color(token.get("box_color") or "#000000"), key)
            else:
                self.assertEqual(fields[6], "&HFF000000&", key)
            self.assertIn(hex_to_ass_color(token["highlight_color"]), content, key)
            if token.get("glow"):
                self.assertIn(r"\blur3", content, key)
            else:
                self.assertNotIn(r"\blur", content, key)
            if key == "capcut_yellow":
                self.assertIn("ASLA", content)
            if key == "mrbeast_style":
                self.assertIn("FARK", content)


if __name__ == "__main__":
    unittest.main()
