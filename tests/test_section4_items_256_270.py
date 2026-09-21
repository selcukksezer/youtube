"""
Unit tests for Section 4 retention items 256-270 (batch 14 audit).
"""
import unittest
from moviepy.editor import ColorClip

from viral_retention_engine import ViralRetentionEngine
from subtitle_generator import _clamp_word_display_durations
from effects.overlays import apply_keyword_white_flash_overlay


class TestSection4Items256270(unittest.TestCase):
    def test_item_256_downscale_prep_exists(self):
        import inspect
        from video_composer import _prep
        src = inspect.getsource(_prep)
        self.assertIn("Downscale", src)
        self.assertIn("4K", src)

    def test_item_257_role_play_hook(self):
        hook = ViralRetentionEngine.generate_role_play_hook("Gizemli Cinayet", lang="tr")
        self.assertIn("dedektif", hook.lower())
        self.assertIn("3 şüpheli", hook.lower())

    def test_item_258_word_display_clamp(self):
        timings = [
            {"text": "hızlı", "offset": 0.0, "duration": 0.05},
            {"text": "yavaş", "offset": 0.5, "duration": 1.2},
        ]
        out = _clamp_word_display_durations(timings)
        self.assertEqual(out[0]["duration"], 0.25)
        self.assertEqual(out[1]["duration"], 0.40)

    def test_item_259_shocking_statistic_hook(self):
        hook = ViralRetentionEngine.generate_shocking_statistic_hook("Genetik", lang="tr")
        self.assertTrue("%" in hook or "Harvard" in hook or "1.000" in hook)

    def test_item_260_white_flash_overlay(self):
        clip = ColorClip(size=(720, 1280), color=(20, 20, 40), duration=2.0)
        flashed = apply_keyword_white_flash_overlay(clip, timestamp=0.5, duration=0.18)
        self.assertEqual(flashed.size, (720, 1280))

    def test_item_263_counter_intuitive_hook(self):
        hook = ViralRetentionEngine.generate_counter_intuitive_hook("Para ve Mutluluk", lang="tr")
        self.assertIn("Harvard", hook)

    def test_item_265_safe_zone(self):
        sz = ViralRetentionEngine.get_subtitles_safe_zone()
        self.assertEqual(sz["max_words_per_frame"], 4)
        self.assertTrue(sz["safe_zone_verified"])

    def test_item_266_cadence_acceleration(self):
        durations = ViralRetentionEngine.calculate_cadence_acceleration(45.0, 14)
        self.assertGreater(durations[0], durations[-1])

    def test_item_268_decision_pressure_in_challenge(self):
        hook = ViralRetentionEngine.generate_challenge_hook("Mantık", lang="tr")
        self.assertIn("5 saniyen", hook)

    def test_item_269_pinned_comment_promise(self):
        bait = ViralRetentionEngine.generate_pinned_comment_bait("Tarih", lang="tr")
        self.assertIn("sabitliyorum", bait["pinned_comment"])

    def test_item_270_community_follow_cta(self):
        cta = ViralRetentionEngine.generate_community_follow_cta("Bilim", lang="tr")
        self.assertIn("Ailemize", cta)
        self.assertIn("takip et", cta)


if __name__ == "__main__":
    unittest.main()
