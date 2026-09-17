"""
Unit tests for Section 8: Channel Health, Proof of Effort, Shadowban Recovery & Monetization (Items 466 - 500).
"""
import unittest
import os
from proof_archiver import proof_archiver, ProofArchiver


class TestSection8ChannelHealth(unittest.TestCase):
    def test_item_466_zero_views_diagnostic(self):
        # < 48h
        early_res = ProofArchiver.diagnose_zero_views(hours_since_upload=12.0, view_count=0, total_videos_on_channel=3)
        self.assertEqual(early_res["status"], "indexing_phase")
        self.assertFalse(early_res["action_required"])

        # > 48h with < 10 videos
        unclass_res = ProofArchiver.diagnose_zero_views(hours_since_upload=50.0, view_count=0, total_videos_on_channel=5)
        self.assertEqual(unclass_res["status"], "unclassified_channel")
        self.assertTrue(unclass_res["action_required"])

    def test_item_467_warmup_protocol(self):
        new_ch = ProofArchiver.check_warmup_protocol(channel_age_days=5, planned_daily_uploads=2)
        self.assertTrue(new_ch["is_compliant"])

        exceeding_ch = ProofArchiver.check_warmup_protocol(channel_age_days=5, planned_daily_uploads=6)
        self.assertFalse(exceeding_ch["is_compliant"])
        self.assertIsNotNone(exceeding_ch["warning"])

    def test_item_470_borderline_risk_scanner(self):
        clean_text = "Marcus Aurelius antik Roma imparatorudur."
        scan_clean = ProofArchiver.scan_borderline_risk(clean_text)
        self.assertTrue(scan_clean["is_clean"])

        risky_text = "Tarihteki bu cinayet ve ölüm vakası şok etti."
        scan_risky = ProofArchiver.scan_borderline_risk(risky_text)
        self.assertFalse(scan_risky["is_clean"])
        self.assertIn("cinayet", scan_risky["flagged_words"])

    def test_item_471_proof_dossier(self):
        proof_file = ProofArchiver.archive_video_proof(
            video_filename="test_video_123.mp4",
            title="Stoic Discipline",
            niche="Stoic",
            script_text="Testing script content",
            scenes=[{"scene": 1, "duration": 3}],
            render_params={"fps": 30}
        )
        self.assertTrue(os.path.exists(proof_file))
        if os.path.exists(proof_file):
            os.remove(proof_file)

    def test_item_472_475_appeal_script(self):
        script = ProofArchiver.generate_appeal_video_script("Shorts Alpha", "The Wisdom of Seneca")
        self.assertIn("Shorts Alpha", script)
        self.assertIn("The Wisdom of Seneca", script)
        self.assertIn("Reused Content", script)
        self.assertIn("YouTube Partner Program Review Team", script)

    def test_item_478_monetization_funnel(self):
        funnel_tr = ProofArchiver.generate_monetization_funnel("Stoacılık", "Zihin Disiplini", lang="tr")
        self.assertIn("Rehberini", funnel_tr["pinned_comment"])
        self.assertIn("linktr.ee", funnel_tr["bio_link_text"])

    def test_item_481_tier1_multiplier(self):
        us_rpm = ProofArchiver.get_tier1_rpm_multiplier("US")
        self.assertEqual(us_rpm["target_country"], "US")
        self.assertIn("8x", us_rpm["rpm_multiplier"])

    def test_item_485_legal_disclaimer(self):
        fin_disc = ProofArchiver.generate_legal_disclaimer("finance", lang="tr")
        self.assertIn("YASAL UYARI", fin_disc)
        self.assertIn("yatırım tavsiyesi", fin_disc)

    def test_item_486_shadowban_recovery(self):
        plan = ProofArchiver.generate_shadowban_recovery_plan(7)
        self.assertEqual(len(plan["steps"]), 5)
        self.assertIn("Shadowban Reset", plan["protocol_name"])


if __name__ == "__main__":
    unittest.main()
