"""
Tests for Master Plan Section 33.3 - P1: Face-Centered 9:16 Vertical Reframing.
Verifies:
1. VideoRenderRequest supports enable_face_center defaulting to False.
2. When enable_face_center=False, landscape sources produce standard fit-and-fill (boxblur).
3. When enable_face_center=True and face detected, produces 9:16 crop with computed x offset.
4. When enable_face_center=True but no face detected or OpenCV fails, safely falls back to fit-and-fill.
5. compose_via_director passes enable_face_center to render_with_ffmpeg_graph.
"""
import os
import unittest
from unittest.mock import patch, MagicMock

from api_models import VideoRenderRequest
from render.ffmpeg_graph import compose_via_director, render_with_ffmpeg_graph


class TestChapter33P1FaceReframe(unittest.TestCase):

    def test_pydantic_video_render_request_has_enable_face_center(self):
        """VideoRenderRequest must have enable_face_center defaulting to False."""
        req_default = VideoRenderRequest(keyword="test")
        self.assertFalse(req_default.enable_face_center)

        req_enabled = VideoRenderRequest(keyword="test", enable_face_center=True)
        self.assertTrue(req_enabled.enable_face_center)

    @patch("imageio_ffmpeg.get_ffmpeg_exe", return_value="ffmpeg")
    @patch("render.ffmpeg_graph._probe_duration", return_value=5.0)
    @patch("render.ffmpeg_graph._probe_is_landscape", return_value=True)
    @patch("render.ffmpeg_graph.subprocess.Popen")
    @patch("render.ffmpeg_graph.subprocess.run")
    @patch("render.ffmpeg_graph.os.path.exists")
    def test_when_enable_face_center_false_produces_fit_fill(self, mock_exists, mock_run, mock_popen, mock_land, mock_dur, mock_ff):
        """When enable_face_center=False, landscape source uses fit-and-fill boxblur, same command as baseline."""
        mock_exists.return_value = True
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout.readline.return_value = ""
        mock_proc.stderr.readline.return_value = ""
        mock_proc.communicate.return_value = ("", "")
        mock_proc.poll.return_value = 0
        mock_popen.return_value = mock_proc

        clips = [{"path": "landscape_video.mp4", "duration": 5.0}]
        captured_cmds = []

        def fake_popen(cmd, *args, **kwargs):
            captured_cmds.append(cmd)
            return mock_proc

        mock_popen.side_effect = fake_popen

        render_with_ffmpeg_graph(
            clips=clips,
            audio_path="audio.mp3",
            output_path="out.mp4",
            enable_face_center=False,
            progress_callback=lambda p, m: None,
        )

        self.assertTrue(len(captured_cmds) > 0)
        cmd = captured_cmds[0]
        filter_complex = ""
        for i, arg in enumerate(cmd):
            if arg == "-filter_complex":
                filter_complex = cmd[i + 1]
                break

        # Must have fit & fill boxblur
        self.assertIn("boxblur=25:5", filter_complex)
        self.assertIn("bg_blur_0", filter_complex)

    @patch("imageio_ffmpeg.get_ffmpeg_exe", return_value="ffmpeg")
    @patch("render.ffmpeg_graph._probe_duration", return_value=5.0)
    @patch("render.ffmpeg_graph._probe_is_landscape", return_value=True)
    @patch("render.ffmpeg_graph.face_cover_crop_x", return_value=640)
    @patch("render.ffmpeg_graph.subprocess.Popen")
    @patch("render.ffmpeg_graph.subprocess.run")
    @patch("render.ffmpeg_graph.os.path.exists")
    def test_when_enable_face_center_true_and_face_found_produces_face_crop(self, mock_exists, mock_run, mock_popen, mock_face_crop, mock_land, mock_dur, mock_ff):
        """When enable_face_center=True and face detected, produces 9:16 crop:x=640 without boxblur."""
        mock_exists.return_value = True
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout.readline.return_value = ""
        mock_proc.stderr.readline.return_value = ""
        mock_proc.communicate.return_value = ("", "")
        mock_proc.poll.return_value = 0
        mock_popen.return_value = mock_proc

        clips = [{"path": "landscape_interview.mp4", "duration": 5.0}]
        captured_cmds = []

        def fake_popen(cmd, *args, **kwargs):
            captured_cmds.append(cmd)
            return mock_proc

        mock_popen.side_effect = fake_popen

        render_with_ffmpeg_graph(
            clips=clips,
            audio_path="audio.mp3",
            output_path="out.mp4",
            enable_face_center=True,
            progress_callback=lambda p, m: None,
        )

        mock_face_crop.assert_called_once()
        self.assertTrue(len(captured_cmds) > 0)
        cmd = captured_cmds[0]
        filter_complex = ""
        for i, arg in enumerate(cmd):
            if arg == "-filter_complex":
                filter_complex = cmd[i + 1]
                break

        # Should NOT use boxblur fit-and-fill
        self.assertNotIn("boxblur=25:5", filter_complex)
        # Should contain crop with x=640
        self.assertIn("crop=1080:1920:x=640", filter_complex)

    @patch("imageio_ffmpeg.get_ffmpeg_exe", return_value="ffmpeg")
    @patch("render.ffmpeg_graph._probe_duration", return_value=5.0)
    @patch("render.ffmpeg_graph._probe_is_landscape", return_value=True)
    @patch("render.ffmpeg_graph.face_cover_crop_x", return_value=None)
    @patch("render.ffmpeg_graph.subprocess.Popen")
    @patch("render.ffmpeg_graph.subprocess.run")
    @patch("render.ffmpeg_graph.os.path.exists")
    def test_when_enable_face_center_true_but_no_face_falls_back_to_fit_fill(self, mock_exists, mock_run, mock_popen, mock_face_crop, mock_land, mock_dur, mock_ff):
        """When enable_face_center=True but no face found, safely falls back to fit-and-fill boxblur."""
        mock_exists.return_value = True
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout.readline.return_value = ""
        mock_proc.stderr.readline.return_value = ""
        mock_proc.communicate.return_value = ("", "")
        mock_proc.poll.return_value = 0
        mock_popen.return_value = mock_proc

        clips = [{"path": "landscape_scenery_no_face.mp4", "duration": 5.0}]
        captured_cmds = []

        def fake_popen(cmd, *args, **kwargs):
            captured_cmds.append(cmd)
            return mock_proc

        mock_popen.side_effect = fake_popen

        render_with_ffmpeg_graph(
            clips=clips,
            audio_path="audio.mp3",
            output_path="out.mp4",
            enable_face_center=True,
            progress_callback=lambda p, m: None,
        )

        mock_face_crop.assert_called_once()
        self.assertTrue(len(captured_cmds) > 0)
        cmd = captured_cmds[0]
        filter_complex = ""
        for i, arg in enumerate(cmd):
            if arg == "-filter_complex":
                filter_complex = cmd[i + 1]
                break

        # Fallback to fit-and-fill
        self.assertIn("boxblur=25:5", filter_complex)

    @patch("render.ffmpeg_graph.render_with_ffmpeg_graph")
    def test_compose_via_director_passes_enable_face_center(self, mock_render):
        mock_render.return_value = "rendered.mp4"
        clips = [{"path": "dummy.mp4", "duration": 3.0}]
        compose_via_director(
            clips=clips,
            audio_path="dummy.mp3",
            word_timings=[],
            output_path="out.mp4",
            enable_face_center=True,
        )
        mock_render.assert_called_once()
        _, kwargs = mock_render.call_args
        self.assertTrue(kwargs.get("enable_face_center"))


if __name__ == "__main__":
    unittest.main()
