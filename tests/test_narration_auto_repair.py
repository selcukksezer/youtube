"""Auto-repair + normalization tests for narration quality gate."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from director import compile_director_plan, pre_render_score
from director.quality_gate import check_narration_integrity
from scenes.narration_validate import (
    auto_repair_plan,
    auto_repair_scene_narration,
    normalize_narration_for_validation,
    plan_narration_ok,
    scene_narration_issues,
)


def _sample_scenes(n=14, narr_template=None):
    scenes = []
    for i in range(n):
        narr = narr_template or f"Bu stoacı kural {i + 1} öfkeyi yok eder ve zihni sakin tutar."
        scenes.append({
            "narration": narr,
            "duration": 3.0,
            "scene_description": "cinematic stoic portrait",
            "search_queries": ["stoic portrait", "roman emperor", "calm mind"],
        })
    return scenes


class TestNarrationNormalization(unittest.TestCase):
    def test_urgent_mood_tag_passes_gate(self):
        raw = "**URGENT** SON DAKİKA! Öfkeyi anında bitiren gizli Roma kuralı sızdırıldı! 🚨🔥"
        norm = normalize_narration_for_validation(raw)
        self.assertTrue(norm.endswith("!"))
        self.assertEqual(scene_narration_issues(raw), [])

    def test_dramatic_scene_passes(self):
        raw = "**DRAMATIC** İmparator Marcus Aurelius'un bu sırrı ortalığı sarsıyor. 👑⚡"
        self.assertEqual(scene_narration_issues(raw), [])

    def test_trailing_emojis_no_false_no_terminal(self):
        raw = "Marcus Aurelius bugün yaşasaydı sana bunu söylerdi! 🚨🔥"
        self.assertEqual(scene_narration_issues(raw), [])


class TestNarrationAutoRepair(unittest.TestCase):
    def test_missing_terminal_repaired(self):
        fixed, fixes = auto_repair_scene_narration("Marcus Aurelius bugün yaşasaydı")
        self.assertTrue(fixed.endswith("."))
        self.assertIn("added_terminal", fixes)
        self.assertEqual(scene_narration_issues(fixed), [])

    def test_two_word_fragment_merged_or_completed(self):
        plan = {
            "title": "Test",
            "scenes": [
                {"narration": "Kisa parca", "duration": 3.0},
                {"narration": "Bu ikinci sahne yeterince uzun bir cumle icerir.", "duration": 3.0},
            ],
        }
        repaired, fixes = auto_repair_plan(plan)
        self.assertTrue(plan_narration_ok(repaired) or any("merged" in f or "completion" in f for f in fixes))

    def test_user_marcus_pattern_repaired(self):
        plan = {
            "title": "Marcus",
            "scenes": [
                {"narration": "Marcus Aurelius bugün yaşasaydı.", "duration": 3.0},
                {"narration": "Öfkeni yok etmek için ilk kural.", "duration": 3.0},
                {"narration": "Karşındakinin kusuru seni değil, insanların hataları senin huzurunu asla.", "duration": 3.0},
                {"narration": "İkinci kural olaylar değil, senin onlara.", "duration": 3.0},
            ],
        }
        repaired, fixes = auto_repair_plan(plan)
        self.assertTrue(fixes, msg="Expected repairs applied")
        for sc in repaired["scenes"]:
            self.assertEqual(scene_narration_issues(sc["narration"]), [])

    def test_formatted_screenshot_plan_pre_render_ok(self):
        scenes = [
            "**URGENT** SON DAKİKA! Öfkeyi anında bitiren gizli Roma kuralı sızdırıldı! 🚨🔥",
            "**DRAMATIC** İmparator Marcus Aurelius'un bu sırrı ortalığı sarsıyor. 👑⚡",
        ]
        for i in range(2, 14):
            scenes.append(f"Stoaci kural {i} zihni sakin tutar ve ofkeyi yok eder.")
        raw = {"title": "Marcus Kural", "scenes": _sample_scenes(14)}
        raw["scenes"][0]["narration"] = scenes[0]
        raw["scenes"][1]["narration"] = scenes[1]
        director = compile_director_plan(raw, title=raw["title"], niche_id="6_stoic_philosophy")
        pre = pre_render_score(director)
        integrity = check_narration_integrity(director)
        self.assertEqual(integrity, [], msg=integrity)
        narr_block = [
            i for i in pre.get("issues", [])
            if i.startswith("fragment") or i.startswith("low_words")
            or i.startswith("empty_narration") or i.startswith("no_terminal")
        ]
        self.assertFalse(narr_block, msg=narr_block)


class TestBrokenStillFails(unittest.TestCase):
    def test_unfixable_empty_still_fails(self):
        plan = {"title": "X", "scenes": [{"narration": "", "duration": 3.0}]}
        repaired, fixes = auto_repair_plan(plan)
        self.assertFalse(plan_narration_ok(repaired))


class TestPlanValidateApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        from server import app
        cls.client = TestClient(app)

    def _formatted_plan(self):
        scenes = []
        for i in range(14):
            narr = (
                "**URGENT** SON DAKIKA! Ofkeyi aninda bitiren gizli Roma kurali sizdirildi!"
                if i == 0 else
                f"Stoaci kural {i + 1} zihni sakin tutar ve ofkeyi yok eder."
            )
            scenes.append({
                "narration": narr,
                "duration": 3.0,
                "scene_description": "cinematic stoic portrait",
                "search_queries": ["stoic portrait", "roman emperor"],
            })
        return {"title": "Marcus Kural", "scenes": scenes, "niche_id": "6_stoic_philosophy"}

    def test_validate_endpoint_exists(self):
        res = self.client.post(
            "/api/plan/validate",
            json={"plan": {"scenes": [{"narration": "Bu cumle yeterince uzun bir anlatimdir.", "duration": 3.0}]}, "title": "Test"},
        )
        self.assertNotEqual(res.status_code, 404, msg=res.text)
        self.assertEqual(res.status_code, 200, msg=res.text)
        body = res.json()
        self.assertEqual(body.get("status"), "ok")
        self.assertIn("ok", body)

    def test_repair_endpoint_exists(self):
        res = self.client.post(
            "/api/plan/repair",
            json={"plan": {"scenes": [{"narration": "Marcus icin.", "duration": 3.0}]}, "title": "Test"},
        )
        self.assertNotEqual(res.status_code, 404, msg=res.text)
        self.assertEqual(res.status_code, 200, msg=res.text)
        body = res.json()
        self.assertEqual(body.get("status"), "ok")
        self.assertIn("fixes", body)

    def test_formatted_narration_passes_validate_api(self):
        res = self.client.post(
            "/api/plan/validate",
            json={
                "plan": self._formatted_plan(),
                "title": "Marcus Kural",
                "niche": "6_stoic_philosophy",
                "language": "tr",
                "auto_repair": True,
                "recompile": True,
            },
        )
        self.assertEqual(res.status_code, 200, msg=res.text)
        body = res.json()
        self.assertEqual(body.get("status"), "ok")
        self.assertTrue(body.get("ok"), msg=body.get("narration_integrity") or body.get("pre_render_score"))


if __name__ == "__main__":
    unittest.main()
