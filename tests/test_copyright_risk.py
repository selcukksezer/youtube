"""Copyright-risk heuristic regression tests."""
import unittest

from copyright_risk import filter_safe_clips, scan_copyright_risk
from viral_seo_agent import scan_copyright_risk as compatibility_scan


class TestCopyrightRisk(unittest.TestCase):
    def test_flags_known_content_id_source(self):
        result = scan_copyright_risk(["pexels_city.mp4", "artlist_music.mp3"])
        self.assertEqual(result["risk_level"], "high")
        self.assertEqual(result["flagged_items"][0]["item"], "artlist_music.mp3")
        self.assertEqual(filter_safe_clips(["pexels_city.mp4", "artlist_music.mp3"]), ["pexels_city.mp4"])

    def test_legacy_import_remains_available(self):
        self.assertTrue(compatibility_scan(["pexels_city.mp4"])["safe"])


if __name__ == "__main__":
    unittest.main()