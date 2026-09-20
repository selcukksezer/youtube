"""P2-04: competitor format fingerprint extraction and prompt wiring."""
import unittest

from research_service import (
    aggregate_format_fingerprint,
    build_content_gap_fingerprint,
    extract_format_fingerprint_from_title,
    infer_hook_style_from_title,
    infer_scene_count_from_title,
)
from scenes.generator import _build_competitor_fingerprint_block


class TestFormatFingerprint(unittest.TestCase):
    def test_list_title_infers_scene_count(self):
        self.assertEqual(infer_scene_count_from_title("3 kural ile öfke kontrolü"), 6)
        self.assertEqual(infer_scene_count_from_title("5 gerçek hakkında"), 8)

    def test_hook_style_classification(self):
        self.assertIn("Liste", infer_hook_style_from_title("3 gizli kural"))
        self.assertIn("Soru", infer_hook_style_from_title("Neden mi?"))
        self.assertIn("Şok", infer_hook_style_from_title("Şok edici haber!"))

    def test_extract_fingerprint_fields(self):
        fp = extract_format_fingerprint_from_title("3 kural ile disiplin", hook_analysis="📊 Sayısal Liste")
        self.assertEqual(fp["scene_count"], 6)
        self.assertIn("Liste", fp["hook_style"])
        self.assertAlmostEqual(fp["avg_scene_duration"], 7.0)

    def test_aggregate_fingerprint(self):
        samples = [
            extract_format_fingerprint_from_title("3 kural"),
            extract_format_fingerprint_from_title("5 gerçek"),
        ]
        agg = aggregate_format_fingerprint(samples)
        self.assertEqual(agg["sample_size"], 2)
        self.assertGreaterEqual(agg["scene_count"], 5)

    def test_content_gap_fingerprint(self):
        from research_service import build_content_gap_suggestions

        suggestions = build_content_gap_suggestions(
            "3 stoacı kural\n5 gerçek hakkında öfke", "6_stoic_philosophy"
        )
        fp = build_content_gap_fingerprint(suggestions, "6_stoic_philosophy")
        self.assertIn("scene_count", fp)
        self.assertIn("hook_style", fp)

    def test_prompt_block_injection(self):
        block = _build_competitor_fingerprint_block(
            {"scene_count": 8, "hook_style": "Liste", "avg_scene_duration": 5.2},
            lang="tr",
        )
        self.assertIn("RAKİP FORMAT FİNGERPRINT", block)
        self.assertIn("8", block)


if __name__ == "__main__":
    unittest.main()
