"""Tests for persistent no-reuse source selection."""
import json
import os
import tempfile
import unittest
from unittest.mock import patch

import database
import video_fetcher as vf
from video_fetcher import (
    _job_used_ids,
    _published_ids,
    _used_ids,
    commit_published_stock_ids,
    count_pool_candidates,
    discard_job_stock_ids,
    reset_used_videos,
)


def _fake_stock_results(query, n=20):
    return [
        {
            "id": f"pexels_{query}_{i}",
            "source": "pexels",
            "width": 1080,
            "height": 1920,
            "duration": 10,
            "fw": 1080,
            "fh": 1920,
            "url": f"https://example.invalid/{i}.mp4",
            "title": query,
            "tags": query,
        }
        for i in range(n)
    ]


class TestSourceSelection(unittest.TestCase):
    def setUp(self):
        reset_used_videos()
        vf._published_ids.clear()
        vf._job_used_ids.clear()

    def test_persisted_source_is_excluded_before_download(self):
        database.init_db()
        source_key = "pexels:test-persisted-source"
        database.record_source_asset(source_key, "https://example.invalid/old.mp4", "old-hash", "pexels")
        self.assertTrue(database.source_asset_was_used(source_key))
        self.assertNotIn("test-persisted-source", _used_ids)

    def test_job_local_ids_not_persisted_until_publish_p1_12(self):
        _job_used_ids.add("job-only-42")
        self.assertIn("job-only-42", _job_used_ids)
        self.assertNotIn("job-only-42", _published_ids)
        committed = commit_published_stock_ids()
        self.assertEqual(committed, 1)
        self.assertIn("job-only-42", _published_ids)

    def test_failed_job_releases_pool_for_next_job_p1_12(self):
        _job_used_ids.update({f"failed-job-{i}" for i in range(6)})
        discard_job_stock_ids()
        reset_used_videos()
        self.assertEqual(len(_job_used_ids), 0)
        for i in range(6):
            self.assertNotIn(f"failed-job-{i}", _job_used_ids)

    @patch("video_fetcher.ALL_SOURCES", [("pexels", lambda q: _fake_stock_results(q, 20))])
    def test_narrow_query_pool_at_least_14_options_p1_12(self):
        pool = count_pool_candidates(["stoic marble bust portrait"], target_duration=5)
        self.assertGreaterEqual(pool, 14)

    @patch("video_fetcher.ALL_SOURCES", [("pexels", lambda q: _fake_stock_results(q, 20))])
    def test_published_ids_shrink_pool_job_local_does_not_p1_12(self):
        vf._published_ids.update({f"pexels_stoic_{i}" for i in range(8)})
        _job_used_ids.update({f"pexels_stoic_{i}" for i in range(8, 12)})
        pool = count_pool_candidates(["stoic"], target_duration=5)
        self.assertGreaterEqual(pool, 14 - 8)

    def test_blocklisted_stock_id_skipped_p2_24(self):
        database.init_db()
        blocked_id = "pexels_block_test_99"
        database.add_stock_blocklist(blocked_id, "id", "test copyright claim")
        database.refresh_stock_blocklist_cache()

        results = _fake_stock_results("stoic", 5)
        results[0]["id"] = blocked_id
        self.assertTrue(vf._stock_candidate_blocked(results[0]))

        pool_before = sum(
            1 for v in results
            if not vf._stock_candidate_blocked(v)
        )
        self.assertEqual(pool_before, 4)


if __name__ == "__main__":
    unittest.main()