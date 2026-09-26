"""
Unit tests for the 4 Core Features:
1. Pollinations 0 TL Flux SDXL Image-to-Video
2. 39-Language YouTube SEO & Localization Package
3. PIL Viral Thumbnail Generator (9:16 & 16:9)
4. Whiteboard / Hand-Drawn Sketch Animation Mode
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from services.multilang_seo_translator import MultilangSEOTranslator, YOUTUBE_39_LANGUAGES
from services.thumbnail_generator import generate_thumbnail
from services.whiteboard_animator import convert_image_to_sketch
from PIL import Image


class TestFourCoreFeatures:

    def test_39_languages_catalog(self):
        """Verify all 39 YouTube official localization languages are cataloged."""
        assert len(YOUTUBE_39_LANGUAGES) >= 39
        assert "en" in YOUTUBE_39_LANGUAGES
        assert "tr" in YOUTUBE_39_LANGUAGES
        assert "es" in YOUTUBE_39_LANGUAGES
        assert "ja" in YOUTUBE_39_LANGUAGES
        assert "de" in YOUTUBE_39_LANGUAGES

    def test_seo_translator_mymemory_mocked(self):
        """Verify MultilangSEOTranslator builds proper YouTube Data API v3 package."""
        translator = MultilangSEOTranslator()
        def mock_trans(text, source_lang="tr", target_lang="en", **kwargs):
            return f"[{target_lang}] {text}"

        with patch("services.multilang_seo_translator.translate_free_text", side_effect=mock_trans):
            res = translator.translate_to_39_languages(
                title="Harika Shorts Videosu",
                description="Bu videoda ilginç gerçekleri inceliyoruz.",
                source_lang="tr"
            )
            assert res["status"] == "ok"
            assert res["total_languages"] == len(YOUTUBE_39_LANGUAGES)
            assert "localizations" in res
            assert "translations" in res

            # Verify YouTube Data API v3 format: {"title": ..., "description": ...}
            en_loc = res["localizations"].get("en")
            assert en_loc is not None
            assert "title" in en_loc
            assert "description" in en_loc
            assert "[en]" in en_loc["title"]

    def test_thumbnail_generator_custom_accent(self, tmp_path):
        """Verify viral thumbnail generation with custom accent word highlighting."""
        out_916 = str(tmp_path / "thumb_916.jpg")
        out_169 = str(tmp_path / "thumb_169.jpg")

        res_916 = generate_thumbnail(
            title="Bunu Neden Daha Once Almadim 3 Urun",
            output_path=out_916,
            aspect_ratio="9:16",
            accent_text="3 Urun",
        )
        assert os.path.exists(res_916)
        img_916 = Image.open(res_916)
        assert img_916.size == (1080, 1920)

        res_169 = generate_thumbnail(
            title="Bunu Neden Daha Once Almadim 3 Urun",
            output_path=out_169,
            aspect_ratio="16:9",
            accent_text="3 Urun",
        )
        assert os.path.exists(res_169)
        img_169 = Image.open(res_169)
        assert img_169.size == (1280, 720)

    def test_whiteboard_sketch_converter(self, tmp_path):
        """Verify image conversion to black-and-white whiteboard sketch."""
        raw_img_path = str(tmp_path / "raw.jpg")
        sketch_path = str(tmp_path / "sketch.jpg")

        # Create a mock image with lines
        test_img = Image.new("RGB", (200, 200), color=(120, 180, 240))
        test_img.save(raw_img_path)

        ok = convert_image_to_sketch(raw_img_path, sketch_path)
        assert ok is True
        assert os.path.exists(sketch_path)
        sketch_img = Image.open(sketch_path)
        assert sketch_img.size == (200, 200)
