"""Tests for public Reddit research source handling."""
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from api_models import ScriptGenerateRequest
from reddit_client import fetch_public_posts
from routers.research_router import _is_nsfw_reddit_post, api_generate_script


class FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {"data": {"children": [{"data": {
            "id": "abc", "title": "A real public post", "selftext": "x" * 120,
            "score": 7, "author": "real_author", "num_comments": 12,
            "permalink": "/r/AITA/comments/abc/test", "over_18": False
        }}]}}


class TokenResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {"access_token": "test-token"}


class TestRedditResearch(unittest.TestCase):
    def test_explicitly_nsfw_reddit_post_is_rejected_before_script_generation(self):
        for flag in ("is_nsfw", "over_18"):
            for value in (True, 1, "true", " YES "):
                with self.subTest(flag=flag, value=value):
                    request = ScriptGenerateRequest(
                        keyword="Source story",
                        niche="2_reddit_confessions",
                        reddit_post={
                            "title": "Source story",
                            "body": "A long source story.",
                            flag: value,
                        },
                    )
                    with patch(
                        "routers.research_router.resolve_topic_intelligence",
                        return_value={"resolved_niche": "2_reddit_confessions"},
                    ) as resolve_topic, patch(
                        "routers.research_router.generate_reddit_rewrite_script",
                        side_effect=AssertionError("NSFW story reached the rewrite model"),
                    ) as rewrite_script:
                        with self.assertRaises(HTTPException) as raised:
                            api_generate_script(request)

                    self.assertEqual(raised.exception.status_code, 422)
                    resolve_topic.assert_not_called()
                    rewrite_script.assert_not_called()

    def test_safe_or_missing_nsfw_markers_are_not_rejected(self):
        for value in (False, 0, "false", None):
            with self.subTest(value=value):
                self.assertFalse(_is_nsfw_reddit_post({"over_18": value}))
        self.assertFalse(_is_nsfw_reddit_post({"title": "No NSFW metadata"}))

    @patch("reddit_client.requests.post", return_value=TokenResponse())
    @patch("reddit_client.requests.get", return_value=FakeResponse())
    @patch("reddit_client.config.REDDIT_CLIENT_SECRET", "test-secret")
    @patch("reddit_client.config.REDDIT_CLIENT_ID", "test-id")
    def test_public_post_is_mapped_for_source_selection(self, _get, _post):
        posts = fetch_public_posts("AITA")
        self.assertEqual(posts[0]["subreddit"], "AITA")
        self.assertEqual(posts[0]["author"], "real_author")
        self.assertEqual(posts[0]["num_comments"], 12)
        self.assertEqual(posts[0]["source"], "oauth")
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

    def test_curated_fallback_is_labeled_as_non_source_content(self):
        with patch("reddit_client.config.REDDIT_CLIENT_ID", ""), \
             patch("reddit_client.config.REDDIT_CLIENT_SECRET", ""), \
             patch("reddit_client.generate_ai_reddit_posts", return_value=[]), \
             patch("reddit_client._SEEN_POST_IDS", set()):
            posts = fetch_public_posts("confession", limit=1)

        self.assertEqual(posts[0]["source"], "curated_archive")


if __name__ == "__main__":
    unittest.main()