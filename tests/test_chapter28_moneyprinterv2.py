"""
Tests for Chapter 28.14 / Section 2.2 (Madde 12):
reference_repos2/MoneyPrinterV2 evolution:
- services/llm_cache.py: LLMResponseCache, sha256 prompt hashing, TTL
- services/video_preflight.py: verify_mp4_integrity, stream validation, orientation check
- services/postbridge_syndicator.py: build_syndication_webhook_payload
- services/affiliate_product_engine.py: parse_ecommerce_url
"""

import json
import os
import shutil
import tempfile
import time
import unittest
from unittest.mock import patch, MagicMock

from services.llm_cache import LLMResponseCache
from services.video_preflight import verify_mp4_integrity
from services.postbridge_syndicator import build_syndication_webhook_payload
from services.affiliate_product_engine import parse_ecommerce_url


class TestMoneyPrinterV2LLMCache(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.cache = LLMResponseCache(cache_dir=self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_cache_miss_then_hit(self):
        model = "gpt-4o"
        sys_p = "You are an expert scriptwriter."
        usr_p = "Write a 50s script about black holes."

        # 1. First get -> miss
        self.assertIsNone(self.cache.get(model, sys_p, usr_p))
        self.assertEqual(self.cache.misses, 1)

        # 2. Set response
        response = "Black holes are regions of spacetime..."
        self.cache.set(model, sys_p, usr_p, response)

        # 3. Second get -> hit
        cached = self.cache.get(model, sys_p, usr_p)
        self.assertEqual(cached, response)
        self.assertEqual(self.cache.hits, 1)

    def test_distinct_prompts_have_distinct_cache(self):
        model = "gpt-4o"
        sys_p = "Prompt A"
        self.cache.set(model, sys_p, "User 1", "Response 1")

        # Different user prompt
        self.assertIsNone(self.cache.get(model, sys_p, "User 2"))


class TestMoneyPrinterV2VideoPreflight(unittest.TestCase):
    def test_missing_file_fails_preflight(self):
        res = verify_mp4_integrity("nonexistent_video.mp4")
        self.assertFalse(res["valid"])
        self.assertIn("File not found", res["errors"][0])

    @patch("os.path.exists", return_value=True)
    @patch("os.path.getsize", return_value=1024 * 1024)
    @patch("subprocess.run")
    def test_valid_vertical_video_passes(self, mock_run, mock_size, mock_exists):
        fake_probe = {
            "format": {"duration": "35.5"},
            "streams": [
                {"codec_type": "video", "width": 1080, "height": 1920},
                {"codec_type": "audio", "codec_name": "aac"},
            ]
        }
        mock_run.return_value = MagicMock(stdout=json.dumps(fake_probe), returncode=0)

        res = verify_mp4_integrity("video.mp4")
        self.assertTrue(res["valid"])
        self.assertEqual(res["duration"], 35.5)
        self.assertEqual(res["width"], 1080)
        self.assertEqual(res["height"], 1920)
        self.assertTrue(res["has_audio"])
        self.assertEqual(len(res["errors"]), 0)

    @patch("os.path.exists", return_value=True)
    @patch("os.path.getsize", return_value=1024 * 1024)
    @patch("subprocess.run")
    def test_landscape_orientation_fails(self, mock_run, mock_size, mock_exists):
        fake_probe = {
            "format": {"duration": "20.0"},
            "streams": [
                {"codec_type": "video", "width": 1920, "height": 1080},
                {"codec_type": "audio", "codec_name": "aac"},
            ]
        }
        mock_run.return_value = MagicMock(stdout=json.dumps(fake_probe), returncode=0)

        res = verify_mp4_integrity("landscape.mp4")
        self.assertFalse(res["valid"])
        self.assertTrue(any("landscape" in e.lower() for e in res["errors"]))

    @patch("os.path.exists", return_value=True)
    @patch("os.path.getsize", return_value=1024 * 1024)
    @patch("subprocess.run")
    def test_missing_audio_fails(self, mock_run, mock_size, mock_exists):
        fake_probe = {
            "format": {"duration": "25.0"},
            "streams": [
                {"codec_type": "video", "width": 1080, "height": 1920},
            ]
        }
        mock_run.return_value = MagicMock(stdout=json.dumps(fake_probe), returncode=0)

        res = verify_mp4_integrity("silent.mp4")
        self.assertFalse(res["valid"])
        self.assertFalse(res["has_audio"])
        self.assertTrue(any("Missing audio track" in e for e in res["errors"]))


class TestMoneyPrinterV2SyndicationAndAFM(unittest.TestCase):
    def test_syndication_payload_structure(self):
        payload = build_syndication_webhook_payload(
            title="Mindblowing Secret",
            video_url="https://example.com/video.mp4",
            duration_seconds=45.0,
            tags=["shorts", "viral", "#secret"],
            target_platforms=["tiktok", "instagram_reels", "youtube_shorts"],
        )
        self.assertEqual(payload["video"]["aspect_ratio"], "9:16")
        self.assertEqual(payload["video"]["duration_seconds"], 45.0)
        self.assertEqual(len(payload["platforms"]), 3)
        self.assertIn("secret", payload["metadata"]["tags"])

    def test_ecommerce_url_parsing(self):
        amazon_url = "https://www.amazon.com/dp/B08N5WRWNW"
        res_amz = parse_ecommerce_url(amazon_url)
        self.assertEqual(res_amz["platform"], "amazon")
        self.assertEqual(res_amz["product_id"], "B08N5WRWNW")

        trendyol_url = "https://www.trendyol.com/brand/product-name-p-12345678"
        res_ty = parse_ecommerce_url(trendyol_url)
        self.assertEqual(res_ty["platform"], "trendyol")
        self.assertEqual(res_ty["product_id"], "12345678")

    def test_scenes_generator_llm_cache_integration(self):
        from scenes.generator import _call
        from services.llm_cache import GLOBAL_LLM_CACHE
        # Seed cache
        GLOBAL_LLM_CACHE.set(
            model="gpt-test-cache",
            system_prompt="sys-prompt",
            user_prompt="user-prompt",
            response_text='{"scenes":[{"scene_number":1,"narration":"Cached test","duration":5}]}',
        )
        # Call _call without a real API client
        params = {
            "model": "gpt-test-cache",
            "messages": [
                {"role": "system", "content": "sys-prompt"},
                {"role": "user", "content": "user-prompt"},
            ],
        }
        resp = _call(None, params, model_name="gpt-test-cache")
        self.assertIsNotNone(resp)
        self.assertIn("Cached test", resp.choices[0].message.content)

    @patch("services.video_preflight.verify_mp4_integrity")
    def test_headless_uploader_preflight_rejection(self, mock_preflight):
        from services.headless_uploader import upload_video_via_browser
        mock_preflight.return_value = {
            "valid": False,
            "errors": ["Video is 1920x1080 horizontal, Shorts must be 9:16 vertical."],
            "duration": 15.0,
            "has_audio": True,
        }
        with patch("os.path.exists", return_value=True):
            res = upload_video_via_browser(
                video_path="horizontal_dummy.mp4",
                title="Test",
                description="Desc",
                dry_run=False,
            )
            self.assertFalse(res["success"])
            self.assertIn("Preflight MP4 bütünlük hatası", res["error"])


if __name__ == "__main__":
    unittest.main()
