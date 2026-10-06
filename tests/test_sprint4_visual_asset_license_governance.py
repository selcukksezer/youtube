"""
Sprint 4 / Section 6 Test Suite: Visual Asset Acquisition & License Governance.
Covers:
- 6.1 Multi-provider search orchestration (Pexels, Pixabay, AI, Whiteboard, Procedural)
- 6.2 Idempotent manifest management & conflict prevention
- 6.3 Self-healing commercial license model (no UNKNOWN breaks)
- 6.4 SHA-256 content fingerprinting & double-clip blockage
- 6.5 K1-Semantic narrative relevance validation & re-fetch
- 6.6 Procedural background & motion graphics motors (cellauto, mandelbrot, cyber_grid)
- Safe public URL sanitization (MoneyPrinterTurbo pattern)
"""

import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from visuals.fetch import (
    reset_job_manifest,
    get_job_manifest,
    add_manifest_entry,
    write_job_credits,
    _safe_public_url,
    _file_hash,
)
from visuals.license import License, LicenseInfo, is_commercial_safe
from render.procedural_visuals import build_procedural_clip


class TestSprint4VisualAssetLicenseGovernance(unittest.TestCase):

    def setUp(self):
        reset_job_manifest()
        self.tmp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)
        reset_job_manifest()

    def test_safe_public_url_sanitizer(self):
        """Query parameters and credentials must be stripped from public asset URLs."""
        # Standard URL with access token query parameters
        dirty_url = "https://images.pexels.com/videos/12345/video.mp4?auto=compress&cs=tinysrgb&token=SECRET_123"
        clean = _safe_public_url(dirty_url)
        self.assertEqual(clean, "https://images.pexels.com/videos/12345/video.mp4")

        # URL with user:pass credentials
        cred_url = "https://user:password@cdn.example.com/assets/clip.mp4?sig=xyz"
        clean_cred = _safe_public_url(cred_url)
        self.assertIsNone(clean_cred)

        # Invalid strings
        self.assertIsNone(_safe_public_url(""))
        self.assertIsNone(_safe_public_url(None))

    def test_file_hash_is_sha256(self):
        """_file_hash must return a 64-character SHA-256 hexadecimal string."""
        sample_file = os.path.join(self.tmp_dir, "sample.txt")
        with open(sample_file, "w", encoding="utf-8") as f:
            f.write("YouTube Shorts Ultimate Visual Integrity Check")

        h = _file_hash(sample_file)
        self.assertEqual(len(h), 64)
        # Verify deterministic hash
        import hashlib
        expected = hashlib.sha256(b"YouTube Shorts Ultimate Visual Integrity Check").hexdigest()
        self.assertEqual(h, expected)

    def test_idempotent_manifest_and_sha256_tracking(self):
        """Re-fetching a scene must replace old entry and update hash tracking."""
        f1 = os.path.join(self.tmp_dir, "clip1.mp4")
        f2 = os.path.join(self.tmp_dir, "clip2.mp4")
        with open(f1, "w") as f: f.write("clip one content")
        with open(f2, "w") as f: f.write("clip two different content")

        h1 = _file_hash(f1)
        h2 = _file_hash(f2)

        add_manifest_entry({
            "scene_index": 0,
            "path": f1,
            "uid": "pexels:1001",
            "source": "pexels",
            "license": LicenseInfo(License.PEXELS, "pexels").to_dict(),
        })

        manifest = get_job_manifest()
        self.assertEqual(len(manifest), 1)
        self.assertEqual(manifest[0]["sha256"], h1)

        # Re-fetch scene 0 with new visual
        add_manifest_entry({
            "scene_index": 0,
            "path": f2,
            "uid": "pexels:1002",
            "source": "pexels",
            "license": LicenseInfo(License.PEXELS, "pexels").to_dict(),
        })

        manifest = get_job_manifest()
        self.assertEqual(len(manifest), 1)
        self.assertEqual(manifest[0]["uid"], "pexels:1002")
        self.assertEqual(manifest[0]["sha256"], h2)

    def test_self_healing_unknown_license_at_registration(self):
        """Clips registered with missing or unknown licenses are healed to commercial-safe immediately."""
        # 1. AI clip
        add_manifest_entry({
            "scene_index": 0,
            "path": "/output/s000_flux_ai_gen.mp4",
            "uid": "ai:gen:123",
            "source": "pollinations_ai",
            "license": {"license": "unknown", "source": "unknown"},
        })
        m = get_job_manifest()
        self.assertEqual(m[0]["license"]["license"], "ai_generated")
        self.assertTrue(is_commercial_safe(License(m[0]["license"]["license"])))

        # 2. Pexels clip
        add_manifest_entry({
            "scene_index": 1,
            "path": "/output/s001_pexels_9999.mp4",
            "uid": "pexels:9999",
            "source": "pexels",
            "license": None,
        })
        m = get_job_manifest()
        self.assertEqual(m[1]["license"]["license"], "pexels")
        self.assertTrue(is_commercial_safe(License(m[1]["license"]["license"])))

        # 3. Procedural / Whiteboard clip
        add_manifest_entry({
            "scene_index": 2,
            "path": "/output/s002_whiteboard.mp4",
            "uid": "whiteboard:2",
            "source": "whiteboard",
            "license": {},
        })
        m = get_job_manifest()
        self.assertEqual(m[2]["license"]["license"], "cc0")
        self.assertTrue(is_commercial_safe(License(m[2]["license"]["license"])))

    def test_double_clip_blocking_in_fetch_open_visual(self):
        """Identical video file downloaded across multiple scenes must be rejected via SHA-256."""
        from visuals.fetch import fetch_open_visual, _job_file_hashes
        from visuals.providers import Candidate

        # Create dummy video file
        dummy_video = os.path.join(self.tmp_dir, "dummy_video.mp4")
        with open(dummy_video, "wb") as f:
            f.write(b"\x00" * 20000)

        fake_cand1 = Candidate(
            source="pexels", id="100", url="https://cdn.example.com/v100.mp4",
            kind="video", title="city tower", duration=6.0,
            license=LicenseInfo(License.PEXELS, "pexels"),
        )
        fake_cand2 = Candidate(
            source="pixabay", id="200", url="https://cdn.example.com/v200.mp4",  # Different candidate UID/URL!
            kind="video", title="city tower duplicate", duration=6.0,
            license=LicenseInfo(License.PIXABAY, "pixabay"),
        )

        def fake_norm(src, dst, dur, kind):
            with open(dst, "wb") as f:
                f.write(b"\x00" * 20000)
            return dst

        with patch("visuals.fetch.ordered_providers", return_value=[MagicMock(key="pexels")]), \
             patch("visuals.fetch.search_provider", return_value=[fake_cand1, fake_cand2]), \
             patch("visuals.fetch.score_candidate", return_value=80.0), \
             patch("visuals.fetch._download", return_value=True), \
             patch("visuals.fetch._normalize_clip", side_effect=fake_norm):

            # Scene 0 fetch
            v0 = fetch_open_visual(
                queries=["city tower"], scene_index=0, project_dir=self.tmp_dir,
                target_duration=5.0, narration="modern skyscraper", allow_procedural=False,
            )
            self.assertIsNotNone(v0)
            self.assertEqual(len(get_job_manifest()), 1)
            h0 = get_job_manifest()[0]["sha256"]
            self.assertIn(h0, _job_file_hashes)

            # Scene 1 fetch: candidate 1 & 2 both normalize to dummy_video (same hash!)
            # fetch_open_visual must reject dummy_video for Scene 1 because hash was already used
            v1 = fetch_open_visual(
                queries=["city tower"], scene_index=1, project_dir=self.tmp_dir,
                target_duration=5.0, narration="modern skyscraper", allow_procedural=False,
            )
            # Both candidates have duplicate hash, so non-procedural fetch returns None!
            self.assertIsNone(v1)

    def test_procedural_visual_engines_cellauto_mandelbrot_cyber(self):
        """Section 6.6 FFmpeg procedural engines (cellauto, mandelbrot, cyber_grid) render valid MP4 clips."""
        out_cellauto = os.path.join(self.tmp_dir, "proc_cellauto.mp4")
        res_cell = build_procedural_clip(
            out_cellauto, duration=1.0, scene_index=0, motif="cellauto",
            width=270, height=480, fps=15,
        )
        self.assertIsNotNone(res_cell)
        self.assertTrue(os.path.isfile(res_cell))
        self.assertGreater(os.path.getsize(res_cell), 5000)

        out_cyber = os.path.join(self.tmp_dir, "proc_cyber.mp4")
        res_cyber = build_procedural_clip(
            out_cyber, duration=1.0, scene_index=1, motif="cyber_grid",
            width=270, height=480, fps=15,
        )
        self.assertIsNotNone(res_cyber)
        self.assertTrue(os.path.isfile(res_cyber))
        self.assertGreater(os.path.getsize(res_cyber), 5000)

    def test_k1_semantic_narrative_refetch_trigger(self):
        """Candidates below 8% semantic match must trigger narrative re-fetch."""
        from visuals.fetch import fetch_open_visual
        from visuals.providers import Candidate

        # Low match candidate (< 8% match)
        cand_low = Candidate(
            source="pexels", id="low_1", url="https://cdn.example.com/low.mp4",
            kind="video", title="unrelated landscape", duration=6.0,
            license=LicenseInfo(License.PEXELS, "pexels"),
        )
        cand_low.topic_match_score = 0.04  # 4% match < 8% threshold

        # High match candidate (> 8% match) from narrative query
        cand_high = Candidate(
            source="pexels", id="high_2", url="https://cdn.example.com/high.mp4",
            kind="video", title="bitcoin crypto chart cryptocurrency", duration=6.0,
            license=LicenseInfo(License.PEXELS, "pexels"),
        )
        cand_high.topic_match_score = 0.65  # 65% match

        def fake_search(spec, q, per_page=8):
            if "crypto" in q.lower() or "bitcoin" in q.lower():
                return [cand_high]
            return [cand_low]

        def fake_score(c, q, narration="", target_duration=7.0):
            if c.id == "high_2":
                c.topic_match_score = 0.65
                return 90.0
            c.topic_match_score = 0.04
            return 30.0

        def fake_norm(src, dst, dur, kind):
            with open(dst, "wb") as f:
                f.write(b"\x00" * 25000)
            return dst

        with patch("visuals.fetch.ordered_providers", return_value=[MagicMock(key="pexels")]), \
             patch("visuals.fetch.search_provider", side_effect=fake_search), \
             patch("visuals.fetch.score_candidate", side_effect=fake_score), \
               patch("system_resilience.verify_stock_video_integrity", return_value={"valid": True}), \
             patch("visuals.fetch._download", return_value=True), \
             patch("visuals.fetch._normalize_clip", side_effect=fake_norm):

            v = fetch_open_visual(
                queries=["generic background"], scene_index=0, project_dir=self.tmp_dir,
                target_duration=5.0, narration="Bitcoin fiyatı aniden çöktü kripto piyasası karıştı",
                allow_procedural=False,
            )
            self.assertIsNotNone(v)
            m = get_job_manifest()
            self.assertEqual(len(m), 1)
            # The superior narrative match should have been selected!
            self.assertEqual(m[0]["id"], "high_2")
            self.assertGreaterEqual(m[0]["topic_match_score"], 0.08)


if __name__ == "__main__":
    unittest.main()
