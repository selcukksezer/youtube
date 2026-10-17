"""
Regression and integration tests for deep audit fixes, modular refactoring invariants,
FastAPI lifespan & static asset cache-busting, Jobs V1 & V2 state propagation,
timeline prepare/replace contracts, and FFmpeg hybrid overlay chaining.
"""
from __future__ import annotations

import asyncio
import json
import os
from unittest.mock import MagicMock, patch

import pytest

import config
import server
from api_models import TtsPreviewRequest, VideoRenderRequest


def test_codebase_modularity_no_py_or_js_over_600_lines():
    """Every active .py and .js source file in the repository must be <= 600 lines."""
    root = config.BASE_DIR
    skip_dirs = {
        ".git", "venv", ".venv", "node_modules", "__pycache__",
        ".pytest_cache", "output", "assets", "proofs", "logs",
        "data", "models", ".kilo", ".gitnexus", ".claude", ".agents",
    }
    over_limit = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            d for d in dirnames
            if d not in skip_dirs and not d.startswith(".tmp")
        ]
        for fn in filenames:
            if not (fn.endswith(".py") or fn.endswith(".js")):
                continue
            full_path = os.path.join(dirpath, fn)
            rel_path = os.path.relpath(full_path, root)
            with open(full_path, "r", encoding="utf-8", errors="ignore") as fh:
                line_count = sum(1 for _ in fh)
            if line_count > 600:
                over_limit.append((rel_path, line_count))
    assert over_limit == [], f"Files exceeding 600-line modularity limit: {over_limit}"


def test_server_lifespan_and_cache_busting_for_split_js_modules():
    """server.py uses lifespan context manager and cache-busts all split JS/CSS modules."""
    assert server.app.router.lifespan_context is not None

    rendered_html = server._render_index_html()
    expected_modules = [
        "js/state-defaults.js",
        "js/state-sync.js",
        "js/state.js",
        "js/studio-plan-editor.js",
        "js/studio-ai-tools.js",
        "js/studio.js",
        "js/timeline-preview.js",
        "js/timeline.js",
        "js/bgm-library.js",
        "js/audio-media.js",
        "js/render-sse-handler.js",
        "js/render-monitor.js",
        "js/channels-manager.js",
        "js/gallery-channels.js",
        "js/quota-analytics.js",
        "js/settings-quota.js",
        "js/viral_features.js",
    ]
    for mod_path in expected_modules:
        assert f"/static/{mod_path}?v=" in rendered_html, f"Missing cache-busted script: {mod_path}"


def test_tts_preview_request_maps_voice_alias():
    """TtsPreviewRequest accepts legacy `voice` field and maps it to `tts_voice`."""
    req = TtsPreviewRequest(text="Merhaba dünya", language="tr", voice="tr-TR-AhmetNeural")
    assert req.tts_voice == "tr-TR-AhmetNeural"


def test_jobs_v1_worker_status_and_cancel_propagation():
    """Jobs V1 worker propagates outcome from process_video_task and releases render_lock."""
    from routers import jobs_v1_router
    from server_core import state

    job_id = "test_job_v1_audit"
    jobs_v1_router._JOBS[job_id] = {
        "job_id": job_id,
        "status": "QUEUED",
        "progress_pct": 0,
        "current_stage": "QUEUED",
        "started_at": None,
        "cancel_requested": False,
    }
    req = jobs_v1_router.JobCreateRequest(
        topic="Stoic Zihin Kontrolü",
        niche_id="6_stoic_philosophy",
    )

    state.is_rendering_active = True
    state.current_render_state["error"] = None
    state.current_render_state["video_url"] = "/output/stoic_test.mp4"

    with patch.object(jobs_v1_router, "process_video_task", return_value="completed"):
        jobs_v1_router._run_job_worker(job_id, req)

    assert jobs_v1_router._JOBS[job_id]["status"] == "COMPLETED"
    assert jobs_v1_router._JOBS[job_id]["output_path"] == "/output/stoic_test.mp4"
    assert state.is_rendering_active is False

    # Test cancel endpoint signaling worker state
    cancel_res = jobs_v1_router.cancel_job(job_id)
    assert cancel_res["status"] == "CANCELLED"
    assert state.current_render_state["cancel_requested"] is True
    state.current_render_state["cancel_requested"] = False
    jobs_v1_router._JOBS.pop(job_id, None)


