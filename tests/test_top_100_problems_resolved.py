from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path


def test_category_1_render_resilience_problems_1_to_10():
    from server_core.render_resilience import (
        cleanup_job_temp_files,
        get_uvicorn_reload_excludes,
        managed_media_clip,
        resolve_safe_render_threads,
        resume_interrupted_render_jobs,
        run_ffmpeg_with_timeout,
        safe_close_clip,
        safe_sse_event_generator,
        verify_video_stream_and_av_sync,
    )

    class DummyClip:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    clip = DummyClip()
    with managed_media_clip(clip) as c:
        assert c is clip
    assert clip.closed is True
    safe_close_clip(None)

    threads = resolve_safe_render_threads(requested_threads=2)
    assert threads == 2

    excludes = get_uvicorn_reload_excludes()
    assert "output/*" in excludes
    assert "*.db-wal" in excludes

    res_timeout = run_ffmpeg_with_timeout(
        ["python3", "-c", "import time; time.sleep(0.05)"],
        timeout_sec=5.0,
        fallback_sw_encoder=False,
    )
    assert res_timeout["ok"] is True

    with tempfile.TemporaryDirectory() as tmpdir:
        stale = Path(tmpdir) / "temp_job42_audio.wav"
        stale.write_bytes(b"1234")
        removed = cleanup_job_temp_files(tmpdir, job_prefix="temp_job42_")
        assert removed["removed_count"] == 1
        assert not stale.exists()

        resumed = resume_interrupted_render_jobs()
        assert "resumable_jobs" in resumed

        async def _broken_gen():
            yield "data: ok\n\n"
            raise ConnectionResetError("client closed")

        async def _collect_sse():
            items = []
            async for item in safe_sse_event_generator(_broken_gen()):
                items.append(item)
            return items

        sse_items = asyncio.run(_collect_sse())
        assert sse_items == ["data: ok\n\n"]

        dummy_mp4 = Path(tmpdir) / "sample.mp4"
        dummy_mp4.write_bytes(b"\x00\x00\x00\x18ftypmp42" + b"0" * 2048)
        probe = verify_video_stream_and_av_sync(dummy_mp4)
        assert probe["ok"] is True
        assert probe["has_video_stream"] is True


def test_category_2_quality_gate_policy_problems_11_to_20():
    from server_core.quality_gate_policy import evaluate_unified_quality_gates

    decision = evaluate_unified_quality_gates(
        mode="advisory",
        originality_similarity=0.91,
        policy_risk_flags=["market_volatility", "crypto_drop"],
        script_contract_issues=["scene_1_short"],
        semantic_mismatch_scenes=[1],
        unique_clips_available=2,
        required_clips=6,
        duration_seconds=36.5,
        research_evidence_found=False,
        has_video_stream=True,
        narration_empty=False,
    )
    assert decision["passed"] is True
    assert decision["ui_render_button_blocked"] is False
    assert decision["render_before_quarantine"] is True
    assert len(decision["advisory_warnings"]) >= 3
    assert len(decision["auto_repairs_applied"]) >= 3


def test_category_3_pipeline_orchestrator_problems_21_to_30():
    from roadmap_500_evaluator import Roadmap500Evaluator
    from server_core.pipeline_orchestrator import (
        audit_deferred_imports,
        evaluate_honest_audit_summary,
        get_active_effects_status_report,
        get_ordered_composer_effect_chain,
        get_workspace_isolation_config,
        run_minimal_e2e_mp4_smoke,
        run_unified_shorts_pipeline,
    )

    out = run_unified_shorts_pipeline("Stoacılık ve Zihin Kontrolü", niche="6_stoic_philosophy", language="tr")
    assert out["ok"] is True
    assert set(out["stages"].keys()) == {"script", "visual", "audio", "compose", "postprocess"}

    chain = get_ordered_composer_effect_chain()
    assert chain[0] == "1_smart_crop_9_16"
    assert chain[-1] == "6_progress_bar_and_watermark"

    fx = get_active_effects_status_report(safe_mode=False)
    assert len(fx["active_effects"]) >= 6
    assert fx["bypassed_effects"] == []

    honest = evaluate_honest_audit_summary()
    assert "rules_100" in honest and "roadmap_500" in honest

    ev = Roadmap500Evaluator()
    audit_res = ev.audit_all_items()
    assert "honest_audit_summary" in audit_res

    imp_audit = audit_deferred_imports(__file__)
    assert "deferred_imports" in imp_audit

    iso = get_workspace_isolation_config()
    assert "cocuk-sarki-bot-paylasim" in iso["isolated_subprojects"]

    with tempfile.TemporaryDirectory() as tmpdir:
        mp4_out = Path(tmpdir) / "smoke.mp4"
        smoke = run_minimal_e2e_mp4_smoke(mp4_out, duration_sec=1.0)
        assert smoke["ok"] is True
        assert smoke["size_bytes"] > 500


