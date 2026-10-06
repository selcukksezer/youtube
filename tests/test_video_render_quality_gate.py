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


class TestVideoRenderQualityGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def setUp(self):
        state.is_rendering_active = False

    def tearDown(self):
        state.is_rendering_active = False

    def test_hard_fail_is_rejected_before_task_or_render_lock(self):
        with patch.object(video_router, "process_video_task") as process_task:
            response = self.client.post(
                "/api/video/render",
                json={"keyword": "test", "plan": _hard_fail_plan()},
            )

        self.assertEqual(response.status_code, 422)
        process_task.assert_not_called()
        self.assertFalse(state.is_rendering_active)
        lock_acquired = state.render_lock.acquire(blocking=False)
        self.assertTrue(lock_acquired)
        if lock_acquired:
            state.render_lock.release()

    def test_valid_plan_queues_render_task(self):
        with patch.object(video_router, "process_video_task") as process_task:
            response = self.client.post(
                "/api/video/render",
                json={"keyword": "test", "plan": _valid_plan()},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get("status"), "started")
        process_task.assert_called_once()
        self.assertTrue(state.is_rendering_active)


if __name__ == "__main__":
    unittest.main()