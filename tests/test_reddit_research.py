"""Tests for public Reddit research source handling."""
import unittest
from unittest.mock import patch

from reddit_client import fetch_public_posts


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {"data": {"children": [{"data": {
            "id": "abc", "title": "A real public post", "selftext": "x" * 120,
            "score": 7, "permalink": "/r/AITA/comments/abc/test", "over_18": False
        }}]}}


class TokenResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {"access_token": "test-token"}


class TestRedditResearch(unittest.TestCase):
    @patch("reddit_client.requests.post", return_value=TokenResponse())
    @patch("reddit_client.requests.get", return_value=FakeResponse())
    @patch("reddit_client.config.REDDIT_CLIENT_SECRET", "test-secret")
    @patch("reddit_client.config.REDDIT_CLIENT_ID", "test-id")
    def test_public_post_is_mapped_for_source_selection(self, _get, _post):
        posts = fetch_public_posts("AITA")
        self.assertEqual(posts[0]["subreddit"], "AITA")
    @patch("reddit_client.config.REDDIT_CLIENT_SECRET", "")
    @patch("reddit_client.config.REDDIT_CLIENT_ID", "")
    def test_auto_discovery_without_credentials(self):
        """Kullanıcı Reddit API anahtarı girmese bile sistem otomatik viral gönderi bulmalı."""
        posts = fetch_public_posts("confession", limit=2)
        self.assertGreaterEqual(len(posts), 1)
        self.assertEqual(posts[0]["subreddit"], "confession")
        self.assertTrue(len(posts[0]["title"]) > 10)
        self.assertTrue(len(posts[0]["body"]) > 50)
        self.assertGreater(posts[0]["score"], 1000)


if __name__ == "__main__":
    unittest.main()