def test_category_4_scenario_enhancements_problems_31_to_40():
    from services.scenario_enhancements import (
        apply_narrator_persona_profile,
        build_ab_hook_render_variants,
        deduplicate_cinematic_query_suffixes,
        expand_six_word_stub_scene,
        inject_series_continuity_into_fallback,
        preserve_clause_integrity_on_cadence_split,
        rebalance_enriched_plan_word_budget,
        rotate_procedural_fallback_variant,
        score_title_ctr_ml_heuristic,
        select_bgm_by_script_sentiment,
    )

    expanded = expand_six_word_stub_scene("Kısa bir cümle.", topic="Yapay Zeka", min_words=10)
    assert len(expanded.split()) >= 10

    rebalanced = rebalance_enriched_plan_word_budget(
        [{"text": " ".join(["kelime"] * 90)}, {"text": " ".join(["kelime"] * 90)}],
        target_duration_sec=30.0,
    )
    assert sum(len(s["text"].split()) for s in rebalanced) <= 85

    deduped = deduplicate_cinematic_query_suffixes("bitcoin trading chart vertical 9:16 4k vertical cinematic 8k")
    assert deduped == "bitcoin trading chart cinematic"

    clauses = preserve_clause_integrity_on_cadence_split(
        "Piyasalar bugün çok sert açıldı, çünkü merkez bankası faiz kararını beklenenden erken açıkladı.",
        max_words_per_segment=8,
    )
    assert len(clauses) >= 2

    rot = rotate_procedural_fallback_variant("finance", "Altın Fiyatları", run_seed=3)
    assert "archetype" in rot and "hook" in rot

    bgm_sel = select_bgm_by_script_sentiment("Sabah uyanınca okunan bu dua kalbi ferahlatır ve huzur verir.")
    assert bgm_sel["bgm_mood"] == "spiritual_ney"

    persona = apply_narrator_persona_profile("street_interviewer")
    assert persona["rate"] == "+12%"

    variants = build_ab_hook_render_variants({"hook": "Kanca 1", "scenes": [{"text": "Kanca 1"}]})
    assert len(variants) == 2 and variants[0]["variant_id"] == "A" and variants[1]["variant_id"] == "B"

    ctr = score_title_ctr_ml_heuristic("Bitcoin Neden Düştü? 3 Kritik Sır Açığa Çıktı!")
    assert ctr["ctr_score"] >= 70.0

    cont = inject_series_continuity_into_fallback(
        [{"text": "Bugün yeni bölümü inceliyoruz."}],
        previous_episode_title="Bölüm 1 Özeti",
        part_number=2,
    )
    assert cont[0].get("series_linked") is True


