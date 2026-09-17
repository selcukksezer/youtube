"""Reddit research-card render test."""
import os
import tempfile
import unittest

from reddit_card_renderer import generate_reddit_post_card_clip


class TestRedditCardRenderer(unittest.TestCase):
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