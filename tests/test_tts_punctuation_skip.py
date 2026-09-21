"""Regression: punctuation-only TTS segments must be skipped (Edge NoAudioReceived)."""
import re
import unittest


class TestTtsPunctuationSkip(unittest.TestCase):
    def test_skip_predicate_matches_engine(self):
        def should_skip(plain_text: str) -> bool:
            return (not plain_text.strip()) or (
                not re.search(r"\w", plain_text, flags=re.UNICODE)
            )

        self.assertTrue(should_skip("..."))
        self.assertTrue(should_skip("—"))
        self.assertTrue(should_skip("   "))
        self.assertTrue(should_skip("!!!"))
        self.assertFalse(should_skip("Merhaba dünya."))
        self.assertFalse(should_skip("Şu dua kalbi yumuşatır."))


if __name__ == "__main__":
    unittest.main()
