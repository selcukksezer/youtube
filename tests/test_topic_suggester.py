"""Tests for advanced niche-aware topic suggestion pipeline."""
import unittest
from unittest.mock import DEFAULT, patch

from services.topic_suggester import (
    suggest_topics,
    _score_candidate,
    _niche_context_words,
    _generate_seed_based_topics,
    _fetch_youtube_candidates,
    _fetch_google_trend_candidates,
    _slugify_topic,
    SOURCE_AI,
    SOURCE_GOOGLE_TRENDS,
    SOURCE_YOUTUBE,
)


class TestTopicSuggester(unittest.TestCase):
    def setUp(self):
        source_patches = patch.multiple(
            "services.topic_suggester",
            _fetch_youtube_candidates=DEFAULT,
            _fetch_google_trend_candidates=DEFAULT,
            _fetch_rss_candidates=DEFAULT,
            _fetch_trend_candidates=DEFAULT,
            _fetch_reddit_candidates=DEFAULT,
            _generate_ai_candidates=DEFAULT,
        )
        self.sources = source_patches.start()
        self.addCleanup(source_patches.stop)
        for source in self.sources.values():
            source.return_value = []

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

    def test_seed_marker_cannot_bypass_cross_niche_classification(self):
        ctx = _niche_context_words("10_religious_quotes")
        item = _score_candidate(
            "Uçuşunuz rötara uğradığında havayolundan tazminat alma yolları",
            "10_religious_quotes",
            SOURCE_AI,
            ctx,
            set(),
            {"is_seed_tailored": True, "viral_score": 99},
        )
        self.assertIsNone(item)

    def test_religious_seed_fallback_does_not_invent_hadith_citations(self):
        self.assertEqual(
            _generate_seed_based_topics(
                "Peygamberimizin sabır hakkındaki hadisi",
                "10_religious_quotes",
                count=5,
                language="tr",
            ),
            [],
        )

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

    def test_off_niche_user_hint_is_not_seeded_or_passed_to_ai(self):
        hint = "Uçuşunuz Rötara Uğradığında Havayolundan Alabileceğiniz Gizli Tazminat Hakkı"
        with patch("services.topic_suggester._generate_ai_candidates", return_value=[]) as ai, \
             patch("services.topic_suggester._collect_used_topics", return_value=set()):
            result = suggest_topics(
                "10_religious_quotes",
                language="tr",
                count=5,
                topic_hint=hint,
            )

        ai.assert_called_once_with("10_religious_quotes", "tr", 5, "")
        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["topic_hint_ignored"])
        self.assertEqual(len(result["suggestions"]), 5)
        self.assertTrue(all(
            "uçuş" not in item["title"].casefold()
            and "tazminat" not in item["title"].casefold()
            for item in result["suggestions"]
        ))
        self.assertTrue(all(item["niche_aligned"] for item in result["suggestions"]))

    def test_seed_hint_contributes_at_most_one_template_and_confidence_is_calibrated(self):
        hint = "Peygamberimizin sabır hakkındaki hadisi"
        with patch("services.topic_suggester._generate_ai_candidates", return_value=[]), \
             patch("services.topic_suggester._collect_used_topics", return_value=set()):
            result = suggest_topics(
                "10_religious_quotes",
                language="tr",
                count=5,
                topic_hint=hint,
            )

        self.assertEqual(result["status"], "ok")
        self.assertFalse(result["topic_hint_ignored"])
        self.assertEqual(len(result["suggestions"]), 5)
        self.assertLessEqual(
            sum(hint.casefold() in item["title"].casefold() for item in result["suggestions"]),
            1,
        )
        self.assertTrue(all(len(item["title"]) <= 75 for item in result["suggestions"]))
        self.assertTrue(all(item["confidence"] <= 95 for item in result["suggestions"]))

    def test_suggestions_mix_live_sources_and_report_source_counts(self):
        self.sources["_fetch_youtube_candidates"].return_value = [{
            "title": "Stoacılık öfke kontrolü: 3 pratik yöntem",
            "source": SOURCE_YOUTUBE,
            "source_detail": "YouTube arama önerisi",
        }]
        self.sources["_fetch_google_trend_candidates"].return_value = [{
            "title": "Stoacılıkta günlük disiplin ve huzur",
            "source": SOURCE_GOOGLE_TRENDS,
            "source_detail": "Google Trends · yaklaşık trafik 20K+",
        }]
        self.sources["_generate_ai_candidates"].return_value = [{
            "title": "Marcus Aurelius'un zor günler için disiplin kuralı",
            "source": SOURCE_AI,
        }]

        result = suggest_topics("6_stoic_philosophy", count=3)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(len(result["suggestions"]), 3)
        sources = {item["source"] for item in result["suggestions"]}
        self.assertEqual(sources, {SOURCE_YOUTUBE, SOURCE_GOOGLE_TRENDS, SOURCE_AI})
        self.assertEqual(result["source_counts"], {
            SOURCE_YOUTUBE: 1,
            SOURCE_GOOGLE_TRENDS: 1,
            SOURCE_AI: 1,
        })
        self.assertEqual(
            next(item for item in result["suggestions"] if item["source"] == SOURCE_GOOGLE_TRENDS)["source_detail"],
            "Google Trends · yaklaşık trafik 20K+",
        )
        self.sources["_fetch_reddit_candidates"].assert_not_called()

    def test_youtube_fallback_cards_are_not_mislabeled_as_live_evidence(self):
        synthetic_card = {
            "title": "Stoacılık Hakkında Muhtemelen Bilmediğiniz 5 Şaşırtıcı Gerçek",
            "video_id": "trend_1",
            "channel": "Viral Studio",
            "view_count": "1.5M izlenme",
            "url": "https://www.youtube.com/hashtag/shorts",
        }
        with patch("services.topic_suggester.fetch_youtube_autocomplete_suggestions", return_value=[]), \
             patch("services.topic_suggester.scan_youtube_shorts_trends", return_value=[synthetic_card]):
            candidates = _fetch_youtube_candidates("6_stoic_philosophy", "tr", 5)

        self.assertEqual(candidates, [])

    def test_google_trends_collector_uses_selected_language_region(self):
        trend = type("Trend", (), {
            "to_dict": lambda self: {
                "title": "Stoicism discipline habits",
                "trending_score": 0.9,
                "metadata": {"traffic": "20K+"},
            },
        })()
        with patch("services.autonomous_topic_engine.AutonomousTopicEngine") as engine:
            engine.return_value.fetch_google_trends.return_value = [trend]
            candidates = _fetch_google_trend_candidates("en")

        engine.assert_called_once_with(timeout=4.0)
        engine.return_value.fetch_google_trends.assert_called_once_with(geo="US", limit=8)
        self.assertEqual(candidates[0]["source"], SOURCE_GOOGLE_TRENDS)
        self.assertIn("20K+", candidates[0]["source_detail"])

    def test_never_returns_generic_hook_variants_or_duplicate_hooks(self):
        with patch("services.topic_suggester._collect_used_topics", return_value=set()):
            result = suggest_topics("10_religious_quotes", language="tr", count=10)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(len(result["suggestions"]), 10)
        hooks = [item["hook"] for item in result["suggestions"]]
        self.assertEqual(len(set(hooks)), 10, "Every topic card must have a unique hook")
        for item in result["suggestions"]:
            self.assertNotIn("bu duaya amin deyin", item["title"].casefold())
            self.assertNotIn("bu hadis-i şerifini biliyor muydunuz", item["title"].casefold())
            self.assertTrue(item.get("summary"))
            self.assertTrue(item.get("angle"))
            self.assertTrue(item.get("keywords"))
            self.assertTrue(item.get("scope"))
            self.assertTrue(item.get("why_viral"))

    def test_exclude_titles_returns_fresh_non_overlapping_batch(self):
        with patch("services.topic_suggester._collect_used_topics", wraps=lambda exclude_titles=None: {t.casefold() for t in (exclude_titles or [])}):
            first = suggest_topics("10_religious_quotes", language="tr", count=8)
            first_titles = [item["title"] for item in first["suggestions"]]
            second = suggest_topics(
                "10_religious_quotes",
                language="tr",
                count=8,
                exclude_titles=first_titles,
            )
            second_titles = [item["title"] for item in second["suggestions"]]
        self.assertEqual(len(first_titles), 8)
        self.assertEqual(len(second_titles), 8)
        self.assertTrue(set(first_titles).isdisjoint(set(second_titles)))

    def test_rejects_noisy_youtube_autocomplete_fragments(self):
        with patch(
            "services.topic_suggester.fetch_youtube_autocomplete_suggestions",
            return_value=[
                "hadis-i şerif işin bereketsiz olması ne demektir",
                "hadis nedir kısaca diyanet",
                "Hz. Peygamber'in 'Ameller Niyetlere Göredir' Hadisi (Buhari)",
            ],
        ), patch("services.topic_suggester.scan_youtube_shorts_trends", return_value=[]):
            cands = _fetch_youtube_candidates("10_religious_quotes", "tr", 5)
        titles = [c["title"] for c in cands]
        self.assertEqual(len(titles), 1)
        self.assertIn("Ameller Niyetlere Göredir", titles[0])

    def test_all_curated_vault_titles_respect_length_limit(self):
        from services.niche_topic_vault import CURATED_NICHE_TOPICS, CURATED_NICHE_TOPICS_EN

        for niche_id, titles in CURATED_NICHE_TOPICS.items():
            for title in titles:
                self.assertLessEqual(
                    len(title),
                    75,
                    f"TR vault title too long ({len(title)} chars) in {niche_id}: {title}",
                )
        for niche_id, titles in CURATED_NICHE_TOPICS_EN.items():
            for title in titles:
                self.assertLessEqual(
                    len(title),
                    75,
                    f"EN vault title too long ({len(title)} chars) in {niche_id}: {title}",
                )


if __name__ == "__main__":
    unittest.main()
