import json
from unittest.mock import MagicMock, patch

import config
import pytest
from services import video_title_ideas


def _gemini_response(payload):
    response = MagicMock()
    response.json.return_value = {
        "candidates": [{
            "content": {
                "parts": [{"text": json.dumps(payload, ensure_ascii=False)}],
            },
        }],
    }
    return response


def test_video_title_ideas_are_frame_grounded_ranked_and_aligned(monkeypatch):
    monkeypatch.setenv("USE_GEMINI_TITLE_IDEAS", "true")
    monkeypatch.setattr(config, "GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setattr(config, "GEMINI_MODEL", "gemini-test")
    brainstorm = {
        "summary": "Bir araştırma videosundaki beklenmedik sonucu anlatıyor.",
        "language": "tr",
        "candidates": ["Birinci özgün başlık", "İkinci farklı merak başlığı"],
    }
    critic = {
        "titles": [
            "İkinci Başlık: Araştırmadaki Beklenmedik Sonuç #Shorts",
            "Birinci Başlık: Bu Bilinmeyen Detay Neden Önemli #Shorts",
        ],
        "thumbnail_texts": ["SONUÇ ŞAŞIRTTI", "GİZLİ DETAY"],
        "recommended": [{"index": 0, "reason": "Video kanıtı bu açıyı destekliyor."}],
        "language": "tr",
    }
    with patch(
        "services.video_title_ideas._sample_frames",
        return_value=["frame1", "frame2"],
    ), patch(
        "services.video_title_ideas.requests.post",
        side_effect=[_gemini_response(brainstorm), _gemini_response(critic)],
    ) as post:
        result = video_title_ideas.generate_video_title_ideas(
            "rendered.mp4",
            keyword="Araştırma",
            script_context="Senaryo içeriği",
            current_title="Mevcut SEO başlığı",
            language="tr",
        )

    assert result is not None
    assert len(result["titles"]) == 2
    assert len(result["thumbnail_texts"]) == len(result["titles"])
    assert all(len(title) <= 60 for title in result["titles"])
    assert result["thumbnail_texts"] == ["SONUÇ ŞAŞIRTTI", "GİZLİ DETAY"]
    assert result["recommended"] == [
        {"index": 0, "reason": "Video kanıtı bu açıyı destekliyor."}
    ]
    first_request = post.call_args_list[0]
    frame_parts = first_request.kwargs["json"]["contents"][0]["parts"]
    assert [part["inlineData"]["data"] for part in frame_parts[:-1]] == ["frame1", "frame2"]
    assert "Mevcut SEO başlığı" in frame_parts[-1]["text"]
    assert post.call_count == 2


def test_video_title_ideas_are_opt_in(monkeypatch):
    monkeypatch.setenv("USE_GEMINI_TITLE_IDEAS", "false")
    monkeypatch.setattr(config, "GEMINI_API_KEY", "test-gemini-key")
    with patch("services.video_title_ideas._sample_frames") as sample:
        assert video_title_ideas.generate_video_title_ideas(
            "rendered.mp4",
            keyword="Konu",
            script_context="Senaryo",
            current_title="Başlık",
        ) is None
    sample.assert_not_called()


def test_video_title_ideas_skip_without_gemini_key(monkeypatch):
    monkeypatch.setenv("USE_GEMINI_TITLE_IDEAS", "true")
    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
    with patch("services.video_title_ideas._sample_frames") as sample:
        assert video_title_ideas.generate_video_title_ideas(
            "rendered.mp4",
            keyword="Konu",
            script_context="Senaryo",
            current_title="Başlık",
        ) is None
    sample.assert_not_called()


def test_video_title_ideas_skip_on_gemini_failure(monkeypatch):
    monkeypatch.setenv("USE_GEMINI_TITLE_IDEAS", "true")
    monkeypatch.setattr(config, "GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setattr(config, "GEMINI_MODEL", "gemini-test")
    with patch(
        "services.video_title_ideas._sample_frames",
        return_value=["frame1"],
    ), patch(
        "services.video_title_ideas.requests.post",
        side_effect=video_title_ideas.requests.Timeout(),
    ):
        assert video_title_ideas.generate_video_title_ideas(
            "rendered.mp4",
            keyword="Konu",
            script_context="Senaryo",
            current_title="Başlık",
        ) is None


def test_video_title_refinement_uses_summary_feedback_and_returns_bounded_title(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setattr(config, "GEMINI_MODEL", "gemini-test")
    with patch(
        "services.video_title_ideas.requests.post",
        return_value=_gemini_response({
            "title": "Bu deneyin beklenmedik sonucu #Shorts",
            "reason": "Başlık daha kısa ve merak uyandırıcı oldu.",
        }),
    ) as post:
        result = video_title_ideas.refine_video_title_idea(
            current_title="Deneyin sonucu",
            feedback="Daha merak uyandırıcı olsun.",
            summary="Video deneyin beklenmedik sonucunu gösteriyor.",
            language="tr",
        )

    prompt = post.call_args.kwargs["json"]["contents"][0]["parts"][-1]["text"]
    assert '"creator_feedback": "Daha merak uyandırıcı olsun."' in prompt
    assert '"video_summary": "Video deneyin beklenmedik sonucunu gösteriyor."' in prompt
    assert result["title"]
    assert len(result["title"]) <= 60
    assert result["reason"] == "Başlık daha kısa ve merak uyandırıcı oldu."


def test_video_title_refinement_rejects_invalid_inputs_and_missing_key(monkeypatch):
    with pytest.raises(ValueError, match="feedback"):
        video_title_ideas.refine_video_title_idea(
            current_title="Başlık",
            feedback=" ",
        )
    with pytest.raises(ValueError, match="language"):
        video_title_ideas.refine_video_title_idea(
            current_title="Başlık",
            feedback="Daha sade olsun.",
            language="x-1",
        )

    monkeypatch.setattr(config, "GEMINI_API_KEY", "")
    with pytest.raises(video_title_ideas.TitleIdeaRefinementUnavailable):
        video_title_ideas.refine_video_title_idea(
            current_title="Başlık",
            feedback="Daha sade olsun.",
        )


def test_video_title_refinement_accepts_region_language_code(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_API_KEY", "test-gemini-key")
    with patch(
        "services.video_title_ideas.requests.post",
        return_value=_gemini_response({
            "title": "This result surprised everyone",
            "reason": "The wording is concise.",
        }),
    ), patch(
        "viral_seo_agent.finalize_seo_title",
        side_effect=lambda title, lang: title if lang == "en-us" else "",
    ):
        result = video_title_ideas.refine_video_title_idea(
            current_title="The experiment result",
            feedback="Make it more concise.",
            language="en-US",
        )

    assert result["title"] == "This result surprised everyone"


def test_video_title_refinement_route_validates_payload_and_returns_result(monkeypatch):
    from fastapi.testclient import TestClient
    import server

    def fake_refine(**kwargs):
        assert kwargs["current_title"] == "Eski başlık"
        assert kwargs["feedback"] == "Daha sade olsun."
        return {"title": "Yeni başlık #Shorts", "reason": "Sadeleştirildi."}

    monkeypatch.setattr(
        "services.video_title_ideas.refine_video_title_idea",
        fake_refine,
    )
    client = TestClient(server.app)
    response = client.post(
        "/api/video/title-ideas/refine",
        json={
            "current_title": "Eski başlık",
            "feedback": "Daha sade olsun.",
            "summary": "Video özeti",
            "language": "tr",
        },
    )
    invalid = client.post(
        "/api/video/title-ideas/refine",
        json={"current_title": "Eski başlık", "feedback": 42},
    )

    assert response.status_code == 200
    assert response.json()["refinement"]["title"] == "Yeni başlık #Shorts"
    assert invalid.status_code == 422
