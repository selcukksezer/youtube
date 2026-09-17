"""
Unit tests for Section 4: Viewer Retention, Psychological Hooks & Visual Cadence (Items 201-275).
"""
import unittest
from viral_retention_engine import viral_retention_engine, ViralRetentionEngine


class TestSection4Retention(unittest.TestCase):
    def test_item_202_cognitive_dissonance_hook(self):
        hook_tr = ViralRetentionEngine.generate_cognitive_dissonance_hook("Marcus Aurelius Felsefesi", lang="tr")
        self.assertIn("Marcus Aurelius Felsefesi", hook_tr)
        self.assertTrue(any(w in hook_tr for w in ["yanılsamaydı", "yanılıyor", "tam tersi", "tuzağına"]))

        hook_en = ViralRetentionEngine.generate_cognitive_dissonance_hook("Stoicism", lang="en")
        self.assertIn("Stoicism", hook_en)

    def test_item_203_zeigarnik_hook(self):
        hook = ViralRetentionEngine.generate_zeigarnik_hook("Zihin Gücü", total_points=3, lang="tr")
        self.assertIn("3. kuralı", hook)
        self.assertIn("önce...", hook)

    def test_item_204_and_137_loop_formulas_and_conjunctions(self):
        formula = ViralRetentionEngine.get_loop_formula("cause_and_effect")
        self.assertEqual(formula["id"], "cause_and_effect")
        self.assertIn("ending_bridge", formula)
        self.assertIn("hook_starter", formula)

        conjs = ViralRetentionEngine.get_diverse_loop_conjunctions(10)
        self.assertGreaterEqual(len(conjs), 10)
        
        bridge1 = ViralRetentionEngine.pick_loop_bridge_for_video(0)
        bridge2 = ViralRetentionEngine.pick_loop_bridge_for_video(1)
        self.assertNotEqual(bridge1, bridge2)

    def test_item_206_and_265_safe_zone_and_eye_tracking(self):
        sz = ViralRetentionEngine.get_subtitles_safe_zone(screen_height=1920, screen_width=1080)
        self.assertTrue(sz["safe_zone_verified"])
        self.assertEqual(sz["max_words_per_frame"], 4)
        # Verify 25% bottom margin
        self.assertEqual(sz["bottom_ui_margin"], 480)
        # Verify eye-tracking range (40%-60%)
        self.assertEqual(sz["eye_tracking_y_range"], [768, 1152])
        self.assertTrue(sz["eye_tracking_y_range"][0] <= sz["optimal_subtitle_y"] <= sz["eye_tracking_y_range"][1])

    def test_item_210_polarizing_dilemma(self):
        dilemma = ViralRetentionEngine.generate_polarizing_dilemma("Yapay Zeka Devrimi", lang="tr")
        self.assertIn("question", dilemma)
        self.assertIn("choice_a", dilemma)
        self.assertIn("choice_b", dilemma)

    def test_item_215_bionic_text(self):
        words = ["Marcus", "Aurelius", "Roma"]
        formatted = ViralRetentionEngine.format_bionic_text(words)
        self.assertEqual(formatted[0], "<b>Mar</b>cus")
        self.assertEqual(formatted[1], "<b>Aure</b>lius")
        self.assertEqual(formatted[2], "<b>Ro</b>ma")

    def test_item_218_219_fomo_forbidden_knowledge(self):
        hook_fomo = ViralRetentionEngine.generate_fomo_forbidden_knowledge_hook("Borsa", category="fomo", lang="tr")
        self.assertIn("%99", hook_fomo)

        hook_forbidden = ViralRetentionEngine.generate_fomo_forbidden_knowledge_hook("Manipülasyon", category="forbidden", lang="tr")
        self.assertIn("karanlık", hook_forbidden)

    def test_item_228_challenge_hook(self):
        challenge = ViralRetentionEngine.generate_challenge_hook("Görsel Mantık", lang="tr")
        self.assertIn("IQ'su 125", challenge)
        self.assertIn("5 saniyen var", challenge)

    def test_item_232_sticky_hook_banner(self):
        b1 = ViralRetentionEngine.get_sticky_hook_banner("Konu", mood="warning", lang="tr")
        b2 = ViralRetentionEngine.get_sticky_hook_banner("Konu", mood="secret", lang="tr")
        self.assertIn("ASLA BUNU YAPMAYIN", b1)
        self.assertIn("SAKLANAN GERÇEK", b2)

    def test_item_234_pinned_comment_bait(self):
        bait = ViralRetentionEngine.generate_pinned_comment_bait("Gizemli Tarih", lang="tr")
        self.assertIn("video_cta", bait)
        self.assertIn("pinned_comment", bait)
        self.assertIn("Gizemli Tarih", bait["pinned_comment"])

    def test_item_241_numbered_rule_hierarchy(self):
        rules = ["Kendine dürüst ol", "Zihnini yönet", "Kaderini sev"]
        formatted = ViralRetentionEngine.format_numbered_rule_hierarchy(rules, lang="tr")
        self.assertEqual(len(formatted), 3)
        self.assertEqual(formatted[0]["prefix"], "Kural 1:")
        self.assertEqual(formatted[1]["prefix"], "Kural 2:")
        self.assertIn("en tehlikelisi Kural 3", formatted[2]["prefix"])

    def test_item_249_subconscious_color_palette(self):
        p_danger = ViralRetentionEngine.get_subconscious_color_palette("gizem ve korku")
        p_money = ViralRetentionEngine.get_subconscious_color_palette("para ve borsa")
        p_tech = ViralRetentionEngine.get_subconscious_color_palette("yapay zeka")
        p_stoic = ViralRetentionEngine.get_subconscious_color_palette("stoic felsefe")

        self.assertEqual(p_danger["primary"], "#FF0033")
        self.assertEqual(p_money["secondary"], "#FFD700")
        self.assertEqual(p_tech["primary"], "#00F5D4")
        self.assertEqual(p_stoic["primary"], "#E0E1DD")

    def test_item_266_cadence_acceleration(self):
        durations = ViralRetentionEngine.calculate_cadence_acceleration(total_duration=45.0, scene_count=14)
        self.assertEqual(len(durations), 14)
        self.assertAlmostEqual(sum(durations), 45.0, places=1)
        # Verify first duration is longer than middle/later ones (acceleration)
        self.assertGreater(durations[0], durations[10])

    def test_item_274_story_arc_breakdown(self):
        arc = ViralRetentionEngine.build_shorts_story_arc_breakdown(45.0)
        self.assertEqual(arc["total_duration"], 45.0)
        self.assertEqual(len(arc["phases"]), 4)
        phase_names = [p["phase"] for p in arc["phases"]]
        self.assertTrue(any("Hook" in name for name in phase_names))
        self.assertTrue(any("Climax" in name for name in phase_names))
        self.assertTrue(any("Resolution & Loop" in name for name in phase_names))

    def test_item_275_retention_score(self):
        res = ViralRetentionEngine.calculate_retention_score(
            has_split_screen=True,
            has_anti_duplicate=True,
            has_karaoke=True,
            has_loop=True,
            audio_ducking=True
        )
        self.assertGreaterEqual(res["score"], 90)
        self.assertIn("Viral Potansiyeli Yüksek", res["tier"])


if __name__ == "__main__":
    unittest.main()
