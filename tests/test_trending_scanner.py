import unittest
from unittest.mock import patch

from trending_scanner import _get_fallback_viral_trends, scan_youtube_shorts_trends


class TestTrendingScanner(unittest.TestCase):
    def test_scan_failure_is_logged_and_returns_fallback(self):
        fallback = [{"title": "Fallback trend"}]
        with patch("trending_scanner.requests.get", side_effect=RuntimeError("network unavailable")):
            with patch("trending_scanner._get_fallback_viral_trends", return_value=fallback) as fallback_mock:
                with self.assertLogs("trending_scanner", level="WARNING") as captured:
                    result = scan_youtube_shorts_trends("space")

        self.assertEqual(result, fallback)
        self.assertIn("YouTube Shorts trend scan failed", captured.output[0])
        fallback_mock.assert_called_once_with("space")

    def test_autocomplete_failure_is_logged_and_uses_generated_fallback(self):
        with patch(
            "research_service.fetch_youtube_autocomplete_suggestions",
            side_effect=RuntimeError("autocomplete unavailable"),
        ):
            with self.assertLogs("trending_scanner", level="WARNING") as captured:
                cards = _get_fallback_viral_trends("space")

        self.assertTrue(cards)
        self.assertIn("YouTube autocomplete fallback failed", captured.output[0])


if __name__ == "__main__":
    unittest.main()
