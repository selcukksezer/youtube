"""
Tests for Chapter 28.15 / Section 2.2 (Madde 15):
reference_repos2/NarratoAI evolution:
- services/audio_normalizer.py: AudioNormalizer, two-pass loudnorm JSON parsing, second-pass filter builder, ducking filter
- render/ffmpeg_hardware.py: FFmpegHardwareDetector, hardware acceleration detection and fallback
"""

import json
import unittest
from unittest.mock import patch, MagicMock

from services.audio_normalizer import (
    AudioNormalizer,
    GLOBAL_AUDIO_NORMALIZER,
    SHORTS_TARGET_LUFS,
)
from render.ffmpeg_hardware import (
    FFmpegHardwareDetector,
    GLOBAL_HW_DETECTOR,
)


class TestNarratoAIAudioNormalizer(unittest.TestCase):
    def setUp(self):
        self.normalizer = AudioNormalizer(target_lufs=-14.0, max_peak=-1.5)

    def test_parse_loudnorm_json_from_stderr(self):
        fake_stderr = """
[Parsed_loudnorm_0 @ 0000021a8b941580] 
{
	"input_i" : "-21.45",
	"input_tp" : "-3.20",
	"input_lra" : "8.40",
	"input_thresh" : "-32.10",
	"output_i" : "-14.05",
	"output_tp" : "-1.50",
	"output_lra" : "6.80",
	"output_thresh" : "-24.70",
	"normalization_type" : "dynamic",
	"target_offset" : "0.05"
}
"""
        res = self.normalizer.parse_loudnorm_json_from_stderr(fake_stderr)
        self.assertIsNotNone(res)
        self.assertEqual(res["input_i"], -21.45)
        self.assertEqual(res["input_tp"], -3.20)
        self.assertEqual(res["input_lra"], 8.40)
        self.assertEqual(res["input_thresh"], -32.10)
        self.assertEqual(res["target_offset"], 0.05)

    def test_build_two_pass_loudnorm_filter(self):
        measured = {
            "input_i": -20.50,
            "input_tp": -2.80,
            "input_lra": 7.50,
            "input_thresh": -31.00,
            "target_offset": 0.10,
        }
        filter_str = self.normalizer.build_two_pass_loudnorm_filter(measured)
        self.assertIn("loudnorm=I=-14.0:TP=-1.5:LRA=7.0", filter_str)
        self.assertIn("measured_I=-20.50", filter_str)
        self.assertIn("measured_TP=-2.80", filter_str)
        self.assertIn("measured_LRA=7.50", filter_str)
        self.assertIn("measured_thresh=-31.00", filter_str)
        self.assertIn("linear=true", filter_str)

    def test_build_ducking_filter(self):
        duck_filter = AudioNormalizer.build_ducking_filter(
            voice_label="[voice]",
            bgm_label="[bgm]",
            output_label="[out]",
            duck_volume=0.25,
        )
        self.assertIn("[bgm]volume=0.25[bgm_ducked]", duck_filter)
        self.assertIn("[voice][bgm_ducked]amix=inputs=2:duration=first:dropout_transition=2[out]", duck_filter)

    def test_missing_audio_returns_none(self):
        res = self.normalizer.analyze_audio_lufs("nonexistent_sound.wav")
        self.assertIsNone(res)


class TestNarratoAIHardwareDetector(unittest.TestCase):
    def setUp(self):
        self.detector = FFmpegHardwareDetector()

    @patch.object(FFmpegHardwareDetector, "get_supported_encoders")
    def test_nvenc_detection(self, mock_encoders):
        mock_encoders.return_value = ["libx264", "h264_nvenc", "hevc_nvenc"]
        profile = self.detector.detect_best_encoder_profile(force_refresh=True)

        self.assertEqual(profile["encoder"], "h264_nvenc")
        self.assertTrue(profile["is_hardware"])
        self.assertIn("-rc", profile["extra_args"])

    @patch.object(FFmpegHardwareDetector, "get_supported_encoders")
    def test_software_cpu_fallback(self, mock_encoders):
        mock_encoders.return_value = ["libx264", "flv"]
        profile = self.detector.detect_best_encoder_profile(force_refresh=True)

        self.assertEqual(profile["encoder"], "libx264")
        self.assertFalse(profile["is_hardware"])
        self.assertIn("-crf", profile["extra_args"])


if __name__ == "__main__":
    unittest.main()
