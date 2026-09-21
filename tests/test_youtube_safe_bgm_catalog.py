"""Tests for YouTube-safe BGM catalog."""
import os
import tempfile
import unittest
from unittest.mock import patch

import config
from youtube_safe_bgm_catalog import (
    catalog_meta,
    get_display_label,
    load_catalog,
    pick_catalog_bgm_for_niche,
    search_catalog,
)


class TestYoutubeSafeBgmCatalog(unittest.TestCase):
    def test_catalog_has_at_least_60_tracks(self):
        tracks = load_catalog()
        self.assertGreaterEqual(len(tracks), 60)

    def test_catalog_meta_count(self):
        meta = catalog_meta()
        self.assertGreaterEqual(meta.get("count", 0), 60)

    def test_search_by_niche(self):
        hits = search_catalog(niche="philosophy", limit=5)
        self.assertTrue(hits)
        blob = " ".join(
            (t.get("title", "") + " " + " ".join(t.get("niche_tags") or [])).lower()
            for t in hits
        )
        self.assertTrue("philosophy" in blob or "stoic" in blob or "meditation" in blob)

    def test_search_by_mood(self):
        hits = search_catalog(mood="calm", limit=5)
        self.assertTrue(hits)
        self.assertTrue(any("calm" in str(t.get("mood", "")).lower() for t in hits))

    def test_display_label(self):
        tracks = load_catalog()
        fn = tracks[0]["filename"]
        label = get_display_label(fn)
        self.assertIn(tracks[0]["title"], label)

    @patch("youtube_safe_bgm_catalog.ensure_catalog_track")
    def test_pick_for_niche(self, mock_ensure):
        mock_ensure.return_value = "yt_safe_127_valley_sunset.mp3"
        fn = pick_catalog_bgm_for_niche("stoic philosophy")
        self.assertEqual(fn, "yt_safe_127_valley_sunset.mp3")
        mock_ensure.assert_called_once()

    def test_track_filenames_unique(self):
        tracks = load_catalog()
        filenames = [t["filename"] for t in tracks]
        self.assertEqual(len(filenames), len(set(filenames)))

    def test_all_tracks_have_urls(self):
        for t in load_catalog():
            self.assertTrue(t.get("url", "").startswith("https://"))
            self.assertTrue(t.get("filename", "").endswith(".mp3"))


if __name__ == "__main__":
    unittest.main()
