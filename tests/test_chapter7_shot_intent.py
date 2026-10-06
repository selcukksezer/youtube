"""Bölüm 7.6: sahne niyeti aramayı ve kamerayı seçer."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from director.schema import ScenePlan
from director.visual_intent import apply_visual_intents, classify_scene_intent
from render.ffmpeg_graph import cheap_pan_filter


class TestChapter7ShotIntent(unittest.TestCase):
    def test_short_word_does_not_false_closeup(self):
        kind = classify_scene_intent("Misafir geldi ve oturdu.", index=1, total_scenes=4)
        self.assertNotEqual(kind, "closeup")

    def test_tags_drive_query_and_camera(self):
        scenes = [
            ScenePlan(index=0, narration="Şehir ufkunda geniş bir sabah başladı.", duration=3.0),
            ScenePlan(index=1, narration="Adamın gözüne yakından baktılar.", duration=3.0),
            ScenePlan(index=2, narration="Kalabalık koşarak kaçtı.", duration=3.0),
            ScenePlan(index=3, narration="Ve tam da bu yüzden başa döner.", duration=3.0),
        ]
        apply_visual_intents(scenes, "1_news_flash", title="şehir sabahı")
        self.assertEqual(scenes[0].scene_intent, "establishing")
        self.assertEqual(scenes[0].visual_intent.shot_type, "establishing")
        wide = " ".join(scenes[0].search_queries).lower()
        self.assertIn("wide shot", wide)
        self.assertNotIn("close up", wide)

        self.assertEqual(scenes[1].scene_intent, "closeup")
        close = " ".join(scenes[1].search_queries).lower()
        self.assertIn("close up", close)
        self.assertNotIn("wide shot", close)

        self.assertEqual(scenes[2].scene_intent, "action")
        self.assertEqual(scenes[3].scene_intent, "transition")
        self.assertTrue(scenes[0].camera_direction)
        self.assertNotEqual(scenes[0].camera_direction, scenes[1].camera_direction)

    def test_camera_label_changes_crop(self):
        left = cheap_pan_filter(1080, 1920, 3.0, 0, camera_direction="pan_left")
        zoom = cheap_pan_filter(1080, 1920, 3.0, 0, camera_direction="zoom_in")
        self.assertNotEqual(left, zoom)
        self.assertIn("(in_h-out_h)/2", left)
        self.assertIn("(in_h-out_h)*0.5*", zoom)
