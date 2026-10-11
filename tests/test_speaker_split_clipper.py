from importlib import import_module
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from services.highlight_clipper import _speaker_split_vf
from services.highlight_clipper import vertical_crop_x_for_center
from visuals.face_reframe import select_speaker_face_pair

clipper_router = import_module("routers.clipper_router")


def _source_resolver(source_path):
    def resolve(payload):
        assert payload.get("source_path") == source_path
        return source_path

    return resolve


def _selected_highlights(highlights, **options):
    assert isinstance(highlights, list)
    assert "num_clips" in options
    return [{"start_time": 1.0, "end_time": 8.0, "score": 90}]


def test_speaker_face_pair_requires_two_separated_faces():
    boxes = [
        (220, 100, 120, 140),
        (225, 105, 110, 130),
        (1180, 90, 150, 160),
    ]

    pair = select_speaker_face_pair(boxes, frame_width=1920, frame_height=1080)

    assert pair is not None
    assert pair[0][0] < pair[1][0]
    assert select_speaker_face_pair(boxes[:2], 1920, 1080) is None
    assert select_speaker_face_pair([(220, 100, 120, 140), (430, 100, 120, 140)], 1920, 1080) is None


def test_speaker_split_filter_stacks_two_face_centered_crops():
    graph = _speaker_split_vf(
        1920,
        1080,
        ((0.3, 0.4), (0.7, 0.4)),
    )

    assert "[vc]split=2" in graph
    assert "crop=1214:1078" in graph
    assert "vstack=inputs=2" in graph
    assert "scale=1080:960" in graph


def test_vertical_crop_x_centers_and_clamps_active_speaker():
    assert vertical_crop_x_for_center(1920, 1080, 0.5) == 1166
    assert vertical_crop_x_for_center(1920, 1080, 0.05) == 0
    assert vertical_crop_x_for_center(1920, 1080, 0.95) == 2332


def test_speaker_split_route_reports_stack_and_fallback(tmp_path, monkeypatch):
    app = FastAPI()
    app.include_router(clipper_router.router)
    client = TestClient(app)
    source_path = str(tmp_path / "source.mp4")
    monkeypatch.setattr(clipper_router.config, "OUTPUT_DIR", str(tmp_path))

    def resolve_source(payload):
        assert payload.get("speaker_split") is True
        return source_path

    def select_highlights(raw, **options):
        assert isinstance(raw, list)
        assert "num_clips" in options
        return [
            {"start_time": 1.0, "end_time": 8.0, "score": 90},
        ]
    monkeypatch.setattr(clipper_router, "_resolve_source", resolve_source)
    monkeypatch.setattr(clipper_router, "select_highlights", select_highlights)

    with (
        patch.object(
            clipper_router,
            "detect_speaker_split_centers",
            return_value=((0.3, 0.4), (0.7, 0.4)),
        ) as detect,
        patch.object(clipper_router, "cut_ranges_vertical", return_value="stacked.mp4") as cut,
    ):
        stacked = client.post(
            "/api/clipper",
            json={
                "highlights": [{"start_time": 1.0, "end_time": 8.0}],
                "render": True,
                "source_path": source_path,
                "speaker_split": True,
            },
        )

    assert stacked.status_code == 200
    assert stacked.json()["clips"][0]["speaker_layout"] == "split_stack"
    assert cut.call_args.kwargs["speaker_split_centers"] == ((0.3, 0.4), (0.7, 0.4))
    detect.assert_called_once()

    with (
        patch.object(clipper_router, "detect_speaker_split_centers", return_value=None),
        patch.object(clipper_router, "cut_ranges_vertical", return_value="crop.mp4"),
    ):
        fallback = client.post(
            "/api/clipper",
            json={
                "highlights": [{"start_time": 1.0, "end_time": 8.0}],
                "render": True,
                "source_path": source_path,
                "speaker_split": True,
            },
        )

    assert fallback.status_code == 200
    clip = fallback.json()["clips"][0]
    assert clip["speaker_layout"] == "vertical_crop"
    assert "güvenilir biçimde algılanamadı" in clip["speaker_layout_reason"]


def test_active_speaker_route_stacks_conversation_locally(tmp_path, monkeypatch):
    from services.speaker_activity import SpeakerActivityResult

    app = FastAPI()
    app.include_router(clipper_router.router)
    client = TestClient(app)
    source_path = str(tmp_path / "source.mp4")
    monkeypatch.setattr(clipper_router.config, "OUTPUT_DIR", str(tmp_path))
    monkeypatch.setattr(
        clipper_router,
        "_resolve_source",
        _source_resolver(source_path),
    )
    monkeypatch.setattr(
        clipper_router,
        "select_highlights",
        _selected_highlights,
    )
    centers = ((0.3, 0.4), (0.7, 0.4))
    with (
        patch.object(clipper_router, "detect_speaker_split_centers", return_value=centers),
        patch(
            "services.speaker_activity.analyze_speaker_activity",
            return_value=SpeakerActivityResult((0.5, 0.5), None, True, 20),
        ) as analyze,
        patch.object(clipper_router, "cut_ranges_vertical", return_value="stacked.mp4") as cut,
    ):
        response = client.post(
            "/api/clipper",
            json={
                "highlights": [{"start_time": 1.0, "end_time": 8.0}],
                "render": True,
                "source_path": source_path,
                "speaker_activity_layout": True,
            },
        )

    assert response.status_code == 200
    assert response.json()["clips"][0]["speaker_layout"] == "split_stack"
    assert cut.call_args.kwargs["speaker_split_centers"] == centers
    assert cut.call_args.kwargs["crop_center_x"] is None
    analyze.assert_called_once_with(source_path, [(1.0, 8.0)], centers)


def test_active_speaker_route_crops_to_dominant_speaker(tmp_path, monkeypatch):
    from services.speaker_activity import SpeakerActivityResult

    app = FastAPI()
    app.include_router(clipper_router.router)
    client = TestClient(app)
    source_path = str(tmp_path / "source.mp4")
    monkeypatch.setattr(clipper_router.config, "OUTPUT_DIR", str(tmp_path))
    monkeypatch.setattr(
        clipper_router,
        "_resolve_source",
        _source_resolver(source_path),
    )
    monkeypatch.setattr(
        clipper_router,
        "select_highlights",
        _selected_highlights,
    )
    centers = ((0.3, 0.4), (0.7, 0.4))
    with (
        patch.object(clipper_router, "detect_speaker_split_centers", return_value=centers),
        patch(
            "services.speaker_activity.analyze_speaker_activity",
            return_value=SpeakerActivityResult((0.9, 0.1), 0, False, 20),
        ),
        patch.object(clipper_router, "cut_ranges_vertical", return_value="crop.mp4") as cut,
    ):
        response = client.post(
            "/api/clipper",
            json={
                "highlights": [{"start_time": 1.0, "end_time": 8.0}],
                "render": True,
                "source_path": source_path,
                "speaker_activity_layout": True,
            },
        )

    assert response.status_code == 200
    clip = response.json()["clips"][0]
    assert clip["speaker_layout"] == "vertical_crop"
    assert "etkinlik pencerelerinin" in clip["speaker_layout_reason"]
    assert cut.call_args.kwargs["speaker_split_centers"] is None
    assert cut.call_args.kwargs["crop_center_x"] == 0.3
