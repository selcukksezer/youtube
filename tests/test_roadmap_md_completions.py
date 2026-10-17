"""
tests/test_roadmap_md_completions.py
====================================
Comprehensive test suite verifying all features completed from:
- FUTURE_ROADMAP.md §5 (#3, #4, #5, #6, #7, #8, #9) & §7
- RULES_100_AUDIT.md (#20 WhatsApp Chat Renderer, #67 Avatar Lip-Sync)
- RESEARCH_YOUTUBE_SHORTS_2026.md (§E3 P1 & §E4 P2 Compliance / C2PA / BGM Library Mode)
"""
from __future__ import annotations

import json
import os
import wave
from pathlib import Path
from unittest.mock import MagicMock, patch

from PIL import Image


def test_deepl_translation_and_dubbing_fallback(monkeypatch):
    """FUTURE_ROADMAP §5 #6 (Item 454): DeepL REST v2 primary translation + fallback."""
    import config
    from services import dubbing

    monkeypatch.setattr(config, "DEEPL_API_KEY", "test-key:fx")
    fake_resp = MagicMock()
    fake_resp.status_code = 200
    fake_resp.json.return_value = {"translations": [{"text": "Hello from DeepL"}]}

    with patch("requests.post", return_value=fake_resp) as mock_post:
        translated = dubbing.translate_text("Merhaba Dünya", source_lang="tr", target_lang="en")
        assert translated == "Hello from DeepL"
        called_url = mock_post.call_args[0][0]
        assert "api-free.deepl.com" in called_url

        pack = dubbing.build_dubbing_pack(
            [{"narration": "Merhaba", "overlay_text": "Selam"}],
            source_lang="tr",
            target_lang="en",
            title="Test",
        )
        assert pack["translation_provider"] == "deepl"
        assert pack["scenes"][0]["dubbed_narration"] == "Hello from DeepL"


def test_webrtc_stun_masking_and_channel_image_exif_scrub(tmp_path):
    """FUTURE_ROADMAP §5 #7 (Items 32-33): WebRTC/STUN IP scrub & channel banner EXIF scrub."""
    from anti_detect.post_render import scrub_channel_image_exif
    from anti_detect.profile import BrowserProfile
    from anti_detect.stealth import generate_stealth_js, get_chrome_cli_args

    profile = BrowserProfile(
        profile_id="test_channel",
        user_agent="Mozilla/5.0",
        viewport_width=1440,
        viewport_height=900,
        hardware_concurrency=8,
        device_memory=8,
    )
    js = generate_stealth_js(profile)
    assert "scrubSdpOrCandidate" in js
    assert "iceTransportPolicy" in js
    assert "RFC1918_RE" in js
    cli_args = get_chrome_cli_args(profile)
    assert "--webrtc-ip-handling-policy=default_public_interface_only" in cli_args
    assert "--enforce-webrtc-ip-permission-check" in cli_args

    img_path = tmp_path / "banner.jpg"
    img = Image.new("RGB", (64, 64), (120, 80, 200))
    img.save(img_path, "JPEG")
    res = scrub_channel_image_exif(str(img_path))
    assert res["ok"] is True
    assert img_path.exists()


