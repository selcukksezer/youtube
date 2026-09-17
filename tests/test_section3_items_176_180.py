"""
Unit tests for Section 3: Items 176 - 180
- Item 176: Gizemli Fısıltı Efekti (0.3s Reverse Reverb Tail)
- Item 177: Doğal Yutkunma ve Duraksama (Natural Swallow & Monologue Pause every 40s)
- Item 178: Soru Cümlesi Tonlaması (Rising Interrogative Pitch Inflection +5%)
- Item 179: Şok Efekti Anında Ses Kesintisi (Shock Silence Drop - 0.2s Absolute Silence)
- Item 180: Müziğin Giriş Hacmi (Intro Music Punch @ 100% for 1s, Then Instant Ducking)
"""
import unittest
import os
import wave
import tempfile
import struct
import math

from voice import (
    apply_reverse_reverb_whisper,
    ensure_swallow_sound,
    inject_monologue_pause_and_swallow,
    inject_monologue_text_pauses,
    apply_question_pitch_inflection,
    apply_audio_question_inflection,
    inject_shock_silence_ssml,
    apply_shock_silence_cut,
    mix_intro_punch_bgm,
    VoiceHumanizer,
)
from bgm_manager import mix_intro_punch_bgm as bgm_mix_intro_punch


def _create_test_wav(filepath: str, duration: float = 3.0, sample_rate: int = 44100, num_channels: int = 1):
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


