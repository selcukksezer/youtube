"""5.1: gap is 12 dB above speech, and the measured sidechain hits -6 / -18 dB."""
import math
import os
import struct
import subprocess
import tempfile
import unittest
import wave

import imageio_ffmpeg

from bgm_manager import (
    DUCK_SIDECHAIN,
    PLAN_GAP_LIN,
    PLAN_SPEECH_LIN,
    gap_volume_for_speech,
    mix_narration_and_bgm,
)


def _rms_db(path, t0, t1):
    with wave.open(path, "rb") as handle:
        sr = handle.getframerate()
        ch = handle.getnchannels()
        handle.setpos(int(t0 * sr))
        raw = handle.readframes(int((t1 - t0) * sr))
    samples = struct.unpack("<" + "h" * (len(raw) // 2), raw)
    if ch == 2:
        samples = samples[::2]
    mean_sq = sum(s * s for s in samples) / len(samples)
    rms = math.sqrt(mean_sq) / 32768.0
    return 20.0 * math.log10(rms)


class TestChapter5Ducking(unittest.TestCase):
    def test_gap_is_12db_above_speech_slider(self):
        gap = gap_volume_for_speech(0.12)
        self.assertAlmostEqual(20.0 * math.log10(gap / 0.12), 12.0, places=1)
        self.assertAlmostEqual(20.0 * math.log10(PLAN_GAP_LIN), -6.0, places=1)
        self.assertAlmostEqual(20.0 * math.log10(PLAN_SPEECH_LIN), -18.0, places=1)
        self.assertAlmostEqual(gap_volume_for_speech(PLAN_SPEECH_LIN), PLAN_GAP_LIN, places=3)

    def test_mix_uses_measured_sidechain_not_ratio_3(self):
        import inspect
        src = inspect.getsource(mix_narration_and_bgm)
        self.assertTrue("{DUCK_SIDECHAIN}" in src or "{duck_chain}" in src)
        self.assertIn("threshold=0.028", DUCK_SIDECHAIN)
        self.assertIn("ratio=2.7", DUCK_SIDECHAIN)
        self.assertIn("level_sc=2", DUCK_SIDECHAIN)
        self.assertNotIn("ratio=3.2", src)
        self.assertNotIn("threshold=0.06", src)

    def test_sine_bed_ducks_12db(self):
        """Full-scale music sine, speech proxy near -14 LUFS. Gap -6 dB, speech -18 dB."""
        ff = imageio_ffmpeg.get_ffmpeg_exe()
        out = os.path.join(tempfile.gettempdir(), "duck_51.wav")
        narr = (
            "sine=frequency=1000:duration=4:sample_rate=48000,"
            "volume=volume='if(between(t,1.0,2.2),2.5,0.01)':eval=frame"
        )
        fc = (
            "[0:a]pan=stereo|c0=0.5*c0+0.5*c1|c1=0.5*c0+0.5*c1[narr_sc];"
            f"[1:a]volume={PLAN_GAP_LIN:.3f}[bgm_wide];"
            f"[bgm_wide][narr_sc]{DUCK_SIDECHAIN}[ducked]"
        )
        cmd = [
            ff, "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", narr,
            "-f", "lavfi", "-i", "sine=frequency=220:duration=4:sample_rate=48000,volume=8",
            "-filter_complex", fc, "-map", "[ducked]", "-c:a", "pcm_s16le", out,
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr[-300:])
        try:
            gap = _rms_db(out, 0.25, 0.85)
            speech = _rms_db(out, 1.45, 2.05)
            back = _rms_db(out, 2.7, 3.4)
        finally:
            if os.path.exists(out):
                os.remove(out)
        # Raw full sine RMS is -3 dB, so -6 dB gain reads near -9 and -18 dB gain near -21.
        self.assertAlmostEqual(gap, -9.0, delta=1.0)
        self.assertAlmostEqual(speech, -21.0, delta=1.5)
        self.assertAlmostEqual(gap - speech, 12.0, delta=1.5)
        self.assertAlmostEqual(back, gap, delta=1.0)


if __name__ == "__main__":
    unittest.main()
