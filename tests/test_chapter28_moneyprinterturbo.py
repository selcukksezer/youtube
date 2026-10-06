"""
Tests for Chapter 28.13 / Section 2.2 (Madde 11):
reference_repos2/MoneyPrinterTurbo evolution:
- services/material_cache.py: safe_public_url, MaterialCache, atomic write, striped locks
- services/bgm_security.py: validate_bgm_filename, validate_bgm_file, should_use_bgm
- render/ffmpeg_graph.py: VIDEO_DURATION_SAFETY_MARGIN (0.1s anti-black frame)
"""

import os
import shutil
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor

from services.material_cache import (
    safe_public_url,
    MaterialCache,
)
from services.bgm_security import (
    validate_bgm_filename,
    validate_bgm_file,
    should_use_bgm,
    BgmSecurityError,
    MAX_BGM_UPLOAD_BYTES,
)
from render.ffmpeg_graph import (
    VIDEO_DURATION_SAFETY_MARGIN,
    get_required_video_duration,
)


class TestMoneyPrinterTurboMaterialCache(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.cache = MaterialCache(cache_dir=self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_safe_public_url(self):
        raw = "https://images.pexels.com/photos/123/test.jpg?auto=compress&cs=tinysrgb&secret_token=abc12345"
        cleaned = safe_public_url(raw)
        self.assertEqual(cleaned, "https://images.pexels.com/photos/123/test.jpg")

        # Credentials stripped
        raw_cred = "https://user:pass@example.com/audio.mp3"
        self.assertIsNone(safe_public_url(raw_cred))

    def test_cache_set_and_get(self):
        items = [{"id": 1, "url": "https://example.com/v.mp4", "source_url": "https://example.com/p?token=123"}]
        self.cache.set("future city", "pexels", items, aspect="portrait")

        cached = self.cache.get("future city", "pexels", aspect="portrait")
        self.assertIsNotNone(cached)
        self.assertEqual(len(cached), 1)
        self.assertEqual(cached[0]["source_url"], "https://example.com/p")

    def test_cache_ttl_expiration(self):
        items = [{"id": 2}]
        self.cache.set("ancient rome", "pixabay", items)

        # Immediate get returns items
        self.assertIsNotNone(self.cache.get("ancient rome", "pixabay", ttl=10))

        # Expired TTL returns None
        time.sleep(0.05)
        self.assertIsNone(self.cache.get("ancient rome", "pixabay", ttl=0.01))

    def test_concurrent_cache_writes(self):
        def worker(idx):
            self.cache.set(f"query_{idx % 10}", "pexels", [{"id": idx}])
            return self.cache.get(f"query_{idx % 10}", "pexels")

        with ThreadPoolExecutor(max_workers=8) as ex:
            results = list(ex.map(worker, range(32)))
            for res in results:
                self.assertIsNotNone(res)


class TestMoneyPrinterTurboBgmSecurity(unittest.TestCase):
    def test_valid_bgm_filenames(self):
        self.assertEqual(validate_bgm_filename("ambient_track.mp3"), "ambient_track.mp3")
        self.assertEqual(validate_bgm_filename("cinematic_drums.wav"), "cinematic_drums.wav")

    def test_traversal_blocked(self):
        with self.assertRaises(BgmSecurityError):
            validate_bgm_filename("../../windows/system32/cmd.exe")

    def test_windows_reserved_names_blocked(self):
        with self.assertRaises(BgmSecurityError):
            validate_bgm_filename("CON.mp3")
        with self.assertRaises(BgmSecurityError):
            validate_bgm_filename("com1.wav")

    def test_unsafe_unicode_bidi_blocked(self):
        # Right-to-left override character
        bad_name = "audio\u202Emp3.exe"
        with self.assertRaises(BgmSecurityError):
            validate_bgm_filename(bad_name)

    def test_unsupported_extension_blocked(self):
        with self.assertRaises(BgmSecurityError):
            validate_bgm_filename("video_clip.mp4")

    def test_file_size_limit(self):
        validate_bgm_file("good.mp3", file_size=1024 * 1024)
        with self.assertRaises(BgmSecurityError):
            validate_bgm_file("oversized.mp3", file_size=MAX_BGM_UPLOAD_BYTES + 100)

    def test_should_use_bgm(self):
        self.assertFalse(should_use_bgm("none", 0.5))
        self.assertFalse(should_use_bgm("ambient", 0.0))
        self.assertTrue(should_use_bgm("ambient", 0.25))


class TestMoneyPrinterTurboDurationSafetyMargin(unittest.TestCase):
    def test_safety_margin_constant_and_duration_math(self):
        self.assertEqual(VIDEO_DURATION_SAFETY_MARGIN, 0.1)
        req_dur = get_required_video_duration(15.4)
        self.assertAlmostEqual(req_dur, 15.5, places=3)

    def test_bgm_manager_security_rejection(self):
        from bgm_manager import get_bgm_path
        # Windows reserved name blocked
        self.assertIsNone(get_bgm_path("CON.mp3"))
        # Traversal blocked
        self.assertIsNone(get_bgm_path("../../etc/passwd.wav"))
        # Unsupported extension blocked
        self.assertIsNone(get_bgm_path("payload.exe"))

    def test_subtitle_bounce_animation(self):
        from subtitle_generator import create_karaoke_subtitles
        words = [
            {"word": "GELİŞME", "start": 0.0, "end": 0.6},
            {"word": "GERÇEKLEŞTİ", "start": 0.6, "end": 1.2},
        ]
        tmp_ass = "assets/temp_test_bounce.ass"
        try:
            create_karaoke_subtitles(words, tmp_ass, style_opts={"bounce": True})
            with open(tmp_ass, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn(r"\t(0,70,\fscx115\fscy115)", content)
        finally:
            if os.path.exists(tmp_ass):
                try:
                    os.remove(tmp_ass)
                except Exception:
                    pass


if __name__ == "__main__":
    unittest.main()
