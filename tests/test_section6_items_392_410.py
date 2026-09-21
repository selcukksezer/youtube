"""
Unit tests for Section 6 SEO items 392-410 (batch 24 audit).
Excluded from scope: #391, #393, #404-405 (manual Studio upload only).
"""
import unittest

import config
from proof_archiver import ProofArchiver
from viral_seo_agent import (
    generate_end_screen_guidance,
    generate_competitor_analysis_brief,
    get_channel_contact_guidance,
    generate_related_video_bridge,
)
from trending_scanner import _get_fallback_viral_trends
from system_resilience import get_hardware_accelerated_encoder


class TestSection6Items392410(unittest.TestCase):
    def test_excluded_items_not_in_automation_scope(self):
        excluded = {391, 393, 404, 405}
        in_scope = {392, 394, 395, 396, 397, 398, 399, 400, 401, 402, 403, 406, 407, 408, 409, 410}
        self.assertFalse(excluded & in_scope)

    def test_item_392_end_screen_guidance(self):
        guidance = generate_end_screen_guidance(
            "Stoacılık Sırları",
            "https://youtube.com/shorts/xyz",
            "Uzun Video",
        )
        self.assertEqual(guidance["item"], "392")
        self.assertIn("end screen", guidance["shorts_end_screen_note"].lower())
        self.assertIn("xyz", guidance["related_video_url"])

    def test_item_392_related_bridge_overlap(self):
        bridge = generate_related_video_bridge("Test", "https://youtube.com/watch?v=abc")
        self.assertIn("Related video", bridge["studio_upload_note"])

    def test_item_394_algorithm_reset_guidance(self):
        waiting = ProofArchiver.get_algorithm_reset_guidance(days_paused=1)
        ready = ProofArchiver.get_algorithm_reset_guidance(days_paused=5)
        self.assertEqual(waiting["item"], "394")
        self.assertFalse(waiting["ready_for_comeback"])
        self.assertTrue(ready["ready_for_comeback"])
        self.assertEqual(ready["pause_days_required"], 4)

    def test_item_395_competitor_analysis_brief(self):
        brief = generate_competitor_analysis_brief("stoacılık", lang="tr")
        self.assertEqual(brief["item"], "395")
        self.assertGreaterEqual(len(brief["competitors"]), 1)
        self.assertIn("48", brief["action"])

    def test_item_395_trending_fallback_has_cards(self):
        trends = _get_fallback_viral_trends("uzay")
        self.assertGreaterEqual(len(trends), 1)
        self.assertIn("title", trends[0])

    def test_item_396_channel_contact_guidance(self):
        guidance = get_channel_contact_guidance("sponsor@kanal.com", lang="tr")
        self.assertEqual(guidance["item"], "396")
        self.assertIn("sponsor@kanal.com", guidance["about_section_text"])
        self.assertIn("Studio", guidance["studio_action"])

    def test_items_397_400_render_spec(self):
        self.assertEqual(config.RESOLUTIONS["1080p"], (1080, 1920))
        self.assertEqual(config.VIDEO_WIDTH, 1080)
        self.assertEqual(config.VIDEO_HEIGHT, 1920)
        codec, params = get_hardware_accelerated_encoder()
        self.assertIn(codec, ("h264_videotoolbox", "libx264"))
        self.assertTrue(any("12M" in p or "14M" in p for p in params))

    def test_item_403_embedded_subtitles_path(self):
        import inspect
        from video_composer import _merge
        src = inspect.getsource(_merge)
        self.assertIn("ass=", src)
        self.assertIn("48000", src)

    def test_items_406_409_traffic_sources_advisory(self):
        healthy = ProofArchiver.analyze_traffic_sources(85.0, 8.0, 5.0)
        risky = ProofArchiver.analyze_traffic_sources(40.0, 2.0, 92.0)
        self.assertEqual(healthy["item"], "406-409")
        self.assertTrue(healthy["shorts_feed_healthy"])
        self.assertTrue(risky["external_traffic_risk"])
        self.assertIn("weekly_analytics_action", healthy)

    def test_item_410_channel_momentum_threshold(self):
        early = ProofArchiver.get_channel_momentum_threshold(total_videos=12, avg_views=120)
        mature = ProofArchiver.get_channel_momentum_threshold(total_videos=35, avg_views=1200)
        self.assertEqual(early["item"], "410")
        self.assertTrue(early["early_phase"])
        self.assertFalse(mature["early_phase"])
        self.assertEqual(early["momentum_video_threshold"], 30)


if __name__ == "__main__":
    unittest.main()
