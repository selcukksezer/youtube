"""
Unit tests for Section 5 items 321-335 (batch 19 audit).
"""
import unittest

from hybrid_niches import (
    HYBRID_NICHES,
    get_hybrid_niche,
    build_hybrid_prompt_block,
    enrich_plan_with_hybrid,
    adapt_to_tier1_market,
    generate_ironic_reverse_advice,
    generate_what_if_hypothesis,
)
from director.visual_intent import resolve_topic_intelligence
from growth_tactics import (
    format_cross_platform_metadata,
    generate_cross_platform_metadata,
    generate_viewer_choice_cta,
)
from viral_retention_engine import ViralRetentionEngine
import config


HYBRID_ITEM_KEYS = {
    325: "subtitle_voice_equalizer",
    326: "night_mode_dark_content",
    327: "interactive_stop_wheel_game",
    328: "collective_subconscious_fears",
    331: "ancient_remedies_egypt",
    332: "time_machine_100years",
    333: "money_psychology_quotes",
    335: "viewer_choice_door_game",
}


class TestSection5Items321335(unittest.TestCase):
    def test_item_321_tier1_market_adaptation(self):
        adapt = adapt_to_tier1_market("Stoacılık Felsefesi", target_country="US")
        self.assertEqual(adapt["target_market"], "US")
        self.assertEqual(adapt["language_code"], "en")
        self.assertIn("en-US", adapt["recommended_voice"])

    def test_item_322_cross_platform_metadata(self):
        meta = format_cross_platform_metadata("Test #Shorts", "Desc", ["shorts", "viral"])
        self.assertIn("tiktok", meta)
        self.assertIn("instagram_reels", meta)
        self.assertIn("#fyp", meta["tiktok"]["caption"])
        self.assertIs(generate_cross_platform_metadata, format_cross_platform_metadata)

    def test_item_323_export_fps_mode_config(self):
        self.assertIn(getattr(config, "EXPORT_FPS_MODE", "30"), ("30", "60"))

    def test_item_324_avatar_animation_stub_config(self):
        self.assertTrue(hasattr(config, "AVATAR_ANIMATION_PROVIDER"))
        self.assertTrue(hasattr(config, "AVATAR_ANIMATION_API_KEY"))

    def test_hybrid_library_covers_325_to_335_niches(self):
        for item_num, key in HYBRID_ITEM_KEYS.items():
            with self.subTest(item=item_num):
                self.assertIn(key, HYBRID_NICHES)
                entry = get_hybrid_niche(key)
                self.assertIn(f"Item {item_num}", entry["name"])
                self.assertTrue(entry.get("system_prompt_addition"))
                self.assertTrue(entry.get("loop_bridge"))
                self.assertTrue(entry.get("bg_style"))

    def test_item_329_ironic_reverse_advice(self):
        advice = generate_ironic_reverse_advice("Disiplin", lang="tr")
        self.assertIn("mahvetmek", advice["hook"])
        self.assertEqual(len(advice["reverse_rules"]), 3)

    def test_item_330_what_if_hypothesis(self):
        sim = generate_what_if_hypothesis("Dünya 5 saniyeliğine oksijensiz kalsaydı", lang="tr")
        self.assertIn("oksi", sim["hook"].lower())
        self.assertEqual(len(sim["phases"]), 3)

    def test_item_334_single_sentence_identity_hook(self):
        hook = ViralRetentionEngine.generate_single_sentence_identity_hook(lang="tr")
        self.assertIn("insan", hook.lower())
        hook_en = ViralRetentionEngine.generate_single_sentence_identity_hook(lang="en")
        self.assertIn("same person", hook_en.lower())

    def test_item_335_viewer_choice_cta(self):
        cta = generate_viewer_choice_cta("Zenginlik", "Özgürlük", lang="tr")
        self.assertIn("Kapı 1", cta["spoken_hook"])
        self.assertIn("yoruma yaz", cta["visual_overlay"].lower())

    def test_build_hybrid_prompt_block_night_mode(self):
        block = build_hybrid_prompt_block("night_mode_dark_content", lang="tr")
        self.assertIn("HİBRİT NİŞ FORMAT", block)
        self.assertIn("23:00", block)

    def test_enrich_plan_with_hybrid_money_psychology(self):
        plan = {
            "title": "Morgan Housel para psikolojisi finans davranış risk alıntı",
            "scenes": [{"search_queries": ["finance"], "duration": 3.0}],
        }
        out = enrich_plan_with_hybrid(plan, plan["title"], "1_news_flash")
        self.assertEqual(out.get("hybrid_niche"), "money_psychology_quotes")

    def test_topic_intelligence_hybrid_signals_325_335(self):
        cases = [
            ("altyazı ekolayzır yeşil bar ses frekans ritim podcast", "subtitle_voice_equalizer"),
            ("gece modu dark mode 23:00 karanlık tema rahatlatıcı", "night_mode_dark_content"),
            ("spinning wheel çark durdurma oyun doğru yerde rulet", "interactive_stop_wheel_game"),
            ("klostrofobi talasofobi araknofobi bilinçaltı korku", "collective_subconscious_fears"),
            ("antik mısır gizli ilaç bitkisel şifa papirüs reçete", "ancient_remedies_egypt"),
            ("zaman makinesi 100 yıl geri timeline dönüşüm", "time_machine_100years"),
            ("morgan housel psychology of money finans alıntı", "money_psychology_quotes"),
            ("kapı 1 kapı 2 seçim yoruma yaz izleyici karar", "viewer_choice_door_game"),
        ]
        for topic, expected_hybrid in cases:
            with self.subTest(topic=topic[:40]):
                intel = resolve_topic_intelligence(topic, "1_news_flash")
                self.assertEqual(intel.get("hybrid_niche"), expected_hybrid)


if __name__ == "__main__":
    unittest.main()
