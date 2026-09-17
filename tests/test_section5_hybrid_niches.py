"""
Unit tests for Section 5: Hybrid Niches, Synergies & Growth Formulas (Items 276 - 345).
"""
import unittest
from hybrid_niches import (
    HYBRID_NICHES,
    get_hybrid_niche,
    list_all_hybrid_niches,
    collide_two_niches,
    generate_episodic_series_hook,
    generate_ironic_reverse_advice,
    generate_what_if_hypothesis,
    adapt_to_tier1_market
)


class TestSection5HybridNiches(unittest.TestCase):
    def test_item_276_to_295_hybrid_niche_library(self):
        niches = list_all_hybrid_niches()
        self.assertGreaterEqual(len(niches), 20)
        
        # Verify key niches
        keys = list(HYBRID_NICHES.keys())
        self.assertIn("stoic_cyberpunk", keys)
        self.assertIn("history_chat", keys)
        self.assertIn("dark_psychology_parkour", keys)
        self.assertIn("cosmic_epic_hans_zimmer", keys)
        self.assertIn("crypto_comic_book", keys)
        self.assertIn("spiritual_rain_nature", keys)
        self.assertIn("whatsapp_horror_voice", keys)
        self.assertIn("old_money_luxury_mindset", keys)
        self.assertIn("untranslatable_words_sonder", keys)
        self.assertIn("alternate_history_ai", keys)

        # Check structure
        for n in niches:
            self.assertIn("id", n)
            self.assertIn("name", n)
            self.assertIn("category", n)
            self.assertIn("rpm_tier", n)
            self.assertIn("bg_style", n)
            self.assertIn("loop_bridge", n)

    def test_item_320_niche_collision_engine(self):
        collision = collide_two_niches("stoic_cyberpunk", "ancient_egypt" if "ancient_egypt" in HYBRID_NICHES else "mystery_earth_zoom")
        self.assertIn("collision_id", collision)
        self.assertIn("title", collision)
        self.assertIn("category_blend", collision)
        self.assertIn("collision_hook", collision)
        self.assertIn("system_prompt", collision)
        self.assertIn("loop_bridge", collision)

    def test_item_314_episodic_series_hook(self):
        series_tr = generate_episodic_series_hook("Dünyanın En Gizemli Yerleri", episode_num=1, total_parts=10, lang="tr")
        self.assertIn("Bölüm 1", series_tr["title"])
        self.assertIn("1. bölümündeyiz", series_tr["hook"])
        self.assertIn("2. bölüm yarın geliyor", series_tr["closing_cta"])

        series_en = generate_episodic_series_hook("Top 10 Ancient Mysteries", episode_num=3, total_parts=5, lang="en")
        self.assertIn("Part 3/5", series_en["title"])
        self.assertIn("Part 4", series_en["closing_cta"])

    def test_item_329_ironic_reverse_advice(self):
        advice_tr = generate_ironic_reverse_advice("Disiplin ve Başarı", lang="tr")
        self.assertIn("hayatınızı tamamen mahvetmek", advice_tr["hook"])
        self.assertEqual(len(advice_tr["reverse_rules"]), 3)

        advice_en = generate_ironic_reverse_advice("Productivity", lang="en")
        self.assertIn("completely ruin your life", advice_en["hook"])
        self.assertEqual(len(advice_en["reverse_rules"]), 3)

    def test_item_330_what_if_hypothesis(self):
        sim_tr = generate_what_if_hypothesis("Dünya 5 saniyeliğine oksijensiz kalsaydı", lang="tr")
        self.assertIn("Dünya 5 saniyeliğine oksijensiz kalsaydı", sim_tr["hook"])
        self.assertEqual(len(sim_tr["phases"]), 3)

        sim_en = generate_what_if_hypothesis("the Sun disappeared for 24 hours", lang="en")
        self.assertIn("Sun disappeared", sim_en["hook"])
        self.assertEqual(len(sim_en["phases"]), 3)

    def test_item_321_tier1_market_adaptation(self):
        adapt = adapt_to_tier1_market("Stoacılık Felsefesi", target_country="US")
        self.assertEqual(adapt["target_market"], "US")
        self.assertEqual(adapt["language_code"], "en")
        self.assertEqual(adapt["currency_symbol"], "$")
        self.assertIn("en-US", adapt["recommended_voice"])
        self.assertIn("EST", adapt["timezone_posting_window"])


if __name__ == "__main__":
    unittest.main()
