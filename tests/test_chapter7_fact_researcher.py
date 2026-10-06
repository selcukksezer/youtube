"""
Bölüm 7.4: Anti-Halüsinasyon İnternet Doğrulama Ajanı (FactResearcher) Test Paketi
- Sayısal, tarihsel ve süperlatif iddia çıkarımı
- Çok kaynaklı arama (DuckDuckGo HTML, DuckDuckGo Lite, Wikipedia Action API)
- Çapraz doğrulama ve güven skoru
- Teyitsiz iddiaların otomatik arındırılması (Sanitization)
- Director derleyicisi entegrasyonu
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.web_fact_researcher import (
    extract_claims_from_text,
    cross_verify_claim,
    sanitize_unverified_claims,
    verify_and_sanitize_scenes,
    research_topic_facts,
    format_research_prompt_context,
)
from director import compile_director_plan


class TestChapter7FactResearcher(unittest.TestCase):
    def test_extract_claims_from_text(self):
        """Metindeki sayısal, tarihsel ve süperlatif iddiaları ayıklama testi."""
        sample_text = (
            "İnsanların %99'u 1945 yılında gerçekleşen bu olayı bilmez. "
            "Yaklaşık 5 milyon kişi etkilendi ve tarihteki tek örnektir."
        )
        claims = extract_claims_from_text(sample_text)
        self.assertGreaterEqual(len(claims), 3)

        types = [c["type"] for c in claims]
        self.assertIn("percentage", types)
        self.assertIn("year", types)
        self.assertIn("metric", types)
        self.assertIn("superlative", types)

        pct_claim = next(c for c in claims if c["type"] == "percentage")
        self.assertEqual(pct_claim["value"], "99")

        year_claim = next(c for c in claims if c["type"] == "year")
        self.assertEqual(year_claim["value"], "1945")

    def test_wikipedia_or_ddg_research_snippets(self):
        """Çoklu sağlayıcı arama motorunun sonuç döndürmesi testi."""
        snippets = research_topic_facts("Marcus Aurelius", max_snippets=3)
        self.assertTrue(isinstance(snippets, list))
        # Ağ bağlantısı varsa en az 1 snippet gelmeli, yoksa boş liste güvenli dönmeli
        for s in snippets:
            self.assertGreaterEqual(len(s), 20)

    def test_format_research_prompt_context(self):
        """Anti-halüsinasyon prompt bağlamının biçimlendirilmesi testi."""
        ctx = format_research_prompt_context("Stoacılık felsefesi", max_snippets=2)
        if ctx:
            self.assertIn("GERÇEK VE GÜNCEL BİLGİ KAYNAĞI", ctx)
            self.assertIn("Kural: Senaryoyu kurgularken", ctx)

    def test_cross_verify_claim_matching(self):
        """İddia teyit eşleştirme mantığı testi."""
        claim_verified = {
            "type": "year",
            "raw_match": "1945",
            "value": "1945",
            "sentence": "1945 yılında savaş sona erdi.",
        }
        mock_snippets = ["İkinci Dünya Savaşı 1945 yılında resmen sona erdi."]
        res = cross_verify_claim(claim_verified, topic="İkinci Dünya Savaşı", web_snippets=mock_snippets)
        self.assertEqual(res["status"], "verified")
        self.assertGreaterEqual(res["confidence"], 0.90)

        claim_unverified = {
            "type": "year",
            "raw_match": "1842",
            "value": "1842",
            "sentence": "Marcus Aurelius 1842 yılında Roma'yı fethetti.",
        }
        res_unverified = cross_verify_claim(claim_unverified, topic="Marcus Aurelius", web_snippets=mock_snippets)
        self.assertEqual(res_unverified["status"], "unverified")

    def test_sanitize_unverified_claims(self):
        """Teyitsiz veya aşırı kesin iddiaların güvenli forma dönüştürülmesi testi."""
        narr = "İnsanların %99'u tarihteki tek gizemi asla bilmez."
        claims = [
            {"type": "percentage", "raw_match": "%99", "value": "99", "status": "unverified"},
            {"type": "superlative", "raw_match": "tarihteki tek", "value": "tarihteki tek", "status": "unverified"},
        ]
        sanitized, mods = sanitize_unverified_claims(narr, claims)
        self.assertEqual(len(mods), 2)
        self.assertNotIn("%99", sanitized)
        self.assertIn("büyük bir çoğunluğu", sanitized)
        self.assertIn("tarihin en nadir", sanitized)

    def test_verify_and_sanitize_scenes_pipeline(self):
        """Sahne listesi üzerinden teyit ve arındırma pipeline testi."""
        scenes = [
            {"index": 0, "narration": "İnsanların %95'i bu sırrı bilmeden yaşıyor."},
            {"index": 1, "narration": "Bu felsefe tarihteki tek kurtuluş yoludur."},
        ]
        updated, report = verify_and_sanitize_scenes(
            scenes,
            topic="Stoacılık",
            web_snippets=["Stoacılık Roma'da bir yaşam öğretisidir."],
        )
        self.assertEqual(len(updated), 2)
        self.assertTrue(updated[0]["fact_verified"])
        self.assertNotIn("%95", updated[0]["narration"])
        self.assertNotIn("tarihteki tek", updated[1]["narration"].lower())
        self.assertIn("total_claims", report)
        self.assertGreaterEqual(report["sanitized_count"], 2)

    def test_high_percent_is_unverified_without_source(self):
        claim = {"type": "percentage", "raw_match": "%99", "value": "99"}
        res = cross_verify_claim(claim, web_snippets=["Roma hakkında genel bir ansiklopedi notu."])
        self.assertEqual(res["status"], "unverified")

    def test_year_and_count_drop_when_missing(self):
        scenes = [{"narration": "Roma 1842 yılında kuruldu. Yaklaşık 5 milyon kişi etkilendi."}]
        updated, report = verify_and_sanitize_scenes(
            scenes,
            topic="Roma",
            web_snippets=["Roma 753 yılında kuruldu."],
        )
        narr = updated[0]["narration"]
        self.assertNotIn("1842", narr)
        self.assertNotIn("5 milyon", narr)
        self.assertIn("o dönem", narr)
        self.assertIn("pek çok", narr)
        self.assertGreaterEqual(report["sanitized_count"], 2)

    def test_opening_hook_percent_stays(self):
        hook = "İnsanların %99'u bunu bilmez."
        scenes = [{"narration": hook + " Roma 1842 yılında kuruldu."}]
        updated, _report = verify_and_sanitize_scenes(
            scenes,
            topic="Roma",
            web_snippets=["Genel ansiklopedi metni, sayı yok."],
            protect_text=hook,
        )
        narr = updated[0]["narration"]
        self.assertIn("%99", narr)
        self.assertNotIn("1842", narr)

    def test_empty_sources_keep_numbers(self):
        scenes = [{"narration": "İnsanların %99'u 1842 yılında bunu duydu."}]
        updated, report = verify_and_sanitize_scenes(scenes, topic="Roma", web_snippets=[])
        self.assertIn("%99", updated[0]["narration"])
        self.assertIn("1842", updated[0]["narration"])
        self.assertEqual(report["sanitized_count"], 0)

    def test_compile_director_plan_attaches_fact_verification(self):
        """DirectorPlan derlemesinde fact_verification raporunun eklenmesi testi."""
        raw = {
            "title": "Stoacı Marcus Aurelius Hayatı",
            "fact_snippets": ["Marcus Aurelius Roma imparatoruydu."],
            "scenes": [
                {"narration": "Bunu öğrenene kadar hayatınızı yanlış yaşıyordunuz.", "duration": 3.5},
                {"narration": "Marcus Aurelius 1842 yılında Roma imparatoru olarak yaşadı.", "duration": 4.0},
                {"narration": "Ve tam da bu yüzden asla pes etmeyin çünkü.", "duration": 3.5},
            ],
        }
        plan = compile_director_plan(raw, niche_id="2_philosophy_stoic")
        self.assertIn("fact_verification", plan.meta)
        report = plan.meta["fact_verification"]
        self.assertIn("sources", report)
        self.assertNotIn("1842", plan.scenes[1].narration)
        self.assertTrue(all(getattr(s, "fact_verified", False) for s in plan.scenes))


if __name__ == "__main__":
    unittest.main()
