"""Batch 2: overlay + audio stub wiring tests (Items 99, 105, 115, 143, 182-188, 201, 235-236)."""
import os
import tempfile
import unittest
import wave

from moviepy.editor import ColorClip
from effects.motion import apply_opening_pattern_interrupt, apply_handheld_camera_shake
from effects.filters import apply_color_splash_moviepy
from effects.overlays import apply_share_cta_overlay, apply_bookmark_cta_overlay, apply_affiliate_3d_mockup
from viral_retention_engine import ViralRetentionEngine
from voice.gender import select_quote_voice
from tts_engine import _is_quote_segment, split_narration_into_voice_segments
from sfx_manager import _panned_whoosh_path, ensure_sfx_files
from hybrid_niches import enrich_plan_with_hybrid
from scenes.enrichment import enrich_continuous_motion_hints


class TestBatch2OverlayAudioWiring(unittest.TestCase):
    def test_item_99_handheld_all_scenes_hint(self):
        scenes = [{"duration": 2.0}, {"duration": 1.5, "is_visual_cutaway": True}]
        out = enrich_continuous_motion_hints(scenes)
        self.assertTrue(out[0].get("handheld_shake"))
        self.assertFalse(out[1].get("handheld_shake"))

    def test_item_201_opening_pattern_interrupt(self):
        clip = ColorClip(size=(720, 1280), color=(40, 40, 80), duration=2.0)
        out = apply_opening_pattern_interrupt(clip, interrupt_type="zoom_punch", duration=1.5)
        self.assertEqual(out.duration, 2.0)

    def test_item_115_color_splash_moviepy(self):
        clip = ColorClip(size=(320, 568), color=(0, 180, 60), duration=1.0)
        out = apply_color_splash_moviepy(clip, keep_hue_center=120.0, tolerance=35.0)
        self.assertEqual(out.size, (320, 568))

    def test_item_105_affiliate_mockup(self):
        mockup = apply_affiliate_3d_mockup(None, target_w=540, target_h=960)
        self.assertIsNotNone(mockup)

    def test_items_235_236_cta_overlays(self):
        clip = ColorClip(size=(720, 1280), color=(10, 10, 20), duration=6.0)
        share = ViralRetentionEngine.generate_share_cta("Stres", lang="tr")
        bookmark = ViralRetentionEngine.generate_bookmark_cta("Stoacılık", lang="tr")
        out = apply_share_cta_overlay(clip, cta_text=share, start_at=2.0, duration=2.5)
        out = apply_bookmark_cta_overlay(out, cta_text=bookmark, start_at=4.0, duration=2.0)
        self.assertEqual(out.duration, 6.0)

    def test_item_143_dual_voice_selection(self):
        q_tr = select_quote_voice("tr-TR-AhmetNeural", "tr")
        self.assertEqual(q_tr, "tr-TR-EmelNeural")
        self.assertTrue(_is_quote_segment('"Marcus Aurelius dedi ki: güç zihindedir."'))
        self.assertFalse(_is_quote_segment("Normal anlatım cümlesi."))

    def test_item_143_standalone_quoted_speech(self):
        """Plain quoted line → single female-voice clause after split."""
        parts = split_narration_into_voice_segments('"Güç zihindedir."')
        self.assertEqual(len(parts), 1)
        self.assertTrue(parts[0]["is_quote"])
        self.assertIn("Güç zihindedir", parts[0]["text"])

    def test_item_143_guillemet_quote(self):
        parts = split_narration_into_voice_segments("«Güç zihindedir.»")
        self.assertEqual(len(parts), 1)
        self.assertTrue(parts[0]["is_quote"])

    def test_item_143_attribution_split_dedi_ki(self):
        """Marcus dedi ki: intro narrator, quoted clause female."""
        parts = split_narration_into_voice_segments("Marcus Aurelius dedi ki: güç zihindedir.")
        self.assertEqual(len(parts), 2)
        self.assertFalse(parts[0]["is_quote"])
        self.assertIn("dedi ki", parts[0]["text"])
        self.assertTrue(parts[1]["is_quote"])
        self.assertIn("güç zihindedir", parts[1]["text"])

    def test_item_143_attribution_split_dedik_ki_wrapped(self):
        parts = split_narration_into_voice_segments('"Marcus Aurelius dedi ki: güç zihindedir."')
        self.assertEqual(len(parts), 2)
        self.assertFalse(parts[0]["is_quote"])
        self.assertTrue(parts[1]["is_quote"])

    def test_item_143_attribution_split_demisti(self):
        parts = split_narration_into_voice_segments('Marcus demişti: "Güç zihindedir."')
        self.assertEqual(len(parts), 2)
        self.assertFalse(parts[0]["is_quote"])
        self.assertIn("demişti", parts[0]["text"])
        self.assertTrue(parts[1]["is_quote"])
        self.assertIn("Güç zihindedir", parts[1]["text"])

    def test_item_143_normal_narration_unsplit(self):
        parts = split_narration_into_voice_segments("Normal anlatım cümlesi.")
        self.assertEqual(len(parts), 1)
        self.assertFalse(parts[0]["is_quote"])

    def test_item_187_panned_whoosh(self):
        whoosh, _, _ = ensure_sfx_files()
        panned = _panned_whoosh_path(whoosh)
        self.assertTrue(os.path.exists(panned))

    def test_items_182_188_acoustic_inject_fns(self):
        from voice.acoustic_assets import (
            inject_dramatic_piano_layer,
            inject_cyberpunk_synth_bass,
            inject_room_ambience,
        )

        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "voice.wav")
            with wave.open(src, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(48000)
                wf.writeframes(b"\x00\x00" * 48000 * 3)
            piano = os.path.join(tmp, "piano.wav")
            synth = os.path.join(tmp, "synth.wav")
            crowd = os.path.join(tmp, "crowd.wav")
            self.assertTrue(inject_dramatic_piano_layer(src, piano).endswith("piano.wav"))
            self.assertTrue(inject_cyberpunk_synth_bass(src, synth).endswith("synth.wav"))
            self.assertTrue(inject_room_ambience(src, crowd).endswith("crowd.wav"))

    def test_hybrid_plan_enrichment_wire(self):
        plan = {
            "title": "Morgan Housel para psikolojisi finans alıntı davranış risk",
            "scenes": [{"search_queries": ["finance chart"], "duration": 3.0}],
        }
        out = enrich_plan_with_hybrid(plan, plan["title"], "16_wealth_entrepreneurship")
        self.assertEqual(out.get("hybrid_niche"), "money_psychology_quotes")


if __name__ == "__main__":
    unittest.main()
