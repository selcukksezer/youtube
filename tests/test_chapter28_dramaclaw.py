"""
Tests for Chapter 28.18 / Section 2.2 (Madde 17):
reference_repos2/dramaclaw evolution:
- services/scene_prerequisites.py: ScenePrerequisiteGate, preflight asset validation, ScenePrerequisiteError
- director/story_analyzer.py: StoryArcAnalyzer, dramatic tension curve, pacing metrics
- render/fit_and_fill.py: build_fit_and_fill_blur_filter, is_landscape_aspect_ratio
"""

import os
import tempfile
import unittest

from services.scene_prerequisites import (
    ScenePrerequisiteGate,
    ScenePrerequisiteError,
    GLOBAL_PREREQUISITE_GATE,
)
from director.story_analyzer import (
    StoryArcAnalyzer,
    GLOBAL_STORY_ANALYZER,
)
from render.fit_and_fill import (
    build_fit_and_fill_blur_filter,
    is_landscape_aspect_ratio,
)


class TestDramaClawScenePrerequisites(unittest.TestCase):
    def test_missing_assets_detected(self):
        scene = {
            "visual_path": None,
            "audio_path": "nonexistent_audio.mp3",
            "duration": 0.0,
        }
        errors = ScenePrerequisiteGate.validate_scene(0, scene)
        self.assertGreaterEqual(len(errors), 3)
        codes = [e["code"] for e in errors]
        self.assertIn("MISSING_VISUAL_ASSET", codes)
        self.assertIn("AUDIO_FILE_NOT_FOUND", codes)
        self.assertIn("INVALID_DURATION", codes)

    def test_valid_scene_passes(self):
        # Create temp dummy assets
        v_fd, v_path = tempfile.mkstemp(suffix=".jpg")
        os.write(v_fd, b"IMAGE_DATA")
        os.close(v_fd)

        a_fd, a_path = tempfile.mkstemp(suffix=".wav")
        os.write(a_fd, b"AUDIO_DATA")
        os.close(a_fd)

        try:
            scene = {
                "visual_path": v_path,
                "audio_path": a_path,
                "duration": 4.5,
            }
            errors = ScenePrerequisiteGate.validate_scene(0, scene)
            self.assertEqual(len(errors), 0)

            # Test check_prerequisites_or_raise does not raise
            ScenePrerequisiteGate.check_prerequisites_or_raise([scene])
        finally:
            if os.path.exists(v_path):
                os.remove(v_path)
            if os.path.exists(a_path):
                os.remove(a_path)

    def test_raise_on_failure(self):
        scene = {"visual_path": "missing.jpg", "audio_path": "missing.wav", "duration": 5.0}
        with self.assertRaises(ScenePrerequisiteError):
            ScenePrerequisiteGate.check_prerequisites_or_raise([scene])


class TestDramaClawStoryAnalyzer(unittest.TestCase):
    def test_hook_and_climax_tension_calculation(self):
        script = [
            "Bu inanılmaz gizli gerçeği hiç kimse bilmiyordu!",
            "Tarih boyunca bu olay hep göz ardı edildi.",
            "İşte o an patlama gerçekleşti ve her şey yok oldu!",
            "Artık hiçbir şey eskisi gibi olmayacak.",
        ]
        metrics = StoryArcAnalyzer.analyze_story_arc(script)
        self.assertEqual(len(metrics), 4)

        # Scene 0 is hook
        self.assertEqual(metrics[0].beat_category, "hook")
        self.assertGreater(metrics[0].tension_score, 0.4)

        # Scene 2 contains high-tension words ("patlama", "yok oldu") and exclamation
        self.assertIn(metrics[2].beat_category, ("climax", "escalation"))
        self.assertGreater(metrics[2].tension_score, 0.6)

        # Scene 3 is resolution
        self.assertEqual(metrics[3].beat_category, "resolution")


class TestDramaClawFitAndFillCompositor(unittest.TestCase):
    def test_landscape_aspect_ratio_detector(self):
        self.assertTrue(is_landscape_aspect_ratio(1920, 1080))
        self.assertFalse(is_landscape_aspect_ratio(1080, 1920))
        self.assertFalse(is_landscape_aspect_ratio(1080, 1080))

    def test_build_fit_and_fill_blur_filter(self):
        filter_str = build_fit_and_fill_blur_filter(
            input_label="[0:v]",
            output_label="[vout]",
            target_width=1080,
            target_height=1920,
            blur_strength=25,
            blur_power=5,
        )
        self.assertIn("split=2[fg_raw][bg_raw]", filter_str)
        self.assertIn("scale=1080:1920:force_original_aspect_ratio=increase", filter_str)
        self.assertIn("boxblur=25:5[bg_blur]", filter_str)
        self.assertIn("scale=1080:-1:force_original_aspect_ratio=decrease[fg_fit]", filter_str)
        self.assertIn("[bg_blur][fg_fit]overlay=(W-w)/2:(H-h)/2[vout]", filter_str)


if __name__ == "__main__":
    unittest.main()
