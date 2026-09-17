"""
Unit tests for Automation, RSS, Batch and Quota Tracking (Items 51-58, 62, 69, 70, 77, 78)
"""
import unittest
from rss_scanner import DEFAULT_RSS_FEEDS, clean_html
from batch_processor import batch_manager
from quota_manager import quota_tracker
from notifications import send_telegram_message

class TestAutomation(unittest.TestCase):
    def test_default_rss_feeds_structure(self):
        """Verify default RSS sources exist and have valid URLs."""
        self.assertIn("aa_guncel", DEFAULT_RSS_FEEDS)
        self.assertIn("bbc_turkce", DEFAULT_RSS_FEEDS)
        for k, v in DEFAULT_RSS_FEEDS.items():
            self.assertTrue(v["url"].startswith("http"))

    def test_clean_html(self):
        """Verify HTML stripping from news descriptions."""
        raw = "<p>Bu bir <b>haber</b> özetidir &quot;flaş&quot;.</p>"
        clean = clean_html(raw)
        self.assertEqual(clean, 'Bu bir haber özetidir "flaş".')

    def test_batch_manager_parse_text(self):
        """Verify newline separated topics get enqueued properly."""
        raw_text = "Konu 1: Okyanus Sırları\nKonu 2: Karadelikler\nKonu 3: Antik Mısır"
        jobs = batch_manager.parse_text_lines(raw_text, default_niche="6_stoic_philosophy", language="tr")
        self.assertEqual(len(jobs), 3)
        self.assertEqual(jobs[0]["topic"], "Konu 1: Okyanus Sırları")
        self.assertEqual(jobs[0]["niche"], "6_stoic_philosophy")

    def test_quota_tracker(self):
        """Verify API quota tracking counts calls and errors."""
        quota_tracker.record_call("Gemini")
        quota_tracker.record_call("Gemini")
        quota_tracker.record_error("Gemini", "Rate limit")
        stats = quota_tracker.get_stats()
        self.assertGreaterEqual(stats["usage"].get("Gemini", 0), 2)
        self.assertGreaterEqual(stats["errors"].get("Gemini", 0), 1)

if __name__ == "__main__":
    unittest.main()
