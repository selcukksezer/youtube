"""
Unit tests for Section 3: Items 186 - 200
Seslendirme, İleri Akustik DSP, Frekans Mühendisliği ve Prosedürel SFX Paketi:
- Item 186: Gereksiz "Merhaba Arkadaşlar" Girişlerini Yasaklama (Script Sanitizer)
- Item 187: Stereo Pan Hareketi (Dynamic Stereo Pan Motion)
- Item 188: Gürültülü Ortam Kurgusu (Crowd Room Ambience)
- Item 189: Altyazı Senkronizasyonunda Whisper İnce Ayarı
- Item 190: Müzik Telif Kontrolü (Audio Fingerprint Check)
- Item 191: Akustik Yankı Odası (Acoustic Reverb Chamber)
- Item 192: Vurgulu Kelimede Alttan Davul Vuruşu (Sub-Kick Hit @ Key Word)
- Item 193: Ses Tonu Tutarlılığı (Voice Level Consistency / RMS Leveller)
- Item 194: Sentetik Ses Artefaktlarını Filtreleme (Low-Pass @ 14kHz)
- Item 195: Derin Anlatıcı Sesi (Epic Movie Trailer Voice)
- Item 196: Hızlı Tempolu Haber Dili (Fast-Paced News Cadence)
- Item 197: Soru-Cevap Arası Sessizlik (Quiz Thinking Gap @ 3.0s)
- Item 198: Kapanış Cümlesinin Ses Tonu (Loop Continuity Inflection)
- Item 199: Özel Ses Efekti Arşivi (10 Core Procedural SFX Archive)
- Item 200: Ses Frekans Çakışmasını Önleme (Vocal Notch Carve EQ @ 1-3kHz)
"""
import os
import wave
import struct
import math
import shutil
import tempfile
import unittest

from voice import (
    VoiceHumanizer,
    apply_stereo_pan_movement,
    ensure_crowd_room_ambience,
    inject_room_ambience,
    ensure_sub_kick_sfx,
    inject_sub_kick_hit,
    apply_acoustic_reverb_chamber,
    apply_voice_level_consistency,
    apply_tts_artifact_lowpass_filter,
    apply_epic_trailer_deep_voice,
    apply_news_rapid_cadence,
    inject_quiz_thinking_gap,
    apply_loop_inflection_preservation,
    apply_vocal_carve_eq,
)
from sfx_manager import ensure_core_sfx_suite
from bgm_manager import apply_vocal_carve_eq as bgm_vocal_carve, mix_narration_and_bgm


def _create_test_wav(filepath: str, duration: float = 2.5, sample_rate: int = 44100, num_channels: int = 1):
    num_samples = int(sample_rate * duration)
    frames = bytearray()
    for i in range(num_samples):
        t = i / sample_rate
        val = int(math.sin(2 * math.pi * 440 * t) * 16000)
        for _ in range(num_channels):
            frames.extend(struct.pack('<h', val))
    with wave.open(filepath, 'wb') as wf:
        wf.setnchannels(num_channels)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(frames))


