"""Scenario writing audit batches C-G — render gate, word budget, diversity, 429, API integration."""
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from scenes.narration_validate import plan_narration_usable, plan_quality_usable, repair_post_hook_word_budget
from scenes.plan_linter import lint_plan_diversity
from server import app


LIVE_TOPIC = (
    "🔴LIVE TRADING: Gold & Bitcoin | 21st Sept 2026| "
    "#crypto #forex #btc #livetrading"
)


def _half_empty_ai_plan():
    good = "Bu sahne en az on iki kelime iceren tam ve anlamli bir Turkce cumledir."
    return {
        "title": LIVE_TOPIC,
        "scenes": [
            {
                "narration": good if i < 7 else ".",
                "search_queries": [f"query {i}"],
                "duration": 3.0,
            }
            for i in range(14)
        ],
    }


def _repetitive_ai_plan():
    return {
        "title": "Test",
        "scenes": [
            {
                "narration": "Bu tekrarlayan plan test cumlesi yeterli kelime sayisina sahip oldugunu gosterir.",
                "scene_description": "Cinematic stock footage of dramatic city skyline at sunset",
                "search_queries": ["same stock clip"],
                "mood": "epic",
                "duration": 3.0,
            }
            for _ in range(14)
        ],
    }


class TestScenarioBatchC(unittest.TestCase):
    def test_render_worker_ui_plan_gate_injects_fallback(self):
        from server_core.render_worker import _ensure_ui_plan_narration_usable

        bad = _half_empty_ai_plan()
        self.assertFalse(plan_narration_usable(bad["scenes"]))
        fixed = _ensure_ui_plan_narration_usable(bad, LIVE_TOPIC, "8_crypto_market", "tr")
        self.assertTrue(plan_quality_usable(fixed.get("scenes") or []))


class TestScenarioBatchD(unittest.TestCase):
    def test_post_hook_word_budget_trims_without_emptying(self):
        scenes = [
            {
                "narration": " ".join(["kelime"] * 40) + ". Son cumle burada biter.",
                "duration": 3.0,
            }
            for _ in range(14)
        ]
        plan = {"scenes": scenes}
        out = repair_post_hook_word_budget(plan, max_words=110)
        total = sum(len((s.get("narration") or "").split()) for s in out["scenes"])
        self.assertLessEqual(total, 110)
        for sc in out["scenes"]:
            self.assertTrue((sc.get("narration") or "").strip())


class TestScenarioBatchE(unittest.TestCase):
    def test_lint_flags_repetitive_plan(self):
        lint = lint_plan_diversity(_repetitive_ai_plan())
        self.assertTrue(lint["weak"])
        joined = " ".join(lint["warnings"])
        self.assertIn("duplicate_queries", joined)
        self.assertIn("low_mood_diversity", joined)


class TestScenarioBatchF(unittest.TestCase):
    def test_gemini_script_circuit_skips_provider(self):
        from scenes.generator import _gemini_script_circuit_open
        from system_resilience import circuit_breaker

        circuit_breaker.record_failure("gemini_script", "HTTP 429 quota")
        circuit_breaker.record_failure("gemini_script", "HTTP 429 quota")
        circuit_breaker.record_failure("gemini_script", "HTTP 429 quota")
        self.assertTrue(_gemini_script_circuit_open())
        circuit_breaker.record_success("gemini_script")


class TestScenarioBatchG(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    @patch("scenes.generator._call")
    def test_api_generate_script_half_empty_ai_response(self, mock_call):
        import json
        import config as app_config

        half = _half_empty_ai_plan()
        mock_resp = MagicMock()
        mock_resp.choices = [
            MagicMock(message=MagicMock(content=json.dumps({"scenes": half["scenes"], "title": LIVE_TOPIC})))
        ]
        mock_call.return_value = mock_resp

        prev = (
            app_config.AI_PROVIDER,
            app_config.AI_API_KEY,
            getattr(app_config, "AI_BASE_URL", ""),
            getattr(app_config, "AI_MODEL", ""),
            getattr(app_config, "_P", None),
        )
        app_config.AI_PROVIDER = "Gemini"
        app_config.AI_API_KEY = "test-key"
        app_config.AI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
        app_config.AI_MODEL = "gemini-flash-lite-latest"
        app_config._P = []
        try:
            resp = self.client.post(
                "/api/script/generate",
                json={"keyword": LIVE_TOPIC, "niche": "8_crypto_market", "language": "tr"},
            )
        finally:
            app_config.AI_PROVIDER, app_config.AI_API_KEY, app_config.AI_BASE_URL, app_config.AI_MODEL, app_config._P = prev

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        scenes = (data.get("plan") or {}).get("scenes") or []
        self.assertGreaterEqual(len(scenes), 10)
        self.assertTrue(plan_quality_usable(scenes))


if __name__ == "__main__":
    unittest.main()
