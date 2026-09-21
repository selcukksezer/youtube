"""
Unit tests for Section 6 SEO items 346-360 (batch 21 audit).
Excluded from scope: #354-357, #359-360 (manual Studio upload only).
"""
import unittest
from unittest.mock import patch

from viral_seo_agent import (
    finalize_seo_title,
    enforce_title_length_limit,
    format_capital_hook_word,
    inject_curiosity_words,
    enforce_three_hashtag_rule,
    build_natural_seo_description,
    get_channel_master_keywords,
    generate_viral_seo_metadata,
)
from research_service import align_title_to_youtube_search, _autocomplete_overlap_score
from growth_tactics import generate_studio_engagement_checklist


class TestSection6Items346360(unittest.TestCase):
    def test_item_346_title_length_via_finalize(self):
        long_title = "Bu Antik Roma İmparatoru Marcus Aurelius'un Hayat Değiştiren 5 Büyük Felsefi Kuralı #Shorts"
        result = finalize_seo_title(long_title)
        self.assertLessEqual(len(result), 60)
        self.assertIn("#Shorts", result)

    def test_item_347_capital_in_finalize_pipeline(self):
        result = finalize_seo_title("Bu kuralı asla unutmayın #Shorts")
        self.assertIn("ASLA", result)

    def test_item_348_curiosity_wired_in_finalize(self):
        result = finalize_seo_title("Roma Taktikleri #Shorts")
        curious = ["Gizli", "Yasaklanan", "Bilinmeyen", "Şok Eden", "Akıl Almaz", "Gözden Kaçan"]
        self.assertTrue(any(w in result for w in curious))

    def test_item_349_three_hashtag_rule(self):
        tags = enforce_three_hashtag_rule("", niche_tag="stoic", general_tag="viral")
        parts = tags.split()
        self.assertEqual(len(parts), 3)
        self.assertEqual(parts[0], "#Shorts")

    def test_item_350_pinned_comment_in_metadata(self):
        meta = generate_viral_seo_metadata("Epiktetos")
        self.assertIn("pinned_comment", meta)
        self.assertGreater(len(meta["pinned_comment"]), 10)
        self.assertIn("?", meta["pinned_comment"])

    def test_item_351_studio_engagement_checklist(self):
        checklist = generate_studio_engagement_checklist(lang="tr")
        self.assertIn("kalp", checklist["heart_action"].lower())
        self.assertIn("sabitle", checklist["pinned_comment_action"].lower())

    def test_item_352_natural_description(self):
        desc = build_natural_seo_description(
            keyword="Stoacılık",
            hook="Zihin gücünün 3 temel kuralı.",
            source_name="Akademik Kaynak",
        )
        self.assertIn("Stoacılık", desc)
        self.assertIn("📌 Kaynak & Araştırma:", desc)
        self.assertIn("#Shorts", desc)

    @patch("research_service.fetch_youtube_autocomplete_suggestions")
    def test_item_353_align_title_to_autocomplete(self, mock_fetch):
        mock_fetch.return_value = [
            "stoacılık nedir",
            "stoacılık felsefesi",
            "stoacılık sözleri",
        ]
        align = align_title_to_youtube_search("stoacılık", "Stoacılık Felsefesi Rehberi")
        self.assertIn("stoacılık", align["aligned_title"].lower())
        self.assertTrue(align["item_353_compliant"])
        self.assertGreaterEqual(align["match_score"], 0.5)

    def test_item_353_overlap_score_helper(self):
        score = _autocomplete_overlap_score("stoacılık felsefesi", "stoacılık felsefesi rehberi")
        self.assertGreaterEqual(score, 0.5)

    def test_item_358_channel_master_keywords(self):
        kw = get_channel_master_keywords("stoic philosophy")
        self.assertEqual(len(kw), 10)
        self.assertIn("stoacılık", kw)

    def test_excluded_items_not_auto_upload_scope(self):
        """354-357, 359-360 are manual Studio upload — no automation assertions here."""
        excluded = {354, 355, 356, 357, 359, 360}
        in_scope = {346, 347, 348, 349, 350, 351, 352, 353, 358}
        self.assertFalse(excluded & in_scope)


if __name__ == "__main__":
    unittest.main()
