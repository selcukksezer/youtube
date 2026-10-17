"""Frontend-Backend contract verification tests (Pass 5, Pass 6 & Wizard Steps 1-3)."""
from pathlib import Path
from fastapi.testclient import TestClient
from server import app

ROOT_DIR = Path(__file__).resolve().parents[1]


def test_pass_5_and_pass_6_frontend_backend_contracts():
    client = TestClient(app)

    # 1. Analytics / SEO / Growth endpoints
    r_ret = client.post("/api/analytics/retention-diagnosis", json={"swipe_away_rate": 0.42, "retention_30s": 0.58, "duration_sec": 45})
    assert r_ret.status_code == 200
    assert r_ret.json()["status"] == "ok"
    assert "diagnosis" in r_ret.json() or "primary_issue" in r_ret.json()

    r_sb = client.post("/api/analytics/shadowban-diagnosis", json={"recent_views": [15, 22, 18], "avg_views": 18, "shorts_feed_share_pct": 12.0})
    assert r_sb.status_code == 200
    assert r_sb.json()["status"] == "ok"

    r_seo = client.get("/api/seo/viral_metadata", params={"topic": "Stoa Disiplini", "niche": "6_stoic_philosophy", "lang": "tr"})
    assert r_seo.status_code == 200
    assert "pinned_comment" in r_seo.json() or "titles" in r_seo.json() or "status" in r_seo.json()

    r_mon = client.get("/api/analytics/monetization-progress")
    assert r_mon.status_code == 200

    r_lb = client.get("/api/analytics/niche-leaderboard")
    assert r_lb.status_code == 200

    # 2. V2 project creation with frontend payload fields
    r_v2 = client.post(
        "/api/v2/projects",
        json={
            "title": "Stoik Test",
            "topic": "Marcus Aurelius",
            "niche": "6_stoic_philosophy",
            "language": "tr",
            "visual_mode": "auto",
            "plan": {"title": "Stoik Test", "scenes": [{"narration": "Test sahnesi", "duration": 4.0}]},
        },
    )
    assert r_v2.status_code == 200
    v2_data = r_v2.json()
    assert v2_data["topic"] == "Marcus Aurelius"
    assert v2_data["project"]["id"] == v2_data["id"]

    # 3. Pacing guard warnings alias & Grounding audit flagged_count/flagged_scenes
    r_pg = client.post("/api/pacing/guard", json={"scenes": [{"narration": "Kısa sahne", "duration": 4.0}]})
    assert r_pg.status_code == 200
    assert "warnings" in r_pg.json()
    assert "violations" in r_pg.json()

    r_ga = client.post(
        "/api/grounding/audit",
        json={
            "niche_id": "6_stoic_philosophy",
            "scenes": [{"narration": "Marcus Aurelius Roma İmparatorudur.", "scene_description": "Ancient Roman marble bust"}],
        },
    )
    assert r_ga.status_code == 200
    assert "flagged_count" in r_ga.json()
    assert "flagged_scenes" in r_ga.json()

    # 4. Voicelab library tracks & Niche AB variants top-level variants
    r_vl = client.get("/api/voicelab/library")
    assert r_vl.status_code == 200
    assert "tracks" in r_vl.json()

    r_ab = client.get("/api/niches/6_stoic_philosophy/ab_variants", params={"topic": "Stoa"})
    assert r_ab.status_code == 200
    assert isinstance(r_ab.json().get("variants"), list)
    assert len(r_ab.json()["variants"]) >= 1

    # 5. Punch-in curve, Helios enhance, Kinetic pages, Syndication crosspost
    r_pi = client.post("/api/punch_in/curve", json={"duration_sec": 3.5, "fps": 30, "intensity": 0.14})
    assert r_pi.status_code == 200
    assert isinstance(r_pi.json().get("curve"), list)
    assert len(r_pi.json()["curve"]) > 0

    r_he = client.post(
        "/api/helios/enhance_scenes",
        json={
            "scenes": [{"narration": "Stoik felsefe", "scene_description": "Ancient temple"}],
            "style_preset": "cinematic_dramatic",
            "character_anchor": "Roman philosopher",
        },
    )
    assert r_he.status_code == 200
    assert "Ancient temple" in r_he.json()["scenes"][0]["helios_prompt"]

    r_kp = client.post(
        "/api/subtitles/kinetic_pages",
        json={"word_timings": [{"word": "Merhaba", "start": 0.0, "end": 0.3}, {"word": "dünya", "start": 0.32, "end": 0.64}], "max_words_per_page": 2},
    )
    assert r_kp.status_code == 200
    assert len(r_kp.json().get("pages", [])) >= 1

    r_sc = client.post(
        "/api/syndication/crosspost",
        json={"video_path": "output/test.mp4", "title": "Test Video", "platforms": ["youtube_shorts", "tiktok", "instagram_reels"]},
    )
    assert r_sc.status_code == 200
    assert "export_bundle" in r_sc.json().get("results", r_sc.json())

    # 6. Static JS DOM ID & Wizard Step 1-3 contracts
    studio_ai_js = (ROOT_DIR / "static/js/studio-ai-tools.js").read_text(encoding="utf-8")
    assert "studio-advanced-engine-output" in studio_ai_js
    assert "box.classList.remove('hidden')" in studio_ai_js

    tl_js = (ROOT_DIR / "static/js/timeline-preview.js").read_text(encoding="utf-8")
    assert "tl-input-char-desc" in tl_js
    assert "outEl.classList.remove('hidden')" in tl_js

    step3_js = (ROOT_DIR / "static/js/studio-wizard-step3.js").read_text(encoding="utf-8")
    for required_id in (
        "wiz-visual-engine-cards",
        "wiz-bgm-mood-chips",
        "wiz-ducking-balance-bar",
        "wiz-step3-subtitle-cards",
        "wiz-subtitle-safezone-picker",
        "wiz-split-screen-cards",
        "wiz-fx-quick-bundles",
        "wiz-transition-preview-strip",
        "wiz-sfx-intensity-bar",
        "wiz-watermark-bar",
    ):
        assert required_id in step3_js