def test_category_5_visual_render_enhancements_problems_41_to_50():
    from services.visual_render_enhancements import (
        compute_hybrid_semantic_visual_score,
        detect_face_center_x_opencv,
        ensure_standard_cube_luts,
        fetch_free_image_with_resilient_fallback,
        generate_images_parallel_batch,
        get_generative_ai_video_adapter_status,
        search_unsplash_and_storyblocks_fallback,
        select_best_of_3_thumbnails,
        should_trigger_action_particles,
    )
    from twitter_card_renderer import build_twitter_card_ffmpeg_filter, generate_transparent_twitter_card_png

    score = compute_hybrid_semantic_visual_score("bitcoin market", ["crypto", "trading", "chart"])
    assert score >= 0.55

    with tempfile.TemporaryDirectory() as tmpdir:
        img_out = Path(tmpdir) / "fallback.jpg"
        res_img = fetch_free_image_with_resilient_fallback("test prompt", img_out, fetcher=None)
        assert res_img["status"] == "procedural_fallback"
        assert img_out.is_file()

        batch_res = asyncio.run(
            generate_images_parallel_batch(
                ["p1", "p2", "p3"],
                worker_fn=lambda prompt, idx: {"prompt": prompt, "idx": idx},
                max_concurrency=2,
            )
        )
        assert len(batch_res) == 3

        gen_status = get_generative_ai_video_adapter_status({})
        assert gen_status["fallback_mode"] == "ken_burns_3d_parallax"

        stock = search_unsplash_and_storyblocks_fallback("nature", local_assets_dir=tmpdir)
        assert len(stock) >= 1

        cx = detect_face_center_x_opencv(1920, 1080, detected_boxes=[(1200, 200, 300, 300)])
        assert 960 < cx <= 1616

        luts = ensure_standard_cube_luts(Path(tmpdir) / "luts")
        assert Path(luts["dark_gold"]).is_file()

        tw_png = generate_transparent_twitter_card_png(Path(tmpdir) / "tweet.png")
        assert Path(tw_png).is_file()
        tw_filter = build_twitter_card_ffmpeg_filter(tw_png)
        assert "overlay=" in tw_filter["filter_expr"]

        best_thumb = select_best_of_3_thumbnails(
            [
                {"contrast_score": 0.5, "has_face": False, "text_legibility": 0.6},
                {"contrast_score": 0.9, "has_face": True, "text_legibility": 0.9},
                {"contrast_score": 0.7, "has_face": False, "text_legibility": 0.7},
            ]
        )
        assert best_thumb["winner_index"] == 1

        part = should_trigger_action_particles("Piyasada büyük patlama ve rekor yükseliş!", audio_rms_db=-10.0)
        assert part["triggered"] is True


def test_category_6_acoustic_mastering_and_bgm_problems_51_to_60():
    import config
    from bgm_manager import get_bgm_path
    from voice.acoustic_mastering_pipeline import (
        align_whisper_words_to_bgm_beats,
        apply_sentence_micro_tempo_jitter,
        build_mastering_eq_and_subbass_mono_filter,
        check_local_piper_kokoro_status,
        enforce_sonic_branding_04s,
        inject_breath_and_room_tone_pipeline,
        synthesize_offline_neural_fallback_wav,
    )

    tts_stat = check_local_piper_kokoro_status()
    assert "fallback_tier" in tts_stat

    with tempfile.TemporaryDirectory() as tmpdir:
        wav_path = Path(tmpdir) / "synth.wav"
        wav_info = synthesize_offline_neural_fallback_wav("Bu bir çevrimdışı ses testidir.", wav_path)
        assert Path(wav_info["output_path"]).is_file()
        assert wav_info["duration_sec"] >= 1.8

    breath_plan = inject_breath_and_room_tone_pipeline([2.5, 3.0, 2.8], room_tone_db=-48.0)
    assert len(breath_plan["breath_insertions"]) == 2
    assert "anoisesrc=color=pink" in breath_plan["room_tone_filter"]

    jitter = apply_sentence_micro_tempo_jitter(["Cümle bir.", "Cümle iki."])
    assert all(0.95 <= j["atempo"] <= 1.05 for j in jitter)

    eq_chain = build_mastering_eq_and_subbass_mono_filter()
    assert "equalizer=f=250" in eq_chain
    assert "equalizer=f=3500" in eq_chain
    assert "loudnorm=I=-14" in eq_chain

    sonic = enforce_sonic_branding_04s(0.4)
    assert sonic["duration_sec"] == 0.4

    snapped = align_whisper_words_to_bgm_beats(
        [{"word": "Şimdi", "start": 1.96, "end": 2.30}],
        beat_times_sec=[1.0, 2.0, 3.0],
        max_snap_window_sec=0.08,
    )
    assert snapped[0]["start"] == 2.0
    assert snapped[0].get("beat_snapped") is True

    # Problem #60: get_bgm_path handles BGM_DIR-prefixed paths and mute tokens cleanly while blocking traversal
    assert get_bgm_path("none") is None
    assert get_bgm_path("../yt_safe_441_meditation.mp3") is None
    prefixed = os.path.join(config.BGM_DIR, "yt_safe_441_meditation.mp3")
    resolved = get_bgm_path(prefixed)
    assert resolved is not None and os.path.isfile(resolved)


