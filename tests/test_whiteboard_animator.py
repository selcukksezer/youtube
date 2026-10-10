import hashlib
import os
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

from services.whiteboard_animator import (
    animate_whiteboard_clip,
    create_whiteboard_scene_clip,
    draw_procedural_whiteboard_sketch,
)


class WhiteboardAnimatorTests(unittest.TestCase):
    def test_procedural_sketches_are_scene_specific(self):
        with tempfile.TemporaryDirectory() as directory:
            phone_path = os.path.join(directory, "phone.jpg")
            wedding_path = os.path.join(directory, "wedding.jpg")

            self.assertTrue(
                draw_procedural_whiteboard_sketch(
                    "Telefon ekranında saklanan mesajı gördüm.",
                    phone_path,
                    narration="Telefonundaki mesaj, bana anlatılanlarla uyuşmuyordu.",
                )
            )
            self.assertTrue(
                draw_procedural_whiteboard_sketch(
                    "Düğün töreni ve karar anı.",
                    wedding_path,
                    narration="Düğünü erteleyip önce gerçeği öğrenmeye karar verdim.",
                )
            )

            with Image.open(phone_path) as image:
                self.assertEqual(image.size, (540, 960))
            with open(phone_path, "rb") as phone_file, open(wedding_path, "rb") as wedding_file:
                self.assertNotEqual(
                    hashlib.sha256(phone_file.read()).digest(),
                    hashlib.sha256(wedding_file.read()).digest(),
                )

    def test_offline_scene_uses_procedural_narration_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            output_path = os.path.join(directory, "scene.mp4")
            with patch("services.whiteboard_animator.generate_whiteboard_sketch_image", return_value=False), \
                 patch("services.whiteboard_animator.draw_procedural_whiteboard_sketch", return_value=True) as draw, \
                 patch("services.whiteboard_animator.animate_whiteboard_clip", return_value=True):
                result = create_whiteboard_scene_clip(
                    "Close-up of a phone with a hidden message.",
                    output_path,
                    scene_index=2,
                    narration="Telefonumdaki gizli mesaj her şeyi değiştirdi.",
                )

        self.assertEqual(result, output_path)
        self.assertEqual(draw.call_args.kwargs["narration"], "Telefonumdaki gizli mesaj her şeyi değiştirdi.")

    def test_animation_uses_selected_transition(self):
        with tempfile.TemporaryDirectory() as directory:
            sketch = os.path.join(directory, "sketch.jpg")
            output = os.path.join(directory, "scene.mp4")
            with open(sketch, "wb") as handle:
                handle.write(b"sketch")
            captured = {}

            def fake_run(command, **_kwargs):
                captured["filter"] = command[command.index("-filter_complex") + 1]
                with open(output, "wb") as handle:
                    handle.write(b"video" * 300)
                return type("Result", (), {"returncode": 0})()

            with patch("services.whiteboard_animator.ensure_marker_hand_asset", return_value=sketch), \
                 patch("services.whiteboard_animator.subprocess.run", side_effect=fake_run):
                self.assertTrue(
                    animate_whiteboard_clip(
                        sketch,
                        output,
                        duration=4.0,
                        transition_style="wiperight",
                    )
                )

            self.assertIn("xfade=transition=wiperight", captured["filter"])


if __name__ == "__main__":
    unittest.main()