def test_scenario_quality_dashboard_metrics():
    """FUTURE_ROADMAP §5 #3: Scenario quality monitoring dashboard metrics."""
    from scenes.plan_linter import build_scenario_quality_dashboard_metrics

    plans = [
        {
            "project_id": 101,
            "title": "Merkez Bankası faiz kararı",
            "niche_id": "23_crypto_finance_news",
            "scenes": [
                {
                    "narration": "Merkez Bankası faiz kararını açıkladı ve piyasalar hızla tepki verdi.",
                    "mood": "urgent",
                    "search_queries": ["central bank meeting"],
                },
                {
                    "narration": "Enflasyon beklentisi düşerken döviz kuru kritik destek seviyesine geriledi.",
                    "mood": "dramatic",
                    "search_queries": ["currency exchange chart"],
                },
                {
                    "narration": "Yatırımcılar şimdi önümüzdeki hafta açıklanacak büyüme verisini bekliyor.",
                    "mood": "calm",
                    "search_queries": ["stock market traders"],
                },
                {
                    "narration": "Peki sizce bu karar altın fiyatlarını nasıl etkiler? Yorumlara yazın.",
                    "mood": "mysterious",
                    "search_queries": ["gold bars vault"],
                },
            ],
        }
    ]
    metrics = build_scenario_quality_dashboard_metrics(plans)
    assert metrics["total_evaluated"] == 1
    assert 0.0 <= metrics["usable_rate_pct"] <= 100.0
    assert metrics["avg_unique_moods"] >= 3.0
    assert len(metrics["recent_plans"]) == 1


def test_niche_family_procedural_fallbacks():
    """FUTURE_ROADMAP §5 #4: Procedural fallback templates for mystery, entertainment, quiz, kids."""
    from scenes.fallback import _topic_bound_narrations

    for fam in ("mystery", "entertainment", "quiz", "kids"):
        tr_lines = _topic_bound_narrations("Kayıp Saat", True, family=fam)
        en_lines = _topic_bound_narrations("The Lost Watch", False, family=fam)
        assert len(tr_lines) == 10
        assert len(en_lines) == 10
        assert "Kayıp Saat" in tr_lines[0]
        assert "The Lost Watch" in en_lines[0]


def test_contextual_word_budget_completion():
    """FUTURE_ROADMAP §5 #5: Contextual completion for short/trimmed scene narrations."""
    from director.timeline import complete_short_scene_contextual

    completed_tr = complete_short_scene_contextual(
        "Fiyat hızla yükseldi.",
        overlay_text="Kritik Direnç",
        max_extra_words=10,
    )
    assert "Kritik Direnç" in completed_tr
    assert len(completed_tr.split()) > 3

    completed_en = complete_short_scene_contextual(
        "The market shifted.",
        overlay_text="Liquidity Spike",
        max_extra_words=10,
    )
    assert "Liquidity Spike" in completed_en


