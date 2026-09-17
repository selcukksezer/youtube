"""
Unit tests for Section 3: Items 171 - 175
- Item 171: Metin Vurgularında Pitch Sıçraması (Pitch Jump on Emphasis)
- Item 172: Gereksiz Arka Plan Uğultusunu Temizleme (Noise Gate)
- Item 173: Çoklu Ses Formatı İhracı (48kHz 24-bit PCM WAV & 320kbps AAC-LC)
- Item 174: Mobil Cihaz Uyumluluk Testi (Mono Downmix & Clarity Audit)
- Item 175: Heyecanlı Cümlelerde Ses Hızlanması (Climax Narrative Speed Acceleration)
"""
import unittest
import os
import wave
import tempfile
import struct
import math

from voice import (
    apply_emphasis_pitch_jumps,
    apply_audio_pitch_jump,
    apply_noise_gate,
    export_master_and_stream_audio,
    run_mobile_device_audio_check,
    apply_climax_tempo_curve,
    accelerate_audio_tempo,
    VoiceHumanizer,
)


def _create_test_wav(filepath: str, duration: float = 2.0, sample_rate: int = 44100, num_channels: int = 1, add_noise: bool = True):
    num_samples = int(sample_rate * duration)
    frames = bytearray()
    for i in range(num_samples):
        t = i / sample_rate
        # 440Hz ana ses sinyali
        tone = math.sin(2 * math.pi * 440 * t) * 16000
        # Düşük seviyeli arka plan gürültüsü
        noise = (math.sin(2 * math.pi * 60 * t) * 200) if add_noise else 0
        sample_val = int(tone + noise)
        for _ in range(num_channels):
            frames.extend(struct.pack('<h', max(-32767, min(32767, sample_val))))

    with wave.open(filepath, 'wb') as wf:
        wf.setnchannels(num_channels)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(frames))


