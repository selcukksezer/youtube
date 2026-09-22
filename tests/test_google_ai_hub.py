"""Smoke tests for Google AI Pro hub + royalty-free audio."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google_ai_hub import (
    GOOGLE_AI_CATALOG,
    PLAN_INFO,
    get_plan_and_quota_snapshot,
    resolve_gemini_tts_voice,
)
from royalty_free_audio import search_mixkit, list_voicelab_library
from tts_engine import active_tts_provider, _estimate_word_timings
import config


class TestGoogleAiHub(unittest.TestCase):
    def test_catalog_has_image_and_video(self):
        families = {c["family"] for c in GOOGLE_AI_CATALOG}
        self.assertIn("text", families)
        self.assertIn("image", families)
        self.assertIn("video", families)
        self.assertTrue(any("flash-image" in c["id"] or "image" in c["id"] for c in GOOGLE_AI_CATALOG))
        self.assertTrue(any(c["id"].startswith("veo") for c in GOOGLE_AI_CATALOG))

    def test_plan_info(self):
        self.assertIn("google_ai_pro", PLAN_INFO)
        plan = PLAN_INFO["google_ai_pro"]
        self.assertIn("subscription_vs_api", plan)
        self.assertIn("Plus", plan["blurb"])
        self.assertIn("aktarılmaz", plan["blurb"])
        snap = get_plan_and_quota_snapshot()
        self.assertIn("quota", snap)
        self.assertIn("catalog", snap)
        self.assertIn("benefits_checklist", snap)

    def test_mixkit_catalog(self):
        tracks = search_mixkit("ambient")
        self.assertGreaterEqual(len(tracks), 1)
        self.assertIn("url", tracks[0])

    def test_voicelab_library_shape(self):
        lib = list_voicelab_library()
        self.assertIn("voicelab_dir", lib)
        self.assertIn("mixkit_catalog", lib)

    def test_gemini_voice_map(self):
        self.assertEqual(resolve_gemini_tts_voice("tr", "male"), "Charon")
        self.assertEqual(resolve_gemini_tts_voice("en", "female"), "Aoede")

    def test_active_tts_provider_default_edge(self):
        prev = config.USE_GEMINI_TTS
        prev_v = config.TTS_VOICE
        config.USE_GEMINI_TTS = False
        config.TTS_VOICE = "tr-TR-AhmetNeural"
        try:
            self.assertIn("Edge TTS", active_tts_provider())
        finally:
            config.USE_GEMINI_TTS = prev
            config.TTS_VOICE = prev_v

    def test_estimate_word_timings(self):
        timings = _estimate_word_timings("bir iki uc", 3.0)
        self.assertEqual(len(timings), 3)
        self.assertAlmostEqual(timings[-1]["offset"] + timings[-1]["duration"], 3.0, places=3)


if __name__ == "__main__":
    unittest.main()
