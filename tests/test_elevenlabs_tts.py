"""Tests for ElevenLabs TTS integration (mocked — no live API key)."""
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import config
from tts_voices import (
    ELEVENLABS_FREE_VOICES,
    clear_elevenlabs_voice_cache,
    get_voice_catalog,
    is_elevenlabs_voice,
    is_valid_voice,
    resolve_voice,
    voice_gender_for_id,
    voice_label_for_id,
)


class TestElevenLabsVoiceCatalog(unittest.TestCase):
    def setUp(self):
        self._orig_key = getattr(config, "ELEVENLABS_API_KEY", "")

    def tearDown(self):
        config.ELEVENLABS_API_KEY = self._orig_key
        clear_elevenlabs_voice_cache()

    def test_free_voice_count_at_least_five(self):
        self.assertGreaterEqual(len(ELEVENLABS_FREE_VOICES), 5)

    def test_voice_ids_use_prefix(self):
        for v in ELEVENLABS_FREE_VOICES:
            self.assertTrue(v["id"].startswith("elevenlabs:"))
            self.assertTrue(is_elevenlabs_voice(v["id"]))

    def test_catalog_hides_elevenlabs_without_key(self):
        config.ELEVENLABS_API_KEY = ""
        catalog = get_voice_catalog()
        self.assertNotIn("elevenlabs", catalog)

    @patch("elevenlabs_tts.fetch_voices_from_api")
    def test_catalog_shows_elevenlabs_with_key(self, mock_fetch):
        config.ELEVENLABS_API_KEY = "test-key"
        clear_elevenlabs_voice_cache()
        mock_fetch.return_value = (list(ELEVENLABS_FREE_VOICES), None)
        catalog = get_voice_catalog(force_refresh=True)
        self.assertIn("elevenlabs", catalog)
        self.assertGreaterEqual(len(catalog["elevenlabs"]), 5)
        self.assertTrue(catalog["elevenlabs_meta"]["configured"])

    @patch("elevenlabs_tts.fetch_voices_from_api")
    def test_catalog_includes_live_api_voices(self, mock_fetch):
        config.ELEVENLABS_API_KEY = "test-key"
        clear_elevenlabs_voice_cache()
        api_voices = [
            {
                "id": f"elevenlabs:mock-{i}",
                "voice_id": f"mock-{i}",
                "label": f"Voice {i}",
                "gender": "female" if i % 2 else "male",
                "quality": "Premade",
                "native": False,
                "provider": "elevenlabs",
            }
            for i in range(12)
        ]
        mock_fetch.return_value = (api_voices, None)
        catalog = get_voice_catalog(force_refresh=True)
        self.assertGreaterEqual(len(catalog["elevenlabs"]), 10)
        self.assertEqual(catalog["elevenlabs_meta"]["source"], "api")

    @patch("elevenlabs_tts.fetch_voices_from_api")
    def test_catalog_invalid_key_shows_error_meta(self, mock_fetch):
        config.ELEVENLABS_API_KEY = "bad-key"
        clear_elevenlabs_voice_cache()
        mock_fetch.return_value = ([], "Geçersiz API key")
        catalog = get_voice_catalog(force_refresh=True)
        self.assertNotIn("elevenlabs", catalog)
        self.assertEqual(catalog["elevenlabs_meta"]["error"], "Geçersiz API key")

    def test_resolve_elevenlabs_voice(self):
        config.ELEVENLABS_API_KEY = "test-key"
        clear_elevenlabs_voice_cache()
        vid = ELEVENLABS_FREE_VOICES[0]["id"]
        with patch("elevenlabs_tts.fetch_voices_from_api", return_value=(list(ELEVENLABS_FREE_VOICES), None)):
            self.assertEqual(resolve_voice("tr", voice_id=vid), vid)
            self.assertTrue(is_valid_voice(vid))

    def test_voice_gender_and_label(self):
        vid = ELEVENLABS_FREE_VOICES[0]["id"]
        self.assertIn(voice_gender_for_id(vid), ("male", "female"))
        self.assertTrue(voice_label_for_id(vid))


class TestElevenLabsApiClient(unittest.TestCase):
    def setUp(self):
        self._orig_key = getattr(config, "ELEVENLABS_API_KEY", "")

    def tearDown(self):
        config.ELEVENLABS_API_KEY = self._orig_key

    @patch("elevenlabs_tts.requests.post")
    @patch("elevenlabs_tts._mp3_to_wav")
    def test_generate_tts_wav_success(self, mock_convert, mock_post):
        from elevenlabs_tts import generate_tts_wav

        config.ELEVENLABS_API_KEY = "sk-test"
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b"fake-mp3-bytes"
        mock_resp.headers = {"character-remaining": "9500"}
        mock_post.return_value = mock_resp

        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "narration.wav")
            wav_path = os.path.join(tmp, "narration.wav")
            mock_convert.return_value = wav_path
            with open(wav_path, "wb") as f:
                f.write(b"RIFF")

            ok, msg = generate_tts_wav("Merhaba dünya", out, ELEVENLABS_FREE_VOICES[0]["id"])
            self.assertTrue(ok)
            self.assertIn("ElevenLabs", msg)
            mock_post.assert_called_once()

    @patch("elevenlabs_tts.requests.post")
    def test_generate_tts_wav_401(self, mock_post):
        from elevenlabs_tts import generate_tts_wav

        config.ELEVENLABS_API_KEY = "bad-key"
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.headers = {}
        mock_resp.text = "Unauthorized"
        mock_post.return_value = mock_resp

        ok, msg = generate_tts_wav("test", "/tmp/x.wav", ELEVENLABS_FREE_VOICES[0]["id"])
        self.assertFalse(ok)
        self.assertIn("401", msg)

    @patch("elevenlabs_tts.requests.post")
    def test_generate_tts_wav_429(self, mock_post):
        from elevenlabs_tts import generate_tts_wav

        config.ELEVENLABS_API_KEY = "sk-test"
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.headers = {"character-remaining": "0"}
        mock_resp.text = "Too Many Requests"
        mock_post.return_value = mock_resp

        ok, msg = generate_tts_wav("test", "/tmp/x.wav", ELEVENLABS_FREE_VOICES[0]["id"])
        self.assertFalse(ok)
        self.assertIn("429", msg)

    def test_not_configured_without_key(self):
        from elevenlabs_tts import generate_tts_wav, is_configured

        config.ELEVENLABS_API_KEY = ""
        self.assertFalse(is_configured())
        ok, msg = generate_tts_wav("test", "/tmp/x.wav", ELEVENLABS_FREE_VOICES[0]["id"])
        self.assertFalse(ok)
        self.assertIn("not configured", msg.lower())


class TestElevenLabsEngineRouting(unittest.TestCase):
    def test_active_provider_label(self):
        from tts_engine import active_tts_provider

        orig = config.TTS_VOICE
        orig_key = config.ELEVENLABS_API_KEY
        try:
            config.TTS_VOICE = ELEVENLABS_FREE_VOICES[0]["id"]
            config.ELEVENLABS_API_KEY = "sk-test"
            label = active_tts_provider()
            self.assertIn("ElevenLabs", label)
        finally:
            config.TTS_VOICE = orig
            config.ELEVENLABS_API_KEY = orig_key


if __name__ == "__main__":
    unittest.main()
