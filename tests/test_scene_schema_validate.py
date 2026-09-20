"""P2-22: strict Pydantic validation for AI scene JSON."""
import unittest
from unittest.mock import MagicMock, patch

from api_models import validate_generated_plan, validate_generated_plan_errors
from scenes.generator import _schema_valid


class TestSceneSchemaValidate(unittest.TestCase):
    def test_valid_plan_passes(self):
        plan = {
            "scenes": [
                {
                    "narration": "Bu tam bir cumledir.",
                    "duration": 3.0,
                    "search_queries": ["marble bust stoic"],
                }
            ]
        }
        self.assertEqual(validate_generated_plan_errors(plan), [])
        self.assertTrue(_schema_valid(plan))

    def test_malformed_scene_missing_narration_rejected(self):
        bad = {"scenes": [{"search_queries": ["city night"]}]}
        errs = validate_generated_plan_errors(bad)
        self.assertTrue(errs)
        self.assertFalse(_schema_valid(bad))

    def test_malformed_scene_missing_visual_ref_rejected(self):
        bad = {"scenes": [{"narration": "Tam cumle ama gorsel yok."}]}
        errs = validate_generated_plan_errors(bad)
        self.assertTrue(any("scene_description" in e or "visual" in e.lower() for e in errs))
        self.assertFalse(_schema_valid(bad))

    def test_empty_scenes_array_rejected(self):
        bad = {"scenes": []}
        self.assertTrue(validate_generated_plan_errors(bad))
        with self.assertRaises(Exception):
            validate_generated_plan(bad)

    @patch("scenes.generator._call")
    def test_generator_schema_retry_path(self, mock_call):
        from scenes import generator

        bad_json = '{"scenes":[{"narration":"kopuk"}]}'
        good_json = (
            '{"scenes":[{"narration":"Bu tam bir cumledir.","duration":3,'
            '"search_queries":["stoic marble"]}]}'
        )
        good_resp = MagicMock()
        good_resp.choices = [MagicMock(message=MagicMock(content=good_json))]
        mock_call.return_value = good_resp

        bad_data = generator._parse_provider_json(bad_json)
        self.assertFalse(generator._schema_valid(bad_data))

        resp = mock_call(MagicMock(), {"temperature": 0.2})
        retry_data = generator._parse_provider_json(resp.choices[0].message.content)
        self.assertTrue(generator._schema_valid(retry_data))
        mock_call.assert_called_once()


if __name__ == "__main__":
    unittest.main()
