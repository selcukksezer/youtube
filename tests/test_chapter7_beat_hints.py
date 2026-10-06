"""
Bölüm 7.3: BPM ve Ritim İpuçları Tabanlı Kurgu (Beat Hints) Test Paketi
- 80-120 BPM kurgu aralığı normalizasyonu
- Gerçek audio / sentetik beat tespiti
- Sahne sürelerinin ritim vuruşlarına kilitlenmesi (Beat Snapping)
- Konuşma kelime sayısı koruma kalkanı (Speech ceiling shield)
- Director derleyicisi ile uçtan uca entegrasyon
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bgm_manager import (
    normalize_bpm_to_shorts_band,
    detect_audio_bpm_and_beats,
    snap_timeline_to_beat_grid,
    compute_scene_beat_hints,
    parse_bgm_bpm,
)
from director import compile_director_plan
from director.schema import ScenePlan
from director.timeline import snap_scenes_to_beat_hints


class TestChapter7BeatHints(unittest.TestCase):
    def test_bpm_normalization_to_shorts_band(self):
        """Müzikal oktav (double / half) normalizasyon testi."""
        # Düşük BPM (<80): x2 oktav 80-120 bandına oturur
        self.assertEqual(normalize_bpm_to_shorts_band(60.0), 120.0)
        self.assertEqual(normalize_bpm_to_shorts_band(50.0), 100.0)
        self.assertEqual(normalize_bpm_to_shorts_band(45.0), 90.0)

        # Yüksek BPM (>120): /2 oktav 80-120 bandına oturur
        self.assertEqual(normalize_bpm_to_shorts_band(160.0), 80.0)
        self.assertEqual(normalize_bpm_to_shorts_band(200.0), 100.0)
        self.assertEqual(normalize_bpm_to_shorts_band(180.0), 90.0)

        # Doğal komşu veya aralıktaki BPM'ler (vuruş kaçırmamak için off-beat olmayan doğal tempo)
        self.assertEqual(normalize_bpm_to_shorts_band(78.0), 78.0)
        self.assertEqual(normalize_bpm_to_shorts_band(125.0), 125.0)
        self.assertEqual(normalize_bpm_to_shorts_band(95.0), 95.0)
        self.assertEqual(normalize_bpm_to_shorts_band(110.0), 110.0)
        self.assertEqual(normalize_bpm_to_shorts_band(80.0), 80.0)
        self.assertEqual(normalize_bpm_to_shorts_band(120.0), 120.0)

        # Geçersiz/sıfır değerler
        self.assertEqual(normalize_bpm_to_shorts_band(0.0), 100.0)
        self.assertEqual(normalize_bpm_to_shorts_band(-10.0), 100.0)

    def test_detect_audio_bpm_and_beats_with_audio_file(self):
        """Mevcut audio dosyası ile veya dosyasız beat tespiti testi."""
        audio_file = "test_audio.wav" if os.path.isfile("test_audio.wav") else ""
        bpm, beats = detect_audio_bpm_and_beats(audio_file, duration=15.0, default_bpm=100.0, enforce_band=True)
        self.assertTrue(80.0 <= bpm <= 120.0, f"BPM must be in 80-120 band, got {bpm}")
        self.assertGreaterEqual(len(beats), 3)
        self.assertTrue(all(beats[i] < beats[i + 1] for i in range(len(beats) - 1)))

    def test_snap_timeline_to_beat_grid_dicts(self):
        """Dict tabanlı sahneleri 80-120 BPM ritmine kilitleme testi."""
        scenes = [
            {"index": 0, "duration": 3.2, "narration": "Kısa açılış cümlesi."},
            {"index": 1, "duration": 4.1, "narration": "Gelişme sahnesi burada anlatılıyor."},
            {"index": 2, "duration": 3.7, "narration": "Son sahne mesajı."},
        ]
        aligned = snap_timeline_to_beat_grid(scenes, bpm=100.0, enforce_band=True)
        self.assertEqual(len(aligned), 3)
        for sc in aligned:
            self.assertTrue(sc.get("beat_synced", False))
            self.assertIn("beat_hint_ms", sc)
            self.assertGreaterEqual(sc["duration"], 1.8)
            self.assertEqual(round(sc["t0"] + sc["duration"], 3), round(sc["t1"], 3))

        # Toplam süre drift olmadan korunmalı
        orig_total = sum(s["duration"] for s in scenes)
        new_total = sum(s["duration"] for s in aligned)
        self.assertAlmostEqual(orig_total, new_total, delta=0.05)

    def test_snap_timeline_to_beat_grid_scene_plans(self):
        """ScenePlan nesneleri ile beat-snapping testi."""
        plans = [
            ScenePlan(index=0, narration="Bilişsel çelişki kancası.", duration=3.0),
            ScenePlan(index=1, narration="İkinci sahne detayı.", duration=3.5),
            ScenePlan(index=2, narration="Üçüncü sahne sonucu.", duration=3.5),
        ]
        aligned = snap_scenes_to_beat_hints(plans, bpm=100.0)
        self.assertEqual(len(aligned), 3)
        for sc in aligned:
            self.assertTrue(sc.beat_synced)
            self.assertIsNotNone(sc.beat_hint_ms)
            self.assertGreaterEqual(sc.duration, 1.8)

    def test_word_count_speech_ceiling_protection(self):
        """Yoğun kelimeli sahnenin konuşma süresinin altına düşürülmemesi testi."""
        long_narration = "Bu sahnede çok fazla kelime var ve spikerin bu kelimeleri eksiksiz okuyabilmesi için zamana ihtiyacı var."
        scenes = [
            {"index": 0, "duration": 5.0, "narration": long_narration},
            {"index": 1, "duration": 3.0, "narration": "Kısa cümle."},
        ]
        aligned = snap_timeline_to_beat_grid(scenes, bpm=120.0, min_scene_dur=1.8)
        # 16 kelime * 0.30s + 0.15s ≈ 4.95s -> sahne süresi ezilmemeli
        self.assertGreaterEqual(aligned[0]["duration"], 4.5)

    def test_compile_director_plan_beat_snap_integration(self):
        """DirectorPlan derlemesinde sahnelerin ritme oturması ve 80-120 BPM bandı testi."""
        raw = {
            "title": "BPM Beat Snap Test",
            "scenes": [
                {"narration": "Bunu öğrenene kadar hayatınızı yanlış yaşıyordunuz.", "duration": 3.5},
                {"narration": "İşte beyninizin size oynadığı en büyük oyun.", "duration": 4.0},
                {"narration": "Ve tam da bu yüzden asla başa dönmeyin çünkü.", "duration": 3.5},
            ],
        }
        plan = compile_director_plan(raw, niche_id="2_philosophy_stoic")
        self.assertTrue(all(sc.beat_hint_ms is not None for sc in plan.scenes))
        self.assertTrue(all(getattr(sc, "beat_synced", False) for sc in plan.scenes))
        beat_bpm = plan.meta.get("beat_bpm")
        self.assertIsNotNone(beat_bpm)
        self.assertTrue(80.0 <= beat_bpm <= 120.0, f"Expected 80-120 BPM, got {beat_bpm}")


if __name__ == "__main__":
    unittest.main()
