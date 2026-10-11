"""Configuration update behavior tests."""
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import config
from pydantic import ValidationError
from api_models import ConfigUpdateModel
from settings_service import (
    _key_hints,
    _save_to_env_file,
    apply_dashboard_config,
    mask_api_key,
)


def _config_payload(**overrides):
    base = dict(
        gemini_key=None, openai_key=None, deepseek_key=None, grok_key=None,
        pexels_key=None, pixabay_key=None, youtube_data_key=None,
        reddit_client_id=None, reddit_client_secret=None, elevenlabs_key=None,
        sonilo_key=None,
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
    def test_config_update_normalizes_supported_tts_settings(self):
        request = ConfigUpdateModel(
            language=" EN ",
            tts_gender=" FEMALE ",
            tts_voice=" en-US-GuyNeural ",
            tts_rate=" +18% ",
            tts_pitch=" -2Hz ",
        )
        self.assertEqual(request.language, "en")
        self.assertEqual(request.tts_gender, "female")
        self.assertEqual(request.tts_voice, "en-US-GuyNeural")
        self.assertEqual(request.tts_rate, "+18%")
        self.assertEqual(request.tts_pitch, "-2Hz")

    def test_config_update_rejects_unsupported_tts_settings(self):
        invalid_values = (
            {"language": "fr"},
            {"tts_gender": "neutral"},
            {"language": "tr", "tts_voice": "en-US-GuyNeural"},
            {"tts_voice": "not-a-real-voice"},
            {"tts_rate": "fast"},
            {"tts_rate": "+101%"},
            {"tts_rate": "-51%"},
            {"tts_pitch": "+5%"},
            {"tts_pitch": "zero"},
        )
        for values in invalid_values:
            with self.subTest(values=values):
                with self.assertRaises(ValidationError):
                    ConfigUpdateModel(**values)

    def test_config_update_validates_shared_render_settings(self):
        request = ConfigUpdateModel(
            subtitle_color=" #aabbcc ",
            subtitle_highlight_color="YELLOW",
            subtitle_font_size=40,
            subtitle_y_position=0.9,
            bgm_volume=0.3,
        )
        self.assertEqual(request.subtitle_color, "#AABBCC")
        self.assertEqual(request.subtitle_highlight_color, "yellow")
        self.assertEqual(request.subtitle_font_size, 40)
        self.assertEqual(request.subtitle_y_position, 0.9)
        self.assertEqual(request.bgm_volume, 0.3)

    def test_config_update_rejects_values_outside_render_contracts(self):
        invalid_values = (
            ("subtitle_color", "not-a-color"),
            ("subtitle_highlight_color", "#123"),
            ("subtitle_font_size", 39),
            ("subtitle_font_size", 73),
            ("subtitle_y_position", 0.49),
            ("subtitle_y_position", 0.91),
            ("bgm_volume", -0.01),
            ("bgm_volume", 0.31),
        )
        for field, value in invalid_values:
            with self.subTest(field=field, value=value):
                with self.assertRaises(ValidationError):
                    ConfigUpdateModel(**{field: value})

    def test_config_update_validates_default_bgm_track_names(self):
        self.assertEqual(
            ConfigUpdateModel(default_bgm_track="  calm_track.mp3 ").default_bgm_track,
            "calm_track.mp3",
        )
        self.assertEqual(
            ConfigUpdateModel(
                default_bgm_track=r"youtube_studio\calm_track.mp3"
            ).default_bgm_track,
            "youtube_studio/calm_track.mp3",
        )
        self.assertEqual(ConfigUpdateModel(default_bgm_track=" ").default_bgm_track, "")
        for filename in ("../../outside.mp3", "malware.exe", "CON.mp3"):
            with self.subTest(filename=filename):
                with self.assertRaises(ValidationError):
                    ConfigUpdateModel(default_bgm_track=filename)

    def test_config_endpoint_rejects_invalid_render_settings_before_update(self):
        import importlib
        from fastapi.testclient import TestClient
        from server import app

        config_router = importlib.import_module("routers.config_router")
        client = TestClient(app)
        for field, value in (
            ("subtitle_color", "invalid"),
            ("subtitle_font_size", 100),
            ("subtitle_y_position", 0.1),
            ("bgm_volume", 2),
            ("language", "fr"),
            ("tts_gender", "neutral"),
            ("tts_voice", "not-a-real-voice"),
            ("tts_rate", "fast"),
            ("tts_pitch", "invalid"),
            ("default_bgm_track", "../../outside.mp3"),
        ):
            with self.subTest(field=field):
                with patch.object(config_router, "apply_dashboard_config") as apply:
                    response = client.post("/api/config", json={field: value})
                self.assertEqual(response.status_code, 422)
                apply.assert_not_called()

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

    def test_sonilo_key_is_masked_and_persisted_to_env(self):
        original_key = config.SONILO_API_KEY
        original_env = os.environ.get("SONILO_API_KEY")
        try:
            with tempfile.TemporaryDirectory() as td, patch.object(config, "BASE_DIR", td):
                data = _config_payload(sonilo_key="sonilo-test-key-1234")
                apply_dashboard_config(data)
                with open(os.path.join(td, ".env"), encoding="utf-8") as env_file:
                    self.assertIn("SONILO_API_KEY=sonilo-test-key-1234", env_file.read())
                self.assertEqual(config.SONILO_API_KEY, "sonilo-test-key-1234")
                self.assertEqual(_key_hints()["sonilo"], "••••1234")
        finally:
            config.SONILO_API_KEY = original_key
            if original_env is None:
                os.environ.pop("SONILO_API_KEY", None)
            else:
                os.environ["SONILO_API_KEY"] = original_env

    def test_save_failure_raises_instead_of_silent_success(self):
        data = _config_payload(elevenlabs_key="sk-should-fail")
        with patch("settings_service._save_to_env_file", return_value=(False, "permission denied")):
            with self.assertRaises(RuntimeError) as ctx:
                apply_dashboard_config(data)
            self.assertIn("permission denied", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
