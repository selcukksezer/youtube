import os
import time
from types import SimpleNamespace

import pytest
import requests
from unittest.mock import Mock

from visuals import providers, registry
from visuals.license import License, LicenseInfo
from visuals.providers import PROVIDERS, Candidate


def test_new_free_providers_registered():
    for key in ("pexels_img", "pixabay_img", "met_img"):
        assert key in PROVIDERS
    assert PROVIDERS["met_img"].key_env is None


def test_coverr_search_uses_configured_api_key(monkeypatch):
    def fake_env(name):
        assert name == "COVERR_API_KEY"
        return "test-coverr-key"

    monkeypatch.setattr(providers, "_env", fake_env)
    request = {}

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"videos": []}

    def fake_get(url, **kwargs):
        request.update(url=url, **kwargs)
        return Response()

    monkeypatch.setattr(providers._session, "get", fake_get)

    assert providers.search_coverr("city", per_page=4) == []
    assert request["headers"]["Authorization"] == "test-coverr-key"


def test_pexels_retries_transient_timeout(monkeypatch):
    monkeypatch.setattr(providers, "_env", Mock(return_value="test-pexels-key"))

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"videos": []}

    mock_get = Mock(side_effect=[requests.Timeout("temporary timeout"), Response()])
    mock_sleep = Mock()
    monkeypatch.setattr(providers._session, "get", mock_get)
    monkeypatch.setattr(providers.time, "sleep", mock_sleep)

    assert providers.search_pexels("city") == []
    assert mock_get.call_count == 2
    mock_sleep.assert_called_once_with(0.25)


def test_pexels_does_not_retry_rate_limit(monkeypatch):
    monkeypatch.setattr(providers, "_env", Mock(return_value="test-pexels-key"))
    response = SimpleNamespace(status_code=429)
    mock_get = Mock(side_effect=requests.HTTPError("429 Too Many Requests", response=response))
    monkeypatch.setattr(providers._session, "get", mock_get)
    monkeypatch.setattr(providers.time, "sleep", Mock())

    with pytest.raises(requests.HTTPError):
        providers.search_pexels("city")

    mock_get.assert_called_once()


def test_429_puts_provider_on_cooldown(monkeypatch):
    registry._cooldowns.clear()
    registry._note_failure("wikimedia", RuntimeError("429 Client Error: Too Many Requests"))
    assert registry.provider_cooling_down("wikimedia")
    keys = [s.key for s in registry.ordered_providers("10_religious_quotes")]
    assert "wikimedia" not in keys
    registry._cooldowns["wikimedia"] = time.time() - 1
    assert not registry.provider_cooling_down("wikimedia")


def test_repeated_timeouts_cool_down(monkeypatch):
    registry._cooldowns.clear()
    registry._fail_counts.clear()
    registry._note_failure("openverse", RuntimeError("Read timed out"))
    assert not registry.provider_cooling_down("openverse")
    registry._note_failure("openverse", RuntimeError("Read timed out"))
    assert registry.provider_cooling_down("openverse")
    registry._cooldowns.clear()


def test_recent_assets_are_penalised(monkeypatch, tmp_path):
    monkeypatch.setattr(registry, "_RECENT_FILE", str(tmp_path / "recent.json"))
    monkeypatch.setattr(registry, "_recent_uids", None)
    registry.reset_used()

    def make(cid):
        return Candidate(
            source="pexels", id=cid, url="https://x/y.mp4", kind="video", width=1080, height=1920,
            duration=7, title="mosque dome interior",
            license=LicenseInfo(License.PEXELS, "pexels"),
        )

    fresh = registry.score_candidate(make("px_1"), "mosque dome interior")
    registry._persist_recent("pexels:px_2")
    old = registry.score_candidate(make("px_2"), "mosque dome interior")
    assert 0 < old < fresh


def test_query_match_outweighs_incidental_narration_terms():
    def make(cid, title):
        return Candidate(
            source="pexels", id=cid, url=f"https://x/{cid}.mp4", kind="video",
            width=1080, height=1920, duration=7, title=title,
            license=LicenseInfo(License.PEXELS, "pexels"),
        )

    exact = make("exact", "skyscraper glass facade")
    incidental = make("incidental", "skyscraper bridge beach")
    narration = "A bridge near the beach frames the skyscraper"

    exact_score = registry.score_candidate(
        exact, "skyscraper glass facade", narration=narration
    )
    incidental_score = registry.score_candidate(
        incidental, "skyscraper glass facade", narration=narration
    )

    assert exact_score > incidental_score
    assert exact.semantic_evidence["query_match_score"] == 1.0
    assert incidental.semantic_evidence["matched_narration_terms"] == ["beach", "bridge"]


