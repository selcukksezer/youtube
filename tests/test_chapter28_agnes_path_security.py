"""
Unit and integration tests for Chapter 28.1: agnes-video-generator adaptations.
Covers:
- Path security helpers (safe_join, safe_workspace_path, validate_asset_path)
- Task ID sanitization and anti-injection (validate_task_id, sanitize_filename)
- GalleryCache lazy thumbnail generation, striped locks, LRU eviction
- REST API /api/videos/{task_id}/thumbnail traversal defense
"""
import os
import shutil
import tempfile
import time
import unittest
from fastapi.testclient import TestClient

import config
from server import app
from services.path_security import (
    UnsafePathError,
    safe_join,
    safe_workspace_path,
    validate_asset_path,
    validate_task_id,
    sanitize_filename,
)
from services.gallery_cache import GalleryCache


class TestChapter28PathSecurity(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.client = TestClient(app)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    # ─── 1. safe_join & Path Traversal ───
    def test_safe_join_normal(self):
        sub = safe_join(self.tmp_dir, "nested", "file.mp4")
        expected = os.path.realpath(os.path.join(self.tmp_dir, "nested", "file.mp4"))
        self.assertEqual(sub, expected)

    def test_safe_join_traversal_blocked(self):
        with self.assertRaises(UnsafePathError):
            safe_join(self.tmp_dir, "..", "secret.txt")

    def test_safe_join_deep_traversal_blocked(self):
        with self.assertRaises(UnsafePathError):
            safe_join(self.tmp_dir, "sub", "..", "..", "escape.txt")

    def test_safe_join_null_byte_blocked(self):
        with self.assertRaises(UnsafePathError):
            safe_join(self.tmp_dir, "sub\x00inject")

    def test_safe_join_empty_root_blocked(self):
        with self.assertRaises(UnsafePathError):
            safe_join("", "file.mp4")

    # ─── 2. safe_workspace_path & validate_asset_path ───
    def test_safe_workspace_path_contained(self):
        sub_file = os.path.join(self.tmp_dir, "video.mp4")
        open(sub_file, "w").close()
        res = safe_workspace_path(sub_file, allowed_root=self.tmp_dir)
        self.assertEqual(res, os.path.realpath(sub_file))

    def test_safe_workspace_path_escaped(self):
        outside_dir = tempfile.mkdtemp()
        try:
            outside_file = os.path.join(outside_dir, "leak.mp4")
            open(outside_file, "w").close()
            with self.assertRaises(UnsafePathError):
                safe_workspace_path(outside_file, allowed_root=self.tmp_dir)
        finally:
            shutil.rmtree(outside_dir, ignore_errors=True)

    def test_validate_asset_path_approved(self):
        test_file = os.path.join(config.OUTPUT_DIR, "test_render.mp4")
        os.makedirs(config.OUTPUT_DIR, exist_ok=True)
        open(test_file, "w").close()
        try:
            val = validate_asset_path(test_file)
            self.assertEqual(val, os.path.realpath(test_file))
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

    def test_validate_asset_path_blocked(self):
        with self.assertRaises(UnsafePathError):
            validate_asset_path("C:\\Windows\\System32\\cmd.exe", allowed_roots=[self.tmp_dir])

    # ─── 3. validate_task_id & sanitize_filename ───
    def test_validate_task_id_valid(self):
        self.assertEqual(validate_task_id("task_12345"), "task_12345")
        self.assertEqual(validate_task_id("abc-def-789.v1"), "abc-def-789.v1")

    def test_validate_task_id_invalid_traversal(self):
        with self.assertRaises(UnsafePathError):
            validate_task_id("../etc/passwd")

    def test_validate_task_id_invalid_injection(self):
        with self.assertRaises(UnsafePathError):
            validate_task_id("-rf")
        with self.assertRaises(UnsafePathError):
            validate_task_id("task;rm -rf")

    def test_sanitize_filename(self):
        self.assertEqual(sanitize_filename("my cool music (1).mp3"), "my_cool_music__1_.mp3")
        self.assertEqual(sanitize_filename("../../danger.mp3"), "danger.mp3")
        self.assertEqual(sanitize_filename(".hidden"), "hidden")


class TestChapter28GalleryCache(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.cache_dir = os.path.join(self.tmp_dir, "thumbs")
        self.cache = GalleryCache(cache_dir=self.cache_dir, max_items=3, max_age_seconds=2)
        self.client = TestClient(app)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _create_dummy_video(self, filename: str) -> str:
        """Create a tiny 1-second 320x240 MP4 via ffmpeg."""
        import imageio_ffmpeg
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        path = os.path.join(self.tmp_dir, filename)
        cmd = [
            ffmpeg, "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=1.5",
            "-c:v", "libx264", "-t", "1.5", "-pix_fmt", "yuv420p",
            path
        ]
        import subprocess
        subprocess.run(cmd, check=True)
        return path

    def test_gallery_cache_lazy_thumbnail(self):
        video_path = self._create_dummy_video("sample_video.mp4")
        task_id = "sample_video"

        self.assertFalse(self.cache.has_thumb(task_id))
        thumb_path = self.cache.ensure_thumb(task_id, video_path)

        self.assertIsNotNone(thumb_path)
        self.assertTrue(os.path.isfile(thumb_path))
        self.assertTrue(os.path.getsize(thumb_path) > 500)
        self.assertTrue(self.cache.has_thumb(task_id))

        # Second hit should reuse existing without running ffmpeg again
        mtime_before = os.path.getmtime(thumb_path)
        thumb_again = self.cache.ensure_thumb(task_id, video_path)
        self.assertEqual(thumb_path, thumb_again)
        self.assertEqual(mtime_before, os.path.getmtime(thumb_again))

    def test_gallery_cache_rejects_unsafe_task_id(self):
        video_path = self._create_dummy_video("sample.mp4")
        self.assertIsNone(self.cache.ensure_thumb("../../escape", video_path))

    def test_gallery_cache_lru_eviction(self):
        video1 = self._create_dummy_video("vid1.mp4")
        video2 = self._create_dummy_video("vid2.mp4")
        video3 = self._create_dummy_video("vid3.mp4")
        video4 = self._create_dummy_video("vid4.mp4")

        # Cache limit is 3
        t1 = self.cache.ensure_thumb("task1", video1)
        time.sleep(0.01)
        t2 = self.cache.ensure_thumb("task2", video2)
        time.sleep(0.01)
        t3 = self.cache.ensure_thumb("task3", video3)
        time.sleep(0.01)

        self.assertTrue(os.path.isfile(t1))
        self.assertTrue(os.path.isfile(t2))
        self.assertTrue(os.path.isfile(t3))

        # Adding 4th should evict task1
        t4 = self.cache.ensure_thumb("task4", video4)
        self.assertTrue(os.path.isfile(t4))
        self.assertFalse(os.path.isfile(t1))
        self.assertTrue(os.path.isfile(t2))
        self.assertTrue(os.path.isfile(t3))

    def test_gallery_cache_cleanup_expired(self):
        # Create a stale file
        stale_file = os.path.join(self.cache_dir, "stale_task.jpg")
        with open(stale_file, "wb") as f:
            f.write(b"data" * 300)
        past_time = time.time() - 100
        os.utime(stale_file, (past_time, past_time))

        # Create orphaned tmp file
        tmp_file = os.path.join(self.cache_dir, "orphaned.tmp_123.jpg")
        with open(tmp_file, "wb") as f:
            f.write(b"temp")
        os.utime(tmp_file, (past_time - 300, past_time - 300))

        removed = self.cache.cleanup_expired()
        self.assertGreaterEqual(removed, 2)
        self.assertFalse(os.path.isfile(stale_file))
        self.assertFalse(os.path.isfile(tmp_file))

    # ─── 4. REST API Endpoint Traversal Defense ───
    def test_api_thumbnail_traversal_rejected(self):
        resp = self.client.get("/api/videos/..%2F..%2Fwindows%2Fsystem32/thumbnail")
        self.assertIn(resp.status_code, [400, 404])

    def test_api_thumbnail_nonexistent_returns_404(self):
        resp = self.client.get("/api/videos/non_existent_task_9999/thumbnail")
        self.assertEqual(resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()
