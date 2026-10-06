"""
Tests for Section 2.2 (Madde 18) / FunClip evolution:
- services/forced_alignment.py: calculate_alignment_drift, align_word_timestamps_to_audio_duration, paginate_aligned_words
"""

import unittest
from services.forced_alignment import (
    calculate_alignment_drift,
    align_word_timestamps_to_audio_duration,
    paginate_aligned_words,
)


class TestFunClipForcedAlignment(unittest.TestCase):
    def test_calculate_alignment_drift(self):
        words = [
            {"word": "Bu", "start": 0.0, "end": 0.5},
            {"word": "harika", "start": 0.6, "end": 1.2},
            {"word": "bir", "start": 1.3, "end": 1.8},
            {"word": "video.", "start": 1.9, "end": 3.4},
        ]
        # Audio is 3.0s, last word is 3.4s -> +0.4s drift
        drift = calculate_alignment_drift(words, 3.0)
        self.assertAlmostEqual(drift, 0.4, places=2)

    def test_align_word_timestamps_to_audio_duration(self):
        raw_words = [
            {"word": "Güneş", "start": 0.0, "end": 0.8},
            {"word": "sistemi", "start": 0.9, "end": 1.9},
            {"word": "hakkında", "start": 2.0, "end": 3.1},
            {"word": "bilgiler.", "start": 3.2, "end": 4.5},
        ]
        audio_dur = 3.6  # Physical audio ends at 3.6s, but raw Whisper ended at 4.5s

        aligned = align_word_timestamps_to_audio_duration(raw_words, audio_dur)
        self.assertEqual(len(aligned), 4)

        # Verify all timestamps are strictly within [0.0, 3.6]
        for w in aligned:
            self.assertGreaterEqual(w["start"], 0.0)
            self.assertLessEqual(w["end"], audio_dur)

        # Verify monotonicity
        for i in range(len(aligned) - 1):
            self.assertLessEqual(aligned[i]["start"], aligned[i]["end"])
            self.assertLessEqual(aligned[i]["end"], aligned[i + 1]["start"])

        # Final word must end very close to audio_dur
        self.assertAlmostEqual(aligned[-1]["end"], audio_dur, delta=0.05)

    def test_paginate_aligned_words(self):
        words = [
            {"word": "1", "start": 0.0, "end": 0.4},
            {"word": "2", "start": 0.4, "end": 0.8},
            {"word": "3", "start": 0.8, "end": 1.2},
            {"word": "4", "start": 1.2, "end": 1.6},
            {"word": "5", "start": 1.6, "end": 2.0},
            {"word": "6", "start": 2.0, "end": 2.4},
        ]

        # Max 3 tokens per page -> expect 2 pages
        pages = paginate_aligned_words(words, max_tokens_per_page=3, max_page_duration=2.0)
        self.assertEqual(len(pages), 2)
        self.assertEqual(pages[0]["text"], "1 2 3")
        self.assertEqual(pages[1]["text"], "4 5 6")
        self.assertEqual(pages[0]["start"], 0.0)
        self.assertEqual(pages[0]["end"], 1.2)
        self.assertEqual(pages[1]["start"], 1.2)
        self.assertEqual(pages[1]["end"], 2.4)


if __name__ == "__main__":
    unittest.main()
