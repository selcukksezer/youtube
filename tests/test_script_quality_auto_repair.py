import json
import importlib
from copy import deepcopy
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from server_core import state
from scenes.generator import repair_script_quality
from server import app


def _repair_response():
    scenes = []
    for index in range(6):
        scenes.append({
            "index": index,
            "narration": [
                "Beklenmedik ayrıntı yolcuların kararını değiştiriyor ve bekleyişin nedenini şimdi daha açık biçimde herkes için ortaya koyuyor.",
                "Uçuş panosundaki son değişiklik beklenen saate dair varsayımları bozuyor ve yolcuları yeni seçenekleri dikkatle değerlendirmeye zorluyor.",
                "Başvuru koşullarındaki küçük fark hangi belgelerin gerektiğini belirliyor ve aceleyle yapılan hatalı başvuruların önüne geçmeye yardımcı oluyor.",
                "Yolcu hizmetleri masasında alınan kayıt gecikmenin süresini gösteriyor ve sonradan yapılacak resmi incelemeyi kolaylaştırıyor.",
                "Bilet ve bildirim kayıtlarını birlikte saklamak yaşanan aksaklığın zaman çizelgesini kuruyor ve başvuru sırasında kanıt sunmayı kolaylaştırıyor.",
                "Her havayolunun süreci değişebildiğinden yolcular resmi kanallardan güncel koşulları doğrulamalı ve destekleyici belgeleri zamanında hazırlamalıdır.",
            ][index],
            "scene_description": f"Distinct airport visual showing a new passenger decision beat {index}",
            "search_queries": [
                f"airport passenger decision scene {index}",
                f"terminal announcement visual {index}",
            ],
            "mood": "curious",
        })
    return {"title": "Uçuş rötarında yolcu hakları", "scenes": scenes}


def _warning_plan():
    title = "Havayolu Uçuş Rötarında Gizli Yolcu Tazminatı Hakkı"
    long_narration = (
        "Havayolu uçuş rötarında gizli yolcu tazminatı hakkı çoğu kişinin gözden kaçırdığı "
        "önemli bir ayrıntıdır ve yolcular başvuru koşullarını önceden mutlaka incelemelidir."
    )
    short_narration = "Yolcular resmi başvuru koşullarını ayrıca kontrol etmelidir."
    scenes = []
    for index in range(4):
        scenes.append({
            "narration": long_narration if index < 3 else short_narration,
            "scene_description": f"Distinct airport scene showing passenger rights detail {index}",
            "search_queries": [
                f"airport passenger rights scene {index}",
                f"flight delay terminal scene {index}",
            ],
            "claim_ids": [f"claim-{index}"],
            "source_citation": f"Source {index}",
            "selected_video": {"path": f"video-{index}.mp4"},
            "visual_intent": {"subject": f"airport scene {index}"},
        })
    return {
        "title": title,
        "niche_id": "1_news_flash",
        "full_narration": " ".join(scene["narration"] for scene in scenes),
        "scenes": scenes,
        "topic_intelligence": {"resolved_niche": "1_news_flash"},
    }


def test_ai_repair_preserves_existing_scene_metadata_and_adds_needed_scenes():
    plan = _warning_plan()
    response = MagicMock()
    response.choices = [
        MagicMock(message=MagicMock(content=json.dumps(_repair_response(), ensure_ascii=False)))
    ]

    with (
        patch(
            "scenes.generator._configured_script_providers",
            return_value=[("OpenAI", "test-key", "https://example.invalid/v1", "test-model")],
        ),
        patch("scenes.generator._call", return_value=response) as call,
    ):
        result = repair_script_quality(
            plan,
            ["duration_near_band_edge:42.86", "opening_repeats_title:1.00"],
        )

    assert result["status"] == "candidate"
    repaired = result["plan"]
    assert len(repaired["scenes"]) == 6
    assert 95 <= sum(len(scene["narration"].split()) for scene in repaired["scenes"]) <= 110
    for index in range(4):
        old_scene = plan["scenes"][index]
        new_scene = repaired["scenes"][index]
        assert new_scene["narration"] != old_scene["narration"]
        for key in ("scene_description", "search_queries", "claim_ids", "source_citation", "selected_video", "visual_intent"):
            assert new_scene[key] == old_scene[key]
    assert repaired["scenes"][4]["scene_description"]
    assert len(repaired["scenes"][4]["search_queries"]) >= 2
    assert repaired["topic_intelligence"] == plan["topic_intelligence"]
    user_prompt = call.call_args.args[1]["messages"][1]["content"]
    assert plan["title"] in user_prompt
    assert "başlığı tekrarlamamalı" in user_prompt


