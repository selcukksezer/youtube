import time

from visuals import registry
from visuals.license import License, LicenseInfo
from visuals.providers import PROVIDERS, Candidate


def test_new_free_providers_registered():
    for key in ("pexels_img", "pixabay_img", "met_img"):
        assert key in PROVIDERS
    assert PROVIDERS["met_img"].key_env is None


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
