"""
Tests for Master Plan Section 33.3 - P6: Dedicated Emphasis Overlay Layer (emphasis.ass).
Verifies:
1. VideoRenderRequest supports enable_emphasis_card defaulting to False.
2. create_emphasis_overlay_ass enforces max 3 items budget (4 numbers -> 3 dialogues).
3. Duration contract: each emphasis item is between 0.8s and 1.4s.
4. Spoken subtitles stay clean without secondary upper-layer annotations.
5. Quality gate validate_emphasis_budget enforces budget <= 3.
6. When enable_emphasis_card=False, FFmpeg graph produces a single subtitles= filter.
7. When enable_emphasis_card=True, FFmpeg graph burns both speech subtitles and emphasis.ass.
8. compose_via_director wires enable_emphasis_card and emphasis_ass_path properly.
"""
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from api_models import VideoRenderRequest
from director.quality_gate import validate_emphasis_budget
from render.ffmpeg_graph import compose_via_director, render_with_ffmpeg_graph
from subtitle_generator import create_emphasis_overlay_ass, create_karaoke_subtitles


class TestChapter33P6EmphasisOverlay(unittest.TestCase):

    def test_pydantic_video_render_request_has_enable_emphasis_card(self):
        """VideoRenderRequest must have enable_emphasis_card defaulting to False."""
        req_default = VideoRenderRequest(keyword="test")
        self.assertFalse(req_default.enable_emphasis_card)

        req_enabled = VideoRenderRequest(keyword="test", enable_emphasis_card=True)
        self.assertTrue(req_enabled.enable_emphasis_card)

    def test_quality_gate_emphasis_budget_validation(self):
        """Quality gate permits <= 3 emphasis overlays and rejects > 3."""
        self.assertTrue(validate_emphasis_budget(0))
        self.assertTrue(validate_emphasis_budget(1))
        self.assertTrue(validate_emphasis_budget(3))
        self.assertFalse(validate_emphasis_budget(4))
        self.assertFalse(validate_emphasis_budget(10))

    def test_emphasis_ass_budget_and_duration_contract(self):
        """4 numbers script must produce strictly 3 emphasis items, each 0.8s - 1.4s long."""
        words = [
            {"text": "Burada", "offset": 0.5, "duration": 0.4},
            {"text": "10", "offset": 1.2, "duration": 0.2},       # Candidate 1 (number)
            {"text": "adımda", "offset": 1.5, "duration": 0.4},
            {"text": "50", "offset": 4.5, "duration": 0.3},       # Candidate 2 (number)
            {"text": "farklı", "offset": 4.9, "duration": 0.4},
            {"text": "100", "offset": 8.0, "duration": 0.5},      # Candidate 3 (number)
            {"text": "sonuç", "offset": 8.6, "duration": 0.4},
            {"text": "500", "offset": 12.0, "duration": 0.3},     # Candidate 4 (number, must be dropped by budget=3)
        ]
        with tempfile.TemporaryDirectory() as tmp_dir:
            emp_ass = os.path.join(tmp_dir, "emphasis.ass")
            res = create_emphasis_overlay_ass(words, emp_ass, target_w=1080, target_h=1920)
            self.assertEqual(res, emp_ass)
            self.assertTrue(os.path.isfile(emp_ass))

            with open(emp_ass, "r", encoding="utf-8") as f:
                content = f.read()

            dialogues = [line for line in content.splitlines() if line.startswith("Dialogue:")]
            # Acceptance criterion: exactly 3 items when 4 numbers exist
            self.assertEqual(len(dialogues), 3, "Strict budget cap of 3 emphasis overlays")

            # Verify duration contract (0.8s - 1.4s)
            for d in dialogues:
                parts = d.split(",")
                start_str, end_str = parts[1], parts[2]
                # Parse timestamp mm:ss.xx or h:mm:ss.xx
                def to_sec(ts):
                    segs = ts.split(":")
                    if len(segs) == 3:
                        return int(segs[0]) * 3600 + int(segs[1]) * 60 + float(segs[2])
                    return int(segs[0]) * 60 + float(segs[1])

                dur = to_sec(end_str) - to_sec(start_str)
                self.assertGreaterEqual(dur, 0.79, "Minimum emphasis duration >= 0.8s")
                self.assertLessEqual(dur, 1.45, "Maximum emphasis duration <= 1.4s")
                # Must be located in upper safe area
                self.assertIn(r"\an5\pos(540,", d)

    def test_budget_argument_cannot_raise_three_item_cap(self):
        words = [
            {"text": str(i), "offset": float(i * 2), "duration": 0.4}
            for i in range(1, 6)
        ]
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = os.path.join(tmp_dir, "emphasis.ass")
            self.assertEqual(create_emphasis_overlay_ass(words, path, budget=99), path)
            dialogues = [line for line in open(path, encoding="utf-8") if line.startswith("Dialogue:")]
            self.assertEqual(len(dialogues), 3)
            self.assertIsNone(create_emphasis_overlay_ass(words, os.path.join(tmp_dir, "off.ass"), budget=0))

    def test_clean_speech_subtitles_when_emphasis_disabled(self):
        """Standard create_karaoke_subtitles produces clean speech subtitles without embedded emphasis."""
        words = [
            {"text": "Toplam", "offset": 1.0, "duration": 0.3},
            {"text": "100", "offset": 1.4, "duration": 0.5},
            {"text": "kişi", "offset": 2.0, "duration": 0.3},
        ]
        with tempfile.TemporaryDirectory() as tmp_dir:
            main_ass = os.path.join(tmp_dir, "subs.ass")
            create_karaoke_subtitles(words, main_ass)
            with open(main_ass, "r", encoding="utf-8") as f:
                content = f.read()
            # Dialogue: 1,... upper annotation should NOT be present in speech subs
            dialogues = [line for line in content.splitlines() if line.startswith("Dialogue:")]
            for d in dialogues:
                self.assertFalse(d.startswith("Dialogue: 1,"), "Speech subtitles must stay clean")

    @patch("imageio_ffmpeg.get_ffmpeg_exe", return_value="ffmpeg")
    @patch("render.ffmpeg_graph._probe_duration", return_value=5.0)
    @patch("render.ffmpeg_graph._probe_is_landscape", return_value=False)
    @patch("render.ffmpeg_graph.subprocess.Popen")
    @patch("render.ffmpeg_graph.subprocess.run")
    @patch("render.ffmpeg_graph.os.path.exists")
    def test_ffmpeg_graph_when_enable_emphasis_false_single_subtitles_filter(self, mock_exists, mock_run, mock_popen, mock_land, mock_dur, mock_ff):
        """When enable_emphasis_card=False, only single main subtitles filter is rendered."""
        mock_exists.return_value = True
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout.readline.return_value = ""
        mock_proc.stderr.readline.return_value = ""
        mock_proc.communicate.return_value = ("", "")
        mock_proc.poll.return_value = 0
        mock_popen.return_value = mock_proc

        clips = [{"path": "clip1.mp4", "duration": 5.0}]
        captured_cmds = []

        def fake_popen(cmd, *args, **kwargs):
            captured_cmds.append(cmd)
            return mock_proc

        mock_popen.side_effect = fake_popen

        render_with_ffmpeg_graph(
            clips=clips,
            audio_path="audio.mp3",
            output_path="out.mp4",
            ass_path="main_subs.ass",
            emphasis_ass_path="emphasis.ass",
            enable_emphasis_card=False,
            progress_callback=lambda p, m: None,
        )

        self.assertTrue(len(captured_cmds) > 0)
        cmd = captured_cmds[0]
        filter_complex = ""
        for i, arg in enumerate(cmd):
            if arg == "-filter_complex":
                filter_complex = cmd[i + 1]
                break

        # Only one subtitles filter
        self.assertEqual(filter_complex.count("subtitles="), 1)
        self.assertNotIn("vemp", filter_complex)

    @patch("imageio_ffmpeg.get_ffmpeg_exe", return_value="ffmpeg")
    @patch("render.ffmpeg_graph._probe_duration", return_value=5.0)
    @patch("render.ffmpeg_graph._probe_is_landscape", return_value=False)
    @patch("render.ffmpeg_graph.subprocess.Popen")
    @patch("render.ffmpeg_graph.subprocess.run")
    @patch("render.ffmpeg_graph.os.path.exists")
    def test_ffmpeg_graph_when_enable_emphasis_true_dual_subtitles_filter(self, mock_exists, mock_run, mock_popen, mock_land, mock_dur, mock_ff):
        """When enable_emphasis_card=True and file exists, renders both main and secondary emphasis layer."""
        mock_exists.return_value = True
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout.readline.return_value = ""
        mock_proc.stderr.readline.return_value = ""
        mock_proc.communicate.return_value = ("", "")
        mock_proc.poll.return_value = 0
        mock_popen.return_value = mock_proc

        clips = [{"path": "clip1.mp4", "duration": 5.0}]
        captured_cmds = []

        def fake_popen(cmd, *args, **kwargs):
            captured_cmds.append(cmd)
            return mock_proc

        mock_popen.side_effect = fake_popen

        render_with_ffmpeg_graph(
            clips=clips,
            audio_path="audio.mp3",
            output_path="out.mp4",
            ass_path="main_subs.ass",
            emphasis_ass_path="emphasis.ass",
            enable_emphasis_card=True,
            progress_callback=lambda p, m: None,
        )

        self.assertTrue(len(captured_cmds) > 0)
        cmd = captured_cmds[0]
        filter_complex = ""
        for i, arg in enumerate(cmd):
            if arg == "-filter_complex":
                filter_complex = cmd[i + 1]
                break

        # Two subtitles filters: main + emphasis
        self.assertEqual(filter_complex.count("subtitles="), 2)
        self.assertIn("vemp", filter_complex)

    @patch("render.ffmpeg_graph.render_with_ffmpeg_graph")
    def test_compose_via_director_passes_emphasis_card(self, mock_render):
        mock_render.return_value = "rendered.mp4"
        clips = [{"path": "dummy.mp4", "duration": 3.0}]
        compose_via_director(
            clips=clips,
            audio_path="dummy.mp3",
            word_timings=[],
            output_path="out.mp4",
            enable_emphasis_card=True,
            emphasis_ass_path="emp.ass",
        )
        mock_render.assert_called_once()
        _, kwargs = mock_render.call_args
        self.assertTrue(kwargs.get("enable_emphasis_card"))
        self.assertEqual(kwargs.get("emphasis_ass_path"), "emp.ass")


if __name__ == "__main__":
    unittest.main()
