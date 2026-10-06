"""API tests for pre-render plan validation endpoints."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from server import app


def _sample_plan(n=3):
    return {
        "title": "Marcus Test",
        "niche_id": "6_stoic_philosophy",
        "scenes": [
            {
                "narration": f"Bu stoaci kural {i + 1} ofkeyi yok eder ve zihni sakin tutar.",
                "duration": 3.0,
                "search_queries": ["stoic portrait", "roman emperor"],
            }
            for i in range(n)
        ],
    }


class TestPlanValidateApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_plan_validate_route_exists(self):
        resp = self.client.post("/api/plan/validate", json={"plan": _sample_plan()})
        self.assertNotEqual(resp.status_code, 404, msg="POST /api/plan/validate must be registered")

    def test_plan_validate_returns_gate_fields(self):
        resp = self.client.post(
            "/api/plan/validate?auto_repair=true",
            json={
                "plan": _sample_plan(),
                "title": "Marcus Test",
                "niche": "6_stoic_philosophy",
                "language": "tr",
                "recompile": True,
                "auto_repair": True,
            },
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("status"), "ok")
        self.assertIn("ok", data)
        self.assertIn("plan", data)
        self.assertIn("narration_integrity", data)
        self.assertIn("pre_render_score", data)
        self.assertIn("scene_continuity_advisories", data)

    def test_topic_discontinuity_is_advisory_only(self):
        discontinuous_plan = _sample_plan()
        narrations = [
            "Astronot Mars yüzeyindeki kraterleri ölçtü ve kaya örneklerini topladı.",
            "Şef mutfakta hamuru yoğurdu, baharatları ekledi ve fırını ısıttı.",
            "Keman sanatçısı sahnede melodiyi çaldı, yayını kaldırdı ve dinleyicileri selamladı.",
        ]
        discontinuous_plan["scenes"] = [
            {**scene, "narration": narrations[index]}
            for index, scene in enumerate(discontinuous_plan["scenes"])
        ]

        def validate(plan):
            return self.client.post(
                "/api/plan/validate?auto_repair=false",
                json={"plan": plan, "recompile": False, "auto_repair": False},
            )

        discontinuous_response = validate(discontinuous_plan)
        self.assertEqual(discontinuous_response.status_code, 200)
        discontinuous = discontinuous_response.json()
        self.assertEqual(discontinuous["ok"], discontinuous["narration_ok"])
        self.assertEqual(len(discontinuous["scene_continuity_advisories"]), 1)

    def test_plan_repair_route_exists(self):
        resp = self.client.post("/api/plan/repair", json={"plan": _sample_plan()})
        self.assertNotEqual(resp.status_code, 404, msg="POST /api/plan/repair must be registered")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("status"), "ok")
        self.assertIn("plan", data)


if __name__ == "__main__":
    unittest.main()
