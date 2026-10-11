import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from api_models import SeriesPlanRequest
from routers.research_router import api_plan_series
from scenes.generator import generate_series_outline
from server import app


def _series_response(episode_count=3):
    episodes = []
    for index in range(1, episode_count + 1):
        episodes.append({
            "title": f"Episode {index}",
            "summary": f"A distinct event advances the main conflict in episode {index}.",
            "central_question": f"What changes after event {index}?",
            "cliffhanger": f"The final clue in episode {index} reveals another problem.",
            "continuity_note": f"Carry the unresolved clue from episode {index} forward.",
        })
    return {
        "series_premise": "A connected short series about a changing city.",
        "episodes": episodes,
    }


def _provider_response(payload):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content=json.dumps(payload, ensure_ascii=False),
                )
            )
        ]
    )


def test_generate_series_outline_validates_and_numbers_episodes():
    response = _provider_response(_series_response())
    with (
        patch(
            "scenes.generator._configured_script_providers",
            return_value=[("OpenAI", "test-key", "https://example.invalid/v1", "test-model")],
        ),
        patch("scenes.generator.OpenAI"),
        patch("scenes.generator._call", return_value=response) as call,
    ):
        outline = generate_series_outline(
            "Why does the old clock stop at midnight?",
            niche_type="1_news_flash",
            language="en",
            episode_count=3,
        )

    assert len(outline["episodes"]) == 3
    assert [episode["number"] for episode in outline["episodes"]] == [1, 2, 3]
    assert outline["episodes"][1]["cliffhanger"].startswith("The final clue")
    assert "cliffhanger" in call.call_args.args[1]["messages"][0]["content"].lower()


def test_generate_series_outline_rejects_invalid_provider_output():
    response = _provider_response({"series_premise": "A premise.", "episodes": []})
    with (
        patch(
            "scenes.generator._configured_script_providers",
            return_value=[("OpenAI", "test-key", "https://example.invalid/v1", "test-model")],
        ),
        patch("scenes.generator.OpenAI"),
        patch("scenes.generator._call", return_value=response),
    ):
        with pytest.raises(RuntimeError, match="valid series outline"):
            generate_series_outline("An eligible topic", episode_count=3)


def test_series_plan_request_bounds_episode_count_and_topic():
    request = SeriesPlanRequest(topic="A connected story", episode_count=5)
    assert request.episode_count == 5

    with pytest.raises(ValidationError):
        SeriesPlanRequest(topic="A story", episode_count=6)
    with pytest.raises(ValidationError):
        SeriesPlanRequest(topic="x", episode_count=3)


def test_series_plan_endpoint_forwards_valid_request():
    request = SeriesPlanRequest(
        topic="A connected story",
        niche="1_news_flash",
        language="en",
        episode_count=2,
    )
    outline = _series_response(2)
    with patch("routers.research_router.generate_series_outline", return_value=outline) as generate:
        response = api_plan_series(request)

    assert response == {"status": "ok", "outline": outline}
    generate.assert_called_once_with(
        topic="A connected story",
        niche_type="1_news_flash",
        language="en",
        episode_count=2,
    )


def test_series_plan_http_route_is_registered_and_validates_input():
    outline = _series_response(2)
    with patch("routers.research_router.generate_series_outline", return_value=outline):
        response = TestClient(app).post(
            "/api/series/plan",
            json={
                "topic": "A connected story",
                "niche": "1_news_flash",
                "language": "en",
                "episode_count": 2,
            },
        )

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "outline": outline}

    invalid = TestClient(app).post(
        "/api/series/plan",
        json={"topic": "A connected story", "episode_count": 6},
    )
    assert invalid.status_code == 422


def test_series_plan_endpoint_surfaces_provider_unavailability():
    request = SeriesPlanRequest(topic="A connected story")
    with patch(
        "routers.research_router.generate_series_outline",
        side_effect=RuntimeError("No configured AI provider is available for series planning."),
    ):
        with pytest.raises(HTTPException) as raised:
            api_plan_series(request)

    assert raised.value.status_code == 503
