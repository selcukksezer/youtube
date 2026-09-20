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

class TestNiches(unittest.TestCase):
    def test_total_niches_count(self):
        """Verify exactly 35 distinct niches are registered."""
        self.assertEqual(len(NICHES), 35)

    def test_list_all_niches(self):
        """Verify list_all_niches provides valid metadata for each niche."""
        niches = list_all_niches()
        self.assertEqual(len(niches), 35)
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

    def test_niche_family_mapping(self):
        self.assertEqual(get_niche_family("6_stoic_philosophy"), "stoic")
        self.assertEqual(get_niche_family("20_whatsapp_chat_story"), "whatsapp")
        self.assertEqual(get_niche_family("2_reddit_confessions"), "reddit")
        self.assertEqual(get_niche_family("1_news_flash"), "news")
        self.assertEqual(get_niche_family("9_five_facts"), "general")

    def test_list_all_niches_includes_family(self):
        for n in list_all_niches():
            self.assertIn("niche_family", n)

    def test_scene_structure_helper(self):
        st = get_niche_scene_structure("6_stoic_philosophy", "tr")
        self.assertIn("KURAL 1", st)
        wa = get_niche_scene_structure("20_whatsapp_chat_story", "tr")
        self.assertIn("mesajlaşma", wa.lower())

if __name__ == "__main__":
    unittest.main()
