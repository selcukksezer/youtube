"""
Unit tests for visuals.face_reframe (Plan Section 33 - P1 Package).
Verifies face detection fallback, short-path resolution, normalized center calculation,
and 9:16 target horizontal crop coordinate computation.
"""
import os
import unittest
import numpy as np
import cv2

from visuals.face_reframe import (
    _get_short_path,
    detect_face_center_x,
    compute_face_crop_x,
)


class TestFaceReframe(unittest.TestCase):
    def setUp(self):
        self.temp_files = []

    def tearDown(self):
        for f in self.temp_files:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except OSError:
                    pass

    def test_short_path_resolution(self):
        """Short path helper handles existing path safely without error."""
        cur_dir = os.path.abspath(".")
        res = _get_short_path(cur_dir)
        self.assertIsInstance(res, str)
        self.assertTrue(len(res) > 0)

    def test_detect_face_center_nonexistent(self):
        """Returns None safely for non-existent file."""
        self.assertIsNone(detect_face_center_x("non_existent_file_xyz_123.mp4"))

    def test_detect_face_on_synthetic_blank_image(self):
        """Returns None when no face exists in image."""
        img = np.zeros((720, 1280, 3), dtype=np.uint8)
        tmp_path = os.path.abspath("test_blank_frame.jpg")
        cv2.imwrite(tmp_path, img)
        self.temp_files.append(tmp_path)

        center = detect_face_center_x(tmp_path)
        self.assertIsNone(center)

    def test_compute_face_crop_x_aspect_ratio_checks(self):
        """Already vertical source returns None since no horizontal crop is needed."""
        # Vertical source 1080x1920
        res = compute_face_crop_x("dummy.jpg", 1080, 1920, 1080, 1920)
        self.assertIsNone(res)

        # Invalid dimensions return None
        self.assertIsNone(compute_face_crop_x("dummy.jpg", 0, 1920))
        self.assertIsNone(compute_face_crop_x("dummy.jpg", 1920, 0))

    def test_compute_face_crop_x_clamping_and_modulo(self):
        """With synthetic center detection mocked, crop coordinates are correctly clamped and even."""
        from unittest.mock import patch

        # 1920x1080 landscape image, 9:16 target (crop width = 1080 * 9 / 16 = 607.5 -> 606)
        # Face centered near right edge (x=0.95 -> 1824px)
        with patch("visuals.face_reframe.detect_face_center_x", return_value=0.95):
            crop_x = compute_face_crop_x("dummy.jpg", 1920, 1080, 1080, 1920)
            self.assertIsNotNone(crop_x)
            # Must be even number
            self.assertEqual(crop_x % 2, 0)
            # Must not exceed src_w - crop_w
            self.assertTrue(crop_x <= 1920 - 606)

        # Face centered near left edge (x=0.05 -> 96px)
        with patch("visuals.face_reframe.detect_face_center_x", return_value=0.05):
            crop_x = compute_face_crop_x("dummy.jpg", 1920, 1080, 1080, 1920)
            self.assertIsNotNone(crop_x)
            self.assertEqual(crop_x % 2, 0)
            self.assertEqual(crop_x, 0)  # Clamped to 0

        # Face in center (x=0.50 -> 960px)
        with patch("visuals.face_reframe.detect_face_center_x", return_value=0.50):
            crop_x = compute_face_crop_x("dummy.jpg", 1920, 1080, 1080, 1920)
            self.assertIsNotNone(crop_x)
            self.assertEqual(crop_x % 2, 0)
            # Expect around (960 - 303) = 657 -> even 656
            self.assertTrue(650 <= crop_x <= 660)

    def test_face_cover_crop_x_translates_source_pixels_after_scale(self):
        """Graph crop runs after scale, so source x must be scaled first."""
        from unittest.mock import MagicMock, patch
        from render.ffmpeg_graph import face_cover_crop_x

        media = os.path.abspath("test_face_source.mp4")
        open(media, "wb").close()
        self.temp_files.append(media)
        capture = MagicMock()
        capture.isOpened.return_value = True
        capture.get.side_effect = lambda prop: 1920 if prop == cv2.CAP_PROP_FRAME_WIDTH else 1080

        with patch("cv2.VideoCapture", return_value=capture), patch(
            "visuals.face_reframe.compute_face_crop_x", return_value=640
        ):
            crop_x = face_cover_crop_x(media, 1080, 1920)

        # 1920x1080 -> 3412x1920 post-scale. 640 source pixels become ~1138.
        self.assertEqual(crop_x, 1138)
        self.assertNotEqual(crop_x, 640)


if __name__ == "__main__":
    unittest.main()
