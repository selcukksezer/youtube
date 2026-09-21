"""
Unit tests for Section 6 SEO items 376-390 (batch 23 audit).
Excluded from scope: #376-378, #385-386, #388-389 (manual Studio upload only).
"""
import unittest

from proof_archiver import ProofArchiver
from viral_seo_agent import build_natural_seo_description, prepend_description_engagement_question
from growth_tactics import generate_weekly_live_stream_plan, generate_live_stream_loop_command
from effects.overlays import overlay_watermark


class TestSection6Items376390(unittest.TestCase):
    def test_excluded_items_not_in_automation_scope(self):
        excluded = {376, 377, 378, 385, 386, 388, 389}
        in_scope = {379, 380, 381, 382, 383, 384, 387, 390}
        self.assertFalse(excluded & in_scope)

    def test_item_379_algorithmic_threshold_retention(self):
        res = ProofArchiver.analyze_algorithmic_view_threshold(850)
        self.assertEqual(res["diagnosis"], "retention_friction")
        self.assertEqual(res["item"], 379)

    def test_item_379_algorithmic_threshold_share(self):
        res = ProofArchiver.analyze_algorithmic_view_threshold(5500)
        self.assertEqual(res["diagnosis"], "share_friction")

    def test_item_380_reupload_guidance(self):
        guidance = ProofArchiver.get_reupload_avoidance_guidance(lang="tr")
        self.assertIn("380", guidance["item"])
        self.assertIn("spam", guidance["rule"].lower())

    def test_item_381_watermark_not_safe_mode_gated(self):
        import inspect
        src = inspect.getsource(overlay_watermark)
        self.assertNotIn("RENDER_SAFE_MODE", src)

    def test_item_383_description_engagement_question(self):
        desc = build_natural_seo_description("Stoacılık", hook="Disiplin sırları.")
        self.assertTrue(desc.startswith("💬"))
        self.assertIn("ne düşünüyorsunuz", desc.lower())
        dup = prepend_description_engagement_question(desc, keyword="Stoacılık")
        self.assertEqual(desc.count("💬"), dup.count("💬"))

    def test_item_384_weekly_live_stream_plan(self):
        plan = generate_weekly_live_stream_plan(lang="tr")
        self.assertIn("384", plan["item"])
        self.assertIn("canlı", plan["schedule"].lower())
        cmd = generate_live_stream_loop_command("out.mp4", "stream_key")
        self.assertIn("ffmpeg", cmd.lower())

    def test_item_387_feed_distribution_phase(self):
        expanded = ProofArchiver.analyze_feed_distribution_phase(20.0)
        throttled = ProofArchiver.analyze_feed_distribution_phase(45.0)
        self.assertTrue(expanded["distribution_expanded"])
        self.assertFalse(throttled["distribution_expanded"])
        self.assertEqual(expanded["test_audience_size"], 500)

    def test_item_390_borderline_sanitize(self):
        risky = "Bu cinayet ve ölüm vakası şok etti."
        res = ProofArchiver.sanitize_borderline_words(risky)
        self.assertFalse(res["is_clean"])
        self.assertIn("cinayet", res["flagged_words"])
        self.assertNotIn("cinayet", res["sanitized_text"].lower())
        self.assertIn("unlived", res["safe_replacements"]["suicide"])


if __name__ == "__main__":
    unittest.main()