def test_v2_api_forwards_extended_render_settings():
    """v2_api.router.render_project forwards extended VideoRenderRequest settings."""
    from fastapi import BackgroundTasks
    from v2_api import router as v2_router
    from v2_api.schemas import RenderRequest
    from server_core import state

    fake_project = {
        "id": "prj_test123",
        "title": "Marcus Aurelius Stoic Kuralları",
        "niche": "6_stoic_philosophy",
        "language": "tr",
        "plan_json": json.dumps({
            "title": "Marcus Aurelius Stoic Kuralları",
            "niche_id": "6_stoic_philosophy",
            "scenes": [
                {
                    "narration": "Marcus Aurelius her sabah kendine bu kritik soruyu sorardı.",
                    "scene_description": "ancient marble bust in dramatic warm candlelight",
                    "search_queries": ["marble statue candle", "ancient philosophy"],
                    "duration": 6.0,
                }
            ],
        }),
        "settings_json": json.dumps({
            "enable_broll_insert": True,
            "enable_audio_visualizer": True,
            "duck_attack_ms": 95,
            "duck_release_ms": 260,
        }),
    }

    bg = BackgroundTasks()
    state.is_rendering_active = False
    with patch("v2_api.router.database.get_project", return_value=fake_project), \
         patch("v2_api.router.database.create_render_job"), \
         patch("v2_api.router.database.update_project"), \
         patch("v2_api.router.database.get_render_job", return_value={"id": "job_1", "status": "queued"}):
        res = v2_router.render_project(
            "prj_test123",
            RenderRequest(settings={"enable_news_ticker": True}),
            bg,
        )
    state.is_rendering_active = False
    assert res["status"] == "started"
    assert len(bg.tasks) == 1
    passed_req = bg.tasks[0].kwargs.get("req") or bg.tasks[0].args[2]
    assert isinstance(passed_req, VideoRenderRequest)
    assert passed_req.enable_broll_insert is True
    assert passed_req.enable_audio_visualizer is True
    assert passed_req.enable_news_ticker is True
    assert passed_req.duck_attack_ms == 95
    assert passed_req.duck_release_ms == 260


def test_ffmpeg_overlays_hybrid_ui_chains_vhybrid_label(tmp_path):
    """apply_global_overlays_to_graph updates picture to 'vhybrid' when hybrid UI overlay is active."""
    from render.ffmpeg_overlays import apply_global_overlays_to_graph

    hybrid_png = tmp_path / "hybrid_ui.png"
    hybrid_png.write_bytes(b"\x89PNG\r\n\x1a\n")
    audio_file = tmp_path / "voice.wav"
    audio_file.write_bytes(b"RIFF0000WAVEfmt ")

    cmd = ["ffmpeg"]
    filter_parts = []
    fake_hybrid_info = {
        "png_path": str(hybrid_png),
        "duration": 5.0,
        "x_expr": "0",
        "y_expr": "0",
        "enable_expr": "between(t,0,5)",
    }

    with patch(
        "effects.hybrid_overlay.create_hybrid_ui_overlay_png",
        return_value=fake_hybrid_info,
    ):
        vlabel, audio_idx, next_input = apply_global_overlays_to_graph(
            cmd=cmd,
            filter_parts=filter_parts,
            valid=[{"path": "a.mp4", "duration": 5.0}],
            total_dur=5.0,
            next_input=1,
            W=1080,
            H=1920,
            tmp_dir=str(tmp_path),
            audio_path=str(audio_file),
            word_timings=[],
            title="Test",
            subtitle_opts={"disable_hook_card": True},
            enable_broll=False,
            ass_path=None,
            emphasis_ass_path=None,
            enable_emphasis_card=False,
            hybrid_render_overlay={"type": "quiz"},
            enable_audio_visualizer=False,
            audio_visualizer_mode="line",
            audio_visualizer_color="0x00D7FF",
            enable_news_ticker=False,
            news_ticker_text=None,
            niche_id="",
            enable_reddit_card=False,
            reddit_card_path=None,
            extra_kwargs={},
        )

    assert vlabel == "[vout]"
    joined = ";".join(filter_parts)
    assert "[vhybrid]" in joined
    assert "[vhybrid]format=yuv420p" in joined


