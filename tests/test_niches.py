"""
Unit tests for 35 Niche Templates & Prompt Engine (Items 1-35, 36, 37, 73, 81, 82, 84, 93, 96)
"""
import unittest
from niche_templates import NICHES, get_niche_prompt, list_all_niches

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

if __name__ == "__main__":
    unittest.main()
