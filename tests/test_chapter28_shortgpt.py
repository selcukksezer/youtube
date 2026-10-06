"""
Tests for Chapter 28.9 / Section 2.1 (Item 9):
reference_repos/shortgpt evolution:
- services/audio_tempo_guard.py: build_atempo_filter_chain, speedup_audio, adjust_audio_pitch
- director/timeline_manifest.py: TimelineManifest, TrackType, single-pass FFmpeg graph compiler
- services/facts_story_engine.py: create_facts_timeline_manifest
"""

import json
import os
import unittest
from unittest.mock import patch, MagicMock

from services.audio_tempo_guard import (
    build_atempo_filter_chain,
    speedup_audio,
    adjust_audio_pitch,
)
from director.timeline_manifest import (
    TimelineManifest,
    TimelineTrack,
    TrackType,
)
from services.facts_story_engine import FactsStoryEngine


class TestShortGPTAudioTempoAndPitch(unittest.TestCase):
    def test_build_atempo_filter_chain(self):
        # 1.0 normal
        self.assertIn("atempo=1.0", build_atempo_filter_chain(1.0))

        # 1.5 in range
        chain_1_5 = build_atempo_filter_chain(1.5)
        self.assertIn("atempo=1.5000", chain_1_5)

        # > 2.0 (e.g. 2.4x) - ShortGPT previously crashed here
        chain_2_4 = build_atempo_filter_chain(2.4)
        self.assertIn("atempo=2.0", chain_2_4)
        self.assertIn("atempo=1.2000", chain_2_4)

        # < 0.5 (e.g. 0.35x) - ShortGPT previously crashed here
        chain_0_35 = build_atempo_filter_chain(0.35)
        self.assertIn("atempo=0.5", chain_0_35)
        self.assertIn("atempo=0.7000", chain_0_35)

    @patch("os.path.exists", return_value=True)
    @patch("services.audio_tempo_guard.get_audio_duration", return_value=20.0)
    @patch("subprocess.run")
    def test_speedup_audio_execution(self, mock_run, mock_dur, mock_exists):
        mock_run.return_value = MagicMock(returncode=0)
        out = speedup_audio("voice.wav", "voice_fast.wav", speed_factor=1.25)
        self.assertEqual(out, "voice_fast.wav")
        self.assertTrue(mock_run.called)
        cmd = mock_run.call_args[0][0]
        self.assertIn("-af", cmd)
        self.assertIn("atempo=1.2500", " ".join(cmd))

    @patch("os.path.exists", return_value=True)
    @patch("subprocess.run")
    def test_adjust_audio_pitch(self, mock_run, mock_exists):
        mock_run.return_value = MagicMock(returncode=0)
        # Shift pitch up by +2 semitones
        out = adjust_audio_pitch("voice.wav", "voice_shifted.wav", semitones=2.0, preserve_tempo=True)
        self.assertEqual(out, "voice_shifted.wav")
        self.assertTrue(mock_run.called)
        cmd = mock_run.call_args[0][0]
        cmd_str = " ".join(cmd)
        self.assertIn("asetrate=", cmd_str)
        self.assertIn("atempo=", cmd_str)


class TestShortGPTTimelineManifest(unittest.TestCase):
    @patch("services.path_security.os.path.exists", return_value=True)
    def test_manifest_tracks_and_durations(self, mock_exists):
        manifest = TimelineManifest(target_width=1080, target_height=1920, fps=30)
        manifest.add_background_video("assets/bg.mp4", duration=15.0)
        manifest.add_broll_clip("assets/broll.mp4", start=5.0, duration=4.0)
        manifest.add_image_overlay("assets/badge.png", start=2.0, duration=3.0)
        manifest.add_subtitles_ass("assets/subs.ass", duration=15.0)
        manifest.add_voiceover("assets/speech.wav", duration=14.5)
        manifest.add_background_music("assets/bgm.mp3", duration=15.0)
        manifest.add_sfx("assets/whoosh.wav", start=4.9, duration=0.8)

        self.assertEqual(manifest.total_duration(), 15.0)
        d = manifest.to_manifest_dict()
        self.assertEqual(d["canvas"]["width"], 1080)
        self.assertEqual(d["canvas"]["height"], 1920)
        self.assertEqual(len(d["visual_tracks"]), 4)
        self.assertEqual(len(d["audio_tracks"]), 3)

    @patch("services.path_security.os.path.exists", return_value=True)
    def test_compile_ffmpeg_command_replaces_moviepy(self, mock_exists):
        manifest = TimelineManifest(target_width=1080, target_height=1920, fps=30)
        manifest.add_background_video("assets/bg.mp4", duration=10.0)
        manifest.add_subtitles_ass("assets/subs.ass", duration=10.0)
        manifest.add_voiceover("assets/speech.wav", duration=10.0)
        manifest.add_background_music("assets/bgm.mp3", duration=10.0, volume=0.2)

        cmd = manifest.compile_ffmpeg_command("output.mp4")
        cmd_str = " ".join(cmd)

        self.assertIn("-filter_complex", cmd_str)
        self.assertIn("scale=1080:1920", cmd_str)
        self.assertIn("crop=1080:1920", cmd_str)
        self.assertIn("ass=", cmd_str)
        self.assertIn("amix=inputs=2", cmd_str)
        self.assertIn("-pix_fmt yuv420p", cmd_str)
        self.assertIn("-movflags +faststart", cmd_str)
        self.assertIn("output.mp4", cmd_str)

    @patch("services.path_security.os.path.exists", return_value=True)
    def test_facts_engine_timeline_binding(self, mock_exists):
        script_data = {
            "title": "Quantum Physics",
            "scenes": [
                {"scene_number": 1, "duration": 5.0, "narration": "Fact one"},
                {"scene_number": 2, "duration": 6.0, "narration": "Fact two"},
            ]
        }
        manifest = FactsStoryEngine.create_facts_timeline_manifest(
            script_data=script_data,
            voiceover_path="assets/speech.wav",
            background_video_path="assets/bg.mp4",
            bgm_path="assets/music.mp3",
        )
        self.assertIsInstance(manifest, TimelineManifest)
        self.assertEqual(manifest.total_duration(), 11.0)

    def test_chained_atempo_extreme_factors(self):
        # 4.5x speedup -> atempo=2.0,atempo=2.0,atempo=1.1250
        chain_4_5 = build_atempo_filter_chain(4.5)
        self.assertEqual(chain_4_5.count("atempo=2.0"), 2)
        self.assertIn("atempo=1.1250", chain_4_5)

        # 0.22x slowdown -> atempo=0.5,atempo=0.5,atempo=0.8800
        chain_0_22 = build_atempo_filter_chain(0.22)
        self.assertEqual(chain_0_22.count("atempo=0.5"), 2)
        self.assertIn("atempo=0.8800", chain_0_22)

    @patch("os.path.exists", return_value=True)
    @patch("services.audio_tempo_guard.get_audio_duration", return_value=75.0)
    @patch("services.audio_tempo_guard.speedup_audio")
    def test_apply_shorts_tempo_guard(self, mock_speedup, mock_dur, mock_exists):
        from services.audio_tempo_guard import apply_shorts_tempo_guard
        mock_speedup.return_value = "guarded.wav"
        res = apply_shorts_tempo_guard("long_voice.wav", "guarded.wav", max_duration=57.0)
        self.assertEqual(res, "guarded.wav")
        self.assertTrue(mock_speedup.called)
        target_d = mock_speedup.call_args[1]["target_duration"]
        self.assertAlmostEqual(target_d, 57.0 * 0.98, places=2)


if __name__ == "__main__":
    unittest.main()
