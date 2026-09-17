"""Configuration update behavior tests."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import config
from settings_service import apply_dashboard_config


class TestSettingsService(unittest.TestCase):
    def test_new_runtime_key_selects_its_provider(self):
        original_provider = (config.AI_PROVIDER, config.AI_API_KEY, config.AI_BASE_URL, config.AI_MODEL)
        data = SimpleNamespace(
            gemini_key="", openai_key="", deepseek_key="new-deepseek", grok_key="",
            pexels_key=None, pixabay_key=None, youtube_data_key=None, reddit_client_id=None,
            reddit_client_secret=None, subtitle_color=None, subtitle_highlight_color=None,
            subtitle_font_size=None, subtitle_y_position=None, enable_bgm=None, bgm_volume=None,
            default_bgm_track=None, language=None, tts_gender=None, tts_rate=None, tts_pitch=None
        )
        try:
            with patch("settings_service._save_to_env_file"), patch.object(config, "GEMINI_API_KEY", ""), patch.object(config, "OPENAI_API_KEY", ""), patch.object(config, "DEEPSEEK_API_KEY", ""), patch.object(config, "GROK_API_KEY", ""):
                apply_dashboard_config(data)
                self.assertEqual(config.AI_PROVIDER, "DeepSeek")
        finally:
            config.AI_PROVIDER, config.AI_API_KEY, config.AI_BASE_URL, config.AI_MODEL = original_provider


if __name__ == "__main__":
    unittest.main()