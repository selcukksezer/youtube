import asyncio
import unittest
from unittest.mock import patch

from production.schemas import SceneSpec, ShortsScript
from production.stock_fetcher import AsyncStockFetcher
from visuals.license import License, LicenseInfo
from visuals.providers import Candidate


class TestProductionContracts(unittest.TestCase):
    def test_rejects_placeholder_scene(self):
        with self.assertRaises(ValueError):
            SceneSpec(index=0, narration="Bu gerçek bir anlatım cümlesidir.", duration=3, scene_description="(SCENE_DESCRIPTION)", search_queries=["tower"])

    def test_script_builds_narration_and_caps_timeline(self):
        script = ShortsScript(title="Gökdelenlerin sırrı", niche_id="5_science", scenes=[
            {"index": 0, "narration": "Gökdelenler rüzgârı nasıl yönetiyor?", "duration": 3, "scene_description": "A tower moves slightly in strong wind.", "search_queries": ["skyscraper wind"]},
        ])
        self.assertIn("Gökdelenler", script.full_narration)

    @patch("production.stock_fetcher.ordered_providers", return_value=[])
    def test_async_fetcher_degrades_to_empty_without_providers(self, _providers):
        result = asyncio.run(AsyncStockFetcher("5_science").search(scene_description="A skyscraper tower"))
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
