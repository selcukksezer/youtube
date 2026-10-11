"""Reddit research-card render test."""
import os
import tempfile
import unittest
from unittest.mock import patch

from reddit_card_renderer import (
    build_reddit_card_metadata,
    generate_reddit_post_card_clip,
    generate_transparent_reddit_card_png,
)


class TestRedditCardRenderer(unittest.TestCase):
    def test_generates_png_in_unique_temp_path_when_output_is_omitted(self):
        path = generate_transparent_reddit_card_png(
            "A temporary card",
            source_label="Test source",
        )
        try:
            self.assertTrue(os.path.isfile(path))
            self.assertTrue(path.endswith("_reddit_card.png"))
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_card_metadata_discloses_only_verified_post_metrics(self):
        verified = build_reddit_card_metadata(
            {
                "source": "oauth",
                "title": "Actual title",
                "subreddit": "AskReddit",
                "author": "real_author",
                "score": 7,
                "num_comments": 12,
            },
            fallback_title="Fallback",
        )
        self.assertEqual(verified["title"], "Actual title")
        self.assertEqual(verified["author"], "u/real_author")
        self.assertEqual(verified["upvotes"], "7")
        self.assertEqual(verified["comments"], "12")

        synthetic = build_reddit_card_metadata(
            {
                "source": "ai_discovery",
                "title": "Generated title",
                "author": "fabricated_author",
                "score": 50000,
                "num_comments": 1000,
            },
            fallback_title="Fallback",
        )
        self.assertIsNone(synthetic["author"])
        self.assertIsNone(synthetic["upvotes"])
        self.assertIsNone(synthetic["comments"])
        self.assertIn("gerçek gönderi değil", synthetic["source_label"])

        archived = build_reddit_card_metadata(
            {
                "source": "curated_archive",
                "title": "Archived title",
                "author": "fabricated_author",
                "score": 50000,
                "num_comments": 1000,
            },
            fallback_title="Fallback",
        )
        self.assertIsNone(archived["author"])
        self.assertIsNone(archived["upvotes"])
        self.assertIsNone(archived["comments"])
        self.assertIn("gerçek gönderi değil", archived["source_label"])

    def test_card_without_metadata_does_not_draw_fake_author_or_metrics(self):
        with tempfile.TemporaryDirectory() as directory:
            output_path = os.path.join(directory, "reddit-card.png")
            with patch("reddit_card_renderer.ImageDraw.Draw") as draw_factory:
                generate_transparent_reddit_card_png(
                    "Test title",
                    output_path=output_path,
                    source_label="Kaynak doğrulanmadı",
                )

            rendered_text = [
                call.args[1]
                for call in draw_factory.return_value.text.call_args_list
            ]
            self.assertIn("Kaynak doğrulanmadı", rendered_text)
            self.assertFalse(any("CuriousThinker" in text for text in rendered_text))
            self.assertFalse(any("32.4k" in text or "1.8k" in text for text in rendered_text))

    def test_generates_a_playable_mp4(self):
        with tempfile.TemporaryDirectory() as directory:
            output_path = os.path.join(directory, "reddit-card.mp4")
            result = generate_reddit_post_card_clip(
                {"subreddit": "stories", "title": "Başlık", "body": "Kaynak metin."},
                output_path,
                duration=0.2,
            )
            self.assertEqual(result, output_path)
            self.assertGreater(os.path.getsize(output_path), 1000)


if __name__ == "__main__":
    unittest.main()