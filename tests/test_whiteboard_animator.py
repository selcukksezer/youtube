import hashlib
import os
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw, ImageFont

from services.whiteboard_animator import (
    _whiteboard_theme,
    _whiteboard_hand_motion,
    _wrap_whiteboard_text,
    animate_whiteboard_clip,
    create_whiteboard_scene_clip,
    draw_procedural_whiteboard_sketch,
)


class WhiteboardAnimatorTests(unittest.TestCase):
    def test_theme_detection_uses_normalized_whole_words(self):
        self.assertEqual(_whiteboard_theme("This is only a story about a decision"), "general")
        self.assertEqual(_whiteboard_theme("İş yatırımı ve finansal karar"), "finance")
        self.assertEqual(_whiteboard_theme("Telefonumdaki gizli mesaj"), "phone")

    def test_wrapped_text_fits_width_and_truncates_long_words(self):
        image = Image.new("RGB", (120, 40), "white")
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default()

        lines = _wrap_whiteboard_text(
            draw,
            "Averylongunbrokenword that must fit on this small board",
            font,
            max_width=90,
            max_lines=2,
        )

        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[-1].endswith("…"))
        for line in lines:
            bounds = draw.textbbox((0, 0), line, font=font)
            self.assertLessEqual(bounds[2] - bounds[0], 90)

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
            self.assertIn("[2:v]scale=180:270,hflip[hand]", captured["filter"])

    def test_marker_motion_follows_linear_wipe_direction(self):
        right_filter, right_x, _, right_enable = _whiteboard_hand_motion(
            "wiperight", 540, 960, 0.15, 2.2
        )
        down_filter, down_x, down_y, down_enable = _whiteboard_hand_motion(
            "wipedown", 540, 960, 0.15, 2.2
        )
        radial_filter, _, _, radial_enable = _whiteboard_hand_motion(
            "radial", 540, 960, 0.15, 2.2
        )

        self.assertIn("hflip", right_filter)
        self.assertIn("496.8 - (t - 0.15) / 2.20 * 496.8", right_x)
        self.assertIn("between(t,", right_enable)
        self.assertIn("transpose=1", down_filter)
        self.assertNotIn("(t - 0.15) / 2.20", down_x)
        self.assertIn("(t - 0.15) / 2.20 * 883.2", down_y)
        self.assertIn("between(t,", down_enable)
        self.assertEqual(radial_filter, "scale=180:270")
        self.assertEqual(radial_enable, "0")


if __name__ == "__main__":
    unittest.main()
