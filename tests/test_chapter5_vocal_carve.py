"""5.2: music loses about 4.5 dB from 1 kHz through 3 kHz, not only at 2 kHz."""
import inspect
import math
import os
import struct
import subprocess
import tempfile
import unittest
import wave

import imageio_ffmpeg

from bgm_manager import mix_narration_and_bgm
from voice.audio_dsp import VOCAL_CARVE_EQ


def _rms_db(path):
    with wave.open(path, "rb") as handle:
        raw = handle.readframes(handle.getnframes())
        channels = handle.getnchannels()
    samples = struct.unpack("<" + "h" * (len(raw) // 2), raw)
    if channels == 2:
        samples = samples[::2]
    mean_sq = sum(sample * sample for sample in samples) / len(samples)
    return 20.0 * math.log10(math.sqrt(mean_sq) / 32768.0)


def _gain_db(freq):
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    raw = os.path.join(tempfile.gettempdir(), f"carve_raw_{freq}.wav")
    out = os.path.join(tempfile.gettempdir(), f"carve_out_{freq}.wav")
    subprocess.run(
        [ff, "-y", "-hide_banner", "-loglevel", "error",
         "-f", "lavfi", "-i", f"sine=frequency={freq}:duration=0.5:sample_rate=48000,volume=8",
         "-c:a", "pcm_s16le", raw],
        check=True,
    )
    proc = subprocess.run(
        [ff, "-y", "-hide_banner", "-loglevel", "error", "-i", raw, "-af", VOCAL_CARVE_EQ,
         "-c:a", "pcm_s16le", out],
        capture_output=True, text=True,
    )
    try:
        if proc.returncode != 0:
            raise AssertionError(proc.stderr[-300:])
        return _rms_db(out) - _rms_db(raw)
    finally:
        for path in (raw, out):
            if os.path.exists(path):
                os.remove(path)


class TestChapter5VocalCarve(unittest.TestCase):
    def test_mix_uses_band_not_minus_3(self):
        src = inspect.getsource(mix_narration_and_bgm)
        self.assertIn("VOCAL_CARVE_EQ", src)
        self.assertNotIn("g=-3.0", src)
        self.assertIn("f=1100", VOCAL_CARVE_EQ)
        self.assertIn("f=2900", VOCAL_CARVE_EQ)

    def test_band_holds_near_minus_4_5(self):
        gains = {freq: _gain_db(freq) for freq in (1000, 2000, 3000, 400, 6000)}
        for freq in (1000, 2000, 3000):
            self.assertAlmostEqual(gains[freq], -4.5, delta=1.0, msg=freq)
        self.assertGreater(gains[400], -1.2)
        self.assertGreater(gains[6000], -1.5)


if __name__ == "__main__":
    unittest.main()
