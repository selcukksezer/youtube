"""Batch 5: DirectorPlan preserves hybrid overlay + retention metadata through compile."""
import unittest

from director.compiler import compile_director_plan
from hybrid_niches import enrich_plan_with_hybrid, get_hybrid_render_overlay_spec
from scenes.retention_hooks import apply_retention_hooks_to_plan
from subtitle_generator import resolve_ab_subtitle_preset, SUBTITLE_PRESETS


class TestBatch5DirectorHybridPreservation(unittest.TestCase):
    def test_to_legacy_plan_keeps_hybrid_render_overlay(self):
        raw = {
            "title": "Marcus Aurelius cyberpunk neon distopya",
            "scenes": [
                {"narration": "Açılış.", "duration": 3.0, "search_queries": ["neon city"]},
                {"narration": "Kapanış.", "duration": 3.0, "search_queries": ["rain"]},
            ],
        }
        raw = enrich_plan_with_hybrid(raw, raw["title"], "1_news_flash")
        raw = apply_retention_hooks_to_plan(raw, raw["title"], lang="tr", variation_attempt=0)
        plan = compile_director_plan(raw, title=raw["title"], niche_id="1_news_flash")
        legacy = plan.to_legacy_plan()
        self.assertEqual(legacy.get("hybrid_niche"), "stoic_cyberpunk")
        self.assertTrue(legacy.get("hybrid_render_overlay"))
        self.assertEqual(
            legacy["hybrid_render_overlay"].get("overlay"),
            get_hybrid_render_overlay_spec("stoic_cyberpunk").get("overlay"),
        )
        self.assertIn("retention_metadata", legacy)
        self.assertIn("hook_strategy", legacy["retention_metadata"])

    def test_unmapped_hybrid_gets_hybrid_frame_in_legacy_plan(self):
        raw = {
            "title": "Mitology zeus thor ai animasyon epic",
            "scenes": [{"narration": "Test.", "duration": 3.0, "search_queries": ["myth"]}],
        }
        raw = enrich_plan_with_hybrid(raw, raw["title"], "1_news_flash")
        plan = compile_director_plan(raw, title=raw["title"], niche_id="1_news_flash")
        legacy = plan.to_legacy_plan()
        self.assertEqual(legacy.get("hybrid_niche"), "mythology_ai_epic")
        self.assertEqual(legacy["hybrid_render_overlay"].get("overlay"), "hybrid_frame")

    def test_item_310_ab_subtitle_preset_resolver(self):
        opts = resolve_ab_subtitle_preset(0, "Karadelikler")
        self.assertIn("font_size", opts)
        self.assertIn("ab_test_variant", opts)
        self.assertEqual(opts["ab_test_variant"], "A_Curiosity")

    def test_item_214_high_contrast_preset_exists(self):
        self.assertIn("high_contrast_retention", SUBTITLE_PRESETS)
        preset = SUBTITLE_PRESETS["high_contrast_retention"]
        self.assertGreaterEqual(preset["stroke_width"], 5)

    def test_item_334_single_sentence_hook_strategy(self):
        plan = {
            "scenes": [
                {"narration": "Body.", "duration": 3.0},
                {"narration": "End.", "duration": 3.0},
            ]
        }
        out = apply_retention_hooks_to_plan(plan, "Zihin", lang="tr", variation_attempt=4)
        self.assertEqual(out["retention_metadata"]["hook_strategy"], "single_sentence")

    def test_item_345_perfect_loop_on_variation(self):
        plan = {
            "scenes": [
                {"narration": "Start.", "duration": 3.0},
                {"narration": "End.", "duration": 3.0},
            ]
        }
        out = apply_retention_hooks_to_plan(plan, "Loop Test", lang="tr", variation_attempt=3)
        self.assertIn("perfect_loop_bridge", out["retention_metadata"])


if __name__ == "__main__":
    unittest.main()
