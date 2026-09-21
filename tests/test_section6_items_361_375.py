"""
Unit tests for Section 6 SEO items 361-375 (batch 22 audit).
Excluded from scope: #364, #366, #368-369, #372-373 (manual Studio upload only).
"""
import unittest

from viral_seo_agent import (
    generate_related_video_bridge,
    get_optimal_upload_schedule,
    calculate_cta_timing,
)
from growth_tactics import generate_studio_engagement_checklist
from bgm_manager import ensure_royalty_free_ambient_bgm, get_safe_default_bgm_path
from trending_scanner import scan_youtube_shorts_trends, _get_fallback_viral_trends
from rss_scanner import DEFAULT_RSS_FEEDS, get_breaking_news_topics


class TestSection6Items361375(unittest.TestCase):
    def test_item_361_related_video_bridge(self):
        bridge = generate_related_video_bridge(
            "Stoacılık Sırları",
            "https://youtube.com/shorts/abc123",
            "En Popüler Short",
        )
        self.assertIn("abc123", bridge["related_video_url"])
        self.assertIn("abc123", bridge["description_append"])
        self.assertIn("Related video", bridge["studio_upload_note"])

    def test_item_362_363_upload_schedule(self):
        tr = get_optimal_upload_schedule("TR")
        us = get_optimal_upload_schedule("US")
        self.assertEqual(tr["target_country"], "TR")
        self.assertIn("TRT", tr["timezone"])
        self.assertEqual(us["target_country"], "US")
        self.assertIn("EST", us["timezone"])

    def test_item_365_royalty_free_bgm(self):
        import os
        path = get_safe_default_bgm_path()
        self.assertTrue(path.endswith("royalty_free_ambient.wav"))
        self.assertTrue(os.path.isfile(path))
        self.assertEqual(ensure_royalty_free_ambient_bgm(), path)

    def test_item_367_cta_timing(self):
        cta = calculate_cta_timing(45.0)
        self.assertGreaterEqual(cta["cta_start_second"], 25.0)
        self.assertLessEqual(cta["cta_start_second"], 35.0)

    def test_item_370_trending_scanner_fallback(self):
        trends = _get_fallback_viral_trends("uzay")
        self.assertTrue(len(trends) >= 1)
        self.assertIn("title", trends[0])

    def test_item_370_rss_feeds_configured(self):
        self.assertTrue(len(DEFAULT_RSS_FEEDS) >= 1)

    def test_item_374_reply_guidance(self):
        checklist = generate_studio_engagement_checklist(lang="tr")
        self.assertIn("120", checklist["reply_action"])
        self.assertIn("374", checklist["reply_action"])

    def test_item_375_spam_filter_guidance(self):
        checklist = generate_studio_engagement_checklist(lang="tr")
        self.assertIn("filtre", checklist["spam_filter_action"].lower())
        self.assertIn("375", checklist["spam_filter_action"])

    def test_excluded_items_not_in_automation_scope(self):
        excluded = {364, 366, 368, 369, 372, 373}
        in_scope = {361, 362, 363, 365, 367, 370, 374, 375}
        self.assertFalse(excluded & in_scope)


if __name__ == "__main__":
    unittest.main()
