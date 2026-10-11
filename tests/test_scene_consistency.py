"""Plan consistency tests for fallback scripts and visual cadence."""
import unittest

from scene_generator import _generate_procedural_fallback_scenes, enforce_visual_cadence_14


class TestSceneConsistency(unittest.TestCase):
    def test_visual_cadence_does_not_duplicate_narration(self):
        scenes = [
            {
                "scene_number": index + 1,
                "duration": 6,
                "narration": (
                    f"Original sentence {index} describes a complete event with meaningful context. "
                    f"Another distinct explanation for scene {index} adds useful supporting detail."
                ),
                "search_queries": ["primary", "alternate"],
            }
            for index in range(8)
        ]
        expanded = enforce_visual_cadence_14(scenes)
        spoken = [scene["narration"] for scene in expanded]
        self.assertTrue(all(spoken))
        self.assertEqual(len(spoken), len(set(spoken)))
        self.assertTrue(any(scene.get("is_visual_cutaway") for scene in expanded))

    def test_cadence_padding_splits_only_at_sentence_boundaries(self):
        narrations = [
            "The first complete scene explains a meaningful change for everyone involved. Its second sentence adds important context to the story today.",
            "The second complete scene describes another meaningful change for everyone involved today.",
            "A third complete scene provides a useful example that explains this important idea.",
            "The fourth complete scene explains why the outcome matters for the people involved.",
            "A fifth complete scene closes the story with a clear result for everyone.",
        ]
        scenes = [
            {
                "scene_number": index + 1,
                "duration": 6.0,
                "narration": narration,
                "scene_description": f"Original visual {index + 1}",
                "search_queries": [f"original query {index + 1}"],
                "source_id": f"source-{index + 1}",
            }
            for index, narration in enumerate(narrations)
        ]

        expanded = enforce_visual_cadence_14(scenes, min_cadence=6)

        self.assertEqual(len(expanded), 6)
        self.assertAlmostEqual(sum(scene["duration"] for scene in expanded), 30.0)
        self.assertCountEqual(
            [scene["narration"] for scene in expanded],
            [
                "The first complete scene explains a meaningful change for everyone involved.",
                "Its second sentence adds important context to the story today.",
                *narrations[1:],
            ],
        )
        self.assertTrue(any(scene.get("is_visual_cutaway") for scene in expanded))
        self.assertTrue(all(scene.get("source_id") for scene in expanded))
        self.assertTrue(all(scene.get("scene_description") for scene in expanded))
        self.assertTrue(all(scene.get("search_queries") for scene in expanded))

    def test_cadence_padding_keeps_unsplittable_sentences_intact(self):
        narrations = [
            "A complete event changes the story for everyone involved.",
            "This separate sentence gives the next scene its own meaning.",
            "Another complete thought explains why the decision matters.",
            "The fourth event shows how patience can change the outcome.",
            "A final complete sentence brings the lesson to a close.",
        ]
        scenes = [
            {"duration": 6.0, "narration": narration, "search_queries": ["story"]}
            for narration in narrations
        ]

        expanded = enforce_visual_cadence_14(scenes, min_cadence=6)

        self.assertEqual(len(expanded), 5)
        self.assertEqual([scene["narration"] for scene in expanded], narrations)
        self.assertAlmostEqual(sum(scene["duration"] for scene in expanded), 30.0)
        self.assertFalse(any(scene.get("is_visual_cutaway") for scene in expanded))

    def test_reddit_fallback_uses_reddit_story_structure(self):
        plan = _generate_procedural_fallback_scenes("Ailemle yaşadığım tartışma", "2_reddit_confessions")
        self.assertEqual(plan["scenes"][0]["narration"].split()[0], "Bunu")
        self.assertIn("Siz olsaydınız", plan["full_narration"])


if __name__ == "__main__":
    unittest.main()