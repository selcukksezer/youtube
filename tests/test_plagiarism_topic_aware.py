"""Item 120: topic-aware originality + stoic procedural differentiation."""
import unittest

from plagiarism_checker import (
    _adjust_similarity_for_topic,
    check_script_originality,
    clear_plagiarism_db,
    compute_similarity,
)
from scene_generator import _generate_procedural_fallback_scenes


class TestPlagiarismTopicAware(unittest.TestCase):
    def setUp(self):
        clear_plagiarism_db()

    def test_stoic_topics_produce_distinct_scripts(self):
        topic_a = "2000 yıllık bu felsefe bugün hayatını kurtarabilir."
        topic_b = "Marcus Aurelius bugün yaşasaydı sana ne derdi?"
        plan_a = _generate_procedural_fallback_scenes(
            topic_a, niche_type="6_stoic_philosophy", language="tr"
        )
        plan_b = _generate_procedural_fallback_scenes(
            topic_b, niche_type="6_stoic_philosophy", language="tr"
        )
        raw_sim = compute_similarity(plan_a["full_narration"], plan_b["full_narration"])
        self.assertLess(raw_sim, 0.85)
        self.assertIn(topic_a[:20], plan_a["full_narration"])
        self.assertIn(topic_b[:20], plan_b["full_narration"])

    def test_topic_discount_reduces_cross_topic_false_positive(self):
        body_a = (
            "Marcus Aurelius yazmıştı kontrol edebilirsin stoacı bilgelik öfke disiplin "
            "Seneca Epiktetos zihin huzur antrenman"
        )
        body_b = body_a
        raw = compute_similarity(body_a, body_b)
        self.assertGreater(raw, 0.9)
        adjusted = _adjust_similarity_for_topic(
            raw,
            "2000 yıllık felsefe hayat kurtar",
            "2000 yıllık felsefe",
            "Marcus Aurelius bugün yaşasaydı",
            "Marcus Aurelius",
        )
        self.assertLess(adjusted, 0.45)

    def test_same_topic_still_rejected(self):
        topic = "Marcus Aurelius disiplin kuralları"
        script = _generate_procedural_fallback_scenes(
            topic, niche_type="6_stoic_philosophy", language="tr"
        )["full_narration"]
        check_script_originality(script, keyword=topic, title=topic, auto_add_if_approved=True)
        ok, sim, _ = check_script_originality(
            script, keyword=topic, title=topic, auto_add_if_approved=False
        )
        self.assertFalse(ok)
        self.assertGreaterEqual(sim, 0.45)

    def test_variation_seed_changes_stoic_output(self):
        topic = "Stoacılık ile sabır öğren"
        base = _generate_procedural_fallback_scenes(
            topic, niche_type="6_stoic_philosophy", language="tr", variation_seed=0
        )["full_narration"]
        alt = _generate_procedural_fallback_scenes(
            topic, niche_type="6_stoic_philosophy", language="tr", variation_seed=2
        )["full_narration"]
        self.assertNotEqual(base, alt)


if __name__ == "__main__":
    unittest.main()