def test_ui_api_contract_aliases_and_provider_cooldown_guards(monkeypatch):
    from fastapi.testclient import TestClient
    from api_models_ext import RoyaltyFreeBgmRequest, _normalize_bgm_track
    from visuals import registry as vis_reg
    from services import public_apis_catalog as pub_cat

    assert _normalize_bgm_track("auto") == ""
    assert _normalize_bgm_track("__auto__") == ""
    rf_req = RoyaltyFreeBgmRequest.model_validate({"mood": "dark ambient"})
    assert rf_req.query == "dark ambient"

    monkeypatch.setattr(
        "services.subtitle_translation.translate_srt",
        lambda srt_text, **kw: "1\n00:00:00,000 --> 00:00:02,000\nHello World\n",
    )
    client = TestClient(server.app)

    sub_res = client.post(
        "/api/subtitles/translate",
        json={"srt_content": "1\n00:00:00,000 --> 00:00:02,000\nMerhaba Dünya", "target_lang": "en"},
    )
    assert sub_res.status_code == 200
    sub_body = sub_res.json()
    assert "Hello World" in sub_body["srt_text"]
    assert sub_body["translated_srt"] == sub_body["srt_text"]
    assert sub_body["srt"] == sub_body["srt_text"]

    kin_res = client.post(
        "/api/subtitles/kinetic_pages",
        json={
            "word_timings": [
                {"word": "Zihninizi", "start": 0.0, "end": 0.32},
                {"word": "kontrol", "start": 0.34, "end": 0.66},
                {"word": "edin.", "start": 0.68, "end": 1.0},
            ]
        },
    )
    assert kin_res.status_code == 200
    kin_body = kin_res.json()
    assert kin_body["page_count"] >= 1
    assert "start" in kin_body["pages"][0] and "end" in kin_body["pages"][0]

    vir_res = client.post(
        "/api/script/virality_audit",
        json={
            "script_text": (
                "Kimsenin bilmediği bu 3 gizli kural neden saklanıyor? "
                "Ortaya çıkan belgeler ve kanıtlar herkesi şaşkınlık içinde bıraktı. "
                "Unutmayın, disiplin ve strateji olmadan başarı asla gelmez ve bu 3 adım hayatınızı değiştirecek."
            ),
            "hook_text": "Kimsenin bilmediği bu 3 gizli kural neden saklanıyor?",
        },
    )
    assert vir_res.status_code == 200
    vir_audit = vir_res.json()["audit"]
    assert vir_audit["virality_score"] > 0
    assert vir_audit["slop_risk"] == "Düşük"

    flow_res = client.post(
        "/api/flow/transform_viral",
        json={"topic": "Yapay Zeka ve Beyin Sırları", "niche": "9_five_facts", "language": "tr"},
    )
    assert flow_res.status_code == 200
    assert flow_res.json()["status"] == "ok"

    vis_reg._cooldowns.pop("openverse", None)
    vis_reg._fail_counts.pop("openverse", None)
    vis_reg._note_failure("openverse", RuntimeError("Read timed out. (read timeout=4)"))
    vis_reg._note_failure("openverse", RuntimeError("Read timed out. (read timeout=4)"))
    assert vis_reg.provider_cooling_down("openverse") is True
    assert pub_cat.fetch_openverse_media("space nebula") == []
    vis_reg._cooldowns.pop("openverse", None)