def test_pass_8_runtime_log_and_cooldown_fixes(monkeypatch):
    from services import web_fact_researcher as wfr
    from visuals import registry as vis_reg
    from anti_detect.engine import AntiDetectEngine

    called = {"count": 0}
    monkeypatch.setattr(wfr, "research_topic_facts", lambda *a, **kw: called.__setitem__("count", called["count"] + 1) or ["test"])

    # Scenes without numeric/year/superlative claims must not trigger live web lookup
    scenes_no_claims = [{"narration": "Sabah erken uyanmak zihinsel disiplini güçlendirir."}]
    _, report = wfr.verify_and_sanitize_scenes(scenes_no_claims, topic="Stoik Disiplin", web_snippets=None)
    assert called["count"] == 0
    assert report["total_claims"] == 0

    # Keyless serialized provider (openverse) cools down after 2 consecutive timeouts
    vis_reg._cooldowns.pop("openverse", None)
    vis_reg._fail_counts.pop("openverse", None)
    vis_reg._note_failure("openverse", RuntimeError("Read timed out. (read timeout=4)"))
    assert vis_reg.provider_cooling_down("openverse") is False
    vis_reg._note_failure("openverse", RuntimeError("Read timed out. (read timeout=4)"))
    assert vis_reg.provider_cooling_down("openverse") is True
    vis_reg._cooldowns.pop("openverse", None)
    vis_reg._fail_counts.pop("openverse", None)

    # AntiDetectEngine gracefully falls back to project root when relative path fails
    eng = AntiDetectEngine()
    assert eng.profiles_dir.endswith("tokens/browser_profiles")

    rr_text = (ROOT_DIR / "routers/research_router.py").read_text(encoding="utf-8")
    assert 'if compliance.get("render_blocking"):' in rr_text


def test_pass_9_gallery_mood_match_and_dom_fallbacks():
    client = TestClient(app)

    # 1. GET /api/gallery alias returns 200 with videos list (matches /api/videos)
    r_gal = client.get("/api/gallery")
    assert r_gal.status_code == 200
    assert isinstance(r_gal.json().get("videos"), list)

    # 2. POST /api/music/mood_match returns string recommended_track and recommended_mood
    r_mm = client.post(
        "/api/music/mood_match",
        json={"scenes": [{"narration": "Gizemli bir gece ve karanlık sırlar.", "mood": "mysterious"}], "niche_id": "1_dark_psychology"},
    )
    assert r_mm.status_code == 200
    mm_data = r_mm.json()
    assert isinstance(mm_data.get("recommended_mood"), str)
    assert isinstance(mm_data.get("recommended_track"), str)

    # 3. JS DOM contract checks for Step 4 mini strip, bgm-library, phone preview & compliance reset
    step4_js = (ROOT_DIR / "static/js/studio-wizard-step4.js").read_text(encoding="utf-8")
    assert "fetch('/api/videos')" in step4_js

    bgm_js = (ROOT_DIR / "static/js/bgm-library.js").read_text(encoding="utf-8")
    assert "rawTrack.filename" in bgm_js

    phone_js = (ROOT_DIR / "static/js/studio-phone-preview.js").read_text(encoding="utf-8")
    assert "pub-target-channel-select" in phone_js
    assert "tl-select-style-profile" in phone_js

    state_js = (ROOT_DIR / "static/js/state-defaults.js").read_text(encoding="utf-8")
    assert "tl-dur-value" in state_js


