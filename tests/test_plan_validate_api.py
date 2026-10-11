"""API tests for pre-render plan validation endpoints."""
import os
import sys
import unittest
from unittest.mock import patch

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
                "scene_description": f"Stoacı düşünceyi gösteren sahne {i + 1}",
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

    def test_plan_validate_uses_plan_niche_when_request_omits_it(self):
        plan = _sample_plan()
        video_router = __import__("routers.video_router", fromlist=["_plan_gate_result"])
        with patch.object(video_router, "_plan_gate_result", return_value={"ok": True}) as gate:
            response = self.client.post(
                "/api/plan/validate",
                json={"plan": plan, "recompile": False},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(gate.call_args.kwargs["niche"], "6_stoic_philosophy")

    def test_plan_repair_uses_plan_niche_when_request_omits_it(self):
        plan = _sample_plan()
        gate_result = {
            "ok": True,
            "plan": plan,
            "narration_ok": True,
            "narration_integrity": [],
            "scene_continuity_advisories": [],
            "script_quality": {},
            "pre_render_score": {},
        }
        video_router = __import__("routers.video_router", fromlist=["_plan_gate_result"])
        with patch(
            "scenes.narration_validate.auto_repair_plan",
            return_value=(plan, []),
        ), patch.object(
            video_router,
            "_plan_gate_result",
            return_value=gate_result,
        ) as gate:
            response = self.client.post("/api/plan/repair", json={"plan": plan})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(gate.call_args.kwargs["niche"], "6_stoic_philosophy")

    def test_scene_enrichment_failure_is_logged_and_validation_continues(self):
        with patch(
            "scenes.enrichment.enrich_plan_scenes",
            side_effect=RuntimeError("enrichment unavailable"),
        ):
            with self.assertLogs("routers.video_router", level="WARNING") as captured:
                response = self.client.post(
                    "/api/plan/validate",
                    json={
                        "plan": _sample_plan(),
                        "recompile": False,
                        "auto_repair": False,
                    },
                )

        self.assertEqual(response.status_code, 200)
        self.assertIn("enrichment unavailable", "\n".join(captured.output))

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
