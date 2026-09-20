"""P2-21 beat hints (advisory) and P2-23 Whisper alignment stub."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from bgm_manager import compute_scene_beat_hints, parse_bgm_bpm
from director import compile_director_plan
from subtitle_generator import align_words_whisper


class TestBeatHints(unittest.TestCase):
    def test_parse_bgm_bpm_from_filename(self):
        self.assertEqual(parse_bgm_bpm("stoic_calm_philosophy.wav"), 78.0)
        self.assertEqual(parse_bgm_bpm("energetic_motivation_workout.wav"), 125.0)
        self.assertEqual(parse_bgm_bpm("unknown_track.mp3", default_bpm=100.0), 100.0)

    def test_compute_scene_beat_hints_advisory(self):
        scenes = [{"duration": 3.0}, {"duration": 3.0}, {"duration": 3.0}]
        hints = compute_scene_beat_hints(scenes, bgm_path="stoic_calm.wav")
        self.assertEqual(len(hints), 3)
        self.assertEqual(hints[0]["bpm"], 78.0)
        self.assertIn("beat_hint_ms", hints[0])
        self.assertIn("delta_ms", hints[0])

    def test_compile_attaches_beat_hint_ms(self):
        plan = compile_director_plan(
            {
                "title": "Test Beat Hints",
                "scenes": [
                    {"narration": "Ilk sahne tam cumle burada.", "duration": 3.0},
                    {"narration": "Ikinci sahne de tam cumle.", "duration": 3.0},
                ],
            },
            niche_id="6_stoic_philosophy",
        )
        self.assertTrue(all(sc.beat_hint_ms is not None for sc in plan.scenes))


class TestWhisperStub(unittest.TestCase):
    def test_whisper_align_flag_default_off(self):
        self.assertFalse(config.WHISPER_ALIGN)

    def test_align_words_whisper_passthrough_when_disabled(self):
        timings = [{"text": "Merhaba", "offset": 0.0, "duration": 0.5}]
        out = align_words_whisper(timings, audio_path="/tmp/narration.wav")
        self.assertEqual(out, timings)


if __name__ == "__main__":
    unittest.main()
