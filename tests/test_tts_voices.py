"""Tests for Edge TTS voice catalog."""
import unittest
from unittest.mock import patch

import config
from tts_voices import (
    EDGE_TTS_VOICE_CATALOG,
    ELEVENLABS_FREE_VOICES,
    LOCAL_OFFLINE_VOICES,
    _el_voice_cache,
    get_voice_catalog,
    is_valid_voice,
    is_voice_available_from_catalog,
    list_voices_for_language,
    resolve_voice,
    voice_gender_for_id,
)


class TestTtsVoiceCatalog(unittest.TestCase):
    def test_tr_voice_count_at_least_ten(self):
        tr = list_voices_for_language("tr")
        self.assertGreaterEqual(len(tr), 10)

    def test_en_voice_count_at_least_ten(self):
        en = list_voices_for_language("en")
        self.assertGreaterEqual(len(en), 10)

    def test_all_edge_entries_have_neural_quality(self):
        for lang in ("tr", "en"):
            for v in get_voice_catalog()[lang]:
                self.assertIn("Neural", v["quality"])
                self.assertTrue(v["id"].endswith("Neural"))
                self.assertIn(v["gender"], ("male", "female"))

    def test_resolve_explicit_voice(self):
        self.assertEqual(resolve_voice("en", voice_id="en-GB-SoniaNeural"), "en-GB-SoniaNeural")

    def test_resolve_gender_default_tr(self):
        self.assertEqual(resolve_voice("tr", gender="female"), "tr-TR-EmelNeural")

    def test_is_valid_voice_scoped(self):
        self.assertTrue(is_valid_voice("tr-TR-AhmetNeural", "tr"))
        self.assertFalse(is_valid_voice("en-US-GuyNeural", "tr"))

    def test_catalog_availability_is_scoped_and_does_not_fetch_remote_voices(self):
        self.assertTrue(is_voice_available_from_catalog("tr-TR-AhmetNeural", "tr"))
        self.assertFalse(is_voice_available_from_catalog("en-US-GuyNeural", "tr"))
        self.assertTrue(
            is_voice_available_from_catalog(LOCAL_OFFLINE_VOICES[0]["id"], "en")
        )
        with patch("tts_voices.list_elevenlabs_voices", side_effect=AssertionError):
            self.assertFalse(
                is_voice_available_from_catalog("elevenlabs:unknown", "tr")
            )

    def test_catalog_availability_accepts_cached_elevenlabs_voices(self):
        voice_id = "elevenlabs:catalogued-custom-voice"
        with patch.object(config, "ELEVENLABS_API_KEY", "configured-test-key"):
            with patch.dict(
                _el_voice_cache,
                {
                    "api_key": "configured-test-key",
                    "voices": [{"id": voice_id}],
                    "error": None,
                    "source": "api",
                },
            ):
                with patch("tts_voices.list_elevenlabs_voices", side_effect=AssertionError):
                    self.assertTrue(is_voice_available_from_catalog(voice_id, "en"))

    def test_catalog_availability_accepts_known_elevenlabs_voice_when_configured(self):
        known_voice = ELEVENLABS_FREE_VOICES[0]["id"]
        with patch.object(config, "ELEVENLABS_API_KEY", "configured-test-key"):
            with patch.dict(
                _el_voice_cache,
                {"api_key": "", "voices": [], "error": None, "source": "none"},
            ):
                with patch("tts_voices.list_elevenlabs_voices", side_effect=AssertionError):
                    self.assertTrue(
                        is_voice_available_from_catalog(known_voice, "tr")
                    )

    def test_voice_gender_for_id(self):
        self.assertEqual(voice_gender_for_id("en-US-JennyNeural", "en"), "female")

    def test_config_imports_catalog(self):
        self.assertIn("tr", EDGE_TTS_VOICE_CATALOG)
        self.assertTrue(config.TTS_VOICE.endswith("Neural") or config.TTS_VOICE.startswith("elevenlabs:"))


if __name__ == "__main__":
    unittest.main()
