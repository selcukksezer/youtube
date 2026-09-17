"""
Unit tests for Section 3: Items 156 - 160
- Item 156: Tape-Stop Efekti (0.4s Kaset Durması & Sessizlik)
- Item 157: Kalp Atışı Efekti (Heartbeat SFX & Layering)
- Item 158: Saat Tik-Tak Sesi (Ticking Clock SFX - 3s)
- Item 159: Daktilo Sesi (Typewriter SFX)
- Item 160: Doğal Duraklama (Micro-Pauses: 120ms / 280ms / 350ms / 450ms)
"""
import unittest
import os
import wave
import tempfile
import struct
import math

from voice import (
    ensure_tape_stop_sfx,
    apply_tape_stop_to_audio,
    ensure_heartbeat_sfx,
    inject_heartbeat_layer,
    ensure_ticking_clock_sfx,
    inject_ticking_clock,
    ensure_typewriter_sfx,
    inject_typewriter_sfx,
    apply_micro_pauses,
    VoiceHumanizer,
)


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


class TestSection3Items156to160(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_audio = os.path.join(self.temp_dir, "test_audio.wav")
        _create_test_wav(self.test_audio, duration=3.5)

    def tearDown(self):
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_item_156_tape_stop_effect(self):
        """Madde 156: 0.4s Tape-Stop sentezi ve tezat anında müziği susturma doğrulaması."""
        sfx_path = os.path.join(self.temp_dir, "test_tape_stop.wav")
        res_sfx = ensure_tape_stop_sfx(output_path=sfx_path, duration=0.40)
        self.assertTrue(os.path.exists(res_sfx))

        with wave.open(res_sfx, 'rb') as wf:
            self.assertEqual(wf.getframerate(), 44100)
            duration = wf.getnframes() / wf.getframerate()
            self.assertAlmostEqual(duration, 0.40, delta=0.03)

        # Sese uygula (1.0 saniyede tezat gerçekleşti)
        out_wav = os.path.join(self.temp_dir, "out_156_tapestop.wav")
        res_out = apply_tape_stop_to_audio(self.test_audio, out_wav, stop_timestamps=[1.0])
        self.assertTrue(os.path.exists(res_out))
        self.assertGreater(os.path.getsize(res_out), 1000)

        # VoiceHumanizer facade doğrulaması
        res_facade = VoiceHumanizer.ensure_tape_stop_sfx(duration=0.40)
        self.assertTrue(os.path.exists(res_facade))

    def test_item_157_heartbeat_effect(self):
        """Madde 157: Gerilim sahneleri için Lub-Dub sub-frekans kalp atışı doğrulaması."""
        sfx_path = os.path.join(self.temp_dir, "test_heartbeat.wav")
        res_sfx = ensure_heartbeat_sfx(output_path=sfx_path, duration=3.0, bpm=65.0)
        self.assertTrue(os.path.exists(res_sfx))

        with wave.open(res_sfx, 'rb') as wf:
            self.assertEqual(wf.getframerate(), 44100)
            duration = wf.getnframes() / wf.getframerate()
            self.assertAlmostEqual(duration, 3.0, delta=0.05)

        # Sese kalp atışı alt katmanı enjekte et
        out_wav = os.path.join(self.temp_dir, "out_157_heartbeat.wav")
        res_out = inject_heartbeat_layer(self.test_audio, out_wav, start_sec=0.5, duration_sec=2.0)
        self.assertTrue(os.path.exists(res_out))

    def test_item_158_ticking_clock_effect(self):
        """Madde 158: Soru/quiz sahneleri için 3 saniyelik saat tik-tak sesi doğrulaması."""
        sfx_path = os.path.join(self.temp_dir, "test_clock.wav")
        res_sfx = ensure_ticking_clock_sfx(output_path=sfx_path, duration=3.0)
        self.assertTrue(os.path.exists(res_sfx))

        with wave.open(res_sfx, 'rb') as wf:
            self.assertEqual(wf.getframerate(), 44100)
            duration = wf.getnframes() / wf.getframerate()
            self.assertAlmostEqual(duration, 3.0, delta=0.05)

        out_wav = os.path.join(self.temp_dir, "out_158_clock.wav")
        res_out = inject_ticking_clock(self.test_audio, out_wav, timestamp_sec=0.2, duration=3.0)
        self.assertTrue(os.path.exists(res_out))

    def test_item_159_typewriter_effect(self):
        """Madde 159: Ekrana harf/belge dökülme sahneleri için daktilo sesi doğrulaması."""
        sfx_path = os.path.join(self.temp_dir, "test_typewriter.wav")
        res_sfx = ensure_typewriter_sfx(output_path=sfx_path, duration=2.0)
        self.assertTrue(os.path.exists(res_sfx))

        with wave.open(res_sfx, 'rb') as wf:
            self.assertEqual(wf.getframerate(), 44100)
            duration = wf.getnframes() / wf.getframerate()
            self.assertAlmostEqual(duration, 2.0, delta=0.05)

        out_wav = os.path.join(self.temp_dir, "out_159_typewriter.wav")
        res_out = inject_typewriter_sfx(self.test_audio, out_wav, timestamp_sec=0.3, duration=2.0)
        self.assertTrue(os.path.exists(res_out))

    def test_item_160_micro_pauses(self):
        """Madde 160: Virgüllerde 120ms, noktalarda 280ms, sorularda 350ms, paragraflarda 450ms duraklama doğrulaması."""
        sample_script = (
            "Marcus Aurelius, antik Roma'nın bilge imparatoruydu.\n\n"
            "Peki onun en büyük sırrı neydi? Zihnini kontrol etmek!"
        )

        # SSML format testi
        ssml_res = apply_micro_pauses(
            sample_script,
            comma_ms=120,
            dot_ms=280,
            question_ms=350,
            paragraph_ms=450,
            engine_type="ssml"
        )

        self.assertIn('<break time="120ms"/>', ssml_res)
        self.assertIn('<break time="280ms"/>', ssml_res)
        self.assertIn('<break time="350ms"/>', ssml_res)
        self.assertIn('<break time="450ms"/>', ssml_res)

        # Plain text format testi
        plain_res = apply_micro_pauses(sample_script, engine_type="plain")
        self.assertIn("...", plain_res)

        # VoiceHumanizer facade testi
        facade_res = VoiceHumanizer.apply_micro_pauses(sample_script)
        self.assertIn('<break time="120ms"/>', facade_res)


if __name__ == '__main__':
    unittest.main()
