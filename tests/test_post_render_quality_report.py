import os
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from render.pipeline_audit import post_render_audit


class PostRenderQualityReportTests(unittest.TestCase):
    def test_reports_dimensions_black_frames_silence_and_peak(self):
        with tempfile.TemporaryDirectory() as directory:
            video_path = os.path.join(directory, "render.mp4")
            audio_path = os.path.join(directory, "voice.wav")
            with open(video_path, "wb") as handle:
                handle.write(b"v" * 120_000)
            with open(audio_path, "wb") as handle:
                handle.write(b"a" * 12_000)

            ffmpeg_log = (
                b"[blackdetect] black_start:3.000000 black_end:4.000000 "
                b"black_duration:1.000000\n"
                b"[silencedetect] silence_start: 0.500000\n"
                b"[silencedetect] silence_end: 2.200000 | silence_duration: 1.700000\n"
                b"[Parsed_volumedetect] max_volume: -0.2 dB\n"
            )
            completed = subprocess.CompletedProcess(args=[], returncode=0, stdout=b"", stderr=ffmpeg_log)
            with patch("render.pipeline_audit._ffprobe_duration", side_effect=[30.0, 30.0]), \
                 patch(
                     "render.pipeline_audit._ffprobe_streams",
                     return_value=[
                         {
                             "codec_type": "video",
                             "codec_name": "h264",
                             "resolution": "1080x1920",
                             "width": "1080",
                             "height": "1920",
                             "fps": "30",
                             "pix_fmt": "yuv420p",
                         },
                         {"codec_type": "audio", "codec_name": "aac"},
                     ],
                 ), \
                 patch("imageio_ffmpeg.get_ffmpeg_exe", return_value="ffmpeg"), \
                 patch("render.pipeline_audit.subprocess.run", return_value=completed) as run:
                report = post_render_audit(video_path, audio_path, [{"duration": 30.0}])

        self.assertTrue(report["ok"], report["errors"])
        metrics = report["report"]
        self.assertEqual(metrics["resolution"], "1080x1920")
        self.assertEqual(metrics["fps"], 30.0)
        self.assertEqual(metrics["signal_analysis"]["black_intervals"], [
            {"start": 3.0, "end": 4.0, "duration": 1.0}
        ])
        self.assertEqual(metrics["signal_analysis"]["silence_intervals"], [
            {"start": 0.5, "end": 2.2, "duration": 1.7}
        ])
        self.assertEqual(metrics["signal_analysis"]["peak_volume_dbfs"], -0.2)
        self.assertIn("detected_black_frames:3.00-4.00s", report["warnings"])
        self.assertIn("long_silence:0.50-2.20s", report["warnings"])
        self.assertIn("audio_peak_clipping_risk:-0.20dBFS", report["warnings"])
        args = run.call_args.args[0]
        self.assertIn("blackdetect=d=0.5:pix_th=0.10", args[args.index("-filter_complex") + 1])
        self.assertIn("silencedetect=noise=-50dB:d=1.5", args[args.index("-filter_complex") + 1])

    def test_signal_analysis_failure_is_visible_as_a_warning(self):
        with tempfile.TemporaryDirectory() as directory:
            video_path = os.path.join(directory, "render.mp4")
            with open(video_path, "wb") as handle:
                handle.write(b"v" * 120_000)

            with patch("render.pipeline_audit._ffprobe_duration", return_value=30.0), \
                 patch(
                     "render.pipeline_audit._ffprobe_streams",
                     return_value=[
                         {"codec_type": "video", "codec_name": "h264", "resolution": "1080x1920"},
                         {"codec_type": "audio", "codec_name": "aac"},
                     ],
                 ), \
                 patch("imageio_ffmpeg.get_ffmpeg_exe", return_value="ffmpeg"), \
                 patch(
                     "render.pipeline_audit.subprocess.run",
                     side_effect=subprocess.TimeoutExpired(cmd="ffmpeg", timeout=90),
                 ):
                report = post_render_audit(video_path, "", [{"duration": 30.0}])

        self.assertTrue(report["ok"])
        self.assertFalse(report["report"]["signal_analysis"]["available"])
        self.assertTrue(any(
            warning.startswith("signal_analysis_unavailable:TimeoutExpired")
            for warning in report["warnings"]
        ))


if __name__ == "__main__":
    unittest.main()
