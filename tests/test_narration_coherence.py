"""Tests for cross-scene split-verb detection and repair."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from director import compile_director_plan
from director.timeline import _split_narration_near_mid, solve_timeline
from director.schema import DirectorPlan, QualityThresholds, ScenePlan
from scenes.narration_coherence import (
    detect_split_verb_pair,
    repair_cross_scene_coherence,
    repair_split_verbs_across_scenes,
)
from scenes.narration_validate import validate_and_fix_scenes


WEDDING_DNA_TITLE = (
    "Kardeşimin düğününde nikah memurunun İtiraz eden var mı sorusuna "
    "cebimdeki DNA test sonucunu gösterdim"
)


def _wedding_dna_broken_scenes():
    """User-reported bug: 'ilan etti' split across scenes 11-12."""
    narrs = [
        "Kardeşimin düğününde herkes mutlu görünüyordu ama ben farklı bir planım vardı.",
        "Nikah memuru geleneksel soruyu sordu: İtiraz eden var mı?",
        "Salondaki herkes nefesini tuttu ve gözler bana döndü.",
        "Cebimde gizli tuttuğum zarfı yavaşça çıkardım.",
        "İçinde kardeşimle babam arasındaki DNA test sonucu vardı.",
        "Sonuçlar her şeyi değiştirecek kadar netti.",
        "Babamın yüzü bir anda bembeyaz oldu.",
        "Kardeşim şok içinde bana bakıyordu.",
        "Gelin ve damat ne olduğunu anlamaya çalışıyordu.",
        "Nikah memuru tekrar sordu: İtiraz eden var mı?",
        "Şimdi bütün aile beni hain ilan.",
        "Etti ve düğünü mahveden cani olarak görüyorlar.",
        "Ama gerçeği söylemek zorundaydım.",
        "Peki sen olsaydın aynı şeyi yapar mıydın?",
    ]
    return [
        {
            "narration": n,
            "duration": 3.0,
            "scene_description": f"wedding drama scene {i + 1}",
            "search_queries": [f"wedding ceremony {i + 1}", "dramatic reaction", "family conflict"],
            "mood": "DRAMATIC",
            "beat_type": "conflict" if i > 0 else "hook",
        }
        for i, n in enumerate(narrs)
    ]


class TestSplitVerbDetection(unittest.TestCase):
    def test_user_ilan_etti_pattern_detected(self):
        self.assertTrue(
            detect_split_verb_pair(
                "Şimdi bütün aile beni hain ilan.",
                "Etti ve düğünü mahveden cani olarak görüyorlar.",
            )
        )

    def test_complete_sentences_not_flagged(self):
        self.assertFalse(
            detect_split_verb_pair(
                "Şimdi bütün aile beni hain ilan etti.",
                "Düğünü mahveden cani olarak görüyorlar.",
            )
        )


class TestSplitVerbRepair(unittest.TestCase):
    def test_merge_ilan_etti_across_scenes(self):
        scenes = _wedding_dna_broken_scenes()
        repaired, fixes = repair_split_verbs_across_scenes(scenes)
        self.assertTrue(any("merged_split_verb" in f for f in fixes))
        self.assertEqual(len(repaired), 13)
        merged = repaired[10]["narration"]
        self.assertIn("ilan etti", merged.lower())
        self.assertNotIn("ilan.", merged.lower())

    def test_validate_and_fix_also_merges(self):
        scenes = _wedding_dna_broken_scenes()
        fixed, issues = validate_and_fix_scenes(scenes)
        self.assertEqual(len(fixed), 13)
        self.assertIn("ilan etti", fixed[10]["narration"].lower())

    def test_wedding_dna_compile_coherent(self):
        plan = {"title": WEDDING_DNA_TITLE, "scenes": _wedding_dna_broken_scenes()}
        repaired, fixes = repair_cross_scene_coherence(plan)
        self.assertTrue(fixes)
        for i in range(len(repaired["scenes"]) - 1):
            prev = repaired["scenes"][i]["narration"]
            nxt = repaired["scenes"][i + 1]["narration"]
            self.assertFalse(
                detect_split_verb_pair(prev, nxt),
                msg=f"Split verb still at scenes {i}-{i + 1}: {prev!r} | {nxt!r}",
            )


class TestTimelineNoMidWordSplit(unittest.TestCase):
    def test_single_sentence_not_split_at_word_midpoint(self):
        text = "Şimdi bütün aile beni hain ilan etti ve düğünü mahveden cani olarak görüyorlar."
        left, right = _split_narration_near_mid(text)
        self.assertEqual(left, "")
        self.assertEqual(right, "")

    def test_two_sentences_split_at_boundary(self):
        text = "Ilk cumle burada bitiyor. Ikinci cumle burada basliyor ve devam ediyor."
        left, right = _split_narration_near_mid(text)
        self.assertTrue(left.endswith("."))
        self.assertTrue(right.startswith("Ikinci"))

    def test_cadence_pad_uses_visual_not_word_split(self):
        scenes = [
            ScenePlan(
                index=0,
                narration="Tek cümlelik uzun anlatım burada devam ediyor ve hiç bölünmemeli.",
                duration=4.0,
                scene_description="wedding hall",
            )
        ]
        plan = DirectorPlan(
            title="Test",
            niche_id="2_reddit_confessions",
            scenes=scenes,
            quality_thresholds=QualityThresholds(min_scenes=14),
        )
        solved = solve_timeline(plan)
        full_narr = " ".join(s.narration for s in solved.scenes if s.narration)
        self.assertIn("bölünmemeli", full_narr)
        self.assertNotIn("ilan.", full_narr.lower())


if __name__ == "__main__":
    unittest.main()
