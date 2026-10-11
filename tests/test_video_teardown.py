import subprocess
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers.clipper_router import router
from services.video_teardown import (
    VideoTeardownError,
    _cut_statistics,
    analyze_reference_video,
)


class TestVideoTeardownStatistics(unittest.TestCase):
    def test_includes_video_edges_in_shot_interval_statistics(self):
        stats = _cut_statistics([2.0, 7.0, 13.0], 18.0)

        self.assertEqual(stats["cut_count"], 3)
        self.assertEqual(stats["cuts_per_minute"], 10.0)
        self.assertEqual(stats["shot_interval_count"], 4)
        self.assertEqual(stats["median_shot_interval_sec"], 5.0)
        self.assertEqual(stats["shortest_shot_sec"], 2.0)

    def test_no_cuts_reports_one_shot_for_entire_video(self):
        stats = _cut_statistics([], 12.0)

        self.assertEqual(stats["cut_count"], 0)
        self.assertEqual(stats["shot_interval_count"], 1)
        self.assertEqual(stats["median_shot_interval_sec"], 12.0)
        self.assertEqual(stats["shot_interval_stddev_sec"], 0.0)


class TestVideoTeardownAnalysis(unittest.TestCase):
    @patch("services.video_teardown.subprocess.run")
    def test_reports_cut_cadence_and_loudness(self, run):
        run.side_effect = [
            subprocess.CompletedProcess(
                ["ffmpeg"], 0, b"",
                b"Duration: 00:00:18.00, start: 0.000000\n"
                b"Stream #0:0: Video: h264, yuv420p, 1280x720, 30 fps\n"
                b"Stream #0:1: Audio: aac, 48000 Hz\n",
            ),
            subprocess.CompletedProcess(
                ["ffmpeg"], 0, b"",
                b"pts_time:2.000000\npts_time:7.000000\npts_time:13.000000\n"
                b"Summary:\n I: -15.2 LUFS\n",
            ),
        ]

        report = analyze_reference_video("reference.mp4")

        self.assertEqual(report["duration_sec"], 18.0)
        self.assertEqual(report["resolution"], {"width": 1280, "height": 720})
        self.assertEqual(report["fps"], 30.0)
        self.assertEqual(report["cut_timestamps_sec"], [2.0, 7.0, 13.0])
        self.assertEqual(report["median_shot_interval_sec"], 5.0)
        self.assertEqual(report["integrated_lufs"], -15.2)
        self.assertIn("reference.mp4", run.call_args_list[0].args[0])
        self.assertIn("reference.mp4", run.call_args_list[1].args[0])

    @patch("services.video_teardown.subprocess.run")
    def test_skips_loudness_when_video_has_no_audio(self, run):
        run.side_effect = [
            subprocess.CompletedProcess(
                ["ffmpeg"], 0, b"",
                b"Duration: 00:00:12.00, start: 0.000000\n"
                b"Stream #0:0: Video: h264, yuv420p, 640x360, 25 fps\n",
            ),
            subprocess.CompletedProcess(["ffmpeg"], 0, b"", b"pts_time:4.000000\n"),
        ]

        report = analyze_reference_video("silent.mp4")

        self.assertIsNone(report["integrated_lufs"])
        self.assertEqual(report["cut_count"], 1)
        self.assertTrue(any("LUFS ölçümü atlandı" in note for note in report["notes"]))

    @patch("services.video_teardown.subprocess.run")
    def test_surfaces_ffmpeg_failure(self, run):
        run.return_value = subprocess.CompletedProcess(["ffmpeg"], 1, b"", b"invalid input")

        with self.assertRaisesRegex(VideoTeardownError, "invalid input"):
            analyze_reference_video("invalid.mp4")


class TestVideoTeardownEndpoint(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)

    def test_returns_local_analysis_report(self):
        expected = {"cut_count": 4, "integrated_lufs": -14.5}
        with patch("routers.clipper_router._resolve_source", return_value="reference.mp4"), \
             patch("services.video_teardown.analyze_reference_video", return_value=expected) as analyze:
            response = self.client.post(
                "/api/clipper/teardown",
                json={"source_path": "reference.mp4"},
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["analysis"], expected)
        analyze.assert_called_once_with("reference.mp4")

    def test_returns_analysis_errors_as_actionable_client_errors(self):
        with patch("routers.clipper_router._resolve_source", return_value="invalid.mp4"), \
             patch(
                 "services.video_teardown.analyze_reference_video",
                 side_effect=VideoTeardownError("Geçerli video akışı yok."),
             ):
            response = self.client.post(
                "/api/clipper/teardown",
                json={"source_path": "invalid.mp4"},
            )

        self.assertEqual(response.status_code, 422)
        self.assertIn("video akışı", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
