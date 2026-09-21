"""Batch 1: retention hook + audio pipeline wiring tests."""
import os
import tempfile
import unittest
import wave

from scenes.retention_hooks import apply_retention_hooks_to_plan, ensure_retention_hooks_on_plan
from viral_retention_engine import ViralRetentionEngine
from viral_seo_agent import enrich_seo_with_retention_metadata
from sfx_manager import build_reaction_sfx_events, build_emphasis_kick_events, ensure_reaction_sfx_files
from voice.script_humanizer import extract_reaction_cues


class TestBatch1RetentionAudioWiring(unittest.TestCase):
    def test_retention_hooks_first_and_last_scene(self):
        plan = {
            "scenes": [
                {"narration": "Eski giriş cümlesi. Devam metni.", "duration": 3.0},
                {"narration": "Orta sahne.", "duration": 3.0},
                {"narration": "Teşekkürler izlediğiniz için hoşça kalın.", "duration": 3.0},
            ]
        }
        out = apply_retention_hooks_to_plan(plan, "Zihin Gücü", lang="tr", niche_type="6_stoic_philosophy")
        first = out["scenes"][0]["narration"]
        last = out["scenes"][-1]["narration"]
        self.assertNotIn("Teşekkürler izlediğiniz", last)
        self.assertIn("retention_metadata", out)
        self.assertIn("ending_bridge", out["retention_metadata"])
        self.assertTrue(len(first) > 10)

    def test_ensure_retention_hooks_idempotent_and_rebuilds_narration(self):
        plan = {
            "scenes": [
                {"narration": "Plain opener. Body text here.", "duration": 3.0},
                {"narration": "Middle.", "duration": 3.0},
                {"narration": "Thanks for watching, goodbye.", "duration": 3.0},
            ]
        }
        out = ensure_retention_hooks_on_plan(
            plan, "Mind Power", lang="en", niche_type="6_stoic_philosophy", variation_attempt=0
        )
        first_after = out["scenes"][0]["narration"]
        self.assertNotEqual(first_after, "Plain opener. Body text here.")
        self.assertIn("Mind Power", out["full_narration"])
        self.assertIn("retention_metadata", out)
        again = ensure_retention_hooks_on_plan(out, "Mind Power", lang="en", niche_type="6_stoic_philosophy")
        self.assertEqual(again["scenes"][0]["narration"], first_after)

    def test_seo_enrichment_polarizing_and_mistake(self):
        meta = {
            "spotted_mistake_bait": "3. maddede bilerek hata yaptım, fark eden?",
            "polarizing_dilemma": ViralRetentionEngine.generate_polarizing_dilemma("AI", lang="tr"),
            "share_cta": "Arkadaşına gönder",
        }
        seo = enrich_seo_with_retention_metadata({"pinned_comment": "Yorum?", "seo_description": "Açıklama."}, meta)
        self.assertIn("hata", seo["pinned_comment"].lower())
        self.assertIn("Tartışma", seo["seo_description"])
        self.assertEqual(seo["share_cta"], "Arkadaşına gönder")

    def test_reaction_and_kick_sfx_events(self):
        scenes = [{"narration": "Şok edici (gül) bir gerçek asla unutma.", "duration": 4.0}]
        cues = extract_reaction_cues(scenes[0]["narration"])
        self.assertIn("chuckle", cues)
        rx = build_reaction_sfx_events(scenes)
        self.assertTrue(any(e["sound"] == "chuckle" for e in rx))
        kicks = build_emphasis_kick_events(scenes)
        self.assertTrue(any(e["sound"] == "sub_kick" for e in kicks))

    def test_reaction_sfx_files_generated(self):
        chuckle, sigh = ensure_reaction_sfx_files()
        self.assertTrue(os.path.exists(chuckle))
        self.assertTrue(os.path.exists(sigh))

    def test_tts_segment_pitch_helpers(self):
        from tts_engine import _segment_pitch, _segment_has_emphasis

        self.assertEqual(_segment_pitch({"style": "hook", "text": "Merhaba"}), "+8Hz")
        self.assertEqual(_segment_pitch({"style": "question", "text": "Neden?"}), "+5Hz")
        self.assertTrue(_segment_has_emphasis("Bu ASLA unutulmamalı"))

    def test_multi_breath_injection(self):
        from voice.audio_dsp import inject_natural_breaths

        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "voice.wav")
            out = os.path.join(tmp, "breath.wav")
            sample_rate = 48000
            frames = b"\x00\x00" * sample_rate * 12
            with wave.open(src, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(frames)
            result = inject_natural_breaths(src, out, interval_seconds=5.0)
            self.assertEqual(result, out)
            self.assertTrue(os.path.exists(out))


if __name__ == "__main__":
    unittest.main()