class TestSection3Items176to180(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_voice = os.path.join(self.temp_dir, "test_voice.wav")
        self.test_music = os.path.join(self.temp_dir, "test_music.wav")
        _create_test_wav(self.test_voice, duration=3.0, num_channels=1)
        _create_test_wav(self.test_music, duration=5.0, num_channels=2)

    def tearDown(self):
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_item_176_reverse_reverb_whisper(self):
        """Madde 176: Gizem nişinde cümle sonuna 0.3s ters çevrilmiş yankı ekleme."""
        out_wav = os.path.join(self.temp_dir, "out_176_rev_reverb.wav")
        res = apply_reverse_reverb_whisper(self.test_voice, out_wav, tail_sec=0.30, wet_mix=0.40)
        self.assertTrue(os.path.exists(res))
        self.assertGreater(os.path.getsize(res), 1000)

        with wave.open(res, 'rb') as wf:
            dur = wf.getnframes() / wf.getframerate()
            self.assertAlmostEqual(dur, 3.0, delta=0.2)

        # Facade testi
        out_facade = os.path.join(self.temp_dir, "out_176_facade.wav")
        res_facade = VoiceHumanizer.apply_reverse_reverb_whisper(self.test_voice, out_facade)
        self.assertTrue(os.path.exists(res_facade))

    def test_item_177_natural_swallow_and_monologue_pause(self):
        """Madde 177: Uzun monologlarda doğal duraksama ve boğaz yutkunma sesi doğrulaması."""
        # 1. 220ms yutkunma sesi sentezi
        sfx_path = os.path.join(self.temp_dir, "test_swallow.wav")
        res_sfx = ensure_swallow_sound(sfx_path)
        self.assertTrue(os.path.exists(res_sfx))

        with wave.open(res_sfx, 'rb') as wf:
            dur = wf.getnframes() / wf.getframerate()
            self.assertAlmostEqual(dur, 0.22, delta=0.03)

        # 2. Ses katmanına yutkunma ve duraksama enjeksiyonu
        out_wav = os.path.join(self.temp_dir, "out_177_swallow.wav")
        res_inject = inject_monologue_pause_and_swallow(self.test_voice, out_wav, interval_seconds=1.5)
        self.assertTrue(os.path.exists(res_inject))
        self.assertGreater(os.path.getsize(res_inject), 1000)

        # 3. Metin içi monolog duraksaması (~65 kelimede bir mola)
        long_script = " ".join(["kelime"] * 140)
        text_out = inject_monologue_text_pauses(long_script, interval_words=65, pause_ms=450, engine_type="ssml")
        self.assertIn('<break time="450ms"/>', text_out)

        # Facade testi
        self.assertTrue(os.path.exists(VoiceHumanizer.ensure_swallow_sound()))

    def test_item_178_question_pitch_inflection(self):
        """Madde 178: Soru cümlelerinin sonunda ses perdesi yukarı bükülmesi (+5%)."""
        # Metin SSML testi
        script = "Roma imparatorluğu nasıl çöktü? Bu sırrı kimse bilmiyordu."
        ssml_out = apply_question_pitch_inflection(script, pitch_boost="+5%", engine_type="ssml")
        self.assertIn('<prosody pitch="+5%">Roma imparatorluğu nasıl çöktü?</prosody>', ssml_out)
        self.assertNotIn('<prosody pitch="+5%">Bu sırrı kimse bilmiyordu.</prosody>', ssml_out)

        # Plain text testi
        plain_out = apply_question_pitch_inflection(script, engine_type="plain")
        self.assertIn("(↑)", plain_out)

        # Ses seviyesinde perde bükülmesi (DSP)
        out_wav = os.path.join(self.temp_dir, "out_178_question_inflection.wav")
        res_audio = apply_audio_question_inflection(self.test_voice, out_wav, end_sec=0.40, pitch_semitones=0.85)
        self.assertTrue(os.path.exists(res_audio))
        self.assertGreater(os.path.getsize(res_audio), 1000)

        # Facade testi
        facade_out = VoiceHumanizer.apply_question_pitch_inflection(script)
        self.assertIn('<prosody pitch="+5%">', facade_out)

    def test_item_179_shock_silence_cut(self):
        """Madde 179: Şok anında 0.2 saniyelik mutlak sessizlik kesintisi doğrulaması."""
        # SSML mutlak sessizlik enjeksiyonu
        text = "Herkes durumu kontrol altında sanıyordu ama aslında büyük bir felaket yaklaşıyordu."
        ssml_out = inject_shock_silence_ssml(text, silence_ms=200)
        self.assertIn('<break time="200ms"/> ama aslında', ssml_out)

        # Ses düzeyinde 0.2s sessizlik kesintisi
        out_wav = os.path.join(self.temp_dir, "out_179_shock_cut.wav")
        res_audio = apply_shock_silence_cut(self.test_voice, out_wav, shock_timestamps=[1.0], silence_sec=0.20)
        self.assertTrue(os.path.exists(res_audio))
        self.assertGreater(os.path.getsize(res_audio), 1000)

        # Facade testi
        facade_out = VoiceHumanizer.inject_shock_silence_ssml(text)
        self.assertIn('<break time="200ms"/>', facade_out)

    def test_item_180_intro_music_punch(self):
        """Madde 180: Videonun ilk 1 saniyesinde %100 müzik vuruşu ve ardından anında ducking."""
        out_wav = os.path.join(self.temp_dir, "out_180_intro_punch.wav")
        res = mix_intro_punch_bgm(
            self.test_voice,
            self.test_music,
            out_wav,
            intro_blast_sec=1.0,
            blast_volume=0.85,
            ducked_volume=0.14
        )
        self.assertTrue(os.path.exists(res))
        self.assertGreater(os.path.getsize(res), 1000)

        with wave.open(res, 'rb') as wf:
            dur = wf.getnframes() / wf.getframerate()
            self.assertGreaterEqual(dur, 2.8)

        # BGM Manager modülü üzerinden çağrı testi
        out_bgm = os.path.join(self.temp_dir, "out_180_bgm_mgr.wav")
        res_bgm = bgm_mix_intro_punch(self.test_voice, self.test_music, out_bgm)
        self.assertTrue(os.path.exists(res_bgm))

        # Facade testi
        out_facade = os.path.join(self.temp_dir, "out_180_facade.wav")
        res_facade = VoiceHumanizer.mix_intro_punch_bgm(self.test_voice, self.test_music, out_facade)
        self.assertTrue(os.path.exists(res_facade))


if __name__ == '__main__':
    unittest.main()
