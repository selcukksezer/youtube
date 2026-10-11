import unittest
from unittest.mock import patch

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from routers.clipper_router import router
from routers.video_router import api_clipper_analyze
from services.multimodal_clipper import parse_pegasus_highlights


class TestPegasusHighlightParsing(unittest.TestCase):
    def test_parses_and_bounds_timestamped_segments(self):
        highlights = parse_pegasus_highlights(
            "1. [12.5-48.25] Speaker reveals the unexpected result.\n"
            "2. [50-135] The second moment is too long.",
            video_duration=120.0,
            num_clips=3,
        )

        self.assertEqual(len(highlights), 1)
        self.assertEqual(highlights[0]["start_time"], 12.5)
        self.assertEqual(highlights[0]["end_time"], 48.25)
        self.assertEqual(highlights[0]["title"], "Speaker reveals the unexpected result.")
        self.assertEqual(highlights[0]["source"], "twelvelabs_pegasus")

    def test_rejects_missing_or_invalid_timestamps(self):
        highlights = parse_pegasus_highlights(
            "A highlight without a time range.\n"
            "1. [30-20] Reversed.\n"
            "2. [NaN-40] Not finite.",
            video_duration=120.0,
            num_clips=3,
        )
        self.assertEqual(highlights, [])

    def test_returns_requested_candidates_in_chronological_order(self):
        highlights = parse_pegasus_highlights(
            "1. [80-110] Later moment.\n"
            "2. [5-35] Opening moment.\n"
            "3. [45-75] Middle moment.",
            video_duration=120.0,
            num_clips=2,
        )

        self.assertEqual(
            [item["start_time"] for item in highlights],
            [5.0, 45.0],
        )


class TestMultimodalClipperEndpoint(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        app.include_router(router)
        self.client = TestClient(app)

    def test_multimodal_mode_requires_explicit_external_analysis_consent(self):
        response = self.client.post(
            "/api/clipper",
            json={
                "url": "https://www.youtube.com/watch?v=example",
                "analysis_mode": "multimodal",
                "render": False,
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("onay", response.json()["detail"].lower())

    def test_multimodal_mode_uses_pegasus_only_after_consent(self):
        suggestions = [
            {
                "start_time": 12.0,
                "end_time": 47.0,
                "title": "Unexpected visual reveal",
                "score": 0,
                "source": "twelvelabs_pegasus",
            }
        ]
        with patch(
            "services.youtube_clipper.youtube_clipper.extract_youtube_info",
            return_value={"duration": 90.0, "title": "Source"},
        ), patch(
            "services.multimodal_clipper.analyze_video_highlights",
            return_value=suggestions,
        ) as analyze:
            response = self.client.post(
                "/api/clipper",
                json={
                    "url": "https://www.youtube.com/watch?v=example",
                    "analysis_mode": "multimodal",
                    "external_analysis_consent": True,
                    "render": False,
                },
            )

        self.assertEqual(response.status_code, 200)
        analyze.assert_called_once_with(
            "https://www.youtube.com/watch?v=example",
            video_duration=90.0,
            num_clips=3,
        )
        self.assertEqual(
            response.json()["highlights"][0]["source"],
            "twelvelabs_pegasus",
        )

    def test_video_router_supports_consented_multimodal_suggestions(self):
        with patch(
            "services.youtube_clipper.youtube_clipper.extract_youtube_info",
            return_value={"duration": 90.0, "title": "Source"},
        ), patch(
            "services.multimodal_clipper.analyze_video_highlights",
            return_value=[
                {
                    "start_time": 12.0,
                    "end_time": 47.0,
                    "title": "Unexpected visual reveal",
                    "score": 0,
                    "source": "twelvelabs_pegasus",
                }
            ],
        ):
            result = api_clipper_analyze({
                "url": "https://www.youtube.com/watch?v=example",
                "analysis_mode": "multimodal",
                "external_analysis_consent": True,
            })

        self.assertEqual(result["highlights_count"], 1)
        self.assertEqual(
            result["highlights"][0]["source"],
            "twelvelabs_pegasus",
        )

    def test_video_router_rejects_multimodal_mode_without_consent(self):
        with self.assertRaises(HTTPException) as raised:
            api_clipper_analyze({
                "url": "https://www.youtube.com/watch?v=example",
                "analysis_mode": "multimodal",
                "external_analysis_consent": False,
            })
        self.assertEqual(raised.exception.status_code, 400)

    def test_missing_provider_configuration_has_actionable_error(self):
        from services.multimodal_clipper import (
            MultimodalConfigurationError,
            analyze_video_highlights,
        )

        with patch.dict("os.environ", {"TWELVELABS_API_KEY": ""}):
            with self.assertRaisesRegex(
                MultimodalConfigurationError,
                "TWELVELABS_API_KEY",
            ):
                analyze_video_highlights(
                    "https://www.youtube.com/watch?v=example",
                    video_duration=90.0,
                    num_clips=3,
                )


if __name__ == "__main__":
    unittest.main()
