"""
Unit tests for 35 Niche Templates & Prompt Engine (Items 1-35, 36, 37, 73, 81, 82, 84, 93, 96)
"""
import unittest
from niche_templates import (
    NICHES,
    get_niche_prompt,
    get_niche_family,
    get_niche_scene_structure,
    list_all_niches,
)
from scenes.prompts import PROMPT_EN, PROMPT_TR, PROMPT_VARIANTS_TR

class TestNiches(unittest.TestCase):
    def test_total_niches_count(self):
        """Verify 36 distinct niches are registered (35 classic + kids animation)."""
        self.assertEqual(len(NICHES), 37)

    def test_list_all_niches(self):
        """Verify list_all_niches provides valid metadata for each niche."""
        niches = list_all_niches()
        self.assertEqual(len(niches), 37)
        for n in niches:
            self.assertIn("id", n)
            self.assertIn("name", n)
            self.assertIn("category", n)
            self.assertIn("has_split_screen", n)

    def test_niche_prompt_generation_tr(self):
        """Verify Turkish prompt contains viral hook, seamless loop, and discussion rules."""
        prompt = get_niche_prompt("6_stoic_philosophy", "Öfkeyi Kontrol Etmek", language="tr")
        self.assertIn("VIRAL HOOK", prompt)
        self.assertIn("SEAMLESS LOOP", prompt)
        self.assertIn("TARTIŞMA", prompt)
        self.assertIn("Öfkeyi Kontrol Etmek", prompt)

    def test_niche_prompt_generation_en(self):
        """Verify English prompt for Tier-1 countries."""
        prompt = get_niche_prompt("1_news_flash", "Global Space Discovery", language="en")
        self.assertIn("VIRAL HOOK", prompt)
        self.assertIn("SEAMLESS LOOP", prompt)
        self.assertIn("Global Space Discovery", prompt)

    def test_niche_prompts_match_director_spoken_scene_budget(self):
        prompt_tr = get_niche_prompt("6_stoic_philosophy", "Marcus Aurelius", language="tr")
        prompt_en = get_niche_prompt("6_stoic_philosophy", "Marcus Aurelius", language="en")

        self.assertIn("Tam 6 konuşma sahnesi oluştur", prompt_tr)
        self.assertIn("en fazla 110 kelime", prompt_tr)
        self.assertIn("Write exactly 6 complete spoken scenes", prompt_en)
        self.assertIn("not exceed 110 words", prompt_en)

    def test_rotated_prompts_do_not_reintroduce_oversized_scripts(self):
        for prompt in (PROMPT_TR, PROMPT_EN, *PROMPT_VARIANTS_TR):
            with self.subTest(prompt=prompt[:40]):
                self.assertIn("110", prompt)
                self.assertNotIn("120-170", prompt)
                self.assertNotIn("8-16", prompt)
                self.assertNotIn("8-12", prompt)

    def test_split_screen_niches_flag(self):
        """Verify specific niches like reddit or split gameplay have has_split_screen enabled."""
        self.assertTrue(NICHES["2_reddit_confessions"]["has_split_screen"])
        self.assertTrue(NICHES["3_split_gameplay"]["has_split_screen"])
        self.assertTrue(NICHES["20_whatsapp_chat_story"]["has_split_screen"])

    def test_p1_01_whatsapp_vs_stoic_structure_differs(self):
        """P1-01: competitor-format templates differ structurally by niche family."""
        wa = get_niche_prompt("20_whatsapp_chat_story", "Eski sevgili mesajı", language="tr")
        st = get_niche_prompt("6_stoic_philosophy", "Marcus Aurelius öfke", language="tr")
        self.assertIn("WHATSAPP CHAT", wa)
        self.assertIn("STOACI 3 KURAL", st)
        self.assertNotIn("FLAŞ HABER YAPISI", st)
        self.assertNotIn("WHATSAPP CHAT", st)
        self.assertNotIn("STOACI 3 KURAL", wa)

    def test_p1_01_marcus_stoic_not_breaking_news(self):
        """Marcus + stoic niche must not use breaking-news template."""
        prompt = get_niche_prompt(
            "6_stoic_philosophy",
            "Marcus Aureliusun Ofkeyi Yok Eden 3 Stoaci Kurali",
            language="tr",
        )
        self.assertIn("STOACI 3 KURAL", prompt)
        self.assertNotIn("FLAŞ HABER YAPISI", prompt)
        self.assertNotIn("Kilit bilgi 1", prompt)

    def test_p1_01_news_flash_uses_breaking_format(self):
        prompt = get_niche_prompt("1_news_flash", "Deprem son dakika", language="tr")
        self.assertIn("FLAŞ HABER", prompt)
        self.assertIn("SON DAKİKA", prompt)

    def test_scenario_pack_shock_policy_by_family(self):
        from niche_templates import get_scenario_pack
        self.assertFalse(get_scenario_pack("8_crypto_market")["allow_shock_queries"])
        self.assertTrue(get_scenario_pack("13_mystery_paranormal")["allow_shock_queries"])
        self.assertEqual(get_niche_family("8_crypto_market"), "crypto")
        self.assertEqual(get_niche_family("18_astrology_horoscope"), "astrology")


    def test_niche_family_mapping(self):
        self.assertEqual(get_niche_family("6_stoic_philosophy"), "stoic")
        self.assertEqual(get_niche_family("20_whatsapp_chat_story"), "whatsapp")
        self.assertEqual(get_niche_family("2_reddit_confessions"), "reddit")
        self.assertEqual(get_niche_family("1_news_flash"), "news")
        self.assertEqual(get_niche_family("9_five_facts"), "quiz")
        self.assertEqual(get_niche_family("10_religious_quotes"), "religious")
        self.assertEqual(get_niche_family("21_ai_tools_hacks"), "tech")
        self.assertEqual(get_niche_family("31_supercars_automotive"), "automotive")
        self.assertEqual(get_niche_family("23_fitness_nutrition_hacks"), "fitness")
        self.assertEqual(get_niche_family("32_legal_consumer_hacks"), "legal")
        self.assertEqual(get_niche_family("33_parenting_child_hacks"), "kids")

    def test_list_all_niches_includes_family(self):
        for n in list_all_niches():
            self.assertIn("niche_family", n)

    def test_scene_structure_helper(self):
        st = get_niche_scene_structure("6_stoic_philosophy", "tr")
        self.assertIn("KURAL 1", st)
        wa = get_niche_scene_structure("20_whatsapp_chat_story", "tr")
        self.assertIn("mesajlaşma", wa.lower())
        tech = get_niche_scene_structure("21_ai_tools_hacks", "tr")
        self.assertIn("yapay zeka", tech.lower())
        auto = get_niche_scene_structure("31_supercars_automotive", "tr")
        self.assertIn("araba", auto.lower())
        fit = get_niche_scene_structure("23_fitness_nutrition_hacks", "tr")
        self.assertIn("fitness", fit.lower())

if __name__ == "__main__":
    unittest.main()
