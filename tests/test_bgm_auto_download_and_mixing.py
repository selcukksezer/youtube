"""Unit tests verifying BGM auto-download, catalog track resolution, and audible ducked mixing."""
import os
import tempfile
import unittest
import numpy as np

import config
from bgm_manager import (
    get_bgm_path,
    get_cached_bgm_path,
    mix_narration_and_bgm,
    get_safe_default_bgm_path,
)
from youtube_safe_bgm_catalog import (
    track_by_filename,
    resolve_bgm_path,
    ensure_catalog_track,
    load_catalog,
)
from copyright_risk import scan_audio_copyright_risk


class TestBgmAutoDownloadAndMixing(unittest.TestCase):
    def test_catalog_query_cleaning_and_matching(self):
        # 1. Matching by filename
        t = track_by_filename("yt_safe_441_meditation.mp3")
        self.assertIsNotNone(t)
        self.assertEqual(t.get("filename"), "yt_safe_441_meditation.mp3")

        # 2. Matching with UI label (indirilecek)
        t_ui = track_by_filename("Meditation (calm) (indirilecek)")
        self.assertIsNotNone(t_ui)
        self.assertEqual(t_ui.get("filename"), "yt_safe_441_meditation.mp3")

        # 3. Matching by display label
        t_disp = track_by_filename("Meditation (calm)")
        self.assertIsNotNone(t_disp)
        self.assertEqual(t_disp.get("filename"), "yt_safe_441_meditation.mp3")

        # 4. Matching by id
        t_id = track_by_filename("yt_safe_441")
        self.assertIsNotNone(t_id)
        self.assertEqual(t_id.get("filename"), "yt_safe_441_meditation.mp3")

    def test_get_bgm_path_auto_resolves_and_downloads(self):
        # Track 441 is downloaded now; should resolve immediately
        p = get_bgm_path("yt_safe_441_meditation.mp3")
        self.assertIsNotNone(p)
        self.assertTrue(os.path.isfile(p))
        self.assertGreater(os.path.getsize(p), 2000)

        # Also via UI label
        p_label = get_bgm_path("Meditation (calm) (indirilecek)")
        self.assertIsNotNone(p_label)
        self.assertTrue(os.path.isfile(p_label))

    def test_get_cached_bgm_path_fallback(self):
        p = get_cached_bgm_path("")
        self.assertIsNotNone(p)
        self.assertTrue(os.path.isfile(p))
        self.assertGreater(os.path.getsize(p), 2000)

    def test_copyright_risk_safe_for_catalog_tracks(self):
        res = scan_audio_copyright_risk([
            "yt_safe_441_meditation.mp3",
            "yt_safe_127_valley_sunset.mp3",
            "royalty_free_ambient.wav",
        ])
        self.assertTrue(res.get("safe"))
        self.assertEqual(len(res.get("flagged_items", [])), 0)

    def test_mix_narration_and_bgm_preserves_audio_and_ducks(self):
        # Create dummy 1-second stereo narration and BGM
        import wave, struct
        with tempfile.TemporaryDirectory() as tmpdir:
            narr_path = os.path.join(tmpdir, "narr.wav")
            bgm_path = os.path.join(tmpdir, "bgm.wav")
            out_path = os.path.join(tmpdir, "out.wav")

            sample_rate = 44100
            dur = 1.5
            n_samples = int(sample_rate * dur)

            # 440 Hz tone for speech
            frames_narr = bytearray()
            for i in range(n_samples):
                val = int(math_sin := 16000 * np.sin(2 * np.pi * 440.0 * (i / sample_rate)))
                frames_narr.extend(struct.pack("<hh", val, val))
            with wave.open(narr_path, "wb") as wf:
                wf.setnchannels(2)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(frames_narr)

            # 880 Hz tone for music
            frames_bgm = bytearray()
            for i in range(n_samples):
                val = int(8000 * np.sin(2 * np.pi * 880.0 * (i / sample_rate)))
                frames_bgm.extend(struct.pack("<hh", val, val))
            with wave.open(bgm_path, "wb") as wf:
                wf.setnchannels(2)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(frames_bgm)

            res = mix_narration_and_bgm(narr_path, bgm_path, out_path, volume=0.12)
            self.assertEqual(res, out_path)
            self.assertTrue(os.path.isfile(out_path))
            self.assertGreater(os.path.getsize(out_path), 2000)

            # Verify that output has distinct music content
            with wave.open(out_path, "rb") as wf:
                out_frames = wf.readframes(wf.getnframes())
                out_data = np.frombuffer(out_frames, dtype=np.int16)
            diff = np.abs(out_data[:n_samples * 2] - np.frombuffer(frames_narr, dtype=np.int16))
            self.assertGreater(np.max(diff), 200)


if __name__ == "__main__":
    unittest.main()
