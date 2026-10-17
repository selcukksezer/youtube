"""
Render Worker Stage 10: Post-Render Verification, Pipeline Audit, MP4 Preflight,
Delivery Packaging, High-CTR Thumbnail Generation, Manual Upload Guide,
Plagiarism Ledger Commit, Telemetry, and Completion Broadcast.
Extracted from server_core/render_worker.py for modularity.
"""
import json
import os
import subprocess
from typing import Any, Callable, Dict, List, Optional

import imageio_ffmpeg

import config
import database
from notifications import notify_render_error, notify_video_ready
from video_fetcher import commit_published_stock_ids
from . import state
from .pipeline_state_machine import PipelineStage


def run_post_render_and_packaging_stage(
    *,
    req: Any,
    result: str,
    audio_path: str,
    clips: List[Dict[str, Any]],
    plan: Dict[str, Any],
    director: Any,
    pre_result: Dict[str, Any],
    pre_audit: Dict[str, Any],
    seo_meta: Dict[str, Any],
    seo_file: str,
    script_text: str,
    proj: str,
    output_root: str,
    safe: str,
    keyword: str,
    target_lang: str,
    ch_paths: Dict[str, str],
    db_id: Optional[int],
    sm: Any,
    log_fn: Callable[..., None],
) -> str:
    """
    Executes post-render validation, packaging, thumbnails, DB update, and completion notifications.
    Returns render_outcome ('completed' or 'failed').
    """
    from director import post_render_score

    if not (result and os.path.exists(result) and os.path.getsize(result) > 100000):
        if sm is not None:
            sm.fail(
                "Video birleştirme MoviePy/FFmpeg hatası nedeniyle tamamlanamadı.",
                broadcast=False,
            )
            sm.save_telemetry(proj)
        if db_id:
            database.update_video_status(
                db_id,
                "failed",
                error_message="Video birleştirme MoviePy/FFmpeg hatası nedeniyle tamamlanamadı.",
            )
        state.broadcast_event("error", "Video birleştirme tamamlanamadı.")
        notify_render_error(
            keyword,
            "Video birleştirme MoviePy/FFmpeg hatası nedeniyle tamamlanamadı.",
        )
        return "failed"

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    validation = subprocess.run(
        [ffmpeg_exe, "-v", "error", "-i", result, "-f", "null", "-"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        timeout=30,
    )
    if validation.returncode != 0:
        raise RuntimeError(
            "Render çıktısı çözümlenemedi: "
            + validation.stderr.decode("utf-8", errors="ignore")[:300]
        )

    _post_audit: Dict[str, Any] = {}
    try:
        from render.pipeline_audit import post_render_audit

        _post_audit = post_render_audit(result, audio_path, clips)
        for _pw in _post_audit.get("warnings") or []:
            log_fn(f"[PipelineAudit] Post-WARN: {_pw}")
        for _pe in _post_audit.get("errors") or []:
            log_fn(f"[PipelineAudit] Post-ERROR: {_pe}", 97)
        _audit_report = _post_audit.get("report") or {}
        _signal_report = _audit_report.get("signal_analysis") or {}
        log_fn(
            "[PipelineAudit] Render metrics: "
            f"{_audit_report.get('resolution') or 'çözünürlük yok'} "
            f"@ {_audit_report.get('fps') or 'FPS yok'} FPS, "
            f"süre={_audit_report.get('video_duration')}s, "
            f"siyah aralık={len(_signal_report.get('black_intervals') or [])}, "
            f"sessizlik={len(_signal_report.get('silence_intervals') or [])}, "
            f"ses tepe={_signal_report.get('peak_volume_dbfs')} dBFS"
        )
        with open(os.path.join(proj, "pipeline_audit_post.json"), "w", encoding="utf-8") as _paf:
            json.dump(_post_audit, _paf, ensure_ascii=False, indent=2)
        if not _post_audit["ok"]:
            _post_blocking = [
                e
                for e in (_post_audit.get("errors") or [])
                if "av_sync_error" in e
                or "video_too_short" in e
                or "no_video_stream" in e
                or "output_too_small" in e
            ]
            if _post_blocking:
                _msg = f"Post-render audit kalite uyarısı: {'; '.join(_post_blocking)}"
                if not os.path.exists(result) or os.path.getsize(result) < 1000:
                    log_fn(f"[PipelineAudit] HARD-FAIL: {_msg} (Çıktı dosyası geçersiz)", 97)
                    if db_id:
                        database.update_video_status(db_id, "failed", error_message=_msg)
                    state.broadcast_event("error", _msg)
                    return "failed"
                else:
                    log_fn(
                        f"[PipelineAudit] UYARI: {_msg} (Video dosyası başarıyla üretildi)",
                        97,
                    )
    except Exception as _post_audit_err:
        log_fn(f"[PipelineAudit] post-audit skip: {_post_audit_err}")

    try:
        from services.video_preflight import verify_mp4_integrity

        preflight = verify_mp4_integrity(result, min_duration=3.0, max_duration=70.0)
        if not preflight.get("valid", False):
            pf_errs = preflight.get("errors", [])
            msg = f"MP4 Preflight Bütünlük Uyarısı: {'; '.join(pf_errs)}"
            if not os.path.exists(result) or os.path.getsize(result) < 1000:
                log_fn(f"[VideoPreflight] HARD-FAIL: {msg}", 97)
                if db_id:
                    database.update_video_status(db_id, "failed", error_message=msg)
                state.broadcast_event("error", msg)
                return "failed"
            else:
                log_fn(
                    f"[VideoPreflight] UYARI: {msg} (Video dosyası mevcut, devam ediliyor)",
                    97,
                )
        log_fn(
            f"[VideoPreflight] Doğrulandı: {preflight.get('width')}x{preflight.get('height')} "
            f"@ {preflight.get('duration')}s (Ses: {preflight.get('has_audio')})",
            96,
        )
    except Exception as pf_exc:
        log_fn(f"[VideoPreflight] Preflight istisnası: {pf_exc}")

    post: Dict[str, Any] = {}
    if director:
        post = post_render_score(director, result, audio_path=audio_path)
        log_fn(
            f"[QualityGate] Post-score={post['score']} ok={post.get('ok')} "
            f"Dav={post.get('av_delta')} issues={post.get('issues')}",
            97,
        )
        with open(os.path.join(proj, "quality_gate.json"), "w", encoding="utf-8") as qf:
            json.dump({"pre": pre_result, "post": post}, qf, ensure_ascii=False, indent=2)
        with open(os.path.join(proj, "render_verification.json"), "w", encoding="utf-8") as vf:
            json.dump(
                {
                    "video_path": result,
                    "audio_path": audio_path,
                    "verified": bool(post.get("ok")),
                    "video_duration": post.get("video_duration"),
                    "audio_duration": post.get("audio_duration"),
                    "av_delta": post.get("av_delta"),
                    "issues": post.get("issues") or [],
                },
                vf,
                ensure_ascii=False,
                indent=2,
            )
        with open(os.path.join(proj, "director_plan.json"), "w", encoding="utf-8") as f:
            json.dump(director.to_dict(), f, ensure_ascii=False, indent=2)

        if not post.get("ok"):
            issues = post.get("issues") or []
            msg = (
                f"Kalite kapısı reddetti (Madde 494): {', '.join(issues)}. "
                f"Süre={post.get('video_duration')}s — yayınlanamaz."
            )
            log_fn(f"[QualityGate] HARD-FAIL: {msg}")
            if db_id:
                database.update_video_status(db_id, "failed", error_message=msg)
            state.broadcast_event("error", msg)
            return "failed"

    size_mb = round(os.path.getsize(result) / (1024 * 1024), 2)
    total_dur = sum(c["duration"] for c in clips)

    try:
        from services.video_title_ideas import generate_video_title_ideas

        title_ideas = generate_video_title_ideas(
            result,
            keyword=keyword,
            script_context=script_text,
            current_title=str(seo_meta.get("seo_title") or keyword),
            language=target_lang,
        )
    except (ImportError, OSError, TypeError, ValueError) as title_err:
        title_ideas = None
        log_fn(
            f"[TitleIdeas] Optional title analysis failed "
            f"({type(title_err).__name__}); keeping existing SEO title.",
            95,
        )
    if title_ideas:
        seo_meta["title_ideas"] = title_ideas
        try:
            with open(seo_file, "w", encoding="utf-8") as sf:
                json.dump(seo_meta, sf, ensure_ascii=False, indent=2)
            log_fn(
                f"[TitleIdeas] {len(title_ideas['titles'])} kareyle doğrulanmış "
                "başlık önerisi hazır.",
                95,
            )
        except OSError as title_file_err:
            log_fn(
                f"[TitleIdeas] SEO dosyasına öneriler yazılamadı "
                f"({type(title_file_err).__name__}).",
                95,
            )

    sm.transition_to(
        PipelineStage.STAGE_10_PACKAGING,
        "Paketleme ve Dağıtım: Lisans künyesi, SEO künyesi ve telemetri arşivleniyor",
        pct=96.0,
    )
    try:
        from production.package import write_delivery_package
        from production.quality import validate_script_quality

        package_quality = (
            (plan.get("meta") or {}).get("script_quality") if isinstance(plan, dict) else None
        )
        if not package_quality:
            package_quality = validate_script_quality(plan or {})
        manifest_payload = None
        manifest_path = os.path.join(proj, "source_manifest.json")
        if os.path.isfile(manifest_path):
            with open(manifest_path, "r", encoding="utf-8") as mf:
                manifest_payload = json.load(mf)
        package_paths = write_delivery_package(
            proj,
            plan=plan if isinstance(plan, dict) else {},
            output_path=result,
            quality_report=package_quality,
            source_manifest=manifest_payload,
            seo=seo_meta if isinstance(seo_meta, dict) else {},
        )
        log_fn(
            f"[Package] Dosya teslim paketi hazır: {', '.join(sorted(package_paths))}",
            98,
        )
    except Exception as package_err:
        msg = f"Teslim paketi oluşturulamadı: {package_err}"
        log_fn(f"[Package] HARD-FAIL: {msg}", 98)
        if db_id:
            database.update_video_status(db_id, "failed", error_message=msg)
        state.broadcast_event("error", msg)
        return "failed"

    proof_filename = f"{os.path.splitext(os.path.basename(result))[0]}_proof.json"
    proof_full_path = os.path.join(config.BASE_DIR, "proofs", proof_filename)
    proof_url = f"/proofs/{proof_filename}" if os.path.exists(proof_full_path) else None

    thumb_path = os.path.join(output_root, f"{safe}_thumb.jpg")
    thumb_169_path = os.path.join(output_root, f"{safe}_thumb_16x9.jpg")
    try:
        from services.thumbnail_generator import extract_best_video_frame, generate_thumbnail

        log_fn("[Thumbnail] High-CTR kapak görseli hazırlanıyor (Verticals v3)...", 99)
        raw_frame = os.path.join(proj, "raw_thumb_frame.jpg")
        got_frame = extract_best_video_frame(
            result, raw_frame, target_sec=min(3.0, total_dur * 0.25)
        )
        bg_src = raw_frame if got_frame else None
        generate_thumbnail(
            title=seo_meta.get("seo_title", keyword),
            output_path=thumb_path,
            background_path=bg_src,
            aspect_ratio="9:16",
        )
        generate_thumbnail(
            title=seo_meta.get("seo_title", keyword),
            output_path=thumb_169_path,
            background_path=bg_src,
            aspect_ratio="16:9",
        )
        log_fn(
            f"[Thumbnail] 9:16 ve 16:9 kapak hazır: "
            f"{os.path.basename(thumb_path)}, {os.path.basename(thumb_169_path)}"
        )
    except Exception as thumb_err:
        log_fn(f"[Thumbnail] Kapak üretim uyarısı: {thumb_err}")

    if db_id:
        database.update_video_status(
            db_id,
            "completed",
            os.path.basename(result),
            total_dur,
            size_mb,
            seo_json=json.dumps(seo_meta, ensure_ascii=False),
            proof_path=proof_full_path if os.path.exists(proof_full_path) else None,
        )

    try:
        manual_pkg = {
            "video_file": os.path.basename(result),
            "title": seo_meta.get("seo_title") or plan.get("title") or keyword,
            "description": (
                seo_meta.get("seo_description")
                or seo_meta.get("description")
                or f"{keyword} #shorts\n\n📌 Kaynak & Araştırma: Bağımsız Eğitici İnceleme\n⚖️ Hakkaniyet & Katma Değer (Fair Use): Bu video eğitim ve analiz amacıyla özgün ses ve dinamik görselleştirme ile üretilmiştir."
            ),
            "tags": seo_meta.get("tags") or ["shorts", "bilgi", "viral", "trend"],
            "pinned_comment": seo_meta.get("pinned_comment")
            or "Sizce bu konudaki en şaşırtıcı detay neydi? Yorumlarda buluşalım! 👇",
            "rule_80_altered_synthetic": "HAYIR (Yüz klonlama veya manipülasyon yoksa etiket seçilmemeli)",
            "rule_83_source_reference": "Açıklamaya araştırma ve kaynak referansı eklendi.",
            "anti_detect_ready": True,
            "size_mb": size_mb,
            "duration": total_dur,
        }
        info_json_targets = {result.rsplit(".", 1)[0] + "_manual_upload_info.json"}
        info_json_targets.add(os.path.join(config.OUTPUT_DIR, f"{safe}_manual_upload_info.json"))
        for target_json in info_json_targets:
            with open(target_json, "w", encoding="utf-8") as fj:
                json.dump(manual_pkg, fj, ensure_ascii=False, indent=2)

        guide_txt_path = result.rsplit(".", 1)[0] + "_manual_upload_guide.txt"
        with open(guide_txt_path, "w", encoding="utf-8") as ft:
            ft.write(
                f"=== YOUTUBE SHORTS MANUEL YÜKLEME REHBERİ ===\n\n"
                f"📌 VİDEO BAŞLIĞI:\n{manual_pkg['title']}\n\n"
                f"📌 VİDEO AÇIKLAMASI:\n{manual_pkg['description']}\n\n"
                f"📌 VİDEO ETİKETLERİ:\n{', '.join(manual_pkg['tags'])}\n\n"
                f"📌 İLK YORUM (Sabitleyin):\n{manual_pkg['pinned_comment']}\n\n"
                f"🎬 DOSYA:\n{os.path.basename(result)} ({size_mb} MB, {total_dur:.1f}s)\n"
            )
    except Exception as e_info:
        log_fn(f"[Package] Manual upload info oluşturulamadı: {e_info}")

    try:
        from plagiarism_checker import add_script_to_db

        add_script_to_db(
            plan.get("full_narration", ""),
            keyword=keyword,
            title=plan.get("title", keyword),
            video_id=db_id,
            render_status="completed",
            channel_slug=ch_paths["slug"],
        )
    except Exception as e:
        log_fn(f"[Item 120] DB kayıt uyarısı: {e}")

    committed = commit_published_stock_ids()
    if committed:
        log_fn(f"[Visual] {committed} stok ID yayın sonrası kalıcı havuza eklendi (P1-12)")

    final_video_url = (
        f"/output/channels/{ch_paths['slug']}/{os.path.basename(result)}"
        if ch_paths["slug"] != "default"
        else f"/output/{os.path.basename(result)}"
    )
    if sm is not None:
        sm.complete(final_video_url, broadcast=False)
        sm.save_telemetry(proj)
    from visuals.fetch import get_job_provider_diagnostics

    _render_diagnostics = {
        "pipeline": sm.export_telemetry() if sm is not None else {},
        "provider_search": get_job_provider_diagnostics(),
    }
    try:
        with open(os.path.join(proj, "render_diagnostics.json"), "w", encoding="utf-8") as _df:
            json.dump(_render_diagnostics, _df, ensure_ascii=False, indent=2)
    except OSError as _diagnostics_err:
        log_fn(f"[RenderPerf] Diagnostics could not be saved: {_diagnostics_err}")
    _pipeline_stages = _render_diagnostics["pipeline"].get("stages") or []
    _slowest_stage = max(
        _pipeline_stages,
        key=lambda item: float(item.get("duration_sec") or 0),
        default=None,
    )
    log_fn(
        f"[RenderPerf] total={_render_diagnostics['pipeline'].get('total_duration_sec')}s"
        + (
            f" longest={_slowest_stage.get('name')} "
            f"{_slowest_stage.get('duration_sec')}s"
            if _slowest_stage
            else ""
        )
    )
    for _provider, _stats in sorted(
        _render_diagnostics["provider_search"]["providers"].items(),
        key=lambda item: item[1]["total_ms"],
        reverse=True,
    ):
        log_fn(
            f"[RenderPerf] provider={_provider} searches={_stats['searches']} "
            f"avg={_stats['avg_ms']}ms max={_stats['max_ms']}ms "
            f"results={_stats['results']} empty={_stats['empty_searches']}"
        )

    done_msg = (
        f"🎉 Video üretimi tamamlandı! Dosya: {os.path.basename(result)} "
        f"({size_mb} MB, {total_dur:.1f}s)"
    )
    print(done_msg)
    state.broadcast_event("progress", {"percent": 100, "step": "Video başarıyla tamamlandı!"})
    state.broadcast_event(
        "complete",
        {
            "video_id": db_id,
            "project_slug": safe,
            "keyword": keyword,
            "filename": os.path.basename(result),
            "url": final_video_url,
            "thumb_url": (
                (
                    f"/output/channels/{ch_paths['slug']}/{safe}_thumb.jpg"
                    if ch_paths["slug"] != "default"
                    else f"/output/{safe}_thumb.jpg"
                )
                if os.path.exists(os.path.join(output_root, f"{safe}_thumb.jpg"))
                else None
            ),
            "channel_slug": ch_paths["slug"],
            "seo": seo_meta,
            "proof_url": proof_url,
            "quality_gate": {
                "pre": pre_result,
                "post": post,
                "pipeline_audit": {
                    **_post_audit,
                    "pre_render": pre_audit,
                    "warnings": list((pre_audit or {}).get("warnings") or [])
                    + list((_post_audit or {}).get("warnings") or []),
                },
                "render_diagnostics": _render_diagnostics,
            },
            "director": {
                "niche_id": director.niche_id if director else req.niche,
                "duration": total_dur,
                "scenes": len(clips),
            },
        },
    )
    notify_video_ready(keyword, f"/output/{os.path.basename(result)}", total_dur)
    return "completed"
