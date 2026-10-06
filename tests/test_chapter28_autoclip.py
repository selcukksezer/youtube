"""
Tests for Chapter 28.17 / Section 2.2 (Madde 16):
reference_repos2/autoclip evolution:
- services/process_cleaner.py: categorize_exception, SubprocessRollbackManager, cleanup_temp_files
- compliance/visual_diversity.py: compute_clip_fingerprint, is_visually_too_similar, enforce_visual_clip_diversity
"""

import os
import subprocess
import tempfile
import unittest

from services.process_cleaner import (
    categorize_exception,
    ErrorCategory,
    SubprocessRollbackManager,
)
from compliance.visual_diversity import (
    is_visually_too_similar,
    enforce_visual_clip_diversity,
)


class TestAutoClipProcessCleaner(unittest.TestCase):
    def test_categorize_exceptions(self):
        # 1. File I/O
        res_file = categorize_exception(FileNotFoundError("Missing asset.mp4"), request_id="req-123")
        self.assertEqual(res_file["error"]["category"], ErrorCategory.FILE_IO.value)
        self.assertEqual(res_file["error"]["request_id"], "req-123")

        # 2. Validation
        res_val = categorize_exception(ValueError("Invalid aspect ratio"))
        self.assertEqual(res_val["error"]["category"], ErrorCategory.VALIDATION.value)

        # 3. Processing
        res_proc = categorize_exception(subprocess.CalledProcessError(1, ["ffmpeg"]))
        self.assertEqual(res_proc["error"]["category"], ErrorCategory.PROCESSING.value)

        # 4. Network
        res_net = categorize_exception(Exception("Connection timeout to Pexels API"))
        self.assertEqual(res_net["error"]["category"], ErrorCategory.NETWORK.value)

    def test_rollback_manager_temp_file_cleanup(self):
        mgr = SubprocessRollbackManager()
        tmp_fd, tmp_path = tempfile.mkstemp(suffix="_test_autoclip.tmp")
        os.close(tmp_fd)

        self.assertTrue(os.path.exists(tmp_path))
        mgr.register_temp_file(tmp_path)

        deleted = mgr.cleanup_temp_files()
        self.assertEqual(deleted, 1)
        self.assertFalse(os.path.exists(tmp_path))

    def test_rollback_context_manager_triggers_on_error(self):
        mgr = SubprocessRollbackManager()
        tmp_fd, tmp_path = tempfile.mkstemp(suffix="_test_err.tmp")
        os.close(tmp_fd)
        mgr.register_temp_file(tmp_path)

        try:
            with mgr:
                raise RuntimeError("Simulated crash during video rendering")
        except RuntimeError:
            pass

        # Verify rollback cleaned up the file
        self.assertFalse(os.path.exists(tmp_path))


class TestAutoClipVisualDiversity(unittest.TestCase):
    def test_similarity_detection_same_creator(self):
        clip_1 = {"id": "c1", "creator_id": "creator_99", "color_tone": "blue", "query": "city"}
        clip_2 = {"id": "c2", "creator_id": "creator_99", "color_tone": "red", "query": "car"}
        self.assertTrue(is_visually_too_similar(clip_1, clip_2))

    def test_similarity_detection_same_query_and_tone(self):
        clip_1 = {"id": "c1", "creator_id": "creator_1", "color_tone": "dark_neon", "query": "cyberpunk"}
        clip_2 = {"id": "c2", "creator_id": "creator_2", "color_tone": "dark_neon", "query": "cyberpunk"}
        self.assertTrue(is_visually_too_similar(clip_1, clip_2))

    def test_distinct_clips_not_similar(self):
        clip_1 = {"id": "c1", "creator_id": "creator_1", "color_tone": "warm", "query": "sunrise"}
        clip_2 = {"id": "c2", "creator_id": "creator_2", "color_tone": "cool", "query": "office meeting"}
        self.assertFalse(is_visually_too_similar(clip_1, clip_2))

    def test_enforce_diversity_substitution(self):
        scene_0 = {"id": "c1", "creator_id": "creator_99", "color_tone": "blue", "query": "finance"}
        scene_1_similar = {"id": "c2", "creator_id": "creator_99", "color_tone": "blue", "query": "finance"}
        scene_2 = {"id": "c3", "creator_id": "creator_3", "color_tone": "green", "query": "nature"}

        candidate_pool = {
            1: [
                scene_1_similar,
                {"id": "c2_alt", "creator_id": "creator_77", "color_tone": "golden", "query": "coins"},
            ]
        }

        adjusted = enforce_visual_clip_diversity([scene_0, scene_1_similar, scene_2], candidate_pools=candidate_pool)
        self.assertEqual(len(adjusted), 3)
        # Verify scene 1 was substituted with alternative candidate
        self.assertEqual(adjusted[1]["id"], "c2_alt")


if __name__ == "__main__":
    unittest.main()
