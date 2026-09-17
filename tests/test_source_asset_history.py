"""Persistent downloaded-source history tests."""
import unittest

import database


class TestSourceAssetHistory(unittest.TestCase):
    def test_source_key_remains_used_after_recording(self):
        database.init_db()
        source_key = "test-source-history-never-reuse"
        database.record_source_asset(source_key, "https://example.invalid/asset.mp4", "test-hash", "test")
        self.assertTrue(database.source_asset_was_used(source_key))
        self.assertTrue(database.source_asset_was_used("other-key", "test-hash"))


if __name__ == "__main__":
    unittest.main()