def test_ai_repair_reports_unavailable_or_invalid_provider_without_mutating_plan():
    plan = _warning_plan()
    before = deepcopy(plan)
    with patch("scenes.generator._configured_script_providers", return_value=[]):
        result = repair_script_quality(plan, ["shorter_than_viewmade_style_default"])
    assert result["status"] == "provider_unavailable"
    assert result["plan"] == before

    invalid_response = MagicMock()
    invalid_response.choices = [
        MagicMock(message=MagicMock(content=json.dumps({"scenes": []})))
    ]
    with (
        patch(
            "scenes.generator._configured_script_providers",
            return_value=[("OpenAI", "test-key", "https://example.invalid/v1", "test-model")],
        ),
        patch("scenes.generator._call", return_value=invalid_response),
    ):
        result = repair_script_quality(plan, ["shorter_than_viewmade_style_default"])
    assert result["status"] == "failed"
    assert result["plan"] == before


def test_ai_repair_replaces_only_invalid_scene_visual_metadata():
    plan = _warning_plan()
    plan["scenes"][0]["scene_description"] = "placeholder"
    plan["scenes"][0]["search_queries"] = []
    response = MagicMock()
    response.choices = [
        MagicMock(message=MagicMock(content=json.dumps(_repair_response(), ensure_ascii=False)))
    ]

    with (
        patch(
            "scenes.generator._configured_script_providers",
            return_value=[("OpenAI", "test-key", "https://example.invalid/v1", "test-model")],
        ),
        patch("scenes.generator._call", return_value=response),
    ):
        result = repair_script_quality(
            plan,
            ["scene_0_visual_description_invalid", "scene_0_queries_insufficient"],
        )

    assert result["status"] == "candidate"
    repaired_scene = result["plan"]["scenes"][0]
    assert repaired_scene["scene_description"] == _repair_response()["scenes"][0]["scene_description"]
    assert len(repaired_scene["search_queries"]) == 2
    assert repaired_scene["claim_ids"] == plan["scenes"][0]["claim_ids"]
    assert result["plan"]["scenes"][1]["scene_description"] == plan["scenes"][1]["scene_description"]


def test_script_generation_recompiles_and_rechecks_ai_repair():
    plan = _warning_plan()
    response = MagicMock()
    response.choices = [
        MagicMock(message=MagicMock(content=json.dumps(_repair_response(), ensure_ascii=False)))
    ]
    research_router = importlib.import_module("routers.research_router")
    media_router = importlib.import_module("routers.media_router")

    with (
        patch.object(research_router, "generate_scenes", return_value=deepcopy(plan)),
        patch.object(research_router, "build_topic_research_brief", return_value={}),
        patch.object(
            media_router,
            "auto_fetch_videos_for_scenes",
            side_effect=lambda scenes, **_kwargs: scenes,
        ),
        patch(
            "scenes.generator._configured_script_providers",
            return_value=[("OpenAI", "test-key", "https://example.invalid/v1", "test-model")],
        ),
        patch("scenes.generator._call", return_value=response),
    ):
        result = TestClient(app).post(
            "/api/script/generate",
            json={
                "keyword": plan["title"],
                "niche": "1_news_flash",
                "language": "tr",
            },
        )

    assert result.status_code == 200, result.text
    data = result.json()
    assert data["script_quality_repair"]["status"] == "repaired"
    assert data["script_quality"]["scene_count"] == 6
    assert data["script_quality"]["duration"] >= 50
    assert not data["script_quality"]["hard_fail"]
    assert not any(
        warning.startswith((
            "duration_near_band_edge:",
            "scene_",
            "opening_repeats_title:",
        ))
        or warning == "shorter_than_viewmade_style_default"
        for warning in data["script_quality"]["warnings"]
    )


def test_script_generation_repairs_hard_title_issue_without_warnings():
    plan = _warning_plan()
    repaired_scenes = _repair_response()["scenes"]
    plan["title"] = (
        "Uçuş rötarında yolcuların tazminat hakkı ve başvuru koşulları "
        "hakkında kapsamlı ve güncel bilgilendirme rehberi"
    )
    plan["scenes"] = [
        {**scene, "duration": 53.5 / 6}
        for scene in repaired_scenes
    ]
    plan["full_narration"] = " ".join(scene["narration"] for scene in plan["scenes"])
    research_router = importlib.import_module("routers.research_router")
    media_router = importlib.import_module("routers.media_router")
    response = MagicMock()
    response.choices = [
        MagicMock(message=MagicMock(content=json.dumps(_repair_response(), ensure_ascii=False)))
    ]

    with (
        patch.object(research_router, "generate_scenes", return_value=deepcopy(plan)),
        patch.object(research_router, "build_topic_research_brief", return_value={}),
        patch.object(
            media_router,
            "auto_fetch_videos_for_scenes",
            side_effect=lambda scenes, **_kwargs: scenes,
        ),
        patch(
            "scenes.generator._configured_script_providers",
            return_value=[("OpenAI", "test-key", "https://example.invalid/v1", "test-model")],
        ),
        patch("scenes.generator._call", return_value=response),
    ):
        result = TestClient(app).post(
            "/api/script/generate",
            json={
                "keyword": plan["title"],
                "niche": "1_news_flash",
                "language": "tr",
            },
        )

    assert result.status_code == 200, result.text
    data = result.json()
    assert any(
        finding.startswith("title_length_out_of_bounds:")
        for finding in data["script_quality_repair"]["findings_before"]
    )
    assert data["script_quality_repair"]["status"] == "repaired"
    assert len(data["plan"]["title"]) <= 100
    assert not data["script_quality"]["hard_fail"]


