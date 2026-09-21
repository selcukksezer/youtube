"""
Unit tests for Section 4 retention items 226-240 (batch 12 audit).
"""
import unittest
import numpy as np
from moviepy.editor import ColorClip

from viral_retention_engine import ViralRetentionEngine
from scenes.enrichment import enrich_closing_gaze_queries
from effects.motion import apply_slow_motion_highlight
from effects.overlays import apply_sticky_hook_banner_overlay, apply_micro_animated_sticker_overlay
from effects.layout import create_before_after_contrast_clip
from subtitle_generator import POWER_WORD_HIGHLIGHTS, _active_word_tags, hex_to_ass_color


class TestSection4Items226240(unittest.TestCase):
    def test_item_226_closing_gaze_queries(self):
        scenes = [{"search_queries": ["city night"], "narration": "Final."}]
        out = enrich_closing_gaze_queries(scenes)
        self.assertTrue(out[-1].get("closing_gaze"))
        joined = " ".join(out[-1]["search_queries"]).lower()
        self.assertTrue(any(k in joined for k in ["direct gaze", "looking at camera", "eye contact"]))

    def test_item_227_before_after_contrast_split(self):
        left = ColorClip(size=(640, 1280), color=(200, 50, 50), duration=2.0)
        right = ColorClip(size=(640, 1280), color=(50, 200, 50), duration=2.0)
        split = create_before_after_contrast_clip(left, right, 1080, 1920)
        self.assertEqual(split.size, (1080, 1920))

    def test_item_228_challenge_hook(self):
        hook = ViralRetentionEngine.generate_challenge_hook("Mantık", lang="tr")
        self.assertIn("IQ'su 125", hook)

    def test_item_229_subtitle_font_size_range(self):
        from subtitle_generator import SUBTITLE_PRESETS
        sizes = [p["font_size"] for p in SUBTITLE_PRESETS.values()]
        self.assertTrue(all(48 <= s <= 56 for s in sizes))

    def test_item_230_power_word_highlights(self):
        self.assertIn("ölümcül", POWER_WORD_HIGHLIGHTS)
        open_tag, _ = _active_word_tags(
            hex_to_ass_color("#FFFFFF"), hex_to_ass_color("#000000"), glow=True, word="ölümcül"
        )
        self.assertIn(hex_to_ass_color("#FF3333"), open_tag)

    def test_item_231_slow_motion_highlight(self):
        clip = ColorClip(size=(720, 1280), color=(100, 150, 200), duration=2.0)
        slowed = apply_slow_motion_highlight(clip, speed_factor=0.5)
        self.assertEqual(slowed.duration, 2.0)
        # factor=0.5: output t maps to source t * 0.5
        self.assertTrue(np.array_equal(slowed.get_frame(1.0), clip.get_frame(0.5)))

    def test_item_232_sticky_hook_banner(self):
        clip = ColorClip(size=(720, 1280), color=(30, 30, 40), duration=2.0)
        bannered = apply_sticky_hook_banner_overlay(clip, banner_text="⚠️ ASLA BUNU YAPMAYIN")
        top = bannered.get_frame(0.0)[0, 540]
        self.assertGreater(int(top.mean()), 30)

    def test_item_233_acoustic_curiosity_hook(self):
        hook = ViralRetentionEngine.generate_acoustic_curiosity_hook("Frekans", lang="tr")
        self.assertIn("Şu sesi duyuyor musunuz", hook)

    def test_item_234_pinned_comment_bait(self):
        bait = ViralRetentionEngine.generate_pinned_comment_bait("Gizem", lang="tr")
        self.assertIn("pinned_comment", bait)

    def test_item_235_share_cta(self):
        cta = ViralRetentionEngine.generate_share_cta("Stres", lang="tr")
        self.assertIn("gönder", cta.lower())

    def test_item_236_bookmark_cta(self):
        cta = ViralRetentionEngine.generate_bookmark_cta("Stoacılık", lang="tr")
        self.assertIn("kaydet", cta.lower())

    def test_item_237_pattern_interrupts_metadata(self):
        types = {p["type"] for p in ViralRetentionEngine.PATTERN_INTERRUPTS}
        self.assertIn("glitch_flash", types)

    def test_item_238_micro_animated_sticker(self):
        clip = ColorClip(size=(720, 1280), color=(20, 20, 30), duration=2.0)
        stickered = apply_micro_animated_sticker_overlay(clip, sticker="arrow", duration=1.5)
        self.assertEqual(stickered.duration, 2.0)

    def test_item_239_plot_twist_closing(self):
        twist = ViralRetentionEngine.generate_plot_twist_closing("Para", lang="tr")
        self.assertTrue("sürpriz" in twist.lower() or "ters" in twist.lower())

    def test_item_240_trigger_name_injection(self):
        hook = ViralRetentionEngine.inject_trigger_name_hook("Zihnini kontrol et.", topic="Disiplin", lang="tr")
        self.assertTrue(any(n in hook for n in ViralRetentionEngine.TRIGGER_NAMES))


if __name__ == "__main__":
    unittest.main()
