"""
Comprehensive Test Suite for Bölüm 34:
- Local MiniMax-H3 Architecture (services/minimax_h3_local.py)
- Public APIs Integration Catalog (services/public_apis_catalog.py)
- System Resilience Circuit Breaker Fallback (system_resilience.py)
- Visuals Fetch Public Media Fallback (visuals/fetch.py)
- FastAPI System Router Endpoints
"""
import unittest
from unittest.mock import MagicMock, patch

from services.public_apis_catalog import (
    APICategory,
    PUBLIC_ENDPOINTS,
    execute_with_public_fallback,
    fetch_met_museum_artworks,
    fetch_openverse_media,
    fetch_philosophical_quote,
    fetch_weather_facts,
    fetch_wikidata_claims,
    fetch_wikipedia_summary,
    get_category_endpoints,
)
from services.minimax_h3_local import (
    assess_minimax_h3_hardware,
    check_local_server_status,
    generate_local_minimax_h3,
)
from system_resilience import CircuitBreaker


class TestPublicAPIsCatalog(unittest.TestCase):
    def test_catalog_categories_and_endpoints(self):
        self.assertGreaterEqual(len(PUBLIC_ENDPOINTS), 7)
        news_eps = get_category_endpoints(APICategory.NEWS_FACTS)
        self.assertTrue(any(ep.name.startswith("wikipedia") for ep in news_eps))
        media_eps = get_category_endpoints(APICategory.MEDIA_ART)
        self.assertTrue(any("openverse" in ep.name for ep in media_eps))
        quote_eps = get_category_endpoints(APICategory.QUOTES_WISDOM)
        self.assertTrue(any("zenquotes" in ep.name for ep in quote_eps))

    def test_wikipedia_summary_mock(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "title": "Stoacılık",
            "extract": "Stoacılık, Helenistik felsefenin en önemli akımlarından biridir.",
            "description": "Felsefe okulu",
        }
        with patch("services.public_apis_catalog.requests.get", return_value=mock_resp):
            data = fetch_wikipedia_summary("Stoacılık", lang="tr")
        self.assertIsNotNone(data)
        self.assertEqual(data["title"], "Stoacılık")
        self.assertIn("Helenistik", data["extract"])

    def test_openverse_media_mock(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "results": [
                {
                    "id": "img123",
                    "title": "Galactic Nebula",
                    "url": "https://example.com/space.jpg",
                    "thumbnail": "https://example.com/space_thumb.jpg",
                    "license": "cc0",
                    "creator": "Hubble",
                }
            ]
        }
        with patch("services.public_apis_catalog.requests.get", return_value=mock_resp):
            results = fetch_openverse_media("nebula", page_size=2)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["id"], "img123")
        self.assertEqual(results[0]["source"], "Openverse")

    def test_philosophical_quote_fallback(self):
        # When ZenQuotes fails, DummyJSON is called
        zen_mock = MagicMock(status_code=500)
        dummy_mock = MagicMock(status_code=200)
        dummy_mock.json.return_value = {"quote": "Stay hungry, stay foolish", "author": "Steve Jobs"}

        with patch("services.public_apis_catalog.requests.get", side_effect=[zen_mock, dummy_mock]):
            q = fetch_philosophical_quote()
        self.assertIsNotNone(q)
        self.assertEqual(q["quote"], "Stay hungry, stay foolish")
        self.assertEqual(q["author"], "Steve Jobs")

    def test_circuit_breaker_public_fallback(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=30.0)
        fallback_called = []

        def failing_primary():
            raise ConnectionError("Pexels 429 Too Many Requests")

        def fallback_action():
            fallback_called.append(True)
            return "fallback_result"

        # Call with fallback
        res = cb.execute_with_fallback("pexels", failing_primary, fallback_action)
        self.assertEqual(res, "fallback_result")
        self.assertTrue(len(fallback_called) == 1)

        # Second failure trips circuit
        res2 = cb.execute_with_fallback("pexels", failing_primary, fallback_action)
        self.assertEqual(res2, "fallback_result")
        self.assertEqual(cb.service_states["pexels"]["state"], CircuitBreaker.STATE_OPEN)

        # Next call routes immediately to fallback without executing failing primary
        primary_mock = MagicMock()
        res3 = cb.execute_with_fallback("pexels", primary_mock, fallback_action)
        self.assertEqual(res3, "fallback_result")
        primary_mock.assert_not_called()

        # Check get_public_fallback_endpoint
        eps = cb.get_public_fallback_endpoint("pexels")
        self.assertIsNotNone(eps)
        self.assertTrue(any(e.name == "openverse_images" for e in eps))


class TestMiniMaxH3Local(unittest.TestCase):
    def test_assess_hardware_nvidia_vram_profiles(self):
        # 1. High VRAM (16GB+) -> FP16
        with patch("hardware_detector.get_gpu_info", return_value={"has_nvidia": True, "vram_mb": 24000}):
            suit = assess_minimax_h3_hardware()
            self.assertTrue(suit.can_run_local)
            self.assertEqual(suit.recommended_quantization, "fp16")

        # 2. Mid VRAM (8-16GB) -> 4bit
        with patch("hardware_detector.get_gpu_info", return_value={"has_nvidia": True, "vram_mb": 8192}):
            suit = assess_minimax_h3_hardware()
            self.assertTrue(suit.can_run_local)
            self.assertEqual(suit.recommended_quantization, "4bit")

        # 3. Low VRAM (<8GB) -> cannot run, safe fallback
        with patch("hardware_detector.get_gpu_info", return_value={"has_nvidia": True, "vram_mb": 4096}):
            suit = assess_minimax_h3_hardware()
            self.assertFalse(suit.can_run_local)
            self.assertIn("VRAM yetersiz", suit.message)

        # 4. No NVIDIA -> cannot run
        with patch("hardware_detector.get_gpu_info", return_value={"has_nvidia": False, "vram_mb": 0}):
            suit = assess_minimax_h3_hardware()
            self.assertFalse(suit.can_run_local)
            self.assertIn("NVIDIA GPU tespit edilemedi", suit.message)

    def test_local_server_status_offline_graceful(self):
        with patch("services.minimax_h3_local.comfy_port_open", return_value=False), \
                patch("services.minimax_h3_local._comfy_proc", None):
            st = check_local_server_status()
            self.assertFalse(st["is_running"])
            self.assertEqual(st["phase"], "offline")

    def test_generate_local_graceful_when_server_offline(self):
        with patch("services.minimax_h3_local.assess_minimax_h3_hardware", return_value=MagicMock(can_run_local=True)), \
             patch("services.minimax_h3_local.check_local_server_status", return_value={"is_running": False, "server_url": "http://127.0.0.1:30010"}):
            out = generate_local_minimax_h3("Test prompt", "test.mp4")
            self.assertIsNone(out)


class TestSystemRoutesPublicAndMiniMax(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient
        from server import app
        self.client = TestClient(app)

    def test_minimax_h3_status_endpoint(self):
        resp = self.client.get("/api/system/minimax-h3/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("status"), "ok")
        self.assertIn("hardware", data)
        self.assertIn("server", data)

    def test_public_apis_status_endpoint(self):
        resp = self.client.get("/api/system/public-apis/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("status"), "ok")
        self.assertGreaterEqual(len(data.get("endpoints", [])), 7)


if __name__ == "__main__":
    unittest.main()