def test_category_7_advanced_subtitle_and_motion_problems_61_to_70():
    from effects.advanced_subtitle_and_motion import (
        build_3d_extrude_ass_dialogue_layers,
        build_light_leak_transition_filter,
        build_nle_timeline_scrub_manifest,
        build_tension_triggered_vignette_filter,
        compute_damped_spring_emoji_bob,
        extract_auto_keyword_popups,
        get_niche_mandatory_font_family,
        perlin_2d_camera_shake_offset,
        render_marker_stroke_highlight_png,
        resolve_occlusion_free_subtitle_y,
    )

    layers = build_3d_extrude_ass_dialogue_layers("0:00:00.00", "0:00:02.00", "KRİTİK VERİ")
    assert len(layers) == 3
    assert layers[0].startswith("Dialogue: 0,")
    assert layers[2].startswith("Dialogue: 2,")

    y_safe = resolve_occlusion_free_subtitle_y(face_boxes=[(300, 1250, 400, 400)], has_lower_third=False)
    assert y_safe < 1100

    popups = extract_auto_keyword_popups("Enflasyon %45 seviyesine ulaştı ve REKOR kırdı!", 0.0, 4.0)
    assert len(popups) >= 1

    vig = build_tension_triggered_vignette_filter([(2.0, 4.5)])
    assert "between(t,2.00,4.50)" in vig

    with tempfile.TemporaryDirectory() as tmpdir:
        marker_png = render_marker_stroke_highlight_png(Path(tmpdir) / "marker.png")
        assert Path(marker_png).is_file()

    spring = compute_damped_spring_emoji_bob(0.15)
    assert "y_offset_px" in spring and "scale" in spring

    font_spec = get_niche_mandatory_font_family("history_empire")
    assert font_spec["primary"] == "Cinzel Bold"

    leak = build_light_leak_transition_filter(4.0)
    assert "brightness=0.22" in leak

    dx, dy = perlin_2d_camera_shake_offset(1.25)
    assert -10.0 <= dx <= 10.0 and -10.0 <= dy <= 10.0

    nle = build_nle_timeline_scrub_manifest([{"text": "Sahne 1 %99", "duration": 3.5}])
    assert nle["total_duration_sec"] == 3.5
    assert len(nle["tracks"]["video"]) == 1


