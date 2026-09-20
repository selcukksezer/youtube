"""
Unit tests for Section 3: Items 161 - 165
- Item 161: Farklı Dillerde Doğru Telaffuz Kütüphanesi (SSML phoneme & spoken alias)
- Item 162: Ses Normalizasyonu (EBU R128 @ -14 LUFS, -1.5 dBTP)
- Item 163: Telefon Filtresi (Lo-Fi EQ @ 300Hz-3000Hz)
- Item 164: Fısıltı Modu (ASMR Katmanı DSP)
- Item 165: Rastgele Ses Tonu Seçimi (Dynamic Voice Actor Persona Rotation)
"""
import unittest
import os
import wave
import tempfile
import struct
import math

from voice import (
    PRONUNCIATION_LIBRARY,
    apply_pronunciation_library,
    normalize_ebu_r128,
    measure_audio_loudness,
    apply_telephone_filter,
    apply_asmr_whisper_dsp,
    get_asmr_voice_settings,
    select_voice_gender,
    select_dynamic_voice_actor,
    VoiceHumanizer,
)


def _create_test_wav(filepath: str, duration: float = 2.0, sample_rate: int = 44100):
    num_samples = int(sample_rate * duration)
    frames = bytearray()
    for i in range(num_samples):
        t = i / sample_rate
        val = int(math.sin(2 * math.pi * 440 * t) * 18000)
        frames.extend(struct.pack('<h', val))
    with wave.open(filepath, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(frames))


class TestSection3Items161to165(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_audio = os.path.join(self.temp_dir, "test_audio.wav")
        _create_test_wav(self.test_audio, duration=2.0)

    def tearDown(self):
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_item_161_pronunciation_library(self):
        """Madde 161: Yabancı filozof ve özel isim telaffuz kütüphanesi doğrulaması."""
        # Kütüphanede zengin isimler var mı?
        self.assertIn("Marcus Aurelius", PRONUNCIATION_LIBRARY)
        self.assertIn("Nietzsche", PRONUNCIATION_LIBRARY)
        self.assertIn("Machiavelli", PRONUNCIATION_LIBRARY)
        self.assertIn("Schopenhauer", PRONUNCIATION_LIBRARY)
        self.assertIn("Seneca", PRONUNCIATION_LIBRARY)
        self.assertGreaterEqual(len(PRONUNCIATION_LIBRARY), 20)

        # SSML format testi (<phoneme alphabet="ipa" ph="...">)
        sample = "Nietzsche ve Marcus Aurelius stoacılık üzerine konuştu."
        ssml_res = apply_pronunciation_library(sample, engine_type="ssml")
        self.assertIn('<phoneme alphabet="ipa"', ssml_res)
        self.assertIn('Marcus Aurelius</phoneme>', ssml_res)

        # Plain text konuşma dostu alias testi
        plain_res = apply_pronunciation_library(sample, engine_type="plain")
        self.assertIn("Niçe", plain_res)
        self.assertIn("Marküs Avreliyus", plain_res)
        self.assertNotIn("Orianus", plain_res)

    def test_item_162_ebu_r128_loudness_normalization(self):
        """Madde 162: YouTube standardı olan -14 LUFS ve -1.5 dBTP normalizasyon doğrulaması."""
        out_wav = os.path.join(self.temp_dir, "out_162_normalized.wav")
        res = normalize_ebu_r128(self.test_audio, out_wav, target_lufs=-14.0, true_peak=-1.5, lra=11.0)
        self.assertTrue(os.path.exists(res))
        self.assertGreater(os.path.getsize(res), 1000)

        # Loudness ölçümü
        metrics = measure_audio_loudness(res)
        self.assertIn("integrated_lufs", metrics)
        self.assertIn("true_peak_db", metrics)
        self.assertIn("lra_lu", metrics)

    def test_item_163_telephone_lofi_filter(self):
        """Madde 163: Telefon konuşması ve alıntılar için 300Hz-3000Hz Lo-Fi EQ doğrulaması."""
        out_wav = os.path.join(self.temp_dir, "out_163_telephone.wav")
        res = apply_telephone_filter(self.test_audio, out_wav)
        self.assertTrue(os.path.exists(res))
        self.assertGreater(os.path.getsize(res), 1000)

        # Facade testi
        res_facade = VoiceHumanizer.apply_telephone_filter(self.test_audio, out_wav)
        self.assertTrue(os.path.exists(res_facade))

    def test_item_164_asmr_whisper_dsp(self):
        """Madde 164: Uyku hikayeleri ve gece nişi için Fısıltı Modu (ASMR Katmanı) doğrulaması."""
        out_wav = os.path.join(self.temp_dir, "out_164_asmr.wav")
        res = apply_asmr_whisper_dsp(self.test_audio, out_wav)
        self.assertTrue(os.path.exists(res))
        self.assertGreater(os.path.getsize(res), 1000)

        # ASMR ayar tespiti testi
        asmr_settings = get_asmr_voice_settings("sleep_stories", "Gece derin uyku meditasyonu")
        self.assertTrue(asmr_settings["enabled"])
        self.assertEqual(asmr_settings["rate"], "-12%")

    def test_item_165_dynamic_voice_actor_selection(self):
        """Madde 165: Konu dramatikliğine ve diline göre dinamik seslendirmen seçimi doğrulaması."""
        # Türkçe erkek (Stoacı / Savaş)
        tr_male = select_dynamic_voice_actor(target_lang="tr", niche_id="stoic", keyword="Marcus Aurelius Roma Savaşı")
        self.assertEqual(tr_male["gender"], "male")
        self.assertEqual(tr_male["voice"], "tr-TR-AhmetNeural")
        self.assertEqual(tr_male["mood"], "tok_ve_guclu")

        # Türkçe kadın (Uyku / Masal)
        tr_female = select_dynamic_voice_actor(target_lang="tr", niche_id="sleep", keyword="Gece uyku masalları")
        self.assertEqual(tr_female["gender"], "female")
        self.assertEqual(tr_female["voice"], "tr-TR-EmelNeural")

        # İngilizce erkek (Tarih / Gizem)
        en_male = select_dynamic_voice_actor(target_lang="en", niche_id="history", keyword="Ancient Roman war secrets")
        self.assertEqual(en_male["gender"], "male")
        self.assertEqual(en_male["voice"], "en-US-ChristopherNeural")

        # İngilizce kadın (ASMR / Meditasyon)
        en_female = select_dynamic_voice_actor(target_lang="en", niche_id="asmr", keyword="Deep sleep whisper relaxation")
        self.assertEqual(en_female["gender"], "female")
        self.assertEqual(en_female["voice"], "en-US-JennyNeural")


if __name__ == '__main__':
    unittest.main()