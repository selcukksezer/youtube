"""Plan consistency tests for fallback scripts and visual cadence."""
import unittest

from scene_generator import _generate_procedural_fallback_scenes, enforce_visual_cadence_14


class TestSceneConsistency(unittest.TestCase):
    def test_visual_cadence_does_not_duplicate_narration(self):
        scenes = [{"scene_number": index + 1, "duration": 6, "narration": f"Özgün cümle {index}", "search_queries": ["primary", "alternate"]} for index in range(10)]
        expanded = enforce_visual_cadence_14(scenes)
        spoken = [scene["narration"] for scene in expanded]
        self.assertTrue(all(spoken))
        self.assertEqual(len(spoken), len(set(spoken)))
        self.assertTrue(any(scene.get("is_visual_cutaway") for scene in expanded))

    def test_reddit_fallback_uses_reddit_story_structure(self):
        plan = _generate_procedural_fallback_scenes("Ailemle yaşadığım tartışma", "2_reddit_confessions")
        self.assertEqual(plan["scenes"][0]["narration"].split()[0], "Bunu")
        self.assertIn("Siz olsaydınız", plan["full_narration"])


if __name__ == "__main__":
    unittest.main()