import os
import tempfile
import unittest

from services.scene_prerequisites import (
    ScenePrerequisiteError,
    ScenePrerequisiteGate,
)


class TestScenePrerequisiteRenderGate(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.visual_path = os.path.join(self.temp_dir.name, "scene.mp4")
        self.audio_path = os.path.join(self.temp_dir.name, "narration.wav")
        with open(self.visual_path, "wb") as visual_file:
            visual_file.write(b"video")
        with open(self.audio_path, "wb") as audio_file:
            audio_file.write(b"audio")

    def test_complete_render_assets_pass_before_compose(self):
        ScenePrerequisiteGate.check_render_prerequisites_or_raise(
            [{"path": self.visual_path, "duration": 4.5}],
            self.audio_path,
        )

    def test_missing_visual_and_narration_are_reported(self):
        with self.assertRaises(ScenePrerequisiteError) as raised:
            ScenePrerequisiteGate.check_render_prerequisites_or_raise(
                [{"path": os.path.join(self.temp_dir.name, "missing.mp4"), "duration": 4.5}],
                os.path.join(self.temp_dir.name, "missing.wav"),
            )

        codes = {error["code"] for error in raised.exception.errors}
        self.assertIn("VISUAL_FILE_NOT_FOUND", codes)
        self.assertIn("AUDIO_FILE_NOT_FOUND", codes)

    def test_invalid_duration_values_are_reported_not_raised(self):
        errors = ScenePrerequisiteGate.validate_scene(
            0,
            {"visual_path": self.visual_path, "duration": "not-a-duration"},
        )
        self.assertIn("INVALID_DURATION", {error["code"] for error in errors})

    def test_nan_duration_is_rejected(self):
        errors = ScenePrerequisiteGate.validate_scene(
            0,
            {"visual_path": self.visual_path, "duration": float("nan")},
        )
        self.assertIn("INVALID_DURATION", {error["code"] for error in errors})

    def test_empty_narration_audio_is_rejected(self):
        with open(self.audio_path, "wb"):
            pass
        with self.assertRaises(ScenePrerequisiteError) as raised:
            ScenePrerequisiteGate.check_render_prerequisites_or_raise(
                [{"path": self.visual_path, "duration": 4.5}],
                self.audio_path,
            )
        self.assertIn(
            "EMPTY_AUDIO_FILE",
            {error["code"] for error in raised.exception.errors},
        )


if __name__ == "__main__":
    unittest.main()