def test_timeline_preflight_repairs_quality_findings_before_render():
    plan = {
        **_warning_plan(),
        "title": (
            "Uçuş rötarında yolcuların tazminat hakkı ve başvuru koşulları "
            "hakkında kapsamlı ve güncel bilgilendirme rehberi"
        ),
        "scenes": [
            {**scene, "duration": 53.5 / 6}
            for scene in _repair_response()["scenes"]
        ],
    }
    plan["full_narration"] = " ".join(scene["narration"] for scene in plan["scenes"])
    response = MagicMock()
    response.choices = [
        MagicMock(message=MagicMock(content=json.dumps(_repair_response(), ensure_ascii=False)))
    ]

    with (
        patch(
            "scenes.generator._configured_script_providers",
            return_value=[("OpenAI", "test-key", "https://example.invalid/v1", "test-model")],
        ),
        patch("scenes.generator._call", return_value=response),
    ):
        result = TestClient(app).post(
            "/api/plan/validate",
            json={
                "plan": plan,
                "title": plan["title"],
                "niche": "1_news_flash",
                "language": "tr",
                "auto_repair": True,
            },
        )

    assert result.status_code == 200, result.text
    data = result.json()
    assert data["quality_repair"]["status"] == "repaired"
    assert len(data["plan"]["title"]) <= 100
    assert data["ok"]
    assert not data["script_quality"]["hard_fail"]


def test_timeline_preflight_reports_unrepaired_hard_quality_issue():
    plan = {
        **_warning_plan(),
        "title": (
            "Uçuş rötarında yolcuların tazminat hakkı ve başvuru koşulları "
            "hakkında kapsamlı ve güncel bilgilendirme rehberi"
        ),
        "scenes": [
            {**scene, "duration": 53.5 / 6}
            for scene in _repair_response()["scenes"]
        ],
    }
    plan["full_narration"] = " ".join(scene["narration"] for scene in plan["scenes"])
    with patch("scenes.generator._configured_script_providers", return_value=[]):
        result = TestClient(app).post(
            "/api/plan/validate",
            json={
                "plan": plan,
                "title": plan["title"],
                "niche": "1_news_flash",
                "language": "tr",
                "auto_repair": True,
            },
        )

    assert result.status_code == 200, result.text
    data = result.json()
    assert data["quality_repair"]["status"] == "provider_unavailable"
    assert data["ok"] == data["narration_ok"]
    assert data["narration_ok"]
    assert data["script_quality"]["hard_fail"]


def test_render_endpoint_repairs_hard_quality_issue_before_queueing():
    import importlib

    plan = {
        **_warning_plan(),
        "title": (
            "Uçuş rötarında yolcuların tazminat hakkı ve başvuru koşulları "
            "hakkında kapsamlı ve güncel bilgilendirme rehberi"
        ),
        "scenes": [
            {**scene, "duration": 53.5 / 6}
            for scene in _repair_response()["scenes"]
        ],
    }
    plan["full_narration"] = " ".join(scene["narration"] for scene in plan["scenes"])
    video_router = importlib.import_module("routers.video_router")
    response = MagicMock()
    response.choices = [
        MagicMock(message=MagicMock(content=json.dumps(_repair_response(), ensure_ascii=False)))
    ]

    try:
        with (
            patch.object(video_router, "process_video_task") as process_task,
            patch(
                "scenes.generator._configured_script_providers",
                return_value=[("OpenAI", "test-key", "https://example.invalid/v1", "test-model")],
            ),
            patch("scenes.generator._call", return_value=response),
        ):
            result = TestClient(app).post(
                "/api/video/render",
                json={
                    "keyword": plan["title"],
                    "niche": "1_news_flash",
                    "language": "tr",
                    "plan": plan,
                },
            )
            assert result.status_code == 200, result.text
            assert result.json()["script_quality_repair"]["status"] == "repaired"
            process_task.assert_called_once()
            queued_request = process_task.call_args.args[0]
            assert queued_request.plan["title"] == _repair_response()["title"]
    finally:
        state.is_rendering_active = False
