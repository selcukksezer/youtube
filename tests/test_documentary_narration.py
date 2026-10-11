from importlib import import_module
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

import config
from services import documentary_narration


def _source_file(tmp_path):
    path = tmp_path / "source.mp4"
    path.write_bytes(b"video")
    return str(path)


def test_documentary_narration_uses_sampled_frames_and_returns_grounded_script(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setattr(config, "GEMINI_MODEL", "gemini-test")
    source_path = _source_file(tmp_path)
    with patch(
        "services.documentary_narration._sample_frames",
        return_value=["frame-one", "frame-two"],
    ), patch(
        "services.documentary_narration._request_gemini_json",
        return_value={
            "summary": "Bir kişi yağmurlu sokakta koşuyor.",
            "narration": "Yağmur hızlanırken karakter sokağın sonuna doğru koşuyor.",
            "frame_observations": ["Islak sokakta bir kişi duruyor.", "Kişi ileride koşuyor."],
        },
    ) as request:
        result = documentary_narration.generate_documentary_narration(
            source_path,
            theme="kaçış anı",
        )

    prompt = request.call_args.kwargs["prompt"]
    assert request.call_args.kwargs["frames"] == ["frame-one", "frame-two"]
    assert "2 kare" in prompt
    assert "kaçış anı" in prompt
    assert "ses/konuşma" not in prompt
    assert result == {
        "summary": "Bir kişi yağmurlu sokakta koşuyor.",
        "narration": "Yağmur hızlanırken karakter sokağın sonuna doğru koşuyor.",
        "frame_observations": ["Islak sokakta bir kişi duruyor.", "Kişi ileride koşuyor."],
        "frames_analyzed": 2,
        "language": "tr",
    }


def test_documentary_narration_rejects_mismatched_observation_count(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "test-gemini-key")
    source_path = _source_file(tmp_path)
    with patch(
        "services.documentary_narration._sample_frames",
        return_value=["frame-one", "frame-two"],
    ), patch(
        "services.documentary_narration._request_gemini_json",
        return_value={
            "summary": "Özet.",
            "narration": "Anlatım taslağı.",
            "frame_observations": ["Tek gözlem."],
        },
    ):
        with pytest.raises(
            documentary_narration.DocumentaryNarrationError,
            match="kare gözlemleri",
        ):
            documentary_narration.generate_documentary_narration(source_path)


def test_documentary_narration_requires_api_key_and_readable_frames(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
    source_path = _source_file(tmp_path)
    with patch("services.documentary_narration._sample_frames") as sample:
        with pytest.raises(documentary_narration.DocumentaryNarrationUnavailable):
            documentary_narration.generate_documentary_narration(source_path)
    sample.assert_not_called()

    monkeypatch.setattr(config, "GEMINI_API_KEY", "test-gemini-key")
    with patch("services.documentary_narration._sample_frames", return_value=[]):
        with pytest.raises(
            documentary_narration.DocumentaryNarrationError,
            match="örnek kare",
        ):
            documentary_narration.generate_documentary_narration(source_path)


def test_documentary_narration_rejects_oversized_focus(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "test-gemini-key")
    source_path = _source_file(tmp_path)
    with patch("services.documentary_narration._sample_frames") as sample:
        with pytest.raises(ValueError, match="240"):
            documentary_narration.generate_documentary_narration(
                source_path,
                theme="x" * 241,
            )
    sample.assert_not_called()


def test_clipper_narration_route_requires_explicit_consent():
    clipper_router = import_module("routers.clipper_router")
    app = FastAPI()
    app.include_router(clipper_router.router)
    client = TestClient(app)
    with patch.object(clipper_router, "_resolve_source") as resolve:
        response = client.post(
            "/api/clipper/narration",
            json={"source_path": "source.mp4", "visual_analysis_consent": False},
        )
    assert response.status_code == 400
    assert "onay" in response.json()["detail"].lower()
    resolve.assert_not_called()


def test_clipper_narration_route_returns_visual_script(monkeypatch):
    clipper_router = import_module("routers.clipper_router")
    app = FastAPI()
    app.include_router(clipper_router.router)
    client = TestClient(app)
    monkeypatch.setattr(
        clipper_router,
        "_resolve_source",
        lambda payload: payload["source_path"],
    )
    expected = {
        "summary": "Görsel özet.",
        "narration": "Görsellere dayalı anlatım.",
        "frame_observations": ["İlk kare.", "İkinci kare."],
        "frames_analyzed": 2,
        "language": "tr",
    }
    with patch(
        "services.documentary_narration.generate_documentary_narration",
        return_value=expected,
    ) as generate:
        response = client.post(
            "/api/clipper/narration",
            files=[
                ("source_path", (None, "source.mp4")),
                ("visual_analysis_consent", (None, "true")),
                ("narration_theme", (None, "sürpriz gelişme")),
            ],
        )
    assert response.status_code == 200
    assert response.json() == {"status": "ok", **expected}
    generate.assert_called_once_with("source.mp4", theme="sürpriz gelişme")


def test_clipper_narration_route_maps_unconfigured_gemini_to_503():
    clipper_router = import_module("routers.clipper_router")
    app = FastAPI()
    app.include_router(clipper_router.router)
    client = TestClient(app)
    with patch.object(
        clipper_router,
        "_resolve_source",
        side_effect=lambda payload: str(payload.get("source_path") or "source.mp4"),
    ), patch(
        "services.documentary_narration.generate_documentary_narration",
        side_effect=documentary_narration.DocumentaryNarrationUnavailable("Gemini yapılandırılmamış."),
    ):
        response = client.post(
            "/api/clipper/narration",
            json={"visual_analysis_consent": True},
        )
    assert response.status_code == 503
    assert "Gemini" in response.json()["detail"]
