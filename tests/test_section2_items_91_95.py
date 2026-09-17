"""
Unit tests for Section 2 Items 91 - 95:
91. Metin Üstü Dinamik Vurgu (Text Highlighting - ASS dynamic color and pulse scale)
92. Kenar Çerçevesi (Border Vignette - FFmpeg vignette=0.18 filter)
93. Ses İçi Nefes ve Duraklama Sentezi (TTS Natural Pauses: 150ms break and '...')
94. Metinleri Resim Olarak Basmama (Vector ASS with ScaledBorderAndShadow)
95. Çift Stok Katmanı (Picture-in-Picture / PIP Analytical Card or B-roll)
"""
import unittest
import os
import tempfile
from moviepy.editor import ColorClip

from subtitle_generator import create_karaoke_subtitles, hex_to_ass_color
from effects_engine import get_ffmpeg_vignette_filter, apply_pip_overlay
from voice_humanizer import VoiceHumanizer
import config

class TestSection2Items91To95(unittest.TestCase):

    def test_item_91_dynamic_text_highlighting(self):
        """Item 91: Word-by-word karaoke highlight with dynamic highlight color and micro-pulse scaling."""
        timings = [
            {"text": "Büyük", "offset": 0.0, "duration": 0.4},
            {"text": "Roma", "offset": 0.4, "duration": 0.5},
            {"text": "İmparatorluğu", "offset": 0.9, "duration": 0.7}
        ]
        with tempfile.NamedTemporaryFile(suffix=".ass", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            create_karaoke_subtitles(
                timings,
                tmp_path,
                style_opts={"color": "#FFFFFF", "highlight_color": "#00FF66"}
            )
            with open(tmp_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Verify green highlight color was converted to ASS format (&H0066FF00&)
            green_ass = hex_to_ass_color("#00FF66")
            self.assertIn(green_ass, content, "ASS should contain configured highlight color")

            # Verify pulse scale tags (\fscx106\fscy106)
            self.assertIn(r"\fscx106\fscy106", content, "Dynamic pulse zoom should be applied to active word")
            self.assertIn(r"\fscx100\fscy100", content, "Normal scale should reset after active word")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_item_92_border_vignette_filter(self):
        """Item 92: Generates subtle FFmpeg vignette filter (angle ~ 0.18 for ~4% shadow)."""
        vignette_vf = get_ffmpeg_vignette_filter(angle=0.18)
        self.assertEqual(vignette_vf, "vignette=0.180")

        # Check default value
        default_vf = get_ffmpeg_vignette_filter()
        self.assertTrue(default_vf.startswith("vignette="))

    def test_item_93_tts_natural_pauses(self):
        """Item 93: Injects natural pauses and breaths into TTS text (150ms break or '...')."""
        sample_text = "Tarihin en büyük sırrı açığa çıktı! Marcus Aurelius, bu kurallara sadık kaldı."

        # 1. Plain TTS mode ('...' injection)
        plain_spoken = VoiceHumanizer.synthesize_natural_pauses(sample_text, engine_type="plain", break_ms=150)
        self.assertIn("...", plain_spoken, "Plain TTS text should contain '...' pauses at punctuation marks")

        # 2. SSML mode (<break time="150ms"/> injection)
        ssml_spoken = VoiceHumanizer.synthesize_natural_pauses(sample_text, engine_type="ssml", break_ms=150)
        self.assertIn('<break time="150ms"/>', ssml_spoken, "SSML text should contain 150ms break elements")

    def test_item_94_vector_ass_subtitles(self):
        """Item 94: Subtitles are rendered as native vector ASS (not rasterized images) with ScaledBorderAndShadow."""
        timings = [
            {"text": "Vektörel", "offset": 0.0, "duration": 0.5},
            {"text": "Altyazı", "offset": 0.5, "duration": 0.5}
        ]
        with tempfile.NamedTemporaryFile(suffix=".ass", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            create_karaoke_subtitles(timings, tmp_path)
            with open(tmp_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Ensure Script Info specifies standard ASS vector properties
            self.assertIn("ScriptType: v4.00+", content)
            self.assertIn("ScaledBorderAndShadow: yes", content)
            self.assertIn("PlayResX: 1080", content)
            self.assertIn("PlayResY: 1920", content)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_item_95_picture_in_picture_pip_overlay(self):
        """Item 95: Picture-in-Picture corner graphic/card overlay composite."""
        clip = ColorClip(size=(720, 1280), color=(10, 10, 20), duration=2.0)
        try:
            pip_clip = apply_pip_overlay(clip, scale=0.28, duration=1.5)
            self.assertEqual(pip_clip.size, (720, 1280))
            self.assertEqual(len(pip_clip.clips), 2, "Composite should contain base clip + PIP card overlay")
            frame = pip_clip.get_frame(0.5)
            self.assertEqual(frame.shape, (1280, 720, 3))
        finally:
            clip.close()

if __name__ == "__main__":
    unittest.main()
