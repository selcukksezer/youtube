"""
Tests for Repo 10 / Verticals v3 Advanced Adaptations:
1. Autonomous Multi-Source Topic Engine (Google Trends + RSS feeds)
2. Niche Guardrails (Forbidden phrases cleaning + Visual avoid/prefer)
3. License Safety Normalization for Pollinations / AI manifests
"""

import unittest
from unittest.mock import patch, MagicMock
from services.autonomous_topic_engine import AutonomousTopicEngine, TopicCandidate
from services.niche_guardrails import clean_forbidden_phrases, get_niche_visual_rules
from visuals.license import LicenseInfo, License, is_commercial_safe


class TestRepo10Adaptations(unittest.TestCase):

    def test_clean_forbidden_phrases_turkish(self):
        dirty = "Hepinize merhaba arkadaşlar! Bu videoda sizlere harika bir alet göstereceğim. Kanalıma abone olun ve like atmayı unutmayın."
        cleaned = clean_forbidden_phrases(dirty, lang="tr")
        self.assertNotIn("abone olun", cleaned.lower())
        self.assertNotIn("bu videoda", cleaned.lower())
        self.assertNotIn("merhaba arkadaşlar", cleaned.lower())
        self.assertIn("harika bir alet", cleaned)

    def test_clean_forbidden_phrases_english(self):
        dirty = "Hey guys, what's up! In this video without further ado, like and subscribe to my channel."
        cleaned = clean_forbidden_phrases(dirty, lang="en")
        self.assertNotIn("like and subscribe", cleaned.lower())
        self.assertNotIn("in this video", cleaned.lower())
        self.assertNotIn("without further ado", cleaned.lower())

    def test_niche_visual_rules(self):
        rules = get_niche_visual_rules("tech")
        self.assertTrue(len(rules.get("prefer", [])) > 0)
        self.assertTrue(len(rules.get("avoid", [])) > 0)
        self.assertIn("#00FF88", rules.get("caption_color", ""))

    def test_license_safety_variants(self):
        # cc0_ai_free variant must normalize to CC0 and be safe
        lic1 = LicenseInfo(license="cc0_ai_free", source="pollinations")
        self.assertTrue(lic1.safe)
        self.assertEqual(lic1.license, License.CC0)

        # ai_generated variant must be safe
        lic2 = LicenseInfo(license="ai_generated", source="pollinations")
        self.assertTrue(lic2.safe)
        self.assertEqual(lic2.license, License.AI_GENERATED)

    @patch("requests.get")
    def test_autonomous_topic_engine_rss_mock(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = """
        <rss version="2.0">
            <channel>
                <item>
                    <title>Show HN: Autonomous Video Agent</title>
                    <link>https://news.ycombinator.com/item?id=123</link>
                    <description>Discussion on AI video pipelines</description>
                </item>
            </channel>
        </rss>
        """
        mock_get.return_value = mock_resp
        engine = AutonomousTopicEngine()
        candidates = engine.fetch_rss_topics(["https://fake-feed.xml"])
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].title, "Show HN: Autonomous Video Agent")


if __name__ == "__main__":
    unittest.main()
