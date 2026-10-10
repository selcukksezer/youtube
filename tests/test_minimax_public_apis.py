"""Public API fallback catalog and system endpoint tests."""
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


class TestSystemRoutesPublic(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient
        from server import app
        self.client = TestClient(app)

    def test_public_apis_status_endpoint(self):
        resp = self.client.get("/api/system/public-apis/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data.get("status"), "ok")
        self.assertGreaterEqual(len(data.get("endpoints", [])), 7)

    def test_removed_local_video_engine_routes_are_not_registered(self):
        self.assertEqual(self.client.get("/api/system/minimax-h3/status").status_code, 404)
        self.assertEqual(self.client.post("/api/system/minimax-h3/start").status_code, 404)


if __name__ == "__main__":
    unittest.main()