class TestSection3Items186to200(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_voice = os.path.join(self.temp_dir, "voice.wav")
        self.test_music = os.path.join(self.temp_dir, "music.wav")
        _create_test_wav(self.test_voice, duration=3.0, num_channels=1)
        _create_test_wav(self.test_music, duration=5.0, num_channels=2)

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_item_186_greeting_sanitizer(self):
        """Madde 186: 'Merhaba arkadaşlar' gibi klişe girişlerin seslendirme metninden elenmesi."""
        raw_text = "Herkese merhaba arkadaşlar kanalıma hoş geldiniz! Bugün Marcus Aurelius'un kurallarını anlatıyorum."
        cleaned = VoiceHumanizer.clean_narration_for_speech(raw_text)
        self.assertNotIn("merhaba arkadaşlar", cleaned.lower())
        self.assertNotIn("kanalıma hoş geldiniz", cleaned.lower())
        # Item 161 phoneme dictionary rewrites the name for TTS ("Marküs Avreliyus");
        # the sanitizer must keep the sentence body either way.
        self.assertTrue("Marcus Aurelius" in cleaned or "Marküs Avreliyus" in cleaned)
        self.assertIn("kurallarını anlatıyorum", cleaned)

    def test_item_187_stereo_pan_movement(self):
        """Madde 187: Soldan sağa stereo pan hareketi."""
        out_wav = os.path.join(self.temp_dir, "pan_out.wav")
        res = apply_stereo_pan_movement(self.test_voice, out_wav, direction="left_to_right", duration=0.35)
        self.assertTrue(os.path.exists(res))
        with wave.open(res, "rb") as wf:
            self.assertEqual(wf.getnchannels(), 2, "Stereo pan 2 kanallı çıktı üretmelidir")

    def test_item_188_crowd_room_ambience(self):
        """Madde 188: Gürültülü ortam / sokak ve oda ambiyansı miksi."""
        amb = ensure_crowd_room_ambience()
        self.assertTrue(os.path.exists(amb))
        out_wav = os.path.join(self.temp_dir, "ambience_out.wav")
        res = inject_room_ambience(self.test_voice, out_wav, volume=0.08)
        self.assertTrue(os.path.exists(res))
        self.assertGreater(os.path.getsize(res), 1000)

    def test_item_191_acoustic_reverb_chamber(self):
        """Madde 191: Korku ve gerilim nişleri için katedral/mağara yankı odası DSP."""
        out_wav = os.path.join(self.temp_dir, "reverb_out.wav")
        res = apply_acoustic_reverb_chamber(self.test_voice, out_wav, room_type="cathedral")
        self.assertTrue(os.path.exists(res))
        self.assertGreater(os.path.getsize(res), 1000)

    def test_item_192_sub_kick_hit(self):
        """Madde 192: Anahtar vurgu kelimesinde 50Hz sub-kick vuruşu."""
        kick = ensure_sub_kick_sfx()
        self.assertTrue(os.path.exists(kick))
        out_wav = os.path.join(self.temp_dir, "kick_out.wav")
        res = inject_sub_kick_hit(self.test_voice, out_wav, timestamp_sec=0.5, volume=0.30)
        self.assertTrue(os.path.exists(res))
        self.assertGreater(os.path.getsize(res), 1000)

    def test_item_193_voice_level_consistency(self):
        """Madde 193: Dinamik RMS dengeleme ve ses tonu tutarlılığı."""
        out_wav = os.path.join(self.temp_dir, "consistent_out.wav")
        res = apply_voice_level_consistency(self.test_voice, out_wav)
        self.assertTrue(os.path.exists(res))
        self.assertGreater(os.path.getsize(res), 1000)

    def test_item_194_tts_artifact_lowpass_filter(self):
        """Madde 194: 14kHz üzerindeki sentetik TTS çınlamalarını kesen alçak geçiren filtre."""
        out_wav = os.path.join(self.temp_dir, "lowpass_out.wav")
        res = apply_tts_artifact_lowpass_filter(self.test_voice, out_wav, cutoff_hz=14000.0)
        self.assertTrue(os.path.exists(res))
        with wave.open(res, "rb") as wf:
            self.assertEqual(wf.getframerate(), 44100)

    def test_item_195_epic_trailer_deep_voice(self):
        """Madde 195: Epik sinematik fragman tonu (-1 oktav derinleştirme)."""
        out_wav = os.path.join(self.temp_dir, "deep_voice_out.wav")
        res = apply_epic_trailer_deep_voice(self.test_voice, out_wav, pitch_ratio=0.88)
        self.assertTrue(os.path.exists(res))
        self.assertGreater(os.path.getsize(res), 1000)

    def test_item_196_news_rapid_cadence(self):
        """Madde 196: Hızlı tempolu haber dili (90ms boşluk & atempo)."""
        out_wav = os.path.join(self.temp_dir, "news_out.wav")
        res = apply_news_rapid_cadence(self.test_voice, out_wav, tempo=1.12, max_pause_sec=0.09)
        self.assertTrue(os.path.exists(res))
        self.assertGreater(os.path.getsize(res), 1000)

    def test_item_197_quiz_thinking_gap(self):
        """Madde 197: Quiz soru-cevap düşünme boşluğu (3.0s fon müziği boşluğu)."""
        out_wav = os.path.join(self.temp_dir, "quiz_gap_out.wav")
        res = inject_quiz_thinking_gap(self.test_voice, out_wav, gap_seconds=3.0, insert_at_sec=1.0)
        self.assertTrue(os.path.exists(res))
        with wave.open(res, "rb") as wf:
            out_dur = wf.getnframes() / float(wf.getframerate())
            self.assertGreaterEqual(out_dur, 5.5, "3.0s boşluk eklendiğinde süre en az 5.5 saniye olmalıdır")

    def test_item_198_loop_inflection_preservation(self):
        """Madde 198: Döngü köprüsünde son kelimenin ton düşüşünü önleyen limiter."""
        out_wav = os.path.join(self.temp_dir, "loop_inflect_out.wav")
        res = apply_loop_inflection_preservation(self.test_voice, out_wav)
        self.assertTrue(os.path.exists(res))
        self.assertGreater(os.path.getsize(res), 1000)

    def test_item_199_core_sfx_suite(self):
        """Madde 199: 10 adet standart prosedürel ve telifsiz SFX arşivinin doğrulanması."""
        suite = ensure_core_sfx_suite()
        self.assertEqual(len(suite), 10, "SFX paketi tam 10 farklı efekt içermelidir")
        expected_keys = [
            "whoosh", "pop", "ding", "sub_impact", "tape_stop",
            "sine_sweep", "square_glitch", "heartbeat", "clock_tick", "sub_kick"
        ]
        for key in expected_keys:
            self.assertIn(key, suite)
            self.assertTrue(os.path.exists(suite[key]), f"{key} SFX dosyası mevcut olmalıdır")

    def test_item_200_vocal_carve_eq(self):
        """Madde 200: Müzikteki 1kHz-3kHz aralığını -4.5dB oyan vokal çentik EQ."""
        out_wav = os.path.join(self.temp_dir, "vocal_carve_out.wav")
        res = apply_vocal_carve_eq(self.test_music, out_wav, notch_freq=2000.0, notch_gain=-4.5)
        self.assertTrue(os.path.exists(res))
        self.assertGreater(os.path.getsize(res), 1000)

        # bgm_manager üzerinden entegre test
        bgm_res = bgm_vocal_carve(self.test_music, os.path.join(self.temp_dir, "bgm_carve.wav"))
        self.assertTrue(os.path.exists(bgm_res))


if __name__ == "__main__":
    unittest.main()
