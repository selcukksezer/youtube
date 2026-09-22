"""Subject lock: a skyscraper sentence must not search for a beach."""
from __future__ import annotations

import unittest

from director.schema import ScenePlan
from director.visual_intent import apply_visual_intents
from visuals.license import License, LicenseInfo
from visuals.providers import Candidate
from visuals.query_builder import build_shot_queries
from visuals.registry import score_candidate
from visuals.subject_lock import match_shot, query_matches_clip


class TestSubjectLock(unittest.TestCase):
    def test_gokdelen_is_skyscraper_not_ocean(self):
        shot = match_shot("Gökdelenler rüzgarı nasıl keser")
        self.assertIsNotNone(shot)
        self.assertEqual(shot.root, "skyscraper")
        queries = build_shot_queries(
            narration="Gökdelenler rüzgarı nasıl keser, cam cephe esner.",
            scene_description="tower swaying",
            niche_id="9_five_facts",
        )
        joined = " ".join(queries).lower()
        self.assertIn("skyscraper", joined)
        self.assertNotIn("ocean", joined)
        self.assertNotIn("forest", joined)
        self.assertNotIn("marble", joined)

    def test_title_fills_abstract_sentence(self):
        scenes = [
            ScenePlan(
                index=0,
                narration="Bunu okulda söylemezler ama mühendisler tam olarak bunu yapar.",
                duration=6.0,
                scene_description="abstract explanation",
                search_queries=["soft sunset clouds", "calm ocean waves"],
            )
        ]
        out = apply_visual_intents(
            scenes,
            "9_five_facts",
            title="Gökdelenlerin rüzgar sırrı",
        )
        joined = " ".join(out[0].search_queries).lower()
        self.assertIn("skyscraper", joined)
        self.assertNotIn("ocean", joined)
        self.assertTrue(out[0].search_queries[0].lower().startswith("skyscraper"))

    def test_city_word_does_not_accept_a_beach(self):
        self.assertFalse(query_matches_clip("skyscraper tower city skyline", "city beach sunset"))
        beach = Candidate(
            source="pixabay", id="9", url="https://example.test/beach.mp4", kind="video",
            title="city beach sunset", tags=["ocean"], duration=6,
            license=LicenseInfo(License.PIXABAY, "pixabay"),
        )
        self.assertLess(score_candidate(beach, "skyscraper tower city skyline"), 0)
        tower = Candidate(
            source="pexels", id="3", url="https://example.test/tower.mp4", kind="video",
            title="aerial view of skyscrapers downtown", tags=["tower"], duration=8,
            license=LicenseInfo(License.PEXELS, "pexels"),
        )
        self.assertGreater(score_candidate(tower, "skyscraper tower city skyline"), 0)

    def test_split_drops_off_subject_query(self):
        from visuals.subject_lock import lock_scene_queries
        scene = {
            "narration": "Gökdelen rüzgarda esner ve cam cephe yükü dağıtır.",
            "scene_description": "tower",
            "search_queries": ["ocean waves aerial", "nature"],
        }
        lock_scene_queries(scene)
        joined = " ".join(scene["search_queries"]).lower()
        self.assertIn("skyscraper", joined)
        self.assertNotIn("ocean", joined)
        self.assertNotIn("nature", joined)
        self.assertTrue(scene["visual_intent"]["subject"].lower().startswith("skyscraper"))
        scenes = []
        for i in range(3):
            scenes.append(ScenePlan(
                index=i,
                narration=f"Gökdelen {i + 1}. Rüzgar yükü camı eğer ve yapı sönümler.",
                duration=6.0,
                search_queries=["ocean waves aerial"],
            ))
        out = apply_visual_intents(scenes, "9_five_facts", title="Gökdelenler")
        roots = []
        for scene in out:
            shot = match_shot(scene.visual_intent.subject)
            self.assertIsNotNone(shot)
            roots.append(shot.root)
            self.assertNotIn("ocean", " ".join(scene.search_queries).lower())
        self.assertEqual(set(roots), {"skyscraper"})
        self.assertNotEqual(out[0].visual_intent.subject, out[1].visual_intent.subject)


if __name__ == "__main__":
    unittest.main()
