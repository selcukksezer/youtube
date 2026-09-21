"""
Unit tests for Section 4 retention items 241-255 (batch 13 audit).
"""
import unittest
import numpy as np
from moviepy.editor import ColorClip

from viral_retention_engine import ViralRetentionEngine
from scenes.enrichment import enrich_numbered_rule_narration, avoid_consecutive_face_visuals
from effects.motion import apply_impact_screen_shake, apply_micro_zoom_out, apply_broll_speed_boost
from effects.overlays import generate_neon_curiosity_opening_graphic
from effects.layout import create_before_after_contrast_clip
from subtitle_generator import SUBTITLE_PRESETS


class TestSection4Items241255(unittest.TestCase):
    def test_item_241_numbered_rule_narration_wire(self):
        scenes = [
            {"narration": "Kural 1: Disiplin"},
            {"narration": "Kural 2: Sabır"},
            {"narration": "Kural 3: Odak"},
        ]
        out = enrich_numbered_rule_narration(scenes, lang="tr")
        self.assertIn("Kural 1:", out[0]["narration"])
        self.assertIn("en tehlikelisi Kural 3", out[2]["narration"])

    def test_item_242_humanizer_module_exists(self):
        from voice.humanizer import VoiceHumanizer
        self.assertTrue(hasattr(VoiceHumanizer, "humanize_script_ssml"))

    def test_item_243_impact_screen_shake(self):
        clip = ColorClip(size=(720, 1280), color=(180, 40, 40), duration=1.0)
        shaken = apply_impact_screen_shake(clip, intensity=12.0, duration=0.3)
        self.assertEqual(shaken.size, (720, 1280))

    def test_item_244_narrow_audience_hook(self):
        hook = ViralRetentionEngine.generate_narrow_audience_hook("Finans", lang="tr")
        self.assertIn("finansal özgürlük", hook.lower())

    def test_item_245_broll_speed_boost(self):
        clip = ColorClip(size=(720, 1280), color=(50, 50, 80), duration=2.0)
        boosted = apply_broll_speed_boost(clip, speed_factor=1.5)
        self.assertLess(boosted.duration, 2.0)

    def test_item_246_neon_curiosity_opening_graphic(self):
        overlay = generate_neon_curiosity_opening_graphic(720, 1280, duration=2.0, symbol="?")
        frame = overlay.get_frame(0.5)
        self.assertEqual(frame.shape[:2], (1280, 720))

    def test_item_247_avoid_consecutive_faces(self):
        scenes = [
            {"search_queries": ["portrait face closeup cinematic"]},
            {"search_queries": ["human face looking at camera"]},
        ]
        out = avoid_consecutive_face_visuals(scenes)
        self.assertTrue(out[1].get("visual_diversity_adjusted"))

    def test_item_248_emotional_bond_hook(self):
        hook = ViralRetentionEngine.generate_emotional_bond_hook(lang="tr")
        self.assertIn("yapayalnız", hook.lower())

    def test_item_249_subconscious_palette(self):
        palette = ViralRetentionEngine.get_subconscious_color_palette("tehlike gizem")
        self.assertEqual(palette["primary"], "#FF0033")

    def test_item_251_vertical_divider_split(self):
        left = ColorClip(size=(640, 1280), color=(80, 80, 200), duration=1.5)
        right = ColorClip(size=(640, 1280), color=(200, 80, 80), duration=1.5)
        split = create_before_after_contrast_clip(left, right, 1080, 1920)
        self.assertEqual(split.size, (1080, 1920))

    def test_item_252_subtitle_font_and_box_preset(self):
        sizes = [p["font_size"] for p in SUBTITLE_PRESETS.values()]
        self.assertTrue(all(48 <= s <= 56 for s in sizes))

    def test_item_253_micro_zoom_out(self):
        clip = ColorClip(size=(720, 1280), color=(90, 120, 60), duration=1.0)
        zoomed = apply_micro_zoom_out(clip, zoom_start=1.04, zoom_end=1.00)
        self.assertEqual(zoomed.size, (720, 1280))

    def test_item_254_pre_answer_tension_gap_fn(self):
        from voice.audio_dsp import inject_pre_answer_tension_gap
        self.assertTrue(callable(inject_pre_answer_tension_gap))

    def test_item_255_loop_formula_exists(self):
        formula = ViralRetentionEngine.get_loop_formula("cause_and_effect")
        self.assertIn("ending_bridge", formula)


if __name__ == "__main__":
    unittest.main()
