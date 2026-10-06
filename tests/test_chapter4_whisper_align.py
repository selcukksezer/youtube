"""4.4: tail clamp, drift scale, script-preserving Whisper snap."""
import os
import tempfile
import unittest
import wave

from subtitle_generator import (
    _rescale_timings_to_audio_duration,
    align_words_whisper,
    merge_continuation_words,
    snap_script_to_whisper,
)


def _wav(seconds: float) -> str:
    path = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(48000)
        wf.writeframes(b"\x00\x00" * int(48000 * seconds))
    return path


class TestChapter4WhisperAlign(unittest.TestCase):
    def test_short_tail_extends_last_word_only(self):
        audio = _wav(2.0)
        try:
            timings = [
                {"text": "Bir", "offset": 0.0, "duration": 0.8},
                {"text": "iki", "offset": 0.8, "duration": 0.9},
            ]
            out = _rescale_timings_to_audio_duration(timings, audio)
            self.assertEqual(out[0]["offset"], 0.0)
            self.assertEqual(out[0]["duration"], 0.8)
            self.assertAlmostEqual(out[1]["offset"] + out[1]["duration"], 2.0, places=2)
        finally:
            os.unlink(audio)

    def test_large_gap_scales_every_word(self):
        audio = _wav(2.0)
        try:
            timings = [{"text": "Merhaba", "offset": 0.0, "duration": 1.0}]
            out = _rescale_timings_to_audio_duration(timings, audio)
            self.assertAlmostEqual(out[0]["duration"], 2.0, places=2)
        finally:
            os.unlink(audio)

    def test_overshoot_clamps_last_word(self):
        audio = _wav(2.0)
        try:
            timings = [
                {"text": "Bir", "offset": 0.0, "duration": 1.2},
                {"text": "iki", "offset": 1.2, "duration": 1.3},
            ]
            out = _rescale_timings_to_audio_duration(timings, audio)
            self.assertEqual(out[0]["duration"], 1.2)
            self.assertAlmostEqual(out[1]["offset"] + out[1]["duration"], 2.0, places=2)
        finally:
            os.unlink(audio)

    def test_continuation_fragment_merges(self):
        merged = merge_continuation_words([
            {"text": " YouTube", "offset": 0.0, "duration": 0.4},
            {"text": "-Kanal.", "offset": 0.4, "duration": 0.3},
        ])
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["text"], "YouTube-Kanal.")
        self.assertAlmostEqual(merged[0]["duration"], 0.7, places=2)

    def test_snap_keeps_script_text(self):
        script = [
            {"text": "Merhaba", "offset": 0.0, "duration": 0.5},
            {"text": "dünya", "offset": 0.5, "duration": 0.5},
        ]
        heard = [
            {"text": " Merhaba", "offset": 0.10, "duration": 0.40},
            {"text": " dünya", "offset": 0.55, "duration": 0.40},
        ]
        out = snap_script_to_whisper(script, heard)
        self.assertEqual([w["text"] for w in out], ["Merhaba", "dünya"])
        self.assertEqual(out[0]["offset"], 0.1)
        self.assertEqual(out[1]["offset"], 0.55)

    def test_weak_match_keeps_scaled_times(self):
        self.assertEqual(
            snap_script_to_whisper(
                [
                    {"text": "elma", "offset": 0.0, "duration": 0.4},
                    {"text": "armut", "offset": 0.4, "duration": 0.4},
                ],
                [{"text": " muz", "offset": 0.1, "duration": 0.2}],
            ),
            [],
        )

    def test_disabled_whisper_does_not_replace_words(self):
        timings = [{"text": "Merhaba", "offset": 0.0, "duration": 0.5}]
        out = align_words_whisper(timings, audio_path="/tmp/no-such-narration.wav", enabled=False)
        self.assertEqual(out[0]["text"], "Merhaba")
        self.assertEqual(out[0]["offset"], 0.0)


if __name__ == "__main__":
    unittest.main()
