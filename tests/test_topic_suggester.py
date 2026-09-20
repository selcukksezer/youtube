"""Tests for advanced niche-aware topic suggestion pipeline."""
import unittest
from unittest.mock import patch

from services.topic_suggester import (
    suggest_topics,
    _score_candidate,
    _niche_context_words,
    _slugify_topic,
    SOURCE_AI,
    SOURCE_YOUTUBE,
)


class TestTopicSuggester(unittest.TestCase):
    def test_stoic_returns_five_suggestions(self):
        with patch("services.topic_suggester._fetch_youtube_candidates", return_value=[]), \
             patch("services.topic_suggester._fetch_trend_candidates", return_value=[]), \
             patch("services.topic_suggester._generate_ai_candidates") as mock_ai:
            mock_ai.return_value = [
                {"title": "Marcus Aurelius'un Öfkeyi Yok Eden 3 Stoacı Kuralı", "source": SOURCE_AI},
                {"title": "Seneca'nın Kaygıyı Yok Eden 4 Stoacı Tekniği", "source": SOURCE_AI},
                {"title": "Epiktetos: Kontrol Edebileceğin Tek Şey Bu", "source": SOURCE_AI},
                {"title": "Stoacıların Asla Şikayet Etmeme Sırrı", "source": SOURCE_AI},
                {"title": "2000 Yıllık Bu Stoacı Kural Hayatını Değiştirir", "source": SOURCE_AI},
            ]
            result = suggest_topics("6_stoic_philosophy", language="tr", count=5)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["niche_id"], "6_stoic_philosophy")
        self.assertEqual(len(result["suggestions"]), 5)
        for item in result["suggestions"]:
            self.assertIn("title", item)
            self.assertIn("source", item)
            self.assertIn("confidence", item)
            self.assertIn("format_fingerprint", item)

    def test_reddit_niche_alignment(self):
        with patch("services.topic_suggester._fetch_youtube_candidates", return_value=[]), \
             patch("services.topic_suggester._fetch_trend_candidates", return_value=[]), \
             patch("services.topic_suggester._fetch_reddit_candidates") as mock_reddit, \
             patch("services.topic_suggester._generate_ai_candidates", return_value=[]):
            mock_reddit.return_value = [
                {"title": "AITA: Düğünümde Kayınbiraderim Her Şeyi Mahvetti", "source": "reddit"},
                {"title": "Gizli Sırrımı 7 Yıl Sonra Eşime İtiraf Ettim", "source": "reddit"},
                {"title": "İş Yerinde Patronumu İfşa Ettim — Pişman mıyım?", "source": "reddit"},
                {"title": "Annem Benden Sakladığı DNA Testi Sonucunu Buldum", "source": "reddit"},
                {"title": "En Yakın Arkadaşımın Nişanında İtiraz Ettim", "source": "reddit"},
            ]
            result = suggest_topics("2_reddit_confessions", language="tr", count=5)
        self.assertEqual(result["status"], "ok")
        self.assertGreaterEqual(len(result["suggestions"]), 3)
        titles = {s["title"] for s in result["suggestions"]}
        self.assertTrue(any("AITA" in t or "itiraf" in t.lower() for t in titles))

    def test_rejects_generic_topics(self):
        ctx = _niche_context_words("6_stoic_philosophy")
        item = _score_candidate("test topic", "6_stoic_philosophy", SOURCE_AI, ctx, set())
        self.assertIsNone(item)

    def test_rejects_off_niche_without_overlap(self):
        ctx = _niche_context_words("6_stoic_philosophy")
        item = _score_candidate(
            "Bitcoin fiyat tahmini 2026 analiz raporu",
            "6_stoic_philosophy",
            SOURCE_AI,
            ctx,
            set(),
        )
        self.assertIsNone(item)

    def test_youtube_source_scored(self):
        ctx = _niche_context_words("6_stoic_philosophy")
        item = _score_candidate(
            "Marcus Aurelius Stoacılık disiplin kuralları",
            "6_stoic_philosophy",
            SOURCE_YOUTUBE,
            ctx,
            set(),
            {"youtube_url": "https://youtube.com/shorts/abc"},
        )
        self.assertIsNotNone(item)
        self.assertEqual(item["source"], SOURCE_YOUTUBE)
        self.assertGreater(item["confidence"], 50)

    def test_invalid_niche_returns_error(self):
        result = suggest_topics("nonexistent_niche_xyz")
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["suggestions"], [])

    def test_deduplication_against_used(self):
        title = "Marcus Aurelius'un Öfkeyi Yok Eden 3 Stoacı Kuralı"
        ctx = _niche_context_words("6_stoic_philosophy")
        used = {_slugify_topic(title)}
        item = _score_candidate(title, "6_stoic_philosophy", SOURCE_AI, ctx, used)
        self.assertIsNone(item)


if __name__ == "__main__":
    unittest.main()