def test_category_8_distribution_and_growth_hub_problems_71_to_80():
    from services.distribution_and_growth_hub import (
        LiveStreamLoopSupervisor,
        PublicationSchedulerDaemon,
        build_20_channel_matrix_overview,
        build_community_post_dispatch_payload,
        build_cross_platform_export_bundle,
        compute_audio_video_content_id_fingerprint,
        fetch_or_estimate_channel_retention_curve,
        get_oauth_upload_readiness,
        prepare_youtube_pinned_comment_payload,
        scan_twitter_x_trending_topics,
    )

    oauth = get_oauth_upload_readiness("nonexistent_secret.json", "nonexistent_token.json")
    assert oauth["live_upload_ready"] is False
    assert oauth["mode"] == "dry_run_queue_only"

    daemon = PublicationSchedulerDaemon(poll_interval_sec=5.0)
    res_pub = asyncio.run(
        daemon.tick_once(
            due_items_fetcher=lambda: [{"id": 1, "title": "Due Video"}],
            publisher_fn=lambda item: {"published": item["id"]},
        )
    )
    assert len(res_pub) == 1 and daemon.processed_count == 1

    pin = prepare_youtube_pinned_comment_payload("vid_123", "Siz ne düşünüyorsunuz?")
    assert pin["api_method"] == "commentThreads.insert"

    ret = fetch_or_estimate_channel_retention_curve("vid_123")
    assert ret["is_estimated"] is True and len(ret["curve"]) == 11

    comm = build_community_post_dispatch_payload("ch_1", "Yeni video yayında!", ["Harika", "Daha fazlası"])
    assert comm["post_type"] == "poll"

    bundle = build_cross_platform_export_bundle("out.mp4", "Başlık")
    assert "tiktok" in bundle["platforms"] and "instagram_reels" in bundle["platforms"]

    trends = scan_twitter_x_trending_topics(["bitcoin"])
    assert trends["count"] >= 1

    fp = compute_audio_video_content_id_fingerprint(__file__, track_name="yt_safe_441.mp3")
    assert fp["copyright_safe"] is True

    sup = LiveStreamLoopSupervisor("rtmp://a.rtmp.youtube.com/live2/key")
    cmd = sup.build_ffmpeg_loop_command("loop.mp4")
    assert "-stream_loop" in cmd
    assert sup.compute_backoff_seconds(3) == 8.0

    matrix = build_20_channel_matrix_overview([{"id": "c1", "name": "Finans TR"}])
    assert matrix["active_channels"] == 1 and matrix["max_capacity"] == 20


def test_category_9_anti_detect_operational_guards_problems_81_to_90():
    from anti_detect.operational_guards import (
        CookieWarmupScheduleRunner,
        ResidentialProxyRotator,
        bind_human_bezier_to_playwright_page,
        enforce_new_channel_7day_resting_gate,
        enqueue_tier1_en_dual_render_job,
        get_account_recovery_2fa_checklist,
        get_appeal_video_operator_status,
        get_notification_channels_health,
        resilient_http_request,
        verify_operator_vault_and_2fa_readiness,
    )

    rot = ResidentialProxyRotator(["http://user:pass@res1.proxy:8080"])
    p_info = rot.get_proxy_for_channel(0)
    assert p_info["isolated"] is True

    warmup = CookieWarmupScheduleRunner().build_warmup_plan("ch_1")
    assert warmup["total_duration_sec"] >= 120

    gate = enforce_new_channel_7day_resting_gate("2099-01-01T00:00:00Z")
    assert gate["allowed"] is False and gate["status"] == "resting_period_active"

    bez = asyncio.run(bind_human_bezier_to_playwright_page(None, 400, 300, steps=5))
    assert bez["moved_steps"] == 5

    appeal = get_appeal_video_operator_status("ch_1")
    assert appeal["requires_human_presenter"] is True

    notif = get_notification_channels_health({"DISCORD_WEBHOOK_URL": "https://discord.gg/webhook"})
    assert notif["any_active"] is True

    en_job = enqueue_tier1_en_dual_render_job({"title": "Kripto Analiz", "scenes": [{"text": "Merhaba"}]})
    assert en_job["target_language"] == "en" and en_job["queued"] is True

    http_res = resilient_http_request("https://example.com", http_fn=lambda url, timeout: {"status": 200})
    assert http_res["ok"] is True

    chk = get_account_recovery_2fa_checklist("ch_1")
    assert len(chk["items"]) == 3

    vault = verify_operator_vault_and_2fa_readiness(
        {"totp_enabled": True, "recovery_phone_verified": True, "backup_codes_stored": True}
    )
    assert vault["ready"] is True


