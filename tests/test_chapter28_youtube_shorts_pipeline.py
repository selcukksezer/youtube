"""
Tests for Chapter 28.10 / Section 2.1 (Item 10):
reference_repos/youtube-shorts-pipeline evolution:
- effects/ticker.py: generate_news_ticker_image, build_news_ticker_ffmpeg_filter, is_ticker_enabled_for_niche
- services/niche_guardrails.py: extended niche guidelines (news, education, fitness, comedy, science)
  and validate_script_niche_compliance
"""

import os
import unittest
from unittest.mock import patch, MagicMock
from PIL import Image

from effects.ticker import (
    generate_news_ticker_image,
    build_news_ticker_ffmpeg_filter,
    is_ticker_enabled_for_niche,
)
from services.niche_guardrails import (
    get_niche_visual_rules,
    validate_script_niche_compliance,
)


class TestYouTubeShortsPipelineTicker(unittest.TestCase):
    def setUp(self):
        self.tmp_ticker_png = "assets/temp_test_ticker.png"

    def tearDown(self):
        if os.path.exists(self.tmp_ticker_png):
            try:
                os.remove(self.tmp_ticker_png)
            except Exception:
                pass

    def test_generate_news_ticker_image(self):
        out = generate_news_ticker_image(
            headline="MERKEZ BANKASI KRİTİK FAİZ KARARINI AÇIKLADI!",
            output_path=self.tmp_ticker_png,
            category="SON DAKİKA",
            width=1080,
            height=130,
        )
        self.assertEqual(out, self.tmp_ticker_png)
        self.assertTrue(os.path.isfile(out))

        with Image.open(out) as img:
            self.assertEqual(img.size, (1080, 130))
            self.assertEqual(img.mode, "RGBA")

    def test_build_news_ticker_ffmpeg_filter(self):
        flt, tag = build_news_ticker_ffmpeg_filter(
            ticker_png_path="ticker.png",
            video_input_tag="0:v",
            overlay_input_index=1,
            out_tag="out_tick",
            y_pos=240,
            enable_start=0.5,
            enable_end=15.0,
        )
        self.assertEqual(tag, "out_tick")
        self.assertIn("[0:v][1:v]overlay=x=0:y=240", flt)
        self.assertIn("between(t,0.50,15.00)", flt)
        self.assertIn("[out_tick]", flt)

    def test_is_ticker_enabled_for_niche(self):
        self.assertTrue(is_ticker_enabled_for_niche("1_news_flash"))
        self.assertTrue(is_ticker_enabled_for_niche("news"))
        self.assertTrue(is_ticker_enabled_for_niche("finance"))
        self.assertFalse(is_ticker_enabled_for_niche("6_stoic_philosophy"))
        self.assertFalse(is_ticker_enabled_for_niche("minecraft"))


class TestNicheGuardrailsAndCompliance(unittest.TestCase):
    def test_extended_niche_guidelines(self):
        news_rules = get_niche_visual_rules("1_news_flash")
        self.assertEqual(news_rules["caption_color"], "#FF1744")
        self.assertTrue(news_rules.get("has_ticker"))

        edu_rules = get_niche_visual_rules("education")
        self.assertEqual(edu_rules["caption_color"], "#FFD600")

        fitness_rules = get_niche_visual_rules("fitness")
        self.assertEqual(fitness_rules["caption_color"], "#FF5722")

        science_rules = get_niche_visual_rules("science")
        self.assertEqual(science_rules["caption_color"], "#00E5FF")

    def test_script_compliance_violations_and_cleanup(self):
        dirty_script = (
            "Merhaba arkadaşlar, bu videoda sizlere kripto para anlatacağım. "
            "Bu kesinlikle bir yatırım tavsiyesi ve garanti kazanç sağlayacak. "
            "Kanalıma abone olmayı unutmayın!"
        )
        result = validate_script_niche_compliance(dirty_script, niche_id="finance", lang="tr")
        self.assertFalse(result["compliant"])
        self.assertGreaterEqual(len(result["violations"]), 2)

        cleaned = result["cleaned_text"]
        self.assertNotIn("abone olmayı unutmayın", cleaned.lower())
        self.assertNotIn("yatırım tavsiyesi", cleaned.lower())
        self.assertNotIn("garanti kazanç", cleaned.lower())

    def test_clean_script_passes_compliance(self):
        clean_script = (
            "Kripto piyasasında son 24 saatte beklenmedik bir likidite kırılması yaşandı. "
            "Verilere göre büyük cüzdanlar pozisyonlarını yeniden dengeliyor."
        )
        result = validate_script_niche_compliance(clean_script, niche_id="finance", lang="tr")
        self.assertTrue(result["compliant"])
        self.assertEqual(len(result["violations"]), 0)

    @patch("os.path.exists", return_value=True)
    @patch("subprocess.Popen")
    def test_ffmpeg_graph_news_ticker_wiring(self, mock_popen, mock_exists):
        from render.ffmpeg_graph import render_with_ffmpeg_graph
        mock_proc = MagicMock()
        mock_proc.poll.return_value = 0
        mock_proc.returncode = 0
        mock_proc.stdout.readline.return_value = ""
        mock_proc.stderr.read.return_value = ""
        mock_popen.return_value = mock_proc

        clips = [
            {"path": "clip1.mp4", "duration": 4.0, "narration": "Haber metni"},
        ]
        with patch("render.ffmpeg_graph._probe_has_audio", return_value=True), \
             patch("render.ffmpeg_graph.os.path.getsize", return_value=204800):
            res = render_with_ffmpeg_graph(
                clips=clips,
                audio_path="speech.wav",
                output_path="out.mp4",
                enable_news_ticker=True,
                news_ticker_text="FLAŞ HABER: BÜYÜK GELİŞME",
            )
            self.assertEqual(res, "out.mp4")
            cmd = mock_popen.call_args[0][0]
            cmd_str = " ".join(cmd)
            self.assertIn("news_ticker.png", cmd_str)
            self.assertIn("vticker", cmd_str)

    def test_video_render_request_ticker_fields(self):
        from api_models import VideoRenderRequest
        req = VideoRenderRequest(
            keyword="Deprem",
            enable_news_ticker=True,
            news_ticker_text="AFAD SON DAKİKA AÇIKLAMASI",
        )
        self.assertTrue(req.enable_news_ticker)
        self.assertEqual(req.news_ticker_text, "AFAD SON DAKİKA AÇIKLAMASI")


if __name__ == "__main__":
    unittest.main()
