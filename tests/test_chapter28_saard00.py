"""
Tests for Chapter 28.7 / Section 2.1 (Item 7):
reference_repos/saard00_shorts_generator evolution:
- subtitle_generator.py: split_subtitle_pages_on_silence (300-350ms silence detection)
- scenes/scene_composer.py: compose_dual_clip_scene (single-pass FFmpeg concat without disk intermediate re-encodes)
"""

import os
import unittest
from unittest.mock import patch, MagicMock

from subtitle_generator import split_subtitle_pages_on_silence
from scenes.scene_composer import compose_dual_clip_scene


class TestSaard00SubtitleSilence(unittest.TestCase):
    def test_silence_splits_pages(self):
        # 4 words: first 2 are continuous, then 400ms pause, then next 2 words
        timings = [
            {"text": "Hello", "offset": 1.000, "duration": 0.300},
            {"text": "world", "offset": 1.350, "duration": 0.250},   # ends at 1.600
            # Gap from 1.600 to 2.050 is 450ms (> 350ms silence threshold)
            {"text": "this", "offset": 2.050, "duration": 0.200},
            {"text": "works", "offset": 2.300, "duration": 0.300},
        ]
        pages = split_subtitle_pages_on_silence(timings, max_words_per_page=6, silence_threshold_sec=0.350)
        self.assertEqual(len(pages), 2, "Expected 2 pages due to > 350ms pause")
        self.assertEqual([w["text"] for w in pages[0]], ["Hello", "world"])
        self.assertEqual([w["text"] for w in pages[1]], ["this", "works"])

    def test_continuous_speech_stays_grouped(self):
        # Continuous speech under 350ms gap
        timings = [
            {"text": "Fast", "offset": 0.100, "duration": 0.200},
            {"text": "and", "offset": 0.350, "duration": 0.150},
            {"text": "furious", "offset": 0.550, "duration": 0.300},
        ]
        pages = split_subtitle_pages_on_silence(timings, max_words_per_page=4, silence_threshold_sec=0.350)
        self.assertEqual(len(pages), 1, "Expected single page for continuous fast speech")
        self.assertEqual(len(pages[0]), 3)

    def test_punctuation_split(self):
        # Even without pause, punctuation terminates page when break_on_punctuation=True
        timings = [
            {"text": "Stop!", "offset": 0.100, "duration": 0.200},
            {"text": "Go", "offset": 0.320, "duration": 0.200},
        ]
        pages = split_subtitle_pages_on_silence(timings, max_words_per_page=5, break_on_punctuation=True)
        self.assertEqual(len(pages), 2)
        self.assertEqual(pages[0][0]["text"], "Stop!")
        self.assertEqual(pages[1][0]["text"], "Go")


class TestSaard00DualClipComposer(unittest.TestCase):
    def test_missing_files_raise_filenotfound(self):
        with self.assertRaises(FileNotFoundError):
            compose_dual_clip_scene("non_existent_a.mp4", "non_existent_b.mp4", 6.0, "output.mp4")

    @patch("os.path.isfile")
    @patch("subprocess.run")
    def test_compose_dual_clip_ffmpeg_command(self, mock_run, mock_isfile):
        # Mock file existence for inputs and output
        mock_isfile.return_value = True
        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_run.return_value = mock_res

        with patch("os.path.getsize", return_value=1024):
            out = compose_dual_clip_scene(
                video_a_path="assets/video_a.mp4",
                video_b_path="assets/video_b.mp4",
                total_duration=6.0,
                output_path="assets/out_dual.mp4",
                split_ratio=0.5,
            )

        self.assertEqual(out, "assets/out_dual.mp4")
        self.assertTrue(mock_run.called)
        cmd = mock_run.call_args[0][0]

        # Verify command flags
        cmd_str = " ".join(cmd)
        self.assertIn("-stream_loop -1 -i", cmd_str)
        self.assertIn("concat=n=2:v=1:a=0", cmd_str)
        self.assertIn("-t 6.000", cmd_str)
        self.assertIn("-pix_fmt yuv420p", cmd_str)
        self.assertIn("-movflags +faststart", cmd_str)
        self.assertIn("-an", cmd_str)  # No audio provided


if __name__ == "__main__":
    unittest.main()
