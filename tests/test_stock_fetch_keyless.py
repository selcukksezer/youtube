"""Regression: UI stock fetch works when Pexels/Pixabay keys are empty."""
import importlib
import unittest
from unittest.mock import patch

_mr = importlib.import_module("routers.media_router")
auto_fetch_videos_for_scenes = _mr.auto_fetch_videos_for_scenes
_fetch_single_scene_video = _mr._fetch_single_scene_video

from visuals.query_builder import keyless_seed_queries


class TestKeylessStockFetch(unittest.TestCase):
    def test_religious_keyless_seeds_are_short(self):
        seeds = keyless_seed_queries(
            niche_id="10_religious_quotes",
            queries=["sunrise over mosque silhouette soft natural light"],
            max_seeds=5,
        )
        self.assertTrue(seeds)
        self.assertTrue(any("mosque" in s.lower() for s in seeds))
        self.assertTrue(all(len(s.split()) <= 4 for s in seeds))

    @patch.object(_mr, "_paid_stock_keys_present", return_value=False)
    @patch.object(_mr, "_search_legacy_stock", return_value=[])
    @patch.object(_mr, "_search_keyless_visuals")
    def test_fetch_falls_back_to_keyless(self, mock_keyless, _legacy, _keys):
        mock_keyless.return_value = {
            "id": "ov_1",
            "source": "openverse",
            "url": "https://example.invalid/mosque.jpg",
            "thumbnail": "https://example.invalid/mosque.jpg",
            "duration": 8,
            "width": 1600,
            "height": 1200,
            "kind": "image",
            "query": "mosque",
        }
        scenes = [
            {
                "search_queries": ["sunrise over mosque silhouette soft natural light"],
                "scene_description": "mosque sunrise",
            }
        ]
        out = auto_fetch_videos_for_scenes(scenes, niche_id="10_religious_quotes")
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["selected_video"]["source"], "openverse")
        self.assertTrue(out[0]["selected_video"]["url"])
        mock_keyless.assert_called()

    @patch.object(_mr, "_search_legacy_stock")
    def test_paid_provider_wins_when_present(self, mock_legacy):
        mock_legacy.return_value = [
            {
                "id": "px_1",
                "source": "pexels",
                "url": "https://example.invalid/clip.mp4",
                "thumbnail": "",
                "duration": 9,
                "width": 1080,
                "height": 1920,
            }
        ]
        sc = _fetch_single_scene_video(
            (0, {"search_queries": ["mosque dome"]}, "10_religious_quotes")
        )
        self.assertEqual(sc["selected_video"]["source"], "pexels")


if __name__ == "__main__":
    unittest.main()
