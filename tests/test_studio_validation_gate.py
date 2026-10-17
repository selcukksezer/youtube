"""API tests for the authoritative pre-render script quality gate."""
import os
import sys
import unittest
import importlib
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from server import app
from server_core import state

video_router = importlib.import_module("routers.video_router")


def _valid_plan():
    narrations = [
        "Stoacılar öfkeyi bastırmak yerine önce onun hangi düşünceden doğduğunu dikkatle inceler ve tepki vermeden önce kendilerine kısa bir düşünme alanı açar.",
        "Kontrol edemediğin olaylara enerji harcamak yerine kendi kararlarına ve tepkilerine odaklan; böylece dış koşullar değişirken iç disiplinini koruyabilirsin.",
        "Marcus Aurelius her sabah zorlukları hatırlayarak günün sürprizlerine zihnini hazırlardı ve karşılaştığı her insanın kendi mücadelesi olduğunu kendine anımsatırdı.",
        "Bir engel çıktığında hedefi bırakma; yöntemi değiştir ve ilerlemek için yeni bir yol ara, çünkü direnç bazen doğru yönü gösteren işarettir.",
        "Başkalarının davranışları senin seçimin değildir, fakat onlara nasıl karşılık verdiğin sana aittir; bu ayrımı korumak gereksiz çatışmaları azaltır.",
        "Bugün küçük bir doğru karar vermek, uzun vadede karakterini ve alışkanlıklarını yeniden şekillendirir; tutarlı seçimler zamanla güvenilir bir yaşam kurar.",
    ]
    return {
        "title": "Stoacı düşünce",
        "scenes": [
            {
                "narration": narration,
                "duration": 8,
                "scene_description": f"Distinct cinematic scene showing stoic practice number {index + 1}",
                "search_queries": [f"stoic practice {index}", f"roman philosophy {index}"],
            }
            for index, narration in enumerate(narrations)
        ],
    }


def _hard_fail_plan():
    return {
        "title": "Incomplete script",
        "scenes": [
            {
                "narration": "Kısa bir anlatım.",
                "duration": 6,
                "scene_description": "A short scene description for testing",
                "search_queries": ["short scene", "test scene"],
            }
        ],
        "meta": {"script_quality": {"hard_fail": False}},
    }


class TestStudioValidationGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def setUp(self):
        state.is_rendering_active = False
        self.provider_patch = patch(
            "scenes.generator._configured_script_providers",
            return_value=[],
        )
        self.provider_patch.start()

    def tearDown(self):
        self.provider_patch.stop()
        state.is_rendering_active = False


    def test_studio_validation_reports_non_numeric_scene_duration_without_500(self):
        plan = _valid_plan()
        plan["scenes"][0]["duration"] = "not-a-number"

        response = self.client.post(
            "/api/plan/validate",
            json={
                "title": plan["title"],
                "niche": "6_stoic_philosophy",
                "language": "tr",
                "plan": plan,
            },
        )

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(result["ok"])
        self.assertTrue(result["script_quality"]["hard_fail"])
        self.assertIn(
            "scene_0_duration_invalid",
            result["script_quality"]["issues"],
        )
        self.assertIn("scene_0_duration_invalid", result["pre_render_score"]["issues"])

    def test_studio_validation_rebuilds_invalid_derived_timing_metadata(self):
        plan = _valid_plan()
        plan["full_narration"] = " ".join(scene["narration"] for scene in plan["scenes"])
        plan["scenes"][0].update({
            "index": "invalid",
            "t0": "not-a-number",
            "t1": "Infinity",
            "beat_hint_ms": "NaN",
        })

        response = self.client.post(
            "/api/plan/validate",
            json={
                "title": plan["title"],
                "niche": "6_stoic_philosophy",
                "language": "tr",
                "plan": plan,
            },
        )

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertFalse(result["script_quality"]["hard_fail"], result["script_quality"]["issues"])
        scene = result["plan"]["scenes"][0]
        self.assertEqual(scene["index"], 0)
        self.assertEqual(scene["t0"], 0.0)
        self.assertGreater(scene["t1"], scene["t0"])
        self.assertIsNone(scene.get("beat_hint_ms"))

    def test_studio_validation_reports_non_list_scenes_without_500(self):
        response = self.client.post(
            "/api/plan/validate",
            json={
                "title": "Malformed scenes",
                "niche": "1_news_flash",
                "plan": {"title": "Malformed scenes", "scenes": 7},
            },
        )

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertFalse(result["ok"])
        self.assertTrue(result["script_quality"]["hard_fail"])
        self.assertIn("scenes_invalid", result["script_quality"]["issues"])

    def test_studio_validation_reports_non_object_visual_intent_without_500(self):
        plan = _valid_plan()
        plan["scenes"][0]["visual_intent"] = "invalid-intent"

        response = self.client.post(
            "/api/plan/validate",
            json={
                "title": plan["title"],
                "niche": "6_stoic_philosophy",
                "language": "tr",
                "plan": plan,
            },
        )

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(result["ok"])
        self.assertTrue(result["script_quality"]["hard_fail"])
        self.assertIn(
            "scene_0_visual_intent_invalid",
            result["script_quality"]["issues"],
        )
        self.assertIn(
            "scene_0_visual_intent_invalid",
            result["pre_render_score"]["issues"],
        )

    def test_studio_validation_replaces_malformed_query_string_with_real_queries(self):
        plan = _valid_plan()
        plan["full_narration"] = " ".join(scene["narration"] for scene in plan["scenes"])
        plan["scenes"][0]["search_queries"] = "fake query string"
        plan["scenes"][0]["visual_intent"] = {
            "search_queries": "fake nested query",
            "must_exclude": "gore",
        }

        response = self.client.post(
            "/api/plan/validate",
            json={
                "title": plan["title"],
                "niche": "6_stoic_philosophy",
                "language": "tr",
                "plan": plan,
            },
        )

        self.assertEqual(response.status_code, 200)
        quality = response.json()["script_quality"]
        self.assertFalse(quality["hard_fail"], quality["issues"])
        queries = response.json()["plan"]["scenes"][0]["search_queries"]
        self.assertIsInstance(queries, list)
        self.assertGreaterEqual(len(queries), 2)
        self.assertTrue(all(isinstance(query, str) and len(query) > 1 for query in queries))
        intent = response.json()["plan"]["scenes"][0]["visual_intent"]
        self.assertTrue(
            all(len(query) > 1 for query in intent["search_queries"])
        )
        self.assertTrue(all(len(term) > 1 for term in intent["must_exclude"]))


if __name__ == "__main__":
    unittest.main()