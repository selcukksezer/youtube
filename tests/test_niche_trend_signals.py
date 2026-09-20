"""Tests for niche-family trend signal generation (stoic must not get news clickbait)."""
import unittest
from unittest.mock import patch

from services.niche_trend_signals import (
    MAX_TREND_CARDS,
    SOURCE_AI,
    generate_synthetic_trend_signals,
    is_stoic_banned_title,
)
NEWS_TEMPLATE_WORDS = (
    "skandal",
    "24 saat",
    "viral",
    "breaking",
    "son dakika",
    "flaş",
    "bomba",
    "sarsan",
    "olay",
)


class TestNicheTrendSignals(unittest.TestCase):
    def test_stoic_banned_detector(self):
        self.assertTrue(is_stoic_banned_title("24 Saat İçinde Viral Olan Stoacılık Skandalı"))
        self.assertFalse(is_stoic_banned_title("Marcus Aurelius'un Öfkeyi Yok Eden 3 Stoacı Kuralı"))

    @patch("services.topic_suggester.suggest_topics")
    def test_stoic_synthetic_returns_five_without_news_templates(self, mock_suggest):
        mock_suggest.return_value = {
            "status": "ok",
            "suggestions": [
                {"title": "Marcus Aurelius'un Öfkeyi Yok Eden 3 Stoacı Kuralı"},
                {"title": "Seneca'nın Kaygıyı Yok Eden 4 Stoacı Tekniği"},
                {"title": "Epiktetos: Kontrol Edebileceğin Tek Şey Bu"},
                {"title": "Stoacıların Asla Şikayet Etmeme Sırrı"},
                {"title": "2000 Yıllık Bu Stoacı Kural Hayatını Değiştirir"},
            ],
        }
        trends = generate_synthetic_trend_signals("6_stoic_philosophy")

        self.assertEqual(len(trends), MAX_TREND_CARDS)
        for trend in trends:
            low = trend["title"].casefold()
            for word in NEWS_TEMPLATE_WORDS:
                self.assertNotIn(word, low, msg=trend["title"])
            self.assertEqual(trend.get("channel"), "")
            self.assertEqual(trend.get("view_count"), 0)
            self.assertEqual(trend.get("source_type"), SOURCE_AI)

    def test_content_gap_rejects_stoic_news_clickbait(self):
        from research_service import build_content_gap_suggestions

        suggestions = build_content_gap_suggestions(
            "Stoacılıkta öfke kontrolü\n24 Saat İçinde Viral Olan Stoacılık Skandalı",
            "6_stoic_philosophy",
        )
        topics = {item["topic"] for item in suggestions}
        self.assertIn("Stoacılıkta öfke kontrolü", topics)
        self.assertTrue(all("skandal" not in t.casefold() for t in topics))


if __name__ == "__main__":
    unittest.main()
