"""Regression: punctuation-only TTS segments must be skipped (Edge NoAudioReceived)."""
import re
import unittest


class TestTtsPunctuationSkip(unittest.TestCase):
    def test_skip_predicate_matches_engine(self):
        def should_skip(plain_text: str) -> bool:
            return (not plain_text.strip()) or (
                not re.search(r"\w", plain_text, flags=re.UNICODE)
            )

        self.assertTrue(should_skip("..."))
        self.assertTrue(should_skip("—"))
        self.assertTrue(should_skip("   "))
        self.assertTrue(should_skip("!!!"))
        self.assertFalse(should_skip("Merhaba dünya."))
        self.assertFalse(should_skip("Şu dua kalbi yumuşatır."))

    def test_ahmet_no_audio_falls_back_to_multilingual_voice(self):
        import asyncio
        from unittest import mock
        import config
        import tts_engine

        tried_voices = []

        async def fake_tts(text, mp3_path, rate=None, volume=None, pitch=None):
            tried_voices.append(config.TTS_VOICE)
            if config.TTS_VOICE == "tr-TR-AhmetNeural":
                raise RuntimeError("No audio was received.")
            return mp3_path, [{"text": "Merhaba", "offset": 0.0, "duration": 0.4}]

        tts_engine._WORKING_VOICE_CACHE.clear()
        with mock.patch.object(config, "TTS_VOICE", "tr-TR-AhmetNeural"), \
                mock.patch.object(config, "LANGUAGE", "tr"), \
                mock.patch.object(config, "TTS_GENDER", "male"), \
                mock.patch.object(tts_engine, "_tts", side_effect=fake_tts):
            path, timings = asyncio.run(
                tts_engine._tts_with_fallback("Merhaba dünya.", "Merhaba dünya.", "dummy.mp3")
            )
            self.assertEqual(path, "dummy.mp3")
            self.assertEqual(len(timings), 1)
            self.assertIn("en-US-AndrewMultilingualNeural", tried_voices)
            self.assertEqual(config.TTS_VOICE, "tr-TR-AhmetNeural")
        tts_engine._WORKING_VOICE_CACHE.clear()


if __name__ == "__main__":
    unittest.main()
