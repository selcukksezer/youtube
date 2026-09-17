"""
Unit tests for Section 3: Items 150 - 155
- Item 150: Yüksek Geçiren Filtre (High-Pass Filter @ 80Hz)
- Item 151: Bas Güçlendirme (Voice Warmth EQ @ 180-250Hz)
- Item 152: Hava Frekansı Parlaklığı (Presence EQ @ 10-12kHz)
- Item 153: Mono Yerine Genişletilmiş Stereo (Stereo Widener)
- Item 154: Sub-Bass Patlaması (Impact Sub - 45Hz)
- Item 155: Riser / Whoosh Senkronizasyonu (250ms)
"""
import unittest
import os
import wave
import tempfile
import struct
import math

from voice import (
    apply_high_pass_filter,
    apply_voice_warmth_eq,
    apply_presence_air_eq,
    apply_stereo_widener,
    mix_wide_stereo_with_center_vocal,
    ensure_sub_bass_impact_sfx,
    inject_sub_bass_impact,
    ensure_riser_whoosh_sfx,
    sync_riser_whoosh_transitions,
    VoiceHumanizer,
)


def _create_test_wav(filepath: str, duration: float = 1.0, sample_rate: int = 44100, num_channels: int = 1):
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


class TestSection3Items150to155(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_mono_wav = os.path.join(self.temp_dir, "test_mono.wav")
        self.test_stereo_wav = os.path.join(self.temp_dir, "test_stereo.wav")
        _create_test_wav(self.test_mono_wav, duration=1.0, num_channels=1)
        _create_test_wav(self.test_stereo_wav, duration=2.0, num_channels=2)

    def tearDown(self):
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_item_150_high_pass_filter(self):
        """Madde 150: 80Hz altı frekansları kesen High-Pass Filter doğrulaması."""
        out_wav = os.path.join(self.temp_dir, "out_150_highpass.wav")
        res = apply_high_pass_filter(self.test_mono_wav, out_wav, cutoff_hz=80.0)
        self.assertTrue(os.path.exists(res))
        self.assertGreater(os.path.getsize(res), 1000)

        # VoiceHumanizer facade method testi
        res2 = VoiceHumanizer.apply_high_pass_filter(self.test_mono_wav, out_wav, cutoff_hz=80.0)
        self.assertTrue(os.path.exists(res2))

    def test_item_151_voice_warmth_eq(self):
        """Madde 151: 180-250Hz bandına +2dB tok tını veren Voice Warmth EQ doğrulaması."""
        out_wav = os.path.join(self.temp_dir, "out_151_warmth.wav")
        res = apply_voice_warmth_eq(self.test_mono_wav, out_wav, center_freq=220.0, gain_db=2.0)
        self.assertTrue(os.path.exists(res))
        self.assertGreater(os.path.getsize(res), 1000)

        # VoiceHumanizer facade method testi
        res2 = VoiceHumanizer.apply_voice_warmth_eq(self.test_mono_wav, out_wav, center_freq=220.0, gain_db=2.0)
        self.assertTrue(os.path.exists(res2))

    def test_item_152_presence_air_eq(self):
        """Madde 152: 10-12kHz bandına +1.5dB kristalize hava tınısı (Presence EQ) doğrulaması."""
        out_wav = os.path.join(self.temp_dir, "out_152_presence.wav")
        res = apply_presence_air_eq(self.test_mono_wav, out_wav, center_freq=11000.0, gain_db=1.5)
        self.assertTrue(os.path.exists(res))
        self.assertGreater(os.path.getsize(res), 1000)

        # VoiceHumanizer facade method testi
        res2 = VoiceHumanizer.apply_presence_air_eq(self.test_mono_wav, out_wav, center_freq=11000.0, gain_db=1.5)
        self.assertTrue(os.path.exists(res2))

    def test_item_153_stereo_widener_and_center_vocal(self):
        """Madde 153: Stereo genişletme ve merkez-mono vokal miksajı doğrulaması."""
        out_wide = os.path.join(self.temp_dir, "out_153_wide.wav")
        res_wide = apply_stereo_widener(self.test_stereo_wav, out_wide, width=1.4)
        self.assertTrue(os.path.exists(res_wide))

        out_mix = os.path.join(self.temp_dir, "out_153_mix.wav")
        res_mix = mix_wide_stereo_with_center_vocal(self.test_stereo_wav, self.test_mono_wav, out_mix)
        self.assertTrue(os.path.exists(res_mix))
        self.assertGreater(os.path.getsize(res_mix), 1000)

    def test_item_154_sub_bass_impact_45hz(self):
        """Madde 154: 45Hz sub-bass patlaması sentezi ve mikse enjeksiyon doğrulaması."""
        sfx_path = os.path.join(self.temp_dir, "test_sub_bass.wav")
        generated_sfx = ensure_sub_bass_impact_sfx(output_path=sfx_path, duration=0.8, base_freq=45.0)
        self.assertTrue(os.path.exists(generated_sfx))

        # Wave parametrelerini kontrol et (44.1kHz, 16bit, ~0.8s)
        with wave.open(generated_sfx, 'rb') as wf:
            self.assertEqual(wf.getframerate(), 44100)
            self.assertEqual(wf.getsampwidth(), 2)
            duration = wf.getnframes() / wf.getframerate()
            self.assertAlmostEqual(duration, 0.8, delta=0.05)

        # Ses dosyasına enjekte et
        out_injected = os.path.join(self.temp_dir, "out_154_injected.wav")
        res_injected = inject_sub_bass_impact(self.test_mono_wav, out_injected, timestamp_sec=0.2)
        self.assertTrue(os.path.exists(res_injected))

    def test_item_155_riser_whoosh_sync(self):
        """Madde 155: 250ms Riser/Whoosh sentezi ve sahne geçişi (scene cut - 0.25s) senkronizasyonu."""
        sfx_path = os.path.join(self.temp_dir, "test_riser.wav")
        generated_sfx = ensure_riser_whoosh_sfx(output_path=sfx_path, duration=0.25)
        self.assertTrue(os.path.exists(generated_sfx))

        with wave.open(generated_sfx, 'rb') as wf:
            self.assertEqual(wf.getframerate(), 44100)
            duration = wf.getnframes() / wf.getframerate()
            self.assertAlmostEqual(duration, 0.25, delta=0.02)

        # Sahne kesim zamanları (örnek: 0.5s ve 1.2s'de sahne geçişi)
        out_synced = os.path.join(self.temp_dir, "out_155_synced.wav")
        scene_cuts = [0.5, 1.2]
        res_synced = sync_riser_whoosh_transitions(self.test_mono_wav, scene_cuts, out_synced)
        self.assertTrue(os.path.exists(res_synced))


if __name__ == '__main__':
    unittest.main()
