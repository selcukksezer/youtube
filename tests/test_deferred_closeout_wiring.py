"""Deferred close-out — growth operator pack, #476 recovery, CI route wiring."""
import unittest

from growth_tactics import export_growth_operator_pack
from proof_archiver import ProofArchiver


class TestDeferredCloseoutWiring(unittest.TestCase):
    def test_growth_operator_pack_covers_311_322_384(self):
        pack = export_growth_operator_pack("Stoacılık", lang="tr")
        self.assertEqual(pack["pack_type"], "growth_operator_pack")
        self.assertIn("311-322,384", pack["items_covered"])
        self.assertIn("comment_to_video", pack)
        self.assertIn("community_poll", pack)
        self.assertIn("related_video_bridge", pack)
        self.assertIn("series_format", pack)
        self.assertIn("live_stream_loop_ffmpeg", pack)
        self.assertIn("weekly_live_plan", pack)
        self.assertIn("affiliate_pinned_cta", pack)
        self.assertIn("niche_collision", pack)
        self.assertIn("tier1_adaptation", pack)
        self.assertIn("cross_platform", pack)
        self.assertTrue(pack["manual_studio_only"])
        self.assertGreaterEqual(len(pack["studio_checklist"]), 10)

    def test_item_476_repeated_content_recovery_plan(self):
        plan = ProofArchiver.get_repeated_content_rejection_recovery_plan(
            channel_name="TestChannel", lang="tr"
        )
        self.assertEqual(plan["item"], 476)
        self.assertEqual(plan["duration_days"], 30)
        self.assertIn("hafta_1", plan["weekly_targets"])
        self.assertTrue(plan["manual_only"])

    def test_growth_operator_pack_api_route(self):
        with open("routers/system_router.py", encoding="utf-8") as f:
            src = f.read()
        self.assertIn("/api/growth/operator-pack", src)
        self.assertIn("export_growth_operator_pack", src)
        self.assertIn("/api/channel-health/repeated-content-recovery", src)

    def test_ci_workflow_exists(self):
        with open(".github/workflows/ci.yml", encoding="utf-8") as f:
            ci = f.read()
        self.assertIn("unittest discover", ci)
        self.assertIn("tests", ci)


if __name__ == "__main__":
    unittest.main()
