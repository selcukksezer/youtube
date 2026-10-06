"""
Bölüm 7.5: 16 Niş Üretim Profili ve Stil Motoru Test Paketi
- 16 standart niş profili eksiksizliği
- Görsel motifler ve sert negatif filtreler
- Altyazı preset eşleşmeleri
- DirectorPlan ve Niche Production Profile entegrasyonu
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.niche_profiles import (
    NICHE_16_PROFILES,
    resolve_niche_profile,
    list_niche_profiles,
)
from director.visual_intent import NICHE_MOTIFS
from subtitle_generator import get_niche_subtitle_preset
from niche_templates import get_niche_production_profile
from director import compile_director_plan


class TestChapter7NicheProfiles(unittest.TestCase):
    EXPECTED_16_NICHES = [
        "1_news_flash",
        "2_philosophy_stoic",
        "3_bizarre_history",
        "4_ai_money_tech",
        "5_luxury_lifestyle",
        "6_psychology_tricks",
        "7_space_cosmos",
        "8_survival_myth",
        "9_five_facts",
        "10_fitness_biohack",
        "11_reddit_stories",
        "12_amazon_affiliate",
        "13_crypto_finance",
        "14_mysterious_cases",
        "15_parenting_hacks",
        "16_islamic_wisdom",
    ]

    def test_16_niche_profiles_complete(self):
        """16 standart niş profilinin eksiksiz mevcut ve alanlarının dolu olduğu testi."""
        self.assertEqual(len(NICHE_16_PROFILES), 16)
        for nid in self.EXPECTED_16_NICHES:
            self.assertIn(nid, NICHE_16_PROFILES, f"Missing niche profile: {nid}")
            prof = NICHE_16_PROFILES[nid]
            self.assertTrue(prof.get("name_tr"))
            self.assertTrue(prof.get("tone"))
            self.assertTrue(prof.get("visual_motif"))
            self.assertTrue(prof.get("subtitle_preset"))
            self.assertTrue(prof.get("bgm_mood"))
            self.assertGreaterEqual(prof.get("target_bpm", 0), 60.0)
            self.assertGreaterEqual(len(prof.get("visual_subjects", [])), 4)
            self.assertGreaterEqual(len(prof.get("must_include", [])), 2)
            self.assertGreaterEqual(len(prof.get("must_exclude", [])), 2)

    def test_resolve_niche_profile_aliases(self):
        """Doğrudan ID ve alias çözümleri testi."""
        self.assertEqual(resolve_niche_profile("2_philosophy_stoic")["niche_id"], "2_philosophy_stoic")
        self.assertEqual(resolve_niche_profile("6_stoic_philosophy")["niche_id"], "2_philosophy_stoic")
        self.assertEqual(resolve_niche_profile("felsefe")["niche_id"], "2_philosophy_stoic")

        self.assertEqual(resolve_niche_profile("7_space_cosmos")["niche_id"], "7_space_cosmos")
        self.assertEqual(resolve_niche_profile("uzay")["niche_id"], "7_space_cosmos")

        self.assertEqual(resolve_niche_profile("10_fitness_biohack")["niche_id"], "10_fitness_biohack")
        self.assertEqual(resolve_niche_profile("fitness")["niche_id"], "10_fitness_biohack")

        self.assertEqual(resolve_niche_profile("16_islamic_wisdom")["niche_id"], "16_islamic_wisdom")
        self.assertEqual(resolve_niche_profile("hadis")["niche_id"], "16_islamic_wisdom")

    def test_visual_motifs_cover_all_16_niches(self):
        """NICHE_MOTIFS içinde 16 nişin görsel politikalarının tanımlı olduğu testi."""
        for nid in self.EXPECTED_16_NICHES:
            self.assertIn(nid, NICHE_MOTIFS, f"NICHE_MOTIFS missing niche: {nid}")
            m = NICHE_MOTIFS[nid]
            self.assertTrue(m.get("motif"))
            self.assertTrue(m.get("era"))
            self.assertTrue(m.get("mood"))
            self.assertGreaterEqual(len(m.get("subjects", [])), 3)
            self.assertGreaterEqual(len(m.get("must_include", [])), 2)
            self.assertGreaterEqual(len(m.get("must_exclude", [])), 2)

    def test_subtitle_preset_mapping_all_16_niches(self):
        """16 nişin her biri için doğru altyazı preset'inin çözümlendiği testi."""
        mapping_expectations = {
            "7_space_cosmos": "space_neon_blue",
            "10_fitness_biohack": "fitness_punch",
            "4_ai_money_tech": "cyber_green",
            "5_luxury_lifestyle": "luxury_elegance",
            "3_bizarre_history": "history_sepia",
            "14_mysterious_cases": "horror_blood",
            "16_islamic_wisdom": "wisdom_emerald",
            "2_philosophy_stoic": "wisdom_emerald",
            "6_psychology_tricks": "psychology_violet",
            "1_news_flash": "high_contrast_retention",
            "11_reddit_stories": "tiktok_bold",
            "12_amazon_affiliate": "capcut_yellow",
            "13_crypto_finance": "crypto_gold",
            "9_five_facts": "mrbeast_style",
            "8_survival_myth": "red_fire",
            "15_parenting_hacks": "clean_white",
        }
        for nid, exp_preset in mapping_expectations.items():
            preset = get_niche_subtitle_preset(nid)
            prof = NICHE_16_PROFILES[nid]
            self.assertEqual(prof["subtitle_preset"], exp_preset)
            self.assertTrue(isinstance(preset, dict))
            self.assertTrue(preset.get("highlight_color"))

    def test_get_niche_production_profile_integration(self):
        """16 plan kimliği haber veya 5-gerçek paketine düşmez."""
        for nid in self.EXPECTED_16_NICHES:
            prod_prof = get_niche_production_profile(nid)
            self.assertEqual(prod_prof["id"], nid)
            rules = prod_prof.get("production_rules", {})
            self.assertEqual(rules.get("subtitle_preset"), NICHE_16_PROFILES[nid]["subtitle_preset"])
            self.assertEqual(prod_prof.get("visual_motif"), NICHE_16_PROFILES[nid]["visual_motif"])
            self.assertEqual(prod_prof.get("target_bpm"), NICHE_16_PROFILES[nid]["target_bpm"])
            self.assertIn("ken_burns", rules)
        space = get_niche_production_profile("7_space_cosmos")
        self.assertNotEqual(space["id"], "9_five_facts")
        self.assertNotEqual(space["id"], "1_news_flash")
        self.assertIn("cosmic", space["tone"])
        stoic = get_niche_production_profile("6_stoic_philosophy")
        self.assertEqual(stoic["production_rules"]["subtitle_preset"], "wisdom_emerald")
        self.assertIn("audio_rules", stoic)

    def test_compile_director_plan_with_16_niches(self):
        """Director derleyicisinin 16 niş ile başarıyla derlendiği testi."""
        raw = {
            "title": "Space and Cosmos Test",
            "scenes": [
                {"narration": "Evrenin sınırında akılalmaz bir keşif yapıldı.", "scene_description": "Deep space nebula stars galaxy telescope view", "duration": 3.5},
                {"narration": "Işık hızını aşan bu gizem bilim insanlarını şaşırttı.", "scene_description": "Black hole gravitational simulation in deep space", "duration": 3.5},
                {"narration": "Ve tam da bu yüzden asla yıldızlara bakmaktan vazgeçmeyin çünkü.", "scene_description": "Astronaut floating near spaceship in space void", "duration": 3.5},
            ],
        }
        plan = compile_director_plan(raw, niche_id="7_space_cosmos")
        self.assertEqual(plan.niche_id, "7_space_cosmos")
        self.assertEqual(plan.niche_profile["id"], "7_space_cosmos")
        self.assertEqual(plan.niche_profile["production_rules"]["subtitle_preset"], "space_neon_blue")
        self.assertTrue(len(plan.scenes) >= 3)
        self.assertTrue(all(sc.visual_intent is not None for sc in plan.scenes))
        self.assertTrue(any(sc.visual_intent.continuity_motif == "deep_space" for sc in plan.scenes))


if __name__ == "__main__":
    unittest.main()