def test_ios_pwa_manifest_and_service_worker_endpoints():
    """Verify iOS PWA meta tags, manifest.json, and sw.js endpoints for standalone mobile app usage."""
    from fastapi.testclient import TestClient

    rendered_html = server._render_index_html()
    assert 'name="apple-mobile-web-app-capable" content="yes"' in rendered_html
    assert "viewport-fit=cover" in rendered_html
    assert 'href="/manifest.json"' in rendered_html
    assert "/static/icons/apple-touch-icon.png" in rendered_html

    client = TestClient(server.app)
    manifest_res = client.get("/manifest.json")
    assert manifest_res.status_code == 200
    manifest_data = manifest_res.json()
    assert manifest_data["display"] == "standalone"
    assert manifest_data["short_name"] == "Shorts Studio"
    assert len(manifest_data["icons"]) >= 3

    sw_res = client.get("/sw.js")
    assert sw_res.status_code == 200
    assert sw_res.headers.get("Service-Worker-Allowed") == "/"
    assert "shorts-studio-pwa-v1" in sw_res.text


def test_studio_auth_login_and_git_update_endpoints():
    """Verify username/password session login, auth enforcement, and Git status/update endpoints."""
    from unittest.mock import AsyncMock
    from fastapi.testclient import TestClient
    from routers import auth_git_router

    rendered_html = server._render_index_html()
    assert 'id="header-btn-git-update"' in rendered_html
    assert 'id="header-btn-logout"' in rendered_html
    assert "/static/js/git-auth-ui.js?v=" in rendered_html

    client = TestClient(server.app)

    # 1. Unauthenticated requests with X-Enforce-Auth=1 are blocked / redirected
    unauth_root = client.get("/", headers={"X-Enforce-Auth": "1"}, follow_redirects=False)
    assert unauth_root.status_code == 302
    assert unauth_root.headers["location"] == "/login"

    unauth_api = client.get("/api/system/git-status", headers={"X-Enforce-Auth": "1"})
    assert unauth_api.status_code == 401

    # 2. Wrong password returns 401
    bad_login = client.post(
        "/api/auth/login",
        json={"username": config.STUDIO_USERNAME, "password": "wrong-password-123"},
    )
    assert bad_login.status_code == 401

    # 3. Valid login sets signed session cookie and unlocks protected endpoints
    ok_login = client.post(
        "/api/auth/login",
        json={"username": config.STUDIO_USERNAME, "password": config.STUDIO_PASSWORD, "remember": True},
    )
    assert ok_login.status_code == 200
    assert auth_git_router.SESSION_COOKIE_NAME in ok_login.cookies

    auth_status = client.get("/api/auth/status", headers={"X-Enforce-Auth": "1"})
    assert auth_status.status_code == 200
    assert auth_status.json()["authenticated"] is True

    # 4. Git status & update endpoints work
    git_status = client.get("/api/system/git-status", headers={"X-Enforce-Auth": "1"})
    assert git_status.status_code == 200
    assert git_status.json()["status"] == "ok"
    assert "commit" in git_status.json()

    fake_pull_res = {
        "status": "ok",
        "trigger": "button",
        "updated": True,
        "old_commit": "111aaaa",
        "new_commit": "222bbbb",
        "branch": "main",
        "subject": "feat: update studio",
        "output": "Fast-forward",
    }
    with patch.object(auth_git_router, "pull_latest_from_git", new=AsyncMock(return_value=fake_pull_res)):
        upd_res = client.post("/api/system/git-update", headers={"X-Enforce-Auth": "1"})
        assert upd_res.status_code == 200
        assert upd_res.json()["updated"] is True
        assert upd_res.json()["new_commit"] == "222bbbb"

    # 5. Logout clears session
    logout_res = client.post("/api/auth/logout")
    assert logout_res.status_code == 200

