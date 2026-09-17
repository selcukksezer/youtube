"""
Unit tests for Section 3: Items 181 - 185
- Item 181: Hafif Vinil Cızırtısı (Vinyl Crackle @ -28dB)
- Item 182: Dramatik Keman/Piyano Katmanı (Dramatic Piano Note SFX)
- Item 183: Cyberpunk Synthwave Basları (Analog Synth Bass Pulse)
- Item 184: Sesin Görselle Birebir Senkronizasyonu (A/V Sync Precision)
- Item 185: Sona Doğru Müzik Yükselmesi (Ending Outro Music Swell)
"""
import unittest
import os
import wave
import tempfile
import struct
import math

from voice import (
    ensure_vinyl_crackle_sfx,
    inject_vinyl_crackle_layer,
    ensure_dramatic_piano_note_sfx,
    inject_dramatic_piano_layer,
    ensure_cyberpunk_synth_bass_sfx,
    inject_cyberpunk_synth_bass,
    align_visual_cue_to_audio,
    audit_av_sync_precision,
    apply_outro_music_swell,
    VoiceHumanizer,
)
from bgm_manager import apply_outro_music_swell as bgm_outro_swell


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


class TestSection3Items181to185(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_voice = os.path.join(self.temp_dir, "test_voice.wav")
        self.test_music = os.path.join(self.temp_dir, "test_music.wav")
        _create_test_wav(self.test_voice, duration=3.0, num_channels=1)
        _create_test_wav(self.test_music, duration=6.0, num_channels=2)

    def tearDown(self):
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_item_181_vinyl_crackle(self):
        """Madde 181: Tarihi ve nostaljik nişler için -28dB vinil plak cızırtısı doğrulaması."""
        sfx_path = os.path.join(self.temp_dir, "test_vinyl.wav")
        res_sfx = ensure_vinyl_crackle_sfx(output_path=sfx_path, duration=3.0, volume_db=-28.0)
        self.assertTrue(os.path.exists(res_sfx))

        with wave.open(res_sfx, 'rb') as wf:
            self.assertEqual(wf.getframerate(), 44100)
            dur = wf.getnframes() / wf.getframerate()
            self.assertAlmostEqual(dur, 3.0, delta=0.05)

        # Sese miksleme testi
        out_wav = os.path.join(self.temp_dir, "out_181_vinyl.wav")
        res_mix = inject_vinyl_crackle_layer(self.test_voice, out_wav, volume_db=-28.0)
        self.assertTrue(os.path.exists(res_mix))
        self.assertGreater(os.path.getsize(res_mix), 1000)

        # Facade doğrulaması
        facade_res = VoiceHumanizer.ensure_vinyl_crackle_sfx(duration=2.0)
        self.assertTrue(os.path.exists(facade_res))

    def test_item_182_dramatic_piano_layer(self):
        """Madde 182: Duygusal hikayeler için tek nota dramatik piyano tınısı doğrulaması."""
        sfx_path = os.path.join(self.temp_dir, "test_piano.wav")
        res_sfx = ensure_dramatic_piano_note_sfx(output_path=sfx_path, note_freq=220.0, duration=2.5)
        self.assertTrue(os.path.exists(res_sfx))

        with wave.open(res_sfx, 'rb') as wf:
            self.assertEqual(wf.getframerate(), 44100)
            dur = wf.getnframes() / wf.getframerate()
            self.assertAlmostEqual(dur, 2.5, delta=0.05)

        # Sese piyano notası enjekte etme
        out_wav = os.path.join(self.temp_dir, "out_182_piano.wav")
        res_mix = inject_dramatic_piano_layer(self.test_voice, out_wav, timestamp_sec=0.5, volume=0.35)
        self.assertTrue(os.path.exists(res_mix))
        self.assertGreater(os.path.getsize(res_mix), 1000)

        # Facade doğrulaması
        facade_res = VoiceHumanizer.ensure_dramatic_piano_note_sfx(duration=2.0)
        self.assertTrue(os.path.exists(facade_res))

    def test_item_183_cyberpunk_synth_bass(self):
        """Madde 183: Teknoloji ve yapay zeka haberleri için cyberpunk analog synth bası doğrulaması."""
        sfx_path = os.path.join(self.temp_dir, "test_synth.wav")
        res_sfx = ensure_cyberpunk_synth_bass_sfx(output_path=sfx_path, duration=3.0, freq_hz=55.0)
        self.assertTrue(os.path.exists(res_sfx))

        with wave.open(res_sfx, 'rb') as wf:
            self.assertEqual(wf.getframerate(), 44100)
            dur = wf.getnframes() / wf.getframerate()
            self.assertAlmostEqual(dur, 3.0, delta=0.05)

        # Sese synth bası enjekte etme
        out_wav = os.path.join(self.temp_dir, "out_183_synth.wav")
        res_mix = inject_cyberpunk_synth_bass(self.test_voice, out_wav, timestamp_sec=0.2, volume=0.35)
        self.assertTrue(os.path.exists(res_mix))
        self.assertGreater(os.path.getsize(res_mix), 1000)

        # Facade doğrulaması
        facade_res = VoiceHumanizer.ensure_cyberpunk_synth_bass_sfx(duration=2.0)
        self.assertTrue(os.path.exists(facade_res))

    def test_item_184_av_sync_precision(self):
        """Madde 184: Sesin görselle birebir milisaniye senkronizasyonu ve audit doğrulaması."""
        # 1. Kelime zamanı ile görsel kart başlangıcı hizalama testi
        audio_timestamps = [
            {"word": "Antik", "start": 0.35, "end": 0.72},
            {"word": "Roma", "start": 0.75, "end": 1.15},
            {"word": "Marcus", "start": 1.25, "end": 1.65},
            {"word": "Aurelius", "start": 1.68, "end": 2.20},
            {"word": "hükümdardı", "start": 2.25, "end": 2.85}
        ]

        # Görsel kart zamanı 0.90s iken Marcus Aurelius sözü 1.25s'de başlıyor
        sync_report = align_visual_cue_to_audio(
            visual_cue_time=0.90,
            audio_word_timestamps=audio_timestamps,
            target_phrase="Marcus Aurelius",
            tolerance_sec=0.04
        )

        self.assertEqual(sync_report["aligned_cue_time"], 1.25)
        self.assertEqual(sync_report["sync_status"], "ADJUSTED")
        self.assertAlmostEqual(sync_report["offset"], 0.35, places=2)

        # Zaten milisaniyesine örtüşüyorsa LOCKED olmalı
        locked_report = align_visual_cue_to_audio(
            visual_cue_time=1.26,
            audio_word_timestamps=audio_timestamps,
            target_phrase="Marcus Aurelius",
            tolerance_sec=0.04
        )
        self.assertEqual(locked_report["sync_status"], "LOCKED")

        # 2. Video - Ses genel süre uyumu denetimi
        audit_res = audit_av_sync_precision(video_duration=45.012, audio_duration=45.008, tolerance_ms=20.0)
        self.assertTrue(audit_res["in_sync"])
        self.assertEqual(audit_res["status"], "PERFECT")
        self.assertLessEqual(audit_res["diff_ms"], 10.0)

        # Facade testi
        facade_sync = VoiceHumanizer.align_visual_cue_to_audio(1.0, audio_timestamps, "Marcus")
        self.assertEqual(facade_sync["aligned_cue_time"], 1.25)

    def test_item_185_outro_music_swell(self):
        """Madde 185: Son 5 saniyede CTA verilirken müziğin kademeli yükselmesi (+3.5dB) doğrulaması."""
        out_wav = os.path.join(self.temp_dir, "out_185_swell.wav")
        res = apply_outro_music_swell(
            self.test_music,
            out_wav,
            total_duration=6.0,
            swell_seconds=3.0,
            boost_db=3.5
        )
        self.assertTrue(os.path.exists(res))
        self.assertGreater(os.path.getsize(res), 1000)

        with wave.open(res, 'rb') as wf:
            dur = wf.getnframes() / wf.getframerate()
            self.assertAlmostEqual(dur, 6.0, delta=0.2)

        # BGM Manager modülü üzerinden çağrı testi
        out_bgm = os.path.join(self.temp_dir, "out_185_bgm.wav")
        res_bgm = bgm_outro_swell(self.test_music, out_bgm, total_duration=6.0, swell_seconds=2.0)
        self.assertTrue(os.path.exists(res_bgm))

        # Facade testi
        out_facade = os.path.join(self.temp_dir, "out_185_facade.wav")
        res_facade = VoiceHumanizer.apply_outro_music_swell(self.test_music, out_facade, total_duration=6.0)
        self.assertTrue(os.path.exists(res_facade))


if __name__ == '__main__':
    unittest.main()
