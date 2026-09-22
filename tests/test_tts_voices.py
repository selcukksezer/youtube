"""Tests for Edge TTS voice catalog."""
import unittest

import config
from tts_voices import (
    EDGE_TTS_VOICE_CATALOG,
    get_voice_catalog,
    is_valid_voice,
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

    def test_voice_gender_for_id(self):
        self.assertEqual(voice_gender_for_id("en-US-JennyNeural", "en"), "female")

    def test_config_imports_catalog(self):
        self.assertIn("tr", EDGE_TTS_VOICE_CATALOG)
        self.assertTrue(config.TTS_VOICE.endswith("Neural") or config.TTS_VOICE.startswith("elevenlabs:"))


if __name__ == "__main__":
    unittest.main()
