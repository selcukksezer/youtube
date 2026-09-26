"""
Unit and integration tests for MoneyPrinterV2 adapted features:
1. Local Ollama Provider (Offline Scriptwriting)
2. AFM Affiliate Product-to-Short Engine
3. Headless Quota-Free YouTube Uploader
4. PostBridge & Webhook Multi-Platform Syndicator
"""

import os
import unittest
from unittest.mock import patch, MagicMock

from services.ollama_provider import (
    is_ollama_available,
    list_ollama_models,
    get_preferred_ollama_model,
)
from services.affiliate_product_engine import (
    extract_product_from_url,
    generate_affiliate_short_plan,
)
from services.headless_uploader import (
    detect_default_browser_profiles,
    upload_video_via_browser,
)
from services.postbridge_syndicator import (
    PostBridgeClient,
    broadcast_to_webhook,
)


class TestMoneyPrinterV2Features(unittest.TestCase):

    def test_ollama_provider_detection_and_selection(self):
        """Test Ollama availability check and preferred model selection."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b'{"models": [{"name": "llama3:latest"}, {"name": "qwen2.5:latest"}]}'
        mock_response.__enter__.return_value = mock_response

        with patch("urllib.request.urlopen", return_value=mock_response):
            self.assertTrue(is_ollama_available())
            models = list_ollama_models()
            self.assertIn("llama3:latest", models)
            self.assertIn("qwen2.5:latest", models)
            pref = get_preferred_ollama_model()
            # qwen2.5 is first in preference list
            self.assertEqual(pref, "qwen2.5:latest")

    def test_affiliate_product_manual_text(self):
        """Test product feature extraction from manual text input."""
        info = extract_product_from_url("Ergonomik Akıllı Masaj Aleti")
        self.assertEqual(info["title"], "Ergonomik Akıllı Masaj Aleti")
        self.assertGreaterEqual(len(info["features"]), 1)

    def test_affiliate_product_plan_generation(self):
        """Test full AFM scene plan generation with viral hooks & scenes."""
        plan = generate_affiliate_short_plan(
            product_input="Akıllı Termos Bardak",
            affiliate_url="https://amzn.to/test1234",
            hook_style="life_hack",
            language="tr",
            cta_text="İndirimli link profilimde!"
        )
        self.assertTrue(plan["ok"])
        self.assertEqual(plan["niche"], "3_gadget_review")
        self.assertEqual(plan["language"], "tr")
        self.assertGreaterEqual(len(plan["scenes"]), 5)
        # Check first scene has viral hook
        first_scene = plan["scenes"][0]
        self.assertIn("narration", first_scene)
        self.assertIn("scene_description", first_scene)
        # Check metadata contains affiliate info
        self.assertIn("affiliate_url", plan["seo_metadata"])
        self.assertEqual(plan["seo_metadata"]["affiliate_url"], "https://amzn.to/test1234")

    def test_affiliate_product_plan_english(self):
        """Test English language AFM generation."""
        plan = generate_affiliate_short_plan(
            product_input="Smart Noise Cancelling Earbuds",
            affiliate_url="https://amzn.to/en_test",
            hook_style="honest_review",
            language="en"
        )
        self.assertTrue(plan["ok"])
        self.assertEqual(plan["language"], "en")
        self.assertIn("Shorts", plan["topic"])
        self.assertIn("Earbuds", plan["scenes"][0]["scene_description"])

    def test_headless_uploader_missing_file_guard(self):
        """Test that non-existent video path is caught immediately."""
        res = upload_video_via_browser(
            video_path="non_existent_fake_video.mp4",
            title="Test Title",
            description="Test Desc",
        )
        self.assertFalse(res["success"])
        self.assertIn("not found", res["error"])

    def test_detect_default_browser_profiles(self):
        """Verify profile scanning executes without crashing."""
        profiles = detect_default_browser_profiles()
        self.assertIn("firefox", profiles)
        self.assertIn("chrome", profiles)

    def test_broadcast_to_webhook_mock(self):
        """Test multi-platform webhook broadcasting."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__.return_value = mock_response

        with patch("urllib.request.urlopen", return_value=mock_response):
            ok = broadcast_to_webhook(
                webhook_url="https://webhook.site/mock-test",
                payload={"video": "test.mp4", "caption": "Viral Short"}
            )
            self.assertTrue(ok)


if __name__ == "__main__":
    unittest.main()
