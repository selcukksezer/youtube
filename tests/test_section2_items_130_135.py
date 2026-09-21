"""
Tests for Section 2 Items 130 - 135 of the 500-Item Roadmap:
- Item 130: İki Farklı Stok Sağlayıcıyı Karıştırma (Multi-stock provider mixing)
- Item 131: Ekrana Sahte Arayüz (UI) Elemanları Ekleme (iOS notification / tweet / search bar)
- Item 132: Görsel Hareketi Yön Değişimi (Alternating pan/tilt directions per scene)
- Item 133: Tekrarlanan İçerik İtiraz Şablonu & Çaba Kanıtı Arşivi (Proof dossier auto-archival)
- Item 134: Yapay Zeka Metnini İnsanlaştırma (Cliche filters: "Sonuç olarak", "Özetle", etc.)
- Item 135: Telifli Müziklerden Kaçınma (Royalty-free fallback synthesis & Audio Library compliance)
"""

import os
import unittest
import numpy as np
from moviepy.editor import ColorClip

from video_fetcher import fetch_multi_source_clips, _pick_next_source, get_session_source_distribution
from effects_engine import (
    generate_ui_element_overlay,
    apply_ui_element_overlay,
    apply_alternating_motion,
    apply_heartbeat_zoom,
    apply_particle_overlay,
    generate_end_card_overlay
)
from proof_archiver import proof_archiver, PROOFS_DIR
from voice_humanizer import VoiceHumanizer
from bgm_manager import list_bgm_tracks, ensure_royalty_free_ambient_bgm


class TestSection2Items130to135(unittest.TestCase):

    def test_item_130_multi_provider_stock_mixing(self):
        """Item 130: Tests that video fetcher supports multi-provider mixed sourcing."""
        from video_fetcher import reset_session_source_counts
        reset_session_source_counts()  # module-level session state may be dirty from other tests
        src0 = _pick_next_source(0)
        src1 = _pick_next_source(1)
        src2 = _pick_next_source(2)
        sources = {src0, src1, src2}
        self.assertTrue(len(sources) >= 2)

    def test_item_131_fake_ui_element_overlays(self):
        """Item 131: Tests generation of UI element overlays (iOS notification, tweet card, search bar)."""
        clip = ColorClip((360, 640), (20, 20, 30), duration=2.0).set_fps(30)
        
        # Test iOS notification
        ios_overlay = generate_ui_element_overlay(360, 640, duration=1.5, ui_type="ios_notification")
        self.assertIsNotNone(ios_overlay.mask)
        frame = ios_overlay.get_frame(0.5)
        self.assertEqual(frame.shape, (640, 360, 3))
        
        # Test applied composite
        comp = apply_ui_element_overlay(clip, ui_type="tweet_card", header_text="Trend", body_text="Test tweet")
        self.assertEqual(comp.get_frame(0.5).shape, (640, 360, 3))

    def test_item_132_alternating_motion(self):
        """Item 132: Tests alternating pan/tilt motion across scenes."""
        clip = ColorClip((360, 640), (40, 40, 50), duration=2.0).set_fps(30)
        
        panned_scene_0 = apply_alternating_motion(clip, scene_index=0)
        panned_scene_1 = apply_alternating_motion(clip, scene_index=1)
        panned_scene_2 = apply_alternating_motion(clip, scene_index=2)
        
        self.assertEqual(panned_scene_0.get_frame(1.0).shape, (640, 360, 3))
        self.assertEqual(panned_scene_1.get_frame(1.0).shape, (640, 360, 3))
        self.assertEqual(panned_scene_2.get_frame(1.0).shape, (640, 360, 3))

    def test_item_133_proof_archiver_and_appeal_template(self):
        """Item 133: Tests automated creative effort proof archiving and appeal script generation."""
        proof_path = proof_archiver.archive_video_proof(
            video_filename="test_proof_video.mp4",
            title="Kanıt Dosyası Başlığı",
            niche="stoic",
            script_text="Tam metin araştırma ve senaryo",
            scenes=[{"scene_number": 1, "duration": 5}],
            render_params={"fps": 30.0, "resolution": "1080x1920"}
        )
        self.assertTrue(os.path.exists(proof_path))
        
        appeal = proof_archiver.generate_appeal_video_script("TestChannel", "Kanıt Dosyası Başlığı")
        self.assertIn("YouTube Partner Program Review Team", appeal)
        self.assertIn("TestChannel", appeal)

    def test_item_134_humanize_ai_cliches(self):
        """Item 134: Tests sanitizing repetitive AI cliches from GPT/Gemini output."""
        raw_text = "Sonuç olarak, bu göz kamaştırıcı tapınak özetle adeta bir sanat eseri! 🏛️"
        sanitized = VoiceHumanizer.clean_narration_for_speech(raw_text)
        
        self.assertNotIn("Sonuç olarak", sanitized)
        self.assertNotIn("özetle", sanitized)
        self.assertNotIn("göz kamaştırıcı", sanitized)
        self.assertIn("etkileyici", sanitized)

    def test_item_135_royalty_free_bgm_library(self):
        """Item 135: Tests royalty-free safe BGM availability and generation."""
        rf_bgm = ensure_royalty_free_ambient_bgm()
        self.assertTrue(os.path.exists(rf_bgm))
        
        tracks = list_bgm_tracks()
        self.assertTrue(len(tracks) > 0)
        self.assertIn("royalty_free_ambient.wav", tracks)

    def test_moviepy_compositor_stability(self):
        """Verifies all visual effects produce 3-channel RGB frames without RGBA shape errors."""
        base = ColorClip((360, 640), (25, 25, 35), duration=1.5).set_fps(30)
        hb = apply_heartbeat_zoom(base, bpm=60)
        self.assertEqual(hb.get_frame(0.5).shape, (640, 360, 3))
        
        part = apply_particle_overlay(base, particle_type="spark", particle_count=15)
        self.assertEqual(part.get_frame(0.5).shape, (640, 360, 3))
        
        ec = generate_end_card_overlay(360, 640, duration=1.5)
        self.assertEqual(ec.get_frame(0.5).shape, (640, 360, 3))


if __name__ == "__main__":
    unittest.main()