def test_category_10_workspace_maintenance_problems_91_to_100():
    from server_core.workspace_maintenance import (
        audit_future_annotations_compatibility,
        build_js_bundle_manifest,
        configure_urllib3_libressl_warning_filter,
        get_html_tab_sections_manifest,
        group_uncommitted_changes_into_batches,
        prune_workspace_media_storage,
        sync_markdown_audit_tables,
        verify_dockerfile_python312,
        verify_sqlite_wal_and_migrations,
    )

    compat = audit_future_annotations_compatibility([__file__])
    assert compat["compatible"] is True

    assert configure_urllib3_libressl_warning_filter() is True

    df = verify_dockerfile_python312("Dockerfile")
    assert df["uses_python_312"] is True

    with tempfile.TemporaryDirectory() as tmpdir:
        db_file = Path(tmpdir) / "test_wal.db"
        wal = verify_sqlite_wal_and_migrations(db_file)
        assert wal["migrations_table_ready"] is True
        assert wal["applied_migrations"] >= 1

        pruned = prune_workspace_media_storage(tmpdir, max_age_days=14.0, dry_run=True)
        assert pruned["dry_run"] is True

    js_manifest = build_js_bundle_manifest("static/js")
    assert js_manifest["bundle_ready"] is True

    html_tabs = get_html_tab_sections_manifest("static/index.html")
    assert html_tabs["exists"] is True

    md_sync = sync_markdown_audit_tables()
    assert md_sync["total_items"] == 500

    batches = group_uncommitted_changes_into_batches(
        ["server.py", "voice/tts.py", "static/js/app.js", "tests/test_x.py"]
    )
    assert len(batches["core_and_routers"]) == 1
    assert len(batches["voice_visuals_and_fx"]) == 1
    assert len(batches["frontend_static"]) == 1
    assert len(batches["tests_and_docs"]) == 1


def test_live_runtime_wiring_endpoints():
    from fastapi.testclient import TestClient

    from server import app
    from server_core.worker_preflight_stage import _get_render_thread_limits

    assert _get_render_thread_limits({"unified_ram_gb": 8, "thermal_throttle_recommended": False}) == (2, 2)

    client = TestClient(app)
    diag = client.get("/api/system/top100-diagnostics")
    assert diag.status_code == 200
    diag_data = diag.json()
    assert diag_data["status"] == "ok"
    assert "render_resilience" in diag_data
    assert "quality_gate_policy" in diag_data
    assert "pipeline_orchestrator" in diag_data
    assert "scenario_enhancements" in diag_data
    assert "visual_render_enhancements" in diag_data
    assert "acoustic_mastering" in diag_data
    assert "subtitle_and_motion" in diag_data
    assert "distribution_and_growth" in diag_data
    assert "operational_guards" in diag_data
    assert "workspace_maintenance" in diag_data

    scenes = [
        {
            "narration": f"Sahne {i} için doğrulanmış, somut ve akıcı Türkçe anlatım cümlesi şimdi burada yer alıyor.",
            "scene_description": f"Cinematic vertical 9:16 shot number {i} with natural lighting and crisp detail.",
            "search_queries": [f"cinematic detail {i}", f"vertical shot {i}"],
            "duration": 8.0,
        }
        for i in range(1, 7)
    ]
    val = client.post(
        "/api/plan/validate",
        json={
            "title": "Test Başlığı",
            "niche": "1_news_flash",
            "language": "tr",
            "auto_repair": False,
            "plan": {
                "title": "Test Başlığı",
                "niche_id": "1_news_flash",
                "scenes": scenes,
                "full_narration": " ".join(s["narration"] for s in scenes),
            },
        },
    )
    assert val.status_code == 200
    val_data = val.json()
    assert "unified_quality_gate" in val_data
    assert val_data["unified_quality_gate"]["passed"] is True


def test_bgm_auto_token_and_frontend_startup_dedup(capsys):
    from pathlib import Path
    import bgm_manager

    assert bgm_manager.get_bgm_path("🎵 Otomatik (Akıllı Niş / Telifsiz Seçim)") is None
    assert bgm_manager.get_bgm_path("auto") is None
    assert bgm_manager.request_mutes_bgm("🔇 Müziksiz (Sadece Seslendirme & SFX)") is True
    captured = capsys.readouterr()
    assert "Invalid BGM track path rejected" not in captured.out

    hw_js = Path("static/hardware_panel.js").read_text(encoding="utf-8")
    assert "inFlightSpecsPromise" in hw_js

    gallery_js = Path("static/js/gallery-channels.js").read_text(encoding="utf-8")
    assert "_galleryLoadInFlight" in gallery_js
    assert 'preload="${preloadMode}"' in gallery_js
    assert 'poster="${thumbUrl}"' in gallery_js
