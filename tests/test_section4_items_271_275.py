"""
Unit tests for Section 4 retention items 271-275 (batch 15 audit — Section 4 closeout).
"""
import unittest

from effects.filters import get_scene_brightness_alternation_filter, apply_scene_brightness_alternation
from moviepy.editor import ColorClip
from scenes.enrichment import enrich_continuous_motion_hints, enrich_audio_visual_contrast_scenes
from viral_retention_engine import ViralRetentionEngine


class TestSection4Items271275(unittest.TestCase):
    def test_item_271_continuous_motion_hints(self):
        scenes = [{"duration": 4.0, "search_queries": ["city night"]}]
        out = enrich_continuous_motion_hints(scenes)
        self.assertTrue(out[0].get("handheld_shake"))

    def test_item_272_brightness_alternation_filter(self):
        dark = get_scene_brightness_alternation_filter(0)
        bright = get_scene_brightness_alternation_filter(1)
        self.assertIn("eq=gamma=", dark)
        self.assertIn("eq=gamma=", bright)
        self.assertNotEqual(dark, bright)

    def test_item_272_brightness_moviepy(self):
        clip = ColorClip(size=(720, 1280), color=(30, 30, 30), duration=1.0)
        alt = apply_scene_brightness_alternation(clip, scene_index=1)
        self.assertEqual(alt.size, (720, 1280))

    def test_item_273_audio_visual_contrast(self):
        scenes = [
            {"duration": 3.0, "search_queries": ["calm forest"], "narration": "Sakin bir gün."},
            {"duration": 3.0, "search_queries": ["office"], "narration": "Herkes bunu biliyor."},
            {"duration": 3.0, "search_queries": ["library"], "narration": "Ama gerçek farklı."},
            {"duration": 3.0, "search_queries": ["storm"], "narration": "Ve işte kanıt."},
        ]
        out = enrich_audio_visual_contrast_scenes(scenes)
        climax = out[2]
        self.assertTrue(climax.get("audio_visual_contrast"))
        self.assertTrue(climax.get("impact_shake"))
        self.assertTrue(climax.get("tts_calm_pace"))
        self.assertTrue(any("shock" in q or "explosion" in q or "horror" in q for q in climax["search_queries"]))

    def test_item_274_story_arc_breakdown(self):
        arc = ViralRetentionEngine.build_shorts_story_arc_breakdown(45.0)
        self.assertEqual(len(arc["phases"]), 4)
        ranges = [p["time_range"] for p in arc["phases"]]
        self.assertIn("0 - 3s", ranges[0])
        self.assertIn("36 - 45s", ranges[-1])

    def test_item_275_retention_score_and_hook_goal(self):
        arc = ViralRetentionEngine.build_shorts_story_arc_breakdown()
        hook_goal = arc["phases"][0]["goal"]
        self.assertIn("Viewed", hook_goal)
        res = ViralRetentionEngine.calculate_retention_score(
            has_split_screen=False,
            has_anti_duplicate=True,
            has_karaoke=True,
            has_loop=True,
            audio_ducking=True,
        )
        self.assertGreaterEqual(res["score"], 80)
        self.assertIn("score", res)


if __name__ == "__main__":
    unittest.main()
