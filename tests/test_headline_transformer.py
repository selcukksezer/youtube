"""Headline transformation regression tests."""
import unittest

from headline_transformer import batch_convert_headlines, convert_headline_to_question
from viral_seo_agent import convert_headline_to_question as compatibility_convert


class TestHeadlineTransformer(unittest.TestCase):
    def test_rule_based_title_is_original_question_and_short(self):
        result = convert_headline_to_question("Dunya piyasalarinda yeni gelisme", use_ai=False)
        self.assertIn("#shorts", result["question_title"])
        self.assertLessEqual(len(result["question_title"]), 70)

    def test_batch_rotates_templates_and_legacy_import_remains_available(self):
        result = batch_convert_headlines(["Birinci baslik", "Ikinci baslik"], lang="en")
        self.assertEqual(len({item["strategy"] for item in result}), 2)
        self.assertEqual(compatibility_convert("Baslik", use_ai=False)["original"], "Baslik")


if __name__ == "__main__":
    unittest.main()