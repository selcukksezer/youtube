"""
Unit tests for Section 6: SEO, Metadata, Algorithmic Signals & Distribution (Items 346 - 410).
"""
import unittest
from viral_seo_agent import (
    enforce_title_length_limit,
    format_capital_hook_word,
    inject_curiosity_words,
    enforce_three_hashtag_rule,
    build_natural_seo_description,
    get_channel_master_keywords,
    get_optimal_upload_schedule,
    calculate_cta_timing,
    generate_viral_seo_metadata,
    generate_title_variants
)


class TestSection6SeoMetadata(unittest.TestCase):
    def test_item_346_title_length_limit(self):
        very_long = "Bu Antik Roma İmparatoru Marcus Aurelius'un Hayat Değiştiren 5 Büyük Felsefi Kuralı ve Gizli Bilgileri #Shorts"
        trimmed = enforce_title_length_limit(very_long, min_len=40, max_len=60)
        self.assertLessEqual(len(trimmed), 60)
        self.assertIn("#Shorts", trimmed)

    def test_item_347_capital_hook_word(self):
        title = "Bu kuralı asla unutmayın ve zihninizi yönetin"
        formatted = format_capital_hook_word(title)
        self.assertIn("ASLA", formatted)
        # Verify not all words are uppercase
        self.assertIn("kuralı", formatted)

    def test_item_348_curiosity_words(self):
        title = "Roma Taktikleri"
        with_curiosity = inject_curiosity_words(title, lang="tr")
        self.assertTrue(any(w in with_curiosity for w in ["Gizli", "Yasaklanan", "Bilinmeyen", "Şok Eden", "Akıl Almaz", "Gözden Kaçan"]))

    def test_item_349_three_hashtag_rule(self):
        tags = enforce_three_hashtag_rule("test", niche_tag="stoic", general_tag="viral")
        tag_list = tags.split()
        self.assertEqual(len(tag_list), 3)
        self.assertEqual(tag_list[0], "#Shorts")
        self.assertEqual(tag_list[1], "#stoic")
        self.assertEqual(tag_list[2], "#viral")

    def test_item_352_natural_seo_description(self):
        desc = build_natural_seo_description(
            keyword="Marcus Aurelius",
            hook="Antik Roma'nın en bilge imparatorunun gizli kuralları.",
            bullet_points=["Zihin kontrolü", "Duygusal dayanıklılık", "Kader sevgisi"],
            source_name="Roma Tarih Kaynakları"
        )
        self.assertIn("Marcus Aurelius", desc)
        self.assertIn("📌 Önemli Noktalar:", desc)
        self.assertIn("📌 Kaynak & Araştırma:", desc)
        self.assertIn("⚖️ Yasal Bildirim (Fair Use):", desc)
        self.assertIn("#Shorts", desc)

    def test_item_358_channel_master_keywords(self):
        stoic_kw = get_channel_master_keywords("stoic")
        self.assertEqual(len(stoic_kw), 10)
        self.assertIn("stoacılık", stoic_kw)
        self.assertIn("marcus aurelius", stoic_kw)

        finance_kw = get_channel_master_keywords("finance")
        self.assertEqual(len(finance_kw), 10)
        self.assertIn("finans", finance_kw)

    def test_item_362_363_optimal_upload_schedule(self):
        tr_sched = get_optimal_upload_schedule("TR")
        self.assertEqual(tr_sched["target_country"], "TR")
        self.assertIn("18:00", tr_sched["primary_window"])

        us_sched = get_optimal_upload_schedule("US")
        self.assertEqual(us_sched["target_country"], "US")
        self.assertIn("EST", us_sched["timezone"])

    def test_item_367_cta_timing(self):
        cta = calculate_cta_timing(total_duration=45.0)
        self.assertGreaterEqual(cta["cta_start_second"], 25.0)
        self.assertIn("Abone Ol", cta["cta_text"])

    def test_viral_seo_metadata_fallback(self):
        meta = generate_viral_seo_metadata("Epiktetos Felsefesi")
        self.assertIn("hook_text", meta)
        self.assertIn("seo_title", meta)
        self.assertIn("seo_description", meta)
        self.assertIn("tags", meta)
        self.assertIn("pinned_comment", meta)


if __name__ == "__main__":
    unittest.main()
