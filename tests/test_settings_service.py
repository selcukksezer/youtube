"""Configuration update behavior tests."""
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import config
from settings_service import (
    _save_to_env_file,
    apply_dashboard_config,
    mask_api_key,
)


def _config_payload(**overrides):
    base = dict(
        gemini_key=None, openai_key=None, deepseek_key=None, grok_key=None,
        pexels_key=None, pixabay_key=None, youtube_data_key=None,
        reddit_client_id=None, reddit_client_secret=None, elevenlabs_key=None,
        subtitle_color=None, subtitle_highlight_color=None,
        subtitle_font_size=None, subtitle_y_position=None,
        enable_bgm=None, bgm_volume=None, default_bgm_track=None,
        language=None, tts_gender=None, tts_voice=None, tts_rate=None, tts_pitch=None,
        gemini_model=None, gemini_image_model=None, gemini_video_model=None,
        gemini_tts_model=None, use_gemini_image_gen=None, use_gemini_video_gen=None,
        use_gemini_tts=None, use_gemini_grounding=None, use_gemini_embeddings=None,
        prefer_gemini_scene_images=None, auto_fetch_royalty_free_bgm=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


class TestSettingsService(unittest.TestCase):
    def test_new_runtime_key_selects_its_provider(self):
        original_provider = (config.AI_PROVIDER, config.AI_API_KEY, config.AI_BASE_URL, config.AI_MODEL)
        data = _config_payload(deepseek_key="new-deepseek")
        try:
            with patch("settings_service._save_to_env_file", return_value=(True, "")), patch.object(config, "GEMINI_API_KEY", ""), patch.object(config, "OPENAI_API_KEY", ""), patch.object(config, "DEEPSEEK_API_KEY", ""), patch.object(config, "GROK_API_KEY", ""):
                apply_dashboard_config(data)
                self.assertEqual(config.AI_PROVIDER, "DeepSeek")
        finally:
            config.AI_PROVIDER, config.AI_API_KEY, config.AI_BASE_URL, config.AI_MODEL = original_provider

    def test_mask_api_key_shows_last_four(self):
        self.assertEqual(mask_api_key("sk-abcdefghijklmnop"), "••••mnop")

    def test_elevenlabs_key_persisted_to_env_with_merge(self):
        original_key = getattr(config, "ELEVENLABS_API_KEY", "")
        with tempfile.TemporaryDirectory() as td:
            env_path = os.path.join(td, ".env")
            with open(env_path, "w", encoding="utf-8") as f:
                f.write("CUSTOM_KEY=keep_me\nGEMINI_API_KEY=old-gemini\n")
            with patch.object(config, "BASE_DIR", td):
                data = _config_payload(elevenlabs_key="sk-test-elevenlabs-key")
                apply_dashboard_config(data)
                with open(env_path, encoding="utf-8") as f:
                    content = f.read()
                self.assertIn("ELEVENLABS_API_KEY=sk-test-elevenlabs-key", content)
                self.assertIn("CUSTOM_KEY=keep_me", content)
                self.assertEqual(config.ELEVENLABS_API_KEY, "sk-test-elevenlabs-key")
        config.ELEVENLABS_API_KEY = original_key

    def test_save_failure_raises_instead_of_silent_success(self):
        data = _config_payload(elevenlabs_key="sk-should-fail")
        with patch("settings_service._save_to_env_file", return_value=(False, "permission denied")):
            with self.assertRaises(RuntimeError) as ctx:
                apply_dashboard_config(data)
            self.assertIn("permission denied", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
