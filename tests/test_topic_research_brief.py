import unittest
from unittest.mock import patch

from research_service import build_topic_research_brief


class TestTopicResearchBrief(unittest.TestCase):
    @patch("research_service.fetch_youtube_autocomplete_suggestions", return_value=["gökdelen nasıl yapılır"])
    def test_brief_is_auditable_and_has_policy_contract(self, _autocomplete):
        brief = build_topic_research_brief("Gökdelenler neden sallanır?", niche_id="5_science", lang="tr")
        self.assertEqual(brief["status"], "signals_found")
        self.assertIn("gökdelen nasıl yapılır", brief["autocomplete"])
        self.assertIn("official primary sources", brief["source_policy"]["preferred"])
        self.assertIn("visual subject must match the scene intent", brief["verification_required"])


if __name__ == "__main__":
    unittest.main()
