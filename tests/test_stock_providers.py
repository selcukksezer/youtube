"""Stock provider adapter tests."""
import unittest
from unittest.mock import patch

from stock_providers import search_mixkit, search_pexels


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {"videos": [{"id": 1, "width": 1080, "height": 1920, "duration": 8, "video_files": [{"width": 1080, "height": 1920, "link": "https://example.invalid/clip.mp4"}]}]}


class FakeHtmlResponse:
    status_code = 200
    text = 'https://assets.mixkit.co/videos/test.mp4'


class TestStockProviders(unittest.TestCase):
    @patch("stock_providers.config.PEXELS_API_KEY", "test-key")
    @patch("stock_providers.requests.get", return_value=FakeResponse())
    def test_pexels_results_use_common_candidate_shape(self, _get):
        result = search_pexels("city")
        self.assertEqual(result[0]["source"], "pexels")
        self.assertEqual(result[0]["url"], "https://example.invalid/clip.mp4")

    @patch("stock_providers.requests.get", return_value=FakeHtmlResponse())
    def test_mixkit_identity_is_deterministic_for_history_tracking(self, _get):
        self.assertEqual(search_mixkit("City Night")[0]["id"], "mx_city-night_0")


if __name__ == "__main__":
    unittest.main()