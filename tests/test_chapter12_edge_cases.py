"""
Test Suite for Bölüm 12: Üretim Uç Durum (Edge Case) ve Arıza Kurtarma Kataloğu (50 Madde).
Verifies failure isolation, graceful degradation, and self-healing mechanisms across the pipeline.
"""
import os
import unittest
import tempfile
from unittest.mock import MagicMock, patch

from system_resilience import (
    CircuitBreaker,
    clean_ai_system_preamble,
    guard_subtitle_audio_drift,
    is_material_resolution_acceptable,
    sanitize_filename_and_title,
    smart_split_narration_for_shorts,
    verify_render_output_sanity,
    verify_stock_video_integrity,
)
from scenes.generator import _tts_word_cap
from scenes.fallback import (
    _generate_dark_psychology_scenes,
    _generate_religious_quotes_scenes,
    _generate_news_flash_scenes,
    _generate_reddit_confession_scenes,
)
from render.ffmpeg_graph import align_even_dimension


class TestChapter12EdgeCases(unittest.TestCase):

    # ─── GRUP A: Ağ, Kota ve API Kesintileri ───
    def test_edge_01_circuit_breaker_fast_failover(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=60.0)
        for _ in range(3):
            cb.record_failure("gemini_flash", "429 Quota Exceeded")
        self.assertFalse(cb.can_execute("gemini_flash"))
        # Check that fallback endpoint is suggested
        eps = cb.get_public_fallback_endpoint("gemini")
        self.assertIsNotNone(eps)

    def test_edge_08_corrupted_stock_zero_byte(self):
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"")
            path = f.name
        try:
            report = verify_stock_video_integrity(path, min_duration=2.0)
            self.assertFalse(report["valid"])
            self.assertIn("0 bayt", report["reason"].lower())
        finally:
            if os.path.exists(path):
                os.remove(path)

    # ─── GRUP B: Ses, TTS ve Akustik Miksaj Uç Durumları ───
    def test_edge_11_tts_word_cap_enforces_60s_safety(self):
        cap = _tts_word_cap()
        self.assertLessEqual(cap, 155)
        self.assertGreaterEqual(cap, 100)

    def test_edge_12_fallback_scenes_bounded_duration_and_scenes(self):
        generator_map = {
            "dark_psychology": _generate_dark_psychology_scenes("Test topic", True),
            "religious_quotes": _generate_religious_quotes_scenes("Test topic", True),
            "news_flash": _generate_news_flash_scenes("Test topic", True),
            "reddit_confessions": _generate_reddit_confession_scenes("Test topic", "Story details", True),
        }
        for niche, plan_obj in generator_map.items():
            scenes = plan_obj.get("scenes", []) if isinstance(plan_obj, dict) else plan_obj
            self.assertLessEqual(len(scenes), 10, f"{niche} sahne sayısı 10'dan fazla olamaz!")
            total_words = sum(len(s.get("narration", "").split()) for s in scenes)
            self.assertLessEqual(total_words, 145, f"{niche} kelime bütçesi 145'i aşamaz!")

    def test_edge_13_subtitle_audio_drift_guard(self):
        timings = [
            {"word": "Merhaba", "start": 0.0, "end": 1.0},
            {"word": "dünya", "start": 1.0, "end": 45.0},
        ]
        adjusted = guard_subtitle_audio_drift(timings, audio_duration=42.0)
        self.assertLessEqual(adjusted[-1]["end"], 42.0)

    # ─── GRUP C: Görüntü ve FFmpeg Grafiği Uç Durumları ───
    def test_edge_21_odd_dimension_align_even(self):
        w = align_even_dimension(1079)
        h = align_even_dimension(1921)
        self.assertEqual(w % 2, 0)
        self.assertEqual(h % 2, 0)
        self.assertEqual(w, 1078)
        self.assertEqual(h, 1920)

    def test_edge_22_low_resolution_telegram_whatsapp_input(self):
        # 478x850 gibi WhatsApp çözünürlüğü kabul edilmeli (P9 kuralı)
        ok = is_material_resolution_acceptable(478, 850)
        self.assertTrue(ok)
        bad = is_material_resolution_acceptable(360, 640)
        self.assertFalse(bad)

    # ─── GRUP D: Senaryo ve Kalite Kapısı Uç Durumları ───
    def test_edge_31_clean_ai_preamble(self):
        dirty = "İşte harika bir video senaryosu:\n\nBunu bilmeden asla uyumayın!"
        cleaned = clean_ai_system_preamble(dirty)
        self.assertNotIn("İşte harika", cleaned)
        self.assertIn("Bunu bilmeden asla uyumayın!", cleaned)

    def test_edge_32_smart_split_narration_sentence_boundary(self):
        long_text = "Birinci önemli cümle burada yer alıyor. İkinci cümle derin düşünceler içeriyor. " * 15
        split_text, was_split = smart_split_narration_for_shorts(long_text, max_words=30)
        self.assertTrue(was_split)
        self.assertLessEqual(len(split_text.split()), 35)

    # ─── GRUP E: Dağıtım, Disk ve Çıktı Doğrulama Uç Durumları ───
    def test_edge_41_sanitize_filename_and_title(self):
        dirty_title = 'Gıybet / Dedikodu: "Gerçek Niyet"? <100% Şok> & test*'
        clean = sanitize_filename_and_title(dirty_title)
        self.assertNotIn("/", clean)
        self.assertNotIn('"', clean)
        self.assertNotIn("?", clean)
        self.assertNotIn("<", clean)
        self.assertNotIn(">", clean)
        self.assertNotIn("*", clean)

    def test_edge_42_render_sanity_checks(self):
        report = verify_render_output_sanity("non_existent_output.mp4")
        self.assertFalse(report["valid"])
        self.assertIn("bulunamadı", report.get("error", "").lower())


if __name__ == "__main__":
    unittest.main()
