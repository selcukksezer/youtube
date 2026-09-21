"""
Unit tests for Section 5 hybrid niches items 276-290 (batch 16 audit).
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
    276: "stoic_cyberpunk",
    277: "history_chat",
    278: "dark_psychology_parkour",
    279: "mystery_earth_zoom",
    280: "would_you_rather_duel",
    281: "reddit_asmr",
    282: "cosmic_epic_hans_zimmer",
    283: "crypto_comic_book",
    284: "country_guess_countdown",
    285: "spiritual_rain_nature",
    286: "whatsapp_horror_voice",
    287: "lifehack_affiliate_3items",
    288: "movie_idiom_english",
    289: "mythology_ai_epic",
    290: "weird_laws_world_map",
}


class TestSection5Items276290(unittest.TestCase):
    def test_hybrid_library_covers_276_to_290(self):
        for item_num, key in ITEM_KEYS.items():
            with self.subTest(item=item_num):
                self.assertIn(key, HYBRID_NICHES)
                entry = get_hybrid_niche(key)
                self.assertIn(f"Item {item_num}", entry["name"])
                self.assertTrue(entry.get("system_prompt_addition"))
                self.assertTrue(entry.get("loop_bridge"))
                self.assertTrue(entry.get("bg_style"))

    def test_build_hybrid_prompt_block(self):
        block = build_hybrid_prompt_block("stoic_cyberpunk", lang="tr")
        self.assertIn("HİBRİT NİŞ FORMAT", block)
        self.assertIn("cyberpunk", block.lower())

    def test_enrich_plan_with_hybrid(self):
        plan = {
            "title": "Marcus Aurelius cyberpunk neon distopya",
            "scenes": [{"search_queries": ["city night"], "duration": 3.0}],
        }
        out = enrich_plan_with_hybrid(plan, plan["title"], "1_news_flash")
        self.assertEqual(out.get("hybrid_niche"), "stoic_cyberpunk")

    def test_director_compiler_hybrid_meta(self):
        raw = {
            "title": "Garip yasalar Singapur harita dünya",
            "scenes": [{"narration": "Test.", "duration": 3.0, "search_queries": ["map"]}],
        }
        plan = compile_director_plan(raw, title=raw["title"], niche_id="1_news_flash")
        self.assertEqual(plan.meta.get("hybrid_niche"), "weird_laws_world_map")
        self.assertIn("topic_intelligence", plan.meta)

    def test_topic_intelligence_hybrid_signals(self):
        cases = [
            ("Marcus Aurelius cyberpunk neon", "stoic_cyberpunk"),
            ("Napolyon whatsapp chat mesaj", "history_chat"),
            ("manipülasyon parkour split screen", "dark_psychology_parkour"),
            ("bermuda ufo google earth zoom", "mystery_earth_zoom"),
            ("would you rather quiz oylama", "would_you_rather_duel"),
            ("reddit itiraf asmr kinetik kum", "reddit_asmr"),
            ("james webb evren epik hans zimmer", "cosmic_epic_hans_zimmer"),
            ("bitcoin satoshi çizgi roman comic", "crypto_comic_book"),
            ("bayrak hangi ülke geri sayım", "country_guess_countdown"),
            ("manevi dua yağmur orman", "spiritual_rain_nature"),
            ("whatsapp korku ses kaydı gece", "whatsapp_horror_voice"),
            ("amazon affiliate hayatınızı kolaylaştır 3 şey", "lifehack_affiliate_3items"),
            ("ingilizce deyim filmde friends", "movie_idiom_english"),
            ("mitoloji zeus thor ai animasyon", "mythology_ai_epic"),
            ("garip yasa singapur dünya haritası", "weird_laws_world_map"),
        ]
        for topic, expected_hybrid in cases:
            with self.subTest(topic=topic[:40]):
                intel = resolve_topic_intelligence(topic, "1_news_flash")
                self.assertEqual(intel.get("hybrid_niche"), expected_hybrid)


if __name__ == "__main__":
    unittest.main()
