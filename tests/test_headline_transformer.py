"""Headline transformation regression tests."""
import unittest
from unittest.mock import Mock, patch

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

    def test_long_batch_headline_keeps_shorts_tag_within_limit(self):
        result = batch_convert_headlines(["Uzun haber başlığı " * 10])[0]["question_title"]
        self.assertLessEqual(len(result), 70)
        self.assertTrue(result.casefold().endswith("#shorts"))

    def test_long_ai_title_keeps_shorts_tag_within_limit(self):
        response = Mock()
        response.choices = [
            Mock(
                message=Mock(
                    content='{"question_title": "' + "A" * 90 + '", "strategy": "curiosity"}'
                )
            )
        ]
        with (
            patch("headline_transformer.config.AI_PROVIDER", "OpenAI"),
            patch("headline_transformer.config.AI_API_KEY", "test-key"),
            patch("headline_transformer.OpenAI"),
            patch("headline_transformer._call", return_value=response),
        ):
            result = convert_headline_to_question("Uzun haber başlığı", use_ai=True)

        self.assertLessEqual(len(result["question_title"]), 70)
        self.assertTrue(result["question_title"].casefold().endswith("#shorts"))


if __name__ == "__main__":
    unittest.main()