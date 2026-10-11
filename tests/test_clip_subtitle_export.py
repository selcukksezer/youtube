import json
from importlib import import_module
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from services.clip_subtitles import build_clip_srt, build_full_srt


clipper_router = import_module("routers.clipper_router")


def test_build_clip_srt_rebases_disjoint_ranges():
    subtitles = build_clip_srt(
        [
            {"start": 0.5, "end": 1.5, "text": "Merhaba, dünya."},
            {"start": 2.0, "end": 3.0, "text": "Aradaki bölüm"},
            {"start": 4.0, "end": 5.0, "text": "İkinci klip"},
            {"start": 5.0, "end": 5.0, "text": "Geçersiz aralık"},
            {"start": float("nan"), "end": 6.0, "text": "Geçersiz zaman"},
        ],
        [(-5.0, -2.0), (1.0, 2.0), (4.5, 5.5)],
    )

    assert subtitles == (
        "1\n"
        "00:00:00,000 --> 00:00:00,500\n"
        "Merhaba, dünya.\n\n"
        "2\n"
        "00:00:01,000 --> 00:00:01,500\n"
        "İkinci klip\n"
    )


def test_build_full_srt_preserves_source_timestamps():
    subtitles = build_full_srt([
        {"start": 2.5, "end": 4.0, "text": "Later source cue."},
        {"start": 0.5, "end": 1.5, "text": "Earlier source cue."},
        {"start": 3.0, "end": 3.0, "text": "Invalid cue."},
    ])

    assert subtitles == (
        "1\n"
        "00:00:00,500 --> 00:00:01,500\n"
        "Earlier source cue.\n\n"
        "2\n"
        "00:00:02,500 --> 00:00:04,000\n"
        "Later source cue.\n"
    )


def test_clipper_route_writes_and_returns_subtitle_download_url(tmp_path, monkeypatch):
    app = FastAPI()
    app.include_router(clipper_router.router)
    client = TestClient(app)
    monkeypatch.setattr(clipper_router.config, "OUTPUT_DIR", str(tmp_path))
    monkeypatch.setattr(clipper_router, "_resolve_source", lambda _payload: "source.mp4")
    monkeypatch.setattr(
        clipper_router,
        "select_highlights",
        lambda _raw, **_options: [
            {"start_time": 1.0, "end_time": 3.0, "score": 90, "title": "Test"},
        ],
    )

    with patch.object(clipper_router, "cut_ranges_vertical"):
        response = client.post(
            "/api/clipper",
            json={
                "source_path": "source.mp4",
                "highlights": [{"start_time": 1.0, "end_time": 3.0}],
                "segments": [
                    {"start": 0.5, "end": 2.0, "text": "Seçilen cümle."},
                    {"start": 2.5, "end": 4.0, "text": "Sonraki cümle."},
                ],
                "render": True,
            },
        )

    assert response.status_code == 200
    clip = response.json()["clips"][0]
    assert clip["video_url"] == "/output/shorts_clipped/source_short_01.mp4"
    assert clip["subtitle_url"] == "/output/shorts_clipped/source_short_01.srt"
    assert response.json()["source_subtitle_url"] == (
        "/output/shorts_clipped/source_short_01_full_transcript.srt"
    )

    subtitle_path = tmp_path / "shorts_clipped" / "source_short_01.srt"
    assert subtitle_path.read_text(encoding="utf-8") == (
        "1\n"
        "00:00:00,000 --> 00:00:01,000\n"
        "Seçilen cümle.\n\n"
        "2\n"
        "00:00:01,500 --> 00:00:02,000\n"
        "Sonraki cümle.\n"
    )
    source_subtitle_path = (
        tmp_path / "shorts_clipped" / "source_short_01_full_transcript.srt"
    )
    assert source_subtitle_path.read_text(encoding="utf-8") == (
        "1\n"
        "00:00:00,500 --> 00:00:02,000\n"
        "Seçilen cümle.\n\n"
        "2\n"
        "00:00:02,500 --> 00:00:04,000\n"
        "Sonraki cümle.\n"
    )


def test_clipper_can_compile_highlights_with_rebased_subtitles(tmp_path, monkeypatch):
    app = FastAPI()
    app.include_router(clipper_router.router)
    client = TestClient(app)
    monkeypatch.setattr(clipper_router.config, "OUTPUT_DIR", str(tmp_path))

    selected = [
        {"start_time": 1.0, "end_time": 3.0, "score": 90, "title": "İlk an"},
        {"start_time": 5.0, "end_time": 7.0, "score": 80, "title": "İkinci an"},
    ]

    def resolve_source(payload):
        assert payload["source_path"] == "source.mp4"
        return "source.mp4"

    def select_highlights(raw, **options):
        assert len(raw) == 2
        assert options["num_clips"] == 2
        return selected

    monkeypatch.setattr(clipper_router, "_resolve_source", resolve_source)
    monkeypatch.setattr(clipper_router, "select_highlights", select_highlights)
    with patch.object(
        clipper_router,
        "cut_ranges_vertical",
        return_value="source_compilation.mp4",
    ) as cut:
        response = client.post(
            "/api/clipper",
            files=[
                ("source_path", (None, "source.mp4")),
                (
                    "highlights",
                    (
                        None,
                        json.dumps([
                            {"start_time": 1.0, "end_time": 3.0},
                            {"start_time": 5.0, "end_time": 7.0},
                        ]),
                    ),
                ),
                (
                    "segments",
                    (
                        None,
                        json.dumps(
                            [
                                {"start": 1.5, "end": 2.5, "text": "İlk altyazı."},
                                {"start": 5.5, "end": 6.0, "text": "İkinci altyazı."},
                            ],
                            ensure_ascii=False,
                        ),
                    ),
                ),
                ("num_clips", (None, "2")),
                ("compile_clips", (None, "true")),
                ("render", (None, "true")),
            ],
        )

    assert response.status_code == 200
    result = response.json()
    assert len(result["clips"]) == 1
    compiled = result["clips"][0]
    assert compiled["compiled"] is True
    assert compiled["source_highlights"] == selected
    assert compiled["video_url"] == "/output/shorts_clipped/source_compilation.mp4"
    assert cut.call_count == 1
    assert cut.call_args.args[1] == [(1.0, 3.0), (5.0, 7.0)]

    subtitle_path = tmp_path / "shorts_clipped" / "source_compilation.srt"
    assert subtitle_path.read_text(encoding="utf-8") == (
        "1\n"
        "00:00:00,500 --> 00:00:01,500\n"
        "İlk altyazı.\n\n"
        "2\n"
        "00:00:02,500 --> 00:00:03,000\n"
        "İkinci altyazı.\n"
    )