class TestSection3Items171to175(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_audio_mono = os.path.join(self.temp_dir, "test_mono.wav")
        self.test_audio_stereo = os.path.join(self.temp_dir, "test_stereo.wav")
        _create_test_wav(self.test_audio_mono, duration=2.5, num_channels=1)
        _create_test_wav(self.test_audio_stereo, duration=2.5, num_channels=2)

    def tearDown(self):
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_item_171_pitch_jump_on_emphasis(self):
        """Madde 171: Önemli kelimelerde perde (pitch) sıçraması doğrulaması."""
        text = "Bu sırrı ASLA unutmayın, çünkü arkasındaki şok edici gerçek ortaya çıktı."

        # SSML formatında perde sıçraması
        ssml_out = apply_emphasis_pitch_jumps(text, engine_type="ssml", pitch_boost="+12%")
        self.assertIn('<prosody pitch="+12%">ASLA</prosody>', ssml_out)
        self.assertIn('<prosody pitch="+12%">sırrı</prosody>', ssml_out)
        self.assertIn('<prosody pitch="+12%">şok</prosody>', ssml_out)
        self.assertIn('<prosody pitch="+12%">gerçek</prosody>', ssml_out)

        # Plain text formatı
        plain_out = apply_emphasis_pitch_jumps(text, engine_type="plain")
        self.assertIn('*ASLA*', plain_out)
        self.assertIn('*sırrı*', plain_out)

        # Ses seviyesinde pitch sıçraması (DSP)
        out_dsp = os.path.join(self.temp_dir, "out_pitch_jump.wav")
        res_audio = apply_audio_pitch_jump(self.test_audio_mono, out_dsp, timestamp_sec=0.5, duration_sec=0.4, pitch_semitones=2.0)
        self.assertTrue(os.path.exists(res_audio))
        self.assertGreater(os.path.getsize(res_audio), 1000)

        # VoiceHumanizer facade doğrulaması
        facade_ssml = VoiceHumanizer.apply_emphasis_pitch_jumps(text)
        self.assertIn('<prosody pitch="+12%">', facade_ssml)

    def test_item_172_noise_gate(self):
        """Madde 172: Arka plan uğultusunu ve dip gürültüsünü kesen Noise Gate doğrulaması."""
        out_gated = os.path.join(self.temp_dir, "out_noise_gate.wav")
        res_gated = apply_noise_gate(
            self.test_audio_mono,
            out_gated,
            threshold_db=-40.0,
            attack_ms=10.0,
            release_ms=100.0,
            range_db=-60.0
        )
        self.assertTrue(os.path.exists(res_gated))
        self.assertGreater(os.path.getsize(res_gated), 1000)

        with wave.open(res_gated, 'rb') as wf:
            dur = wf.getnframes() / wf.getframerate()
            self.assertAlmostEqual(dur, 2.5, delta=0.2)

        # Facade testi
        out_facade = os.path.join(self.temp_dir, "out_gate_facade.wav")
        res_facade = VoiceHumanizer.apply_noise_gate(self.test_audio_mono, out_facade)
        self.assertTrue(os.path.exists(res_facade))

    def test_item_173_dual_audio_export(self):
        """Madde 173: 48kHz 24-bit PCM Master WAV & 320kbps AAC akış formatı ihracı."""
        export_result = export_master_and_stream_audio(
            self.test_audio_mono,
            output_dir=self.temp_dir,
            base_name="export_test"
        )

        self.assertTrue(export_result["success"])
        self.assertEqual(export_result["sample_rate"], 48000)
        self.assertEqual(export_result["pcm_bit_depth"], 24)
        self.assertEqual(export_result["aac_bitrate"], "320k")

        master_wav = export_result["master_wav"]
        stream_aac = export_result["stream_aac"]

        self.assertTrue(os.path.exists(master_wav))
        self.assertTrue(os.path.exists(stream_aac))

        # 48000Hz ve 24-bit derinlik doğrulaması (RIFF fmt chunk analizi)
        with open(master_wav, "rb") as f:
            riff_bytes = f.read(100)
            self.assertEqual(riff_bytes[:4], b"RIFF")
            self.assertEqual(riff_bytes[8:12], b"WAVE")
            fmt_idx = riff_bytes.find(b"fmt ")
            self.assertNotEqual(fmt_idx, -1)
            sr = struct.unpack_from("<I", riff_bytes, fmt_idx + 12)[0]
            bits = struct.unpack_from("<H", riff_bytes, fmt_idx + 22)[0]
            self.assertEqual(sr, 48000)
            self.assertEqual(bits, 24)

        # AAC stream dosyasının geçerli boyutta olduğunu doğrula
        self.assertGreater(os.path.getsize(stream_aac), 500)

        # Facade doğrulaması
        facade_res = VoiceHumanizer.export_master_and_stream_audio(self.test_audio_mono, output_dir=self.temp_dir, base_name="facade")
        self.assertTrue(facade_res["success"])

    def test_item_174_mobile_device_audio_check(self):
        """Madde 174: Mobil tek hoparlör mono netlik ve faz iptali audit testi."""
        # Stereo dosya üzerinde mobil uyumluluk analizi
        report = run_mobile_device_audio_check(self.test_audio_stereo)

        self.assertIn("passed", report)
        self.assertIn("mobile_readiness_score", report)
        self.assertIn("phase_correlation", report)
        self.assertIn("mono_rms_db", report)
        self.assertIn("recommendations", report)

        # Faz korelasyonu geçerli aralıkta [-1.0, 1.0]
        self.assertGreaterEqual(report["phase_correlation"], -1.0)
        self.assertLessEqual(report["phase_correlation"], 1.0)
        self.assertGreaterEqual(report["mobile_readiness_score"], 0)

        # Facade testi
        facade_report = VoiceHumanizer.run_mobile_device_audio_check(self.test_audio_mono)
        self.assertIn("mobile_readiness_score", facade_report)

    def test_item_175_climax_narrative_tempo_acceleration(self):
        """Madde 175: Hikaye doruk noktasında kademeli ses hızlanması (%115 tempo)."""
        scenes = [
            {"text": "İşte tarihin en gizemli keşfi hakkında bilmeniz gerekenler."},
            {"text": "Arkeologlar yıllarca bu antik yapının sırrını çözmeye çalıştı."},
            {"text": "Ve tam bu noktada, yerin metrelerce altında şok edici gerçek ortaya çıktı!"},
            {"text": "Çünkü bulunan tabletler tüm tarihi baştan yazıyordu."}
        ]

        # Doruk sahnesini otomatik tespit edip %115 tempo uygulama
        processed = apply_climax_tempo_curve(scenes, engine_type="ssml")
        self.assertEqual(len(processed), 4)

        # 3. sahne (doruk cümlesi: 'şok edici gerçek ortaya çıktı') +15% hıza sahip olmalı
        climax_scene = processed[2]
        self.assertEqual(climax_scene["prosody_rate"], "+15%")
        self.assertEqual(climax_scene["tempo_role"], "climax_peak")
        self.assertIn('<prosody rate="+15%">', climax_scene["ssml_text"])

        # Doruk öncesi hazırlık sahnesi (+8%)
        self.assertEqual(processed[1]["prosody_rate"], "+8%")
        self.assertEqual(processed[1]["tempo_role"], "climax_buildup")

        # Kanca sahnesi (+9%)
        self.assertEqual(processed[0]["prosody_rate"], "+9%")

        # Audio düzeyinde tempo hızlandırma (atempo=1.15)
        out_accel = os.path.join(self.temp_dir, "out_accel.wav")
        res_accel = accelerate_audio_tempo(self.test_audio_mono, out_accel, speed_factor=1.15)
        self.assertTrue(os.path.exists(res_accel))

        # Hızlanan sesin süresi daha kısa olmalı (2.5s / 1.15 ≈ 2.17s)
        with wave.open(res_accel, 'rb') as wf:
            dur_accel = wf.getnframes() / wf.getframerate()
            self.assertLess(dur_accel, 2.5)
            self.assertAlmostEqual(dur_accel, 2.5 / 1.15, delta=0.15)

        # Facade doğrulaması
        facade_scenes = VoiceHumanizer.apply_climax_tempo_curve(scenes)
        self.assertEqual(facade_scenes[2]["prosody_rate"], "+15%")


if __name__ == '__main__':
    unittest.main()