def test_pass_10_tts_preview_and_dom_selector_contracts():
    from api_models_ext import TtsPreviewRequest

    # 1. TtsPreviewRequest auto-infers language from BCP-47 voice prefix when language is omitted
    req_en = TtsPreviewRequest(text="Hello world", voice="en-US-GuyNeural")
    assert req_en.language == "en"
    req_tr = TtsPreviewRequest(text="Merhaba dünya", voice="tr-TR-AhmetNeural")
    assert req_tr.language == "tr"

    # 2. Duplicate resetComplianceDashboard removed from timeline.js; normalizeSceneMediaUrl present
    tl_js = (ROOT_DIR / "static/js/timeline.js").read_text(encoding="utf-8")
    assert "function resetComplianceDashboard()" not in tl_js
    assert "function normalizeSceneMediaUrl(" in tl_js

    # 3. Audio preview stop hook wired between timeline-preview.js and studio-phone-preview.js
    tl_prev_js = (ROOT_DIR / "static/js/timeline-preview.js").read_text(encoding="utf-8")
    phone_js = (ROOT_DIR / "static/js/studio-phone-preview.js").read_text(encoding="utf-8")
    assert "window.stopSceneAudioPreview" in tl_prev_js
    assert "stopSceneAudioPreview" in phone_js

    # 4. DOM selector fallbacks in studio-wizard.js, gallery-channels-ux.js, visual-hierarchy-ux.js, state-sync.js
    wiz_js = (ROOT_DIR / "static/js/studio-wizard.js").read_text(encoding="utf-8")
    assert "select-subtitle-preset" in wiz_js
    assert "btn-quick-render" in wiz_js

    gal_ux_js = (ROOT_DIR / "static/js/gallery-channels-ux.js").read_text(encoding="utf-8")
    assert "select-language" in gal_ux_js
    assert ".header-right" in gal_ux_js

    vh_ux_js = (ROOT_DIR / "static/js/visual-hierarchy-ux.js").read_text(encoding="utf-8")
    assert ".header-right" in vh_ux_js

    state_sync_js = (ROOT_DIR / "static/js/state-sync.js").read_text(encoding="utf-8")
    assert "tl-project-title" in state_sync_js


def test_pass_11_full_ui_audit_kids_song_rss_roadmap_and_wizard_alias():
    # 1. Kids Song bridge: refreshKidsSong only fetches /api/kids-song/projects when data.running is true
    plan_ed_js = (ROOT_DIR / "static/js/studio-plan-editor.js").read_text(encoding="utf-8")
    assert "if (data.running) {" in plan_ed_js
    assert "const pRes = await fetch('/api/kids-song/projects');" in plan_ed_js

    # 2. Gallery & RSS: window.loadGallery exposed, RSS preserves existing cards on refresh & falls back cleanly
    gal_js = (ROOT_DIR / "static/js/gallery-channels.js").read_text(encoding="utf-8")
    assert "window.loadGallery = loadGallery;" in gal_js
    assert "FALLBACK_RSS_ITEMS" in gal_js

    # 3. Roadmap 500: Show All (500) button wired in settings-quota.js
    sq_js = (ROOT_DIR / "static/js/settings-quota.js").read_text(encoding="utf-8")
    assert "btn-roadmap-show-all" in sq_js
    assert "renderFilteredRoadmap(true)" in sq_js

    # 4. Wizard alias exposed on window
    wiz_js = (ROOT_DIR / "static/js/studio-wizard.js").read_text(encoding="utf-8")
    assert "window.switchWizardStep" in wiz_js



def test_pass_11_route_uniqueness_hardware_panel_and_style_contracts():
    from fastapi.routing import APIRoute
    from services.style_profile_manager import ContentStyle, style_profile_manager

    # 1. Zero duplicate (method, path) routes registered on FastAPI app
    route_map = {}
    for r in app.routes:
        if isinstance(r, APIRoute):
            for m in r.methods:
                route_map.setdefault((m, r.path), []).append(f"{r.endpoint.__module__}.{r.endpoint.__name__}")
    duplicates = {k: v for k, v in route_map.items() if len(v) > 1}
    assert duplicates == {}, f"Duplicate FastAPI routes detected: {duplicates}"

    # 2. UI style profile dropdown options map to distinct ContentStyle values
    assert style_profile_manager.resolve_style("clean_commercial") == ContentStyle.PRODUCT_AD
    assert style_profile_manager.resolve_style("cinematic_dark") == ContentStyle.STOIC_FACTS
    assert style_profile_manager.resolve_style("cinematic_noir") == ContentStyle.STOIC_FACTS
    assert style_profile_manager.resolve_style("editorial_warm") == ContentStyle.DOCUMENTARY
    assert style_profile_manager.resolve_style("neon_kinetic") == ContentStyle.VIRAL_VIDEO

    # 3. /api/dubbing/apply accepts top-level scenes + target_language alias
    client = TestClient(app)
    r_dub = client.post(
        "/api/dubbing/apply",
        json={"target_language": "en", "scenes": [{"narration": "Merhaba dünya, bugün tarihin en büyük sırrını inceliyoruz.", "duration": 4.0}]},
    )
    assert r_dub.status_code == 200
    assert r_dub.json().get("status") == "ok"

    # 4. Hardware panel & podcast host inputs wired in JS
    sq_js = (ROOT_DIR / "static/js/settings-quota.js").read_text(encoding="utf-8")
    for hw_id in ("btn-detect-hardware-now", "btn-apply-hardware-max", "btn-save-hardware-manual", "select-hw-codec", "select-hw-threads"):
        assert hw_id in sq_js

    ai_tools_js = (ROOT_DIR / "static/js/studio-ai-tools.js").read_text(encoding="utf-8")
    assert "input-podcast-host-a" in ai_tools_js
    assert "input-podcast-host-b" in ai_tools_js


