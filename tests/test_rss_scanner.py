import unittest
from unittest.mock import Mock, patch

from rss_scanner import fetch_rss_feed


class TestRssScanner(unittest.TestCase):
    def test_non_success_status_is_logged_and_uses_fallback(self):
        response = Mock(status_code=503)
        with patch("rss_scanner.requests.get", return_value=response):
            with self.assertLogs("rss_scanner", level="WARNING") as captured:
                items = fetch_rss_feed("https://example.com/feed.xml")

        self.assertTrue(items)
        self.assertIn("RSS feed returned HTTP 503", captured.output[0])

    def test_request_failure_is_logged_and_uses_fallback(self):
        with patch("rss_scanner.requests.get", side_effect=RuntimeError("network unavailable")):
            with self.assertLogs("rss_scanner", level="WARNING") as captured:
                items = fetch_rss_feed("https://example.com/feed.xml")

        self.assertTrue(items)
        self.assertIn("RSS feed fetch failed", captured.output[0])


if __name__ == "__main__":
    unittest.main()
