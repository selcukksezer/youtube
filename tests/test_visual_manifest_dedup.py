"""
Test visual manifest deduplication & retry resilience.
Verifies that re-fetching clips or cache hits with identical UIDs does NOT trigger:
'ValueError: source manifest contains duplicate visual assets'
"""

import os
import shutil
import tempfile
import unittest

from visuals.fetch import (
    reset_job_manifest,
    get_job_manifest,
    add_manifest_entry,
    write_job_credits,
)
from visuals.license import License, LicenseInfo


class TestVisualManifestDedup(unittest.TestCase):

    def setUp(self):
        reset_job_manifest()
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)
        reset_job_manifest()

    def test_add_manifest_entry_replaces_same_scene_index(self):
        """Re-fetching a scene must replace the old entry for that scene_index."""
        lic = LicenseInfo(License.PEXELS, "pexels").to_dict()

        add_manifest_entry({
            "scene_index": 0,
            "uid": "pexels:100",
            "path": "/path/clip_old.mp4",
            "license": lic,
        })
        self.assertEqual(len(get_job_manifest()), 1)
        self.assertEqual(get_job_manifest()[0]["uid"], "pexels:100")

        # Simulate K1-Semantic re-fetching scene 0
        add_manifest_entry({
            "scene_index": 0,
            "uid": "pexels:200",
            "path": "/path/clip_new.mp4",
            "license": lic,
        })
        self.assertEqual(len(get_job_manifest()), 1)
        self.assertEqual(get_job_manifest()[0]["uid"], "pexels:200")

    def test_write_job_credits_handles_duplicate_uids_gracefully(self):
        """Multiple scenes with cache hits (same UID) must be auto-suffixed and succeed."""
        lic = LicenseInfo(License.CC0, "ai_procedural").to_dict()

        # Scene 0 and Scene 1 both hit the same cache entry (same UID)
        add_manifest_entry({
            "scene_index": 0,
            "uid": "ai:pollinations:db4783b0637ae24f8e876ab2",
            "path": "/path/s0.mp4",
            "license": lic,
        })
        add_manifest_entry({
            "scene_index": 1,
            "uid": "ai:pollinations:db4783b0637ae24f8e876ab2",  # Duplicate UID!
            "path": "/path/s1.mp4",
            "license": lic,
        })

        # Calling write_job_credits must NOT raise "source manifest contains duplicate visual assets"
        credits = write_job_credits(self.tmp_dir)
        self.assertIn("json", credits)
        self.assertIn("manifest", credits)

        # Inspect resulting manifest
        manifest = get_job_manifest()
        self.assertEqual(len(manifest), 2)
        uids = [m["uid"] for m in manifest]
        self.assertEqual(len(uids), len(set(uids)))  # All UIDs are strictly unique!

    def test_write_job_credits_auto_heals_legacy_ai_license(self):
        """Legacy AI clips with missing or unknown licenses are self-healed as commercial safe."""
        add_manifest_entry({
            "scene_index": 0,
            "uid": "legacy:unknown:2c331128f14c7dd360afa42280e4db41",
            "path": "/output/project/s000_ai_video.mp4",
            "license": {"license": "unknown", "source": "unknown"},
        })
        credits = write_job_credits(self.tmp_dir)
        self.assertIn("json", credits)
        manifest = get_job_manifest()
        self.assertEqual(manifest[0]["license"]["license"], "ai_generated")


if __name__ == "__main__":
    unittest.main()
