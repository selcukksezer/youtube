"""
Unit tests for Section 5 hybrid niches items 291-305 (batch 17 audit).
"""
import unittest

from hybrid_niches import (
    HYBRID_NICHES,
    get_hybrid_niche,
    build_hybrid_prompt_block,
    enrich_plan_with_hybrid,
)
from director.visual_intent import resolve_topic_intelligence
from director.compiler import compile_director_plan


ITEM_KEYS = {
    291: "old_money_luxury_mindset",
    292: "conspiracy_fbi_newspaper",
    293: "animal_funny_dub",
    294: "dream_surreal_psychology",
    295: "ai_tools_screen",
    296: "micro_book_summary",
    297: "true_crime_police_radio",
    298: "optical_illusion_focus",
    299: "price_timeline_tunnel",
    300: "military_tactics_map",
    301: "celebrity_failure_stories",
    302: "body_language_celebrity",
    303: "future_2050_simulation",
    304: "deep_sea_thalassophobia",
    305: "forgotten_historical_figures",
}


class TestSection5Items291305(unittest.TestCase):
    def test_hybrid_library_covers_291_to_305(self):
        for item_num, key in ITEM_KEYS.items():
            with self.subTest(item=item_num):
                self.assertIn(key, HYBRID_NICHES)
                entry = get_hybrid_niche(key)
                self.assertIn(f"Item {item_num}", entry["name"])
                self.assertTrue(entry.get("system_prompt_addition"))
                self.assertTrue(entry.get("loop_bridge"))
                self.assertTrue(entry.get("bg_style"))

    def test_build_hybrid_prompt_block_old_money(self):
        block = build_hybrid_prompt_block("old_money_luxury_mindset", lang="tr")
        self.assertIn("HİBRİT NİŞ FORMAT", block)
        self.assertIn("luxury", block.lower())

    def test_enrich_plan_with_hybrid_true_crime(self):
        plan = {
            "title": "Gerçek suç mahkeme polis telsiz cctv vaka",
            "scenes": [{"search_queries": ["crime"], "duration": 3.0}],
        }
        out = enrich_plan_with_hybrid(plan, plan["title"], "1_news_flash")
        self.assertEqual(out.get("hybrid_niche"), "true_crime_police_radio")

    def test_director_compiler_hybrid_meta_293(self):
        raw = {
            "title": "Komik kedi hayvan dublaj iç ses monolog",
            "scenes": [{"narration": "Test.", "duration": 3.0, "search_queries": ["cat"]}],
        }
        plan = compile_director_plan(raw, title=raw["title"], niche_id="1_news_flash")
        self.assertEqual(plan.meta.get("hybrid_niche"), "animal_funny_dub")
        self.assertIn("topic_intelligence", plan.meta)

    def test_topic_intelligence_hybrid_signals(self):
        cases = [
            ("old money disiplin yacht lüks klasik saat", "old_money_luxury_mindset"),
            ("fbi komplo gizli dosya gazete küpür sansür", "conspiracy_fbi_newspaper"),
            ("komik kedi hayvan dublaj iç ses", "animal_funny_dub"),
            ("rüya tabiri rüyada surreal dali eriyen saat", "dream_surreal_psychology"),
            ("yapay zeka chatgpt canlı ekran laptop site", "ai_tools_screen"),
            ("atomik alışkanlıklar kitap özeti hap bilgi", "micro_book_summary"),
            ("gerçek suç mahkeme polis telsiz cctv", "true_crime_police_radio"),
            ("optik illüzyon merkeze 5 saniye odak test", "optical_illusion_focus"),
            ("1990 100 dolar enflasyon fiyat zaman tüneli", "price_timeline_tunnel"),
            ("askeri taktik kuşatma harita kırmızı ok", "military_tactics_map"),
            ("steve jobs kovuldu başarısızlık ünlü", "celebrity_failure_stories"),
            ("beden dili yalan röportaj ünlü mikro jest", "body_language_celebrity"),
            ("2050 gelecek simülasyon fütürist bir gün", "future_2050_simulation"),
            ("derin deniz mariana talasofobi yaratık abyss", "deep_sea_thalassophobia"),
            ("unutulmuş tarihi şahsiyet gizli kahraman arşiv", "forgotten_historical_figures"),
        ]
        for topic, expected_hybrid in cases:
            with self.subTest(topic=topic[:40]):
                intel = resolve_topic_intelligence(topic, "1_news_flash")
                self.assertEqual(intel.get("hybrid_niche"), expected_hybrid)


if __name__ == "__main__":
    unittest.main()