def test_ranked_candidates_keep_best_match_for_duplicate_asset():
    from visuals.fetch import _rank_scored_candidates

    duplicate_weak = Candidate(source="pexels", id="same", url="https://x/1", kind="video")
    duplicate_strong = Candidate(source="pexels", id="same", url="https://x/1", kind="video")
    distinct = Candidate(source="pixabay", id="other", url="https://x/2", kind="video")

    ranked = _rank_scored_candidates([
        (40.0, duplicate_weak, "wide query"),
        (75.0, duplicate_strong, "specific query"),
        (60.0, distinct, "other query"),
    ])

    assert [(score, candidate.uid, query) for score, candidate, query in ranked] == [
        (75.0, duplicate_strong.uid, "specific query"),
        (60.0, distinct.uid, "other query"),
    ]


def test_broaden_queries_and_expansion(tmp_path, monkeypatch):
    from visuals import fetch
    wide = fetch._broaden_queries(["islamic prayer mosque dawn"], "10_religious_quotes")
    assert "islamic prayer" in wide and "mosque architecture" in wide

    calls = []
    real = fetch.fetch_open_visual
    def fake_providers(*a, **k):
        return []
    monkeypatch.setattr(fetch, "ordered_providers", fake_providers)
    monkeypatch.setattr(fetch, "_procedural_enabled", lambda: False)
    monkeypatch.setattr("services.public_apis_catalog.fetch_openverse_media", lambda *a, **k: [])
    monkeypatch.setattr("services.public_apis_catalog.fetch_met_museum_artworks", lambda *a, **k: [])
    out = fetch.fetch_open_visual(["a b c d"], project_dir=str(tmp_path), narration="x y z w",
                                  niche_id="10_religious_quotes", allow_procedural=True)
    assert out is None


def test_empty_queries_are_built_from_narration_without_scope_error(tmp_path, monkeypatch):
    from visuals import fetch

    built = []

    def fake_build_shot_queries(**kwargs):
        built.append(kwargs)
        return ["mosque prayer"]

    def no_providers(niche_id):
        assert niche_id == "10_religious_quotes"
        return []

    def no_openverse_media(query, page_size=3):
        assert query
        assert page_size == 3
        return []

    def no_met_museum_artworks(query, limit=2):
        assert query
        assert limit == 2
        return []

    monkeypatch.setattr(fetch, "build_shot_queries", fake_build_shot_queries)
    monkeypatch.setattr(fetch, "ordered_providers", no_providers)
    monkeypatch.setattr(
        "services.public_apis_catalog.fetch_openverse_media",
        no_openverse_media,
    )
    monkeypatch.setattr(
        "services.public_apis_catalog.fetch_met_museum_artworks",
        no_met_museum_artworks,
    )

    result = fetch.fetch_open_visual(
        queries=[],
        project_dir=str(tmp_path),
        narration="Bir camide sabah namazı",
        niche_id="10_religious_quotes",
        allow_procedural=False,
    )

    assert result is None
    assert built[0]["narration"] == "Bir camide sabah namazı"


