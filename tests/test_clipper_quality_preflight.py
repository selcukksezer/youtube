from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers.clipper_router import router
from services.youtube_clipper import youtube_clipper


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_extract_youtube_info_reports_best_video_resolution():
    ydl = MagicMock()
    ydl.__enter__.return_value = ydl
    ydl.extract_info.return_value = {
        "id": "source-id",
        "duration": 120,
        "formats": [
            {"height": 360, "vcodec": "avc1", "protocol": "https", "ext": "mp4"},
            {"height": 2160, "vcodec": "none", "protocol": "https", "ext": "m4a"},
            {"height": 1440, "vcodec": "avc1", "protocol": "mhtml", "ext": "mhtml"},
            {"height": 720, "vcodec": "avc1", "protocol": "https", "ext": "mp4"},
        ],
    }
    with patch("services.youtube_clipper.yt_dlp.YoutubeDL", return_value=ydl):
        info = youtube_clipper.extract_youtube_info("https://youtu.be/source-id")

    assert info["max_height"] == 720


def test_low_resolution_url_requires_confirmation_before_transcription(client, monkeypatch):
    def low_quality_info(url):
        assert url == "https://youtu.be/low-resolution"
        return {"duration": 120, "max_height": 360}

    monkeypatch.setattr(
        youtube_clipper,
        "extract_youtube_info",
        low_quality_info,
    )
    with patch.object(youtube_clipper, "fetch_subtitles_or_transcribe") as transcribe:
        response = client.post(
            "/api/clipper",
            json={"url": "https://youtu.be/low-resolution", "render": False},
        )

    assert response.status_code == 409
    assert response.json()["detail"] == {
        "code": "source_quality_confirmation_required",
        "message": (
            "Kaynak yalnızca 360p çözünürlükte mevcut. 720p altı görüntüler "
            "dikey Shorts çıktısında daha bulanık olabilir. Yine de analiz edilsin mi?"
        ),
        "max_height": 360,
        "minimum_height": 720,
    }
    transcribe.assert_not_called()


@pytest.mark.parametrize(
    ("max_height", "force_low_quality"),
    [(0, False), (720, False), (1080, False), (360, True)],
)
def test_unknown_recommended_or_confirmed_resolution_does_not_block_analysis(
    client, monkeypatch, max_height, force_low_quality
):
    def source_info(url):
        assert url == "https://youtu.be/source"
        return {"duration": 120, "max_height": max_height}

    monkeypatch.setattr(
        youtube_clipper,
        "extract_youtube_info",
        source_info,
    )
    with (
        patch.object(
            youtube_clipper,
            "fetch_subtitles_or_transcribe",
            return_value=[{"start": 0.0, "end": 1.0, "text": "hello"}],
        ),
        patch.object(youtube_clipper, "format_transcript_segments", return_value="hello"),
        patch.object(youtube_clipper, "detect_highlights_with_llm", return_value=[]),
        patch.object(youtube_clipper, "ground_highlights_in_transcript", return_value=[]),
    ):
        response = client.post(
            "/api/clipper",
            json={
                "url": "https://youtu.be/source",
                "render": False,
                "force_low_quality": force_low_quality,
            },
        )

    assert response.status_code == 200
