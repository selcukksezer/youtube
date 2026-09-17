"""Tests for importing YouTube Studio Content gaps research."""
import unittest

from research_service import build_content_gap_suggestions


class TestContentGapResearch(unittest.TestCase):
    def test_normalizes_deduplicates_and_keeps_user_queries(self):
        suggestions = build_content_gap_suggestions(
            "1. Stoacılıkta öfke kontrolü\nStoacılıkta öfke kontrolü\n- Seneca ile kaygı yönetimi", "6_stoic_philosophy"
        )
        self.assertEqual(len(suggestions), 2)
        self.assertIn("Stoacılıkta öfke kontrolü", {item["topic"] for item in suggestions})

    def test_rejects_empty_and_overlong_entries(self):
        suggestions = build_content_gap_suggestions("ab\n" + "x" * 161, "1_news_flash")
        self.assertEqual(suggestions, [])


if __name__ == "__main__":
    unittest.main()