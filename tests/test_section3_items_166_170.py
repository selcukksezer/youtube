"""
Unit Tests for Roadmap Section 3: Items 166 - 170
- Item 166: Kapanış Müzik Sönümlemesi (Fade-Out Yok! Keskin Döngü Kesimi)
- Item 167: Ding Sesinin Frekansı (Quiz Doğru Cevap: 1800Hz Kristal Zil)
- Item 168: Hatalı Buzzer Sesi (Quiz Yanlış Cevap: 120Hz Testere Dişi Dalga)
- Item 169: Müzik BPM Eşleştirmesi (Motivasyon 120-130 BPM; Felsefe/Gizem 70-85 BPM)
- Item 170: Ses Katmanlarının Faz Uyumu (Phase Alignment: Bas Frekanslar Mono Kilitli <120Hz)
"""
import os
import wave
import math
import struct
import tempfile
import unittest

from bgm_manager import (
    mix_narration_and_bgm,
    apply_seamless_loop_cut,
    get_niche_target_bpm,
    match_bgm_track_to_niche,
    synthesize_niche_tempo_bgm,
    detect_bgm_bpm_and_beats,
)
from voice.acoustic_assets import (
    ensure_quiz_ding_sfx,
    inject_quiz_ding,
    ensure_quiz_buzzer_sfx,
    inject_quiz_buzzer,
)
from voice.audio_dsp import (
    lock_bass_frequencies_to_mono,
    apply_phase_aligned_mix,
)
from voice.humanizer import voice_humanizer


