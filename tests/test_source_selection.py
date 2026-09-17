"""Tests for persistent no-reuse source selection."""
import unittest
from unittest.mock import patch

import database
from video_fetcher import _used_ids


class TestSourceSelection(unittest.TestCase):
    def test_persisted_source_is_excluded_before_download(self):
        database.init_db()
        source_key = "pexels:test-persisted-source"
        database.record_source_asset(source_key, "https://example.invalid/old.mp4", "old-hash", "pexels")
        self.assertTrue(database.source_asset_was_used(source_key))
        self.assertNotIn("test-persisted-source", _used_ids)


if __name__ == "__main__":
    unittest.main()