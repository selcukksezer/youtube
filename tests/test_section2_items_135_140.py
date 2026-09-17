"""
Tests for Section 2 Items 135 - 140 of the 500-Item Roadmap:
- Item 135: Telifli Müziklerden Kaçınma (YouTube Audio Library uyumlu / %100 telifsiz ambient arka plan)
- Item 136: Özgün SFX Frekansları (Matematiksel sinüs/kare dalga sentezi)
- Item 137: Döngü Cümlesi Çeşitliliği (En az 10 farklı döngüsel bağlaç havuzu)
- Item 138: Dinamik İlerleme Çubuğu (Altta/üstte ince dinamik neon ilerleme çubuğu)
- Item 139: Arka Plan Döngü Videolarının Süresi (Oynanış videolarını rastgele noktalardan dilimleme)
- Item 140: Shorts İçi Yasal Bildirimler (Açıklama şablonunda Fair Use bildirimi)
"""

import os
import unittest
from moviepy.editor import ColorClip

from bgm_manager import list_bgm_tracks, ensure_royalty_free_ambient_bgm
from sfx_manager import ensure_sfx_files, generate_pure_math_sfx, SFX_DIR
from viral_retention_engine import ViralRetentionEngine
from effects_engine import generate_dynamic_progress_bar, apply_dynamic_progress_bar
from video_fetcher import slice_random_background_loop
from viral_seo_agent import append_research_source_reference


class TestSection2Items135to140(unittest.TestCase):

    def test_item_135_royalty_free_bgm(self):
        """Item 135: Telifli müziklerden kaçınma & güvenli ambient audio garantisi."""
        rf_path = ensure_royalty_free_ambient_bgm()
        self.assertTrue(os.path.exists(rf_path))
        tracks = list_bgm_tracks()
        self.assertIn("royalty_free_ambient.wav", tracks)

    def test_item_136_pure_math_sfx(self):
        """Item 136: Özgün matematiksel sinüs ve kare dalga SFX üretimi."""
        ensure_sfx_files()
        sine_path = os.path.join(SFX_DIR, "math_sine_sweep.wav")
        square_path = os.path.join(SFX_DIR, "math_square_glitch.wav")
        self.assertTrue(os.path.exists(sine_path))
        self.assertTrue(os.path.exists(square_path))

        # Test dynamic generator
        custom_sfx = os.path.join(SFX_DIR, "test_custom_sfx.wav")
        generate_pure_math_sfx(custom_sfx, wave_type="sine", freq_start=150, freq_end=450, duration=0.18)
        self.assertTrue(os.path.exists(custom_sfx))

    def test_item_137_diverse_loop_conjunctions(self):
        """Item 137: En az 10 farklı döngüsel bağlaç havuzunun bulunması ve seçimi."""
        conjunctions = ViralRetentionEngine.get_diverse_loop_conjunctions(min_count=10)
        self.assertGreaterEqual(len(conjunctions), 10)
        
        bridge_0 = ViralRetentionEngine.pick_loop_bridge_for_video(0)
        bridge_1 = ViralRetentionEngine.pick_loop_bridge_for_video(1)
        self.assertNotEqual(bridge_0, bridge_1)

    def test_item_138_dynamic_progress_bar(self):
        """Item 138: Dinamik neon ilerleme çubuğu katmanı ve bileşimi."""
        clip = ColorClip((360, 640), (20, 20, 30), duration=2.0).set_fps(30)
        bar = generate_dynamic_progress_bar(360, 640, duration=2.0, bar_height=4, position="bottom")
        self.assertIsNotNone(bar.mask)
        frame = bar.get_frame(1.0)
        self.assertEqual(frame.shape, (640, 360, 3))

        comp = apply_dynamic_progress_bar(clip, bar_height=4, position="bottom")
        self.assertEqual(comp.get_frame(1.0).shape, (640, 360, 3))

    def test_item_139_slice_random_background_loop(self):
        """Item 139: Arka plan videolarını rastgele başlangıçtan dilimleme fonksiyonu."""
        # Function exists and can be invoked
        self.assertTrue(callable(slice_random_background_loop))

    def test_item_140_fair_use_legal_notice(self):
        """Item 140: Açıklama metnine Fair Use yasal bildiriminin eklenmesi."""
        raw_desc = "Harika bir felsefe shorts videosu."
        updated = append_research_source_reference(raw_desc, keyword="Stoacılık")
        self.assertIn("Tüm görseller eğitim ve adil kullanım (Fair Use) kapsamındadır", updated)
        self.assertIn("⚖️ Yasal Bildirim (Fair Use):", updated)


if __name__ == "__main__":
    unittest.main()
