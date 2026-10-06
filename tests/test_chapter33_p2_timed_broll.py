"""
Tests for Master Plan Section 33.3 - P2: Timed B-roll in single FFmpeg graph.
Verifies:
1. enable_broll=False produces zero B-roll overlay inputs and zero overlay=between filters.
2. enable_broll=True places timed B-roll in a single filter_complex with max 3 non-overlapping overlays.
3. Overlays satisfy the 2.0s - 3.2s duration contract.
4. VideoRenderRequest supports enable_broll_insert (default False).
5. compose_via_director passes enable_broll_insert to render_with_ffmpeg_graph.
"""
import os
import unittest
from unittest.mock import patch, MagicMock

from api_models import VideoRenderRequest
from render.ffmpeg_graph import _plan_cutaways, compose_via_director, render_with_ffmpeg_graph


class TestChapter33P2TimedBroll(unittest.TestCase):

    def test_plan_cutaways_duration_and_non_overlapping_constraints(self):
        """Overlay duration must be between 2.0s and 3.2s, non-overlapping, max 3."""
        tmp_clips = [
            {"path": __file__, "duration": 5.0, "broll_inserts": [
                {"path": __file__, "start": 1.0, "end": 4.5}  # raw 3.5s -> should cap to 3.2s
            ]},
            {"path": __file__, "duration": 5.0, "broll_inserts": [
                {"path": __file__, "start": 3.0, "end": 4.0}  # overlaps with first -> should shift or skip
            ]},
            {"path": __file__, "duration": 5.0, "broll_inserts": [
                {"path": __file__, "start": 6.0, "end": 8.5}  # 2.5s -> valid
            ]},
            {"path": __file__, "duration": 5.0, "broll_inserts": [
                {"path": __file__, "start": 10.0, "end": 12.5}  # valid
            ]},
            {"path": __file__, "duration": 5.0, "broll_inserts": [
                {"path": __file__, "start": 14.0, "end": 16.5}  # 4th valid -> must cap at 3
            ]},
        ]
        cutaways = _plan_cutaways(tmp_clips, 25.0, None)
        self.assertLessEqual(len(cutaways), 3, "Max 3 overlays allowed")
        last_end = 0.0
        for path, start, end in cutaways:
            self.assertEqual(path, __file__)
            dur = end - start
            self.assertGreaterEqual(dur, 2.0, "Min duration 2.0s")
            self.assertLessEqual(dur, 3.25, "Max duration 3.2s")
            self.assertGreaterEqual(start, last_end - 0.01, "Overlays must not overlap")
            last_end = end

    def test_explicit_cues_protect_hook_and_preserve_shifted_duration(self):
        clips = [{"path": __file__, "duration": 8.0, "broll_inserts": [
            {"path": __file__, "start": 0.0, "end": 3.0},
            {"path": __file__, "start": 1.0, "end": 4.2},
        ]}]
        cutaways = _plan_cutaways(clips, 12.0, None)
        self.assertLessEqual(len(cutaways), 2)
        self.assertGreaterEqual(cutaways[0][1], 1.8)
        for _, start, end in cutaways:
            self.assertGreaterEqual(end - start, 2.0)
            self.assertLessEqual(end - start, 3.2)
        if len(cutaways) == 2:
            self.assertGreaterEqual(cutaways[1][1], cutaways[0][2])

    def test_short_video_drops_cutaway_instead_of_breaking_min_duration(self):
        clips = [{"path": __file__, "broll_inserts": [
            {"path": __file__, "start": 0, "end": 2.0},
        ]}]
        self.assertEqual(_plan_cutaways(clips, 4.6, None), [])

    def test_dynamic_cues_obey_same_hook_and_tail_guards(self):
        from services.dynamic_broll_director import BRollCue
        clips = [{"path": __file__, "duration": 4.0} for _ in range(3)]
        cues = [BRollCue(0, 3, "a", "a"), BRollCue(9.1, 12, "b", "b")]
        with patch("render.ffmpeg_graph.config.RENDER_SAFE_MODE", False), patch(
            "services.dynamic_broll_director.dynamic_broll_director.plan_retention_broll",
            return_value=cues,
        ):
            cutaways = _plan_cutaways(clips, 12.0, None)
        self.assertEqual(cutaways, [(__file__, 1.8, 4.8)])

    def test_pydantic_video_render_request_has_enable_broll_insert(self):
        """VideoRenderRequest must have enable_broll_insert defaulting to False."""
        req_default = VideoRenderRequest(keyword="test")
        self.assertFalse(req_default.enable_broll_insert)

        req_enabled = VideoRenderRequest(keyword="test", enable_broll_insert=True)
        self.assertTrue(req_enabled.enable_broll_insert)

    @patch("imageio_ffmpeg.get_ffmpeg_exe", return_value="ffmpeg")
    @patch("render.ffmpeg_graph._probe_duration", return_value=12.0)
    @patch("render.ffmpeg_graph._probe_is_landscape", return_value=False)
    @patch("render.ffmpeg_graph.subprocess.Popen")
    @patch("render.ffmpeg_graph.subprocess.run")
    @patch("render.ffmpeg_graph.os.path.exists")
    def test_ffmpeg_graph_when_enable_broll_false_no_overlay(self, mock_exists, mock_run, mock_popen, mock_land, mock_dur, mock_ff):
        """When enable_broll=False, no B-roll cutaway input or overlay filter is generated."""
        mock_exists.return_value = True
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout.readline.return_value = ""
        mock_proc.stderr.readline.return_value = ""
        mock_proc.communicate.return_value = ("", "")
        mock_proc.poll.return_value = 0
        mock_popen.return_value = mock_proc

        clips = [
            {"path": "clip1.mp4", "duration": 4.0},
            {"path": "clip2.mp4", "duration": 4.0},
            {"path": "clip3.mp4", "duration": 4.0},
        ]
        with patch("render.ffmpeg_graph._plan_cutaways") as mock_plan:
            mock_plan.return_value = [("donor.mp4", 1.0, 3.5)]
            captured_cmds = []

            def fake_popen(cmd, *args, **kwargs):
                captured_cmds.append(cmd)
                return mock_proc

            mock_popen.side_effect = fake_popen

            render_with_ffmpeg_graph(
                clips=clips,
                audio_path="audio.mp3",
                output_path="out.mp4",
                enable_broll=False,
                progress_callback=lambda p, m: None,
            )

            # mock_plan should NOT be called when enable_broll=False
            mock_plan.assert_not_called()

            if captured_cmds:
                cmd = captured_cmds[0]
                filter_complex = ""
                for i, arg in enumerate(cmd):
                    if arg == "-filter_complex":
                        filter_complex = cmd[i + 1]
                        break
                self.assertNotIn("vcut", filter_complex)
                self.assertNotIn("broll0", filter_complex)

    @patch("imageio_ffmpeg.get_ffmpeg_exe", return_value="ffmpeg")
    @patch("render.ffmpeg_graph._probe_duration", return_value=12.0)
    @patch("render.ffmpeg_graph._probe_is_landscape", return_value=False)
    @patch("render.ffmpeg_graph.subprocess.Popen")
    @patch("render.ffmpeg_graph.subprocess.run")
    @patch("render.ffmpeg_graph.os.path.exists")
    def test_ffmpeg_graph_when_enable_broll_true_generates_single_graph_overlay(self, mock_exists, mock_run, mock_popen, mock_land, mock_dur, mock_ff):
        """When enable_broll=True, overlays are placed in the single filter_complex."""
        mock_exists.return_value = True
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout.readline.return_value = ""
        mock_proc.stderr.readline.return_value = ""
        mock_proc.communicate.return_value = ("", "")
        mock_proc.poll.return_value = 0
        mock_popen.return_value = mock_proc

        clips = [
            {"path": "clip1.mp4", "duration": 4.0},
            {"path": "clip2.mp4", "duration": 4.0},
            {"path": "clip3.mp4", "duration": 4.0},
        ]
        with patch("render.ffmpeg_graph._plan_cutaways") as mock_plan:
            mock_plan.return_value = [("donor.mp4", 1.0, 3.5), ("donor2.mp4", 5.0, 7.5)]
            captured_cmds = []

            def fake_popen(cmd, *args, **kwargs):
                captured_cmds.append(cmd)
                return mock_proc

            mock_popen.side_effect = fake_popen

            render_with_ffmpeg_graph(
                clips=clips,
                audio_path="audio.mp3",
                output_path="out.mp4",
                enable_broll=True,
                progress_callback=lambda p, m: None,
            )

            mock_plan.assert_called_once()
            if captured_cmds:
                cmd = captured_cmds[0]
                filter_complex = ""
                for i, arg in enumerate(cmd):
                    if arg == "-filter_complex":
                        filter_complex = cmd[i + 1]
                        break
                self.assertIn("vcut0", filter_complex)
                self.assertIn("between(t,1.00,3.50)", filter_complex)
                self.assertIn("between(t,5.00,7.50)", filter_complex)

    @patch("render.ffmpeg_graph.render_with_ffmpeg_graph")
    def test_compose_via_director_passes_enable_broll(self, mock_render):
        mock_render.return_value = "rendered.mp4"
        clips = [{"path": "dummy.mp4", "duration": 3.0}]
        compose_via_director(
            clips=clips,
            audio_path="dummy.mp3",
            word_timings=[],
            output_path="out.mp4",
            enable_broll_insert=True,
        )
        mock_render.assert_called_once()
        _, kwargs = mock_render.call_args
        self.assertTrue(kwargs.get("enable_broll"))


if __name__ == "__main__":
    unittest.main()
