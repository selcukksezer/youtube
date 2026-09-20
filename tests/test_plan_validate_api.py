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

    def test_plan_repair_route_exists(self):
        resp = self.client.post("/api/plan/repair", json={"plan": _sample_plan()})
        self.assertNotEqual(resp.status_code, 404, msg="POST /api/plan/repair must be registered")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("status"), "ok")
        self.assertIn("plan", data)


if __name__ == "__main__":
    unittest.main()