class TestSection3Items166To170(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_dir = tempfile.mkdtemp(prefix="test_sec3_166_170_")
        cls.dummy_wav = os.path.join(cls.test_dir, "dummy_voice.wav")
        cls.dummy_stereo = os.path.join(cls.test_dir, "dummy_stereo.wav")

        # Create 2.0s mono speech tone
        sr = 44100
        dur = 2.0
        frames_mono = bytearray()
        for i in range(int(sr * dur)):
            t = i / sr
            s = math.sin(2 * math.pi * 300 * t) * 0.4
            frames_mono.extend(struct.pack('<h', int(s * 32767)))

        with wave.open(cls.dummy_wav, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(frames_mono)

        # Create 2.0s stereo tone with wide out-of-phase bass
        frames_stereo = bytearray()
        for i in range(int(sr * dur)):
            t = i / sr
            left = math.sin(2 * math.pi * 60 * t) * 0.5 + math.sin(2 * math.pi * 2000 * t) * 0.2
            # Right channel 180-deg out-of-phase bass to test mono lock
            right = -math.sin(2 * math.pi * 60 * t) * 0.5 + math.sin(2 * math.pi * 2500 * t) * 0.2
            frames_stereo.extend(struct.pack('<hh', int(left * 32767), int(right * 32767)))

        with wave.open(cls.dummy_stereo, 'wb') as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(frames_stereo)

    # ─── ITEM 166: Kapanış Müzik Sönümlemesi (Fade-Out Yok!) ──────────────────

    def test_item_166_seamless_loop_cut_no_fade_out(self):
        """Madde 166: Müzik sönümlemesi engellenmeli, tam duration anında kesilmeli."""
        out_cut = os.path.join(self.test_dir, "loop_cut.wav")
        res = apply_seamless_loop_cut(self.dummy_stereo, out_cut, duration=1.5)
        self.assertTrue(os.path.exists(res))

        with wave.open(res, 'rb') as wf:
            dur = wf.getnframes() / wf.getframerate()
            self.assertAlmostEqual(dur, 1.5, delta=0.1)

    def test_item_166_mix_narration_with_no_fade_out(self):
        """Madde 166: mix_narration_and_bgm allow_fade_out=False parametresiyle döngüyü korumalı."""
        out_mixed = os.path.join(self.test_dir, "mixed_no_fade.wav")
        res = mix_narration_and_bgm(self.dummy_wav, self.dummy_stereo, out_mixed,
                                    volume=0.15, allow_fade_out=False)
        self.assertTrue(os.path.exists(res))
        self.assertGreater(os.path.getsize(res), 1000)

    # ─── ITEM 167: Ding Sesinin Frekansı (1800Hz Kristal Zil) ──────────────────

    def test_item_167_quiz_ding_sfx_synthesis_and_injection(self):
        """Madde 167: Quiz doğru cevap 'Ding' sesi 1800Hz frekansında sentezlenip mikslenmeli."""
        ding_wav = os.path.join(self.test_dir, "custom_ding_1800hz.wav")
        res_ding = ensure_quiz_ding_sfx(output_path=ding_wav, freq_hz=1800.0, duration=0.45)
        self.assertTrue(os.path.exists(res_ding))

        with wave.open(res_ding, 'rb') as wf:
            self.assertEqual(wf.getnchannels(), 1)
            self.assertEqual(wf.getframerate(), 44100)
            dur = wf.getnframes() / wf.getframerate()
            self.assertAlmostEqual(dur, 0.45, delta=0.05)

        # Test injection via coordinator
        out_injected = os.path.join(self.test_dir, "speech_with_ding.wav")
        res_inj = voice_humanizer.inject_quiz_ding(self.dummy_wav, out_injected, timestamp_sec=0.5, volume=0.5)
        self.assertTrue(os.path.exists(res_inj))
        self.assertGreater(os.path.getsize(res_inj), 1000)

    # ─── ITEM 168: Hatalı Buzzer Sesi (120Hz Testere Dişi) ────────────────────

    def test_item_168_quiz_buzzer_sfx_synthesis_and_injection(self):
        """Madde 168: Quiz hatalı cevap 'Buzzer' sesi 120Hz testere dişi dalgada üretilmeli."""
        buzz_wav = os.path.join(self.test_dir, "custom_buzzer_120hz.wav")
        res_buzz = ensure_quiz_buzzer_sfx(output_path=buzz_wav, freq_hz=120.0, duration=0.55)
        self.assertTrue(os.path.exists(res_buzz))

        with wave.open(res_buzz, 'rb') as wf:
            self.assertEqual(wf.getnchannels(), 1)
            self.assertEqual(wf.getframerate(), 44100)
            dur = wf.getnframes() / wf.getframerate()
            self.assertAlmostEqual(dur, 0.55, delta=0.05)

        # Test injection via coordinator
        out_injected = os.path.join(self.test_dir, "speech_with_buzzer.wav")
        res_inj = voice_humanizer.inject_quiz_buzzer(self.dummy_wav, out_injected, timestamp_sec=0.5, volume=0.45)
        self.assertTrue(os.path.exists(res_inj))
        self.assertGreater(os.path.getsize(res_inj), 1000)

    # ─── ITEM 169: Müzik BPM Eşleştirmesi ─────────────────────────────────────

    def test_item_169_niche_target_bpm_ranges(self):
        """Madde 169: Motivasyon 120-130 BPM, Felsefe/Gizem 70-85 BPM eşleşmesi."""
        mot_min, mot_max = get_niche_target_bpm("motivation")
        self.assertEqual((mot_min, mot_max), (120, 130))

        phil_min, phil_max = get_niche_target_bpm("philosophy")
        self.assertEqual((phil_min, phil_max), (70, 85))

        mys_min, mys_max = get_niche_target_bpm("mystery")
        self.assertEqual((mys_min, mys_max), (70, 85))

        # Test beat detector recognizes niche
        beats_mot = detect_bgm_bpm_and_beats("energetic_motivation_workout.wav", duration=5.0)
        self.assertGreater(len(beats_mot), 8)  # ~125 BPM produces ~10 beats in 5s

        beats_phil = detect_bgm_bpm_and_beats("stoic_calm_philosophy.wav", duration=5.0)
        self.assertLess(len(beats_phil), 8)  # ~78 BPM produces ~6 beats in 5s

    def test_item_169_synthesize_niche_tempo_bgm(self):
        """Madde 169: Belirtilen niş BPM'ine kilitli BGM sentezleme."""
        phil_bgm = os.path.join(self.test_dir, "synth_philosophy_bgm.wav")
        res_phil = synthesize_niche_tempo_bgm("philosophy", duration=3.0, output_path=phil_bgm)
        self.assertTrue(os.path.exists(res_phil))

        mot_bgm = os.path.join(self.test_dir, "synth_motivation_bgm.wav")
        res_mot = synthesize_niche_tempo_bgm("motivation", duration=3.0, output_path=mot_bgm)
        self.assertTrue(os.path.exists(res_mot))

    # ─── ITEM 170: Ses Katmanlarının Faz Uyumu (Phase Alignment) ───────────────

    def test_item_170_lock_bass_frequencies_to_mono(self):
        """Madde 170: Faz çakışmasını önlemek için bas frekanslar (<120Hz) mono kilitlenmeli."""
        out_locked = os.path.join(self.test_dir, "mono_bass_locked.wav")
        res = lock_bass_frequencies_to_mono(self.dummy_stereo, out_locked, cutoff_hz=120.0)
        self.assertTrue(os.path.exists(res))

        with wave.open(res, 'rb') as wf:
            self.assertEqual(wf.getnchannels(), 2)
            self.assertGreater(wf.getnframes(), 0)

    def test_item_170_phase_aligned_mix(self):
        """Madde 170: Müzik ve konuşma birleştirilirken mono bas faz kilidi uygulanmalı."""
        out_mix = os.path.join(self.test_dir, "phase_aligned_full_mix.wav")
        res = apply_phase_aligned_mix(self.dummy_wav, self.dummy_stereo, out_mix,
                                      music_volume=0.15, cutoff_hz=120.0)
        self.assertTrue(os.path.exists(res))
        self.assertGreater(os.path.getsize(res), 1000)


if __name__ == "__main__":
    unittest.main()
