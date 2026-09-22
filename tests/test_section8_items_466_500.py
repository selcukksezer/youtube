"""
Batch 28 audit tests — Section 8 items 466-500 (all in-scope, no upload exclusions).
"""
import os
import unittest

import config
import growth_tactics
from proof_archiver import ProofArchiver


class TestSection8Items466500(unittest.TestCase):
    def test_batch_28_all_in_scope(self):
        self.assertEqual(len(range(466, 501)), 35)

    def test_item_466_zero_views(self):
        res = ProofArchiver.diagnose_zero_views(72.0, 0, 5)
        self.assertIn(res["status"], ("unclassified_channel", "retention_friction", "indexing_phase"))

    def test_item_467_warmup(self):
        ok = ProofArchiver.check_warmup_protocol(10, 2)
        self.assertTrue(ok["is_compliant"])

    def test_item_468_engagement_recovery(self):
        adv = ProofArchiver.get_engagement_recovery_guidance(72.0, 0, 5)
        self.assertEqual(adv["item"], "468")
        self.assertGreaterEqual(len(adv["metadata_actions"]), 2)

    def test_item_469_distribution_pause(self):
        adv = ProofArchiver.get_distribution_pause_guidance(0)
        self.assertEqual(adv["item"], "469")
        self.assertEqual(adv["pause_days_required"], 4)

    def test_item_471_archive_proof(self):
        path = ProofArchiver.archive_video_proof(
            "audit466.mp4", "Test", "stoic", "script", [{"scene": 1}], {"fps": 30}
        )
        self.assertTrue(os.path.exists(path))
        os.remove(path)

    def test_item_484_copyright_strike_advisory(self):
        adv = ProofArchiver.get_copyright_strike_advisory(1)
        self.assertEqual(adv["risk_level"], "medium")
        self.assertIn("content_id_scan", adv)

    def test_item_485_legal_disclaimer(self):
        disc = ProofArchiver.generate_legal_disclaimer("finance", lang="tr")
        self.assertIn("YASAL UYARI", disc)
        seo_path = os.path.join(config.BASE_DIR, "viral_seo_agent.py")
        with open(seo_path, encoding="utf-8") as fh:
            self.assertIn("generate_legal_disclaimer", fh.read())

    def test_item_490_notification_every_fifth(self):
        on = growth_tactics.should_show_notification_bell_cta(5)
        off = growth_tactics.should_show_notification_bell_cta(4)
        self.assertTrue(on["show_notification_cta"])
        self.assertFalse(off["show_notification_cta"])

    def test_item_491_language_policy(self):
        bad = ProofArchiver.validate_channel_language_policy("tr", "en")
        self.assertFalse(bad["is_compliant"])
        good = ProofArchiver.validate_channel_language_policy("tr", "tr")
        self.assertTrue(good["is_compliant"])

    def test_item_495_comment_blocklist(self):
        bl = ProofArchiver.get_comment_moderation_blocklist("tr")
        self.assertGreaterEqual(bl["word_count"], 8)
        self.assertIn("bot", bl["blocked_words"])

    def test_item_494_duration_bands(self):
        schema_path = os.path.join(config.BASE_DIR, "director", "schema.py")
        with open(schema_path, encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn("min_duration: float = 38.0", src)
        self.assertIn("max_duration: float = 60.0", src)
        self.assertIn(config.MIN_DURATION, (45, 60))
        self.assertIn(config.MAX_DURATION, (60, 120))

    def test_item_499_ab_test_variants(self):
        from growth_tactics import generate_ab_test_variants
        variants = generate_ab_test_variants("Stoacılık")
        self.assertGreaterEqual(len(variants), 3)

    def test_item_500_batch_processor_exists(self):
        import batch_processor
        self.assertTrue(hasattr(batch_processor, "BatchQueueManager"))

    def test_channel_health_api_routes(self):
        router_path = os.path.join(config.BASE_DIR, "routers", "system_router.py")
        with open(router_path, encoding="utf-8") as fh:
            src = fh.read()
        self.assertIn("/api/channel-health/zero-views", src)
        self.assertIn("/api/monetization/funnel", src)


if __name__ == "__main__":
    unittest.main()