def test_avatar_pipeline_audio_envelope_and_lip_sync(tmp_path):
    """FUTURE_ROADMAP §5 #8 (Item 324) & RULES_100_AUDIT #67: Audio-envelope lip-sync avatar."""
    from effects.overlay_card_drawers import generate_retro_avatar_png
    from services.avatar_pipeline import (
        compute_audio_mouth_envelope,
        render_talking_avatar_frame,
        request_remote_talking_avatar,
    )

    wav_path = tmp_path / "speech.wav"
    with wave.open(str(wav_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(8000)
        wf.writeframes(b"\x00\x20" * 4000 + b"\x00\x00" * 4000)

    env = compute_audio_mouth_envelope(wav_path, duration=1.0, fps=12)
    assert len(env) == 12
    assert max(env) > min(env)

    avatar_png = tmp_path / "avatar.png"
    generate_retro_avatar_png(str(avatar_png), avatar_style="robot", size=120, seed=7)
    base_img = Image.open(avatar_png)
    closed_frame = render_talking_avatar_frame(base_img, 0.0)
    open_frame = render_talking_avatar_frame(base_img, 0.95)
    assert closed_frame.shape == (120, 120, 3)
    assert open_frame.shape == (120, 120, 3)
    assert not (closed_frame == open_frame).all()

    remote_info = request_remote_talking_avatar(str(avatar_png), str(wav_path))
    assert remote_info["mode"] in ("local_envelope_fallback", "remote_ready")


def test_whatsapp_chat_renderer(tmp_path):
    """RULES_100_AUDIT #20: WhatsApp dark-mode chat bubble PNG & FFmpeg filter builder."""
    from whatsapp_chat_renderer import (
        build_whatsapp_card_ffmpeg_filter,
        generate_transparent_whatsapp_chat_png,
    )

    out_png = tmp_path / "wa_card.png"
    res_path = generate_transparent_whatsapp_chat_png(
        str(out_png),
        messages=[
            {"sender": "other", "text": "Evde biri mi var?", "time": "01:12"},
            {"sender": "me", "text": "Hayır, tek başımayım.", "time": "01:13"},
        ],
        contact_name="Bilinmeyen Numara",
    )
    assert os.path.isfile(res_path)
    img = Image.open(res_path)
    assert img.mode == "RGBA"
    assert img.width == 920

    ff = build_whatsapp_card_ffmpeg_filter(res_path, duration=3.5)
    assert "[wa_card]overlay" in ff["filter_complex"]
    assert ff["output_map"] == "[outv]"


def test_compliance_e3_p1_and_c2pa_manifest(tmp_path, monkeypatch):
    """RESEARCH_YOUTUBE_SHORTS_2026 §E3 P1 & §E4 P2: BGM library mode, C2PA sidecar, review gate, cadence."""
    import bgm_manager
    import config
    from compliance import (
        check_upload_cadence_and_diversity,
        export_output_package,
        get_or_create_channel_style_fingerprint,
    )

    monkeypatch.setattr(config, "BGM_AUDIO_LIBRARY_ONLY", True)
    tracks = bgm_manager.list_bgm_tracks(include_catalog=True)
    assert all(str(t).startswith("youtube_studio/") for t in tracks)

    video_file = tmp_path / "sample.mp4"
    video_file.write_bytes(b"\x00\x00\x00\x18ftypmp42")
    pkg_dir = tmp_path / "pkg"
    pkg = export_output_package(
        str(pkg_dir),
        video_path=str(video_file),
        title="Test Shorts",
        description="Test açıklama",
        tags=["shorts", "test"],
        compliance={"originality_score": 52.0, "niche_id": "9_five_facts"},
        viewer_score={"overall_score": 64.0},
    )
    assert "c2pa_manifest" in pkg["files"]
    c2pa_data = json.loads(Path(pkg["files"]["c2pa_manifest"]).read_text(encoding="utf-8"))
    assert c2pa_data["c2pa_version"] == "2.1"
    assert pkg["human_review_gate"]["requires_human_review"] is True
    assert (pkg_dir / "manual_review_queue.json").is_file()

    cadence = check_upload_cadence_and_diversity(
        [{"uploaded_at_ts": 1000.0, "title": "Bitcoin neden yükseliyor analiz"}],
        candidate_title="Bitcoin neden yükseliyor detaylı analiz",
        now_ts=1000.0 + 3600.0,
    )
    assert cadence["allowed"] is False
    assert cadence["duplicate_topic"] is True

    fp_a = get_or_create_channel_style_fingerprint("channel_alpha")
    fp_b = get_or_create_channel_style_fingerprint("channel_beta")
    assert fp_a["channel_id"] == "channel_alpha"
    assert fp_a != fp_b


def test_frontend_state_persistence_contract_in_app_js():
    """FUTURE_ROADMAP §5 #9: Verify frontend localStorage state & schema migration contract."""
    state_defaults = Path("/Users/selcuk/Documents/youtubeoto/static/js/state-defaults.js").read_text(encoding="utf-8")
    state_sync = Path("/Users/selcuk/Documents/youtubeoto/static/js/state-sync.js").read_text(encoding="utf-8")
    app_js = Path("/Users/selcuk/Documents/youtubeoto/static/app.js").read_text(encoding="utf-8")
    assert "PLAN_SCHEMA_VERSION" in state_defaults
    assert "persistCurrentPlan" in state_sync
    assert "restoreCurrentPlan" in state_sync
    assert "localStorage.setItem" in state_sync
    assert "restoreCurrentPlan()" in app_js