def test_hook_window_uses_sharp_exposed_stable_source_segment(monkeypatch):
    from PIL import Image, ImageDraw
    from types import SimpleNamespace
    from visuals import fetch

    dark = Image.new("L", (120, 214), 15)
    detailed = Image.new("L", (120, 214), 0)
    draw = ImageDraw.Draw(detailed)
    for x in range(0, 120, 8):
        draw.rectangle((x, 0, x + 3, 213), fill=200 if (x // 8) % 2 else 50)
    frames = [dark.copy() for _ in range(4)] + [detailed.copy() for _ in range(8)]
    command_seen = {}

    def fake_run(command, **kwargs):
        assert kwargs["timeout"] == 30
        command_seen["command"] = command
        pattern = command[-1]
        for index, frame in enumerate(frames, start=1):
            frame.save(os.path.join(os.path.dirname(pattern), f"frame_{index:03d}.jpg"))
        return SimpleNamespace(returncode=0, stderr=b"")

    monkeypatch.setattr(fetch.imageio_ffmpeg, "get_ffmpeg_exe", lambda: "ffmpeg")
    monkeypatch.setattr(fetch.subprocess, "run", fake_run)

    start = fetch._best_hook_window_start("source.mp4", 2.0, 6.0)

    assert start == 2.5
    assert "-frames:v" in command_seen["command"]
    assert "fps=2.000" in command_seen["command"][command_seen["command"].index("-vf") + 1]


def test_quality_window_is_only_selected_for_the_opening_stock_video(monkeypatch):
    from visuals import fetch

    candidate = Candidate(
        source="pexels",
        id="hook-window",
        url="https://example.test/video.mp4",
        kind="video",
        duration=15.0,
        license=LicenseInfo(License.PEXELS, "pexels"),
    )
    window_calls = []
    normalize_calls = []

    def choose_window(path, target_duration, source_duration):
        window_calls.append((path, target_duration, source_duration))
        return 2.5

    def normalize(path, output, duration, kind, **kwargs):
        normalize_calls.append((path, duration, kind, kwargs))
        return output

    monkeypatch.setattr(fetch, "_best_hook_window_start", choose_window)
    monkeypatch.setattr(fetch, "_normalize_clip", normalize)

    fetch._normalize_candidate("raw.mp4", "hook.mp4", 5.0, candidate, scene_index=0)
    fetch._normalize_candidate("raw.mp4", "later.mp4", 5.0, candidate, scene_index=1)

    assert window_calls == [("raw.mp4", 5.0, 15.0)]
    assert normalize_calls == [
        ("raw.mp4", 5.0, "video", {"start_sec": 2.5}),
        ("raw.mp4", 5.0, "video", {}),
    ]


def test_fetch_open_visual_applies_hook_window_once_per_scene_set(tmp_path, monkeypatch, request):
    from types import SimpleNamespace
    from visuals import fetch

    fetch.reset_job_manifest()
    request.addfinalizer(fetch.reset_job_manifest)
    candidates = [
        Candidate(
            source="pexels",
            id=f"clip-{index}",
            url=f"https://example.test/clip-{index}.mp4",
            kind="video",
            duration=15.0,
            license=LicenseInfo(License.PEXELS, "pexels"),
        )
        for index in range(2)
    ]
    search_index = 0
    selected_windows = []
    normalized = []

    def fake_search(spec, query, per_page=8):
        nonlocal search_index
        assert spec.key == "pexels"
        assert query == "historic temple"
        assert per_page == 8
        candidate = candidates[search_index]
        search_index += 1
        return [candidate]

    def fake_score(candidate, query, narration="", target_duration=7.0):
        assert query == "historic temple"
        assert narration == "An ancient temple"
        assert target_duration == 5.0
        candidate.topic_match_score = 0.5
        return 80.0

    def fake_normalize(source, output, duration, kind, **kwargs):
        normalized.append((source, duration, kind, kwargs))
        with open(output, "wb") as stream:
            stream.write((os.path.basename(output) * 2000).encode())
        return output

    def choose_window(source, target_duration, source_duration):
        selected_windows.append((source, target_duration, source_duration))
        return 2.5

    def fake_ordered_providers(niche):
        assert not niche
        return [SimpleNamespace(key="pexels")]

    def fake_download(url, path):
        assert url.startswith("https://example.test/")
        assert path.endswith("_raw.mp4")
        return True

    def verify_integrity(path, min_duration=0.5):
        assert path.endswith("_raw.mp4")
        assert min_duration == 0.5
        return {"valid": True}

    monkeypatch.setattr(fetch, "ordered_providers", fake_ordered_providers)
    monkeypatch.setattr(fetch, "search_provider", fake_search)
    monkeypatch.setattr(fetch, "score_candidate", fake_score)
    monkeypatch.setattr(fetch, "_download", fake_download)
    monkeypatch.setattr(fetch, "_normalize_clip", fake_normalize)
    monkeypatch.setattr(fetch, "_best_hook_window_start", choose_window)
    monkeypatch.setattr("system_resilience.verify_stock_video_integrity", verify_integrity)

    first = fetch.fetch_open_visual(
        ["historic temple"],
        scene_index=0,
        project_dir=str(tmp_path),
        target_duration=5.0,
        narration="An ancient temple",
        allow_procedural=False,
    )
    second = fetch.fetch_open_visual(
        ["historic temple"],
        scene_index=1,
        project_dir=str(tmp_path),
        target_duration=5.0,
        narration="An ancient temple",
        allow_procedural=False,
    )

    assert first and second
    assert len(selected_windows) == 1
    assert normalized == [
        (str(tmp_path / "s000_pexels_raw.mp4"), 5.0, "video", {"start_sec": 2.5}),
        (str(tmp_path / "s001_pexels_raw.mp4"), 5.0, "video", {}),
    ]
    fetch.reset_job_manifest()


def test_normalize_clip_seeks_to_selected_source_window(monkeypatch, tmp_path):
    from types import SimpleNamespace
    from visuals import fetch

    output = tmp_path / "normalized.mp4"
    commands = []

    def fake_run(command, **kwargs):
        assert kwargs["timeout"] == 120
        commands.append(command)
        output.write_bytes(b"x" * 10_001)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(fetch.imageio_ffmpeg, "get_ffmpeg_exe", lambda: "ffmpeg")
    monkeypatch.setattr(fetch.subprocess, "run", fake_run)

    result = fetch._normalize_clip(
        "source.mp4",
        str(output),
        5.0,
        "video",
        start_sec=2.5,
    )

    assert result == str(output)
    assert commands[0][commands[0].index("-ss") + 1] == "2.500"
    assert commands[0].index("-ss") < commands[0].index("-i")
