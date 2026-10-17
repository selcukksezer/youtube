"""Voice preview, BGM upload/catalog, pacing/subtitle utilities, and syndication routes."""
from __future__ import annotations

import os
import shutil
import sys
import threading
import time
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

import config
from api_models import TtsPreviewRequest
from bgm_manager import list_bgm_tracks_detailed
from subtitle_generator import SUBTITLE_PRESETS

router = APIRouter(tags=["Media"])

ALLOWED_BGM_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".ogg"}
_tts_preview_lock = threading.Lock()


def _mr_attr(name: str, default):
    mod = sys.modules.get("routers.media_router")
    return getattr(mod, name, default) if mod is not None else default


@router.get("/api/bgm/list")
def get_bgm_list(include_catalog: bool = True):
    list_fn = _mr_attr("list_bgm_tracks_detailed", list_bgm_tracks_detailed)
    tracks = list_fn(include_catalog=include_catalog)
    return {
        "tracks": [t["filename"] for t in tracks],
        "tracks_detailed": tracks,
        "count": len(tracks),
    }


@router.get("/api/bgm/catalog")
def get_bgm_catalog():
    try:
        from youtube_safe_bgm_catalog import catalog_meta, list_catalog_entries

        meta = catalog_meta()
        entries = list_catalog_entries(include_studio=True)
        return {
            **meta,
            "entries": entries,
            "downloaded": sum(1 for e in entries if e.get("downloaded")),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/api/tts/voices")
def get_tts_voices(refresh: bool = False):
    """Full TTS voice catalog (Edge TR/EN + ElevenLabs when configured)."""
    from tts_voices import get_voice_catalog

    return get_voice_catalog(force_refresh=refresh)


@router.post("/api/tts/preview")
def tts_preview(req: TtsPreviewRequest):
    """Short narration sample — Edge TTS (0 TL) or Gemini TTS when enabled."""
    cfg = _mr_attr("config", config)
    lock = _mr_attr("_tts_preview_lock", _tts_preview_lock)
    sample = (req.text or "Merhaba, bu kısa ses önizlemesidir.").strip()[:280]
    lang = (req.language or cfg.LANGUAGE or "tr").lower()
    gender = req.voice_gender or "male"
    if gender == "auto":
        from voice_humanizer import select_voice_gender

        gender = select_voice_gender("", sample)

    from tts_voices import resolve_voice, voice_gender_for_id

    with lock:
        orig_lang = cfg.LANGUAGE
        orig_voice = cfg.TTS_VOICE
        orig_gender = cfg.TTS_GENDER
        try:
            cfg.LANGUAGE = lang
            cfg.TTS_VOICE = resolve_voice(lang, voice_id=req.tts_voice, gender=gender)
            cfg.TTS_GENDER = voice_gender_for_id(cfg.TTS_VOICE, lang)

            out_dir = os.path.join(cfg.AUDIO_DIR, "previews")
            os.makedirs(out_dir, exist_ok=True)
            wav_path = os.path.join(out_dir, f"preview_{uuid.uuid4().hex[:10]}.wav")

            from tts_engine import active_tts_provider, generate_narration_with_timing

            generate_narration_with_timing(sample, wav_path, natural_pauses=False)
            if not os.path.isfile(wav_path):
                raise HTTPException(502, "Önizleme sesi üretilemedi")

            return FileResponse(
                wav_path,
                media_type="audio/wav",
                filename="voice_preview.wav",
                headers={"X-TTS-Provider": active_tts_provider()},
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(502, f"Ses önizleme hatası: {e}") from e
        finally:
            cfg.LANGUAGE = orig_lang
            cfg.TTS_VOICE = orig_voice
            cfg.TTS_GENDER = orig_gender


@router.post("/api/bgm/upload")
async def upload_bgm(file: UploadFile = File(...)):
    from services.path_security import safe_join, sanitize_filename

    cfg = _mr_attr("config", config)
    allowed_exts = _mr_attr("ALLOWED_BGM_EXTS", ALLOWED_BGM_EXTS)
    raw_name = os.path.basename(file.filename or "")
    safe_name = sanitize_filename(raw_name)
    ext = os.path.splitext(safe_name)[1].lower()
    if not safe_name or ext not in allowed_exts:
        raise HTTPException(
            status_code=400,
            detail=f"Desteklenmeyen dosya formatı ({ext}). Yalnızca MP3, WAV, M4A, AAC ve OGG kabul edilir.",
        )
    import asyncio

    def _save_bgm() -> None:
        os.makedirs(cfg.BGM_DIR, exist_ok=True)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

    try:
        file_path = safe_join(cfg.BGM_DIR, safe_name)
    except Exception as path_err:
        raise HTTPException(status_code=400, detail=f"Geçersiz dosya adı: {path_err}")
    await asyncio.to_thread(_save_bgm)
    return {"status": "ok", "filename": safe_name}


@router.delete("/api/bgm/{filename}")
def delete_bgm_track(filename: str):
    from services.path_security import UnsafePathError, safe_join

    cfg = _mr_attr("config", config)
    safe_name = os.path.basename(filename)
    try:
        fp = safe_join(cfg.BGM_DIR, safe_name)
    except UnsafePathError:
        raise HTTPException(status_code=404, detail="Geçersiz dosya yolu.")
    if not os.path.exists(fp):
        raise HTTPException(status_code=404, detail="Müzik dosyası bulunamadı.")
    try:
        os.remove(fp)
        return {"status": "ok", "message": f"{safe_name} silindi."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/subtitle_presets")
def get_subtitle_presets():
    """Returns preset subtitle styles including CapCut yellow & cyber green (Item 43)."""
    presets = _mr_attr("SUBTITLE_PRESETS", SUBTITLE_PRESETS)
    return {"presets": presets}


@router.post("/api/music/mood_match")
def api_music_mood_match(payload: dict):
    """Detects script sentiment mood and matches background music with ducking volume."""
    script_text = str(payload.get("script_text") or payload.get("text") or "").strip()
    if not script_text and isinstance(payload.get("scenes"), list):
        script_text = " ".join(
            str(s.get("narration") or s.get("text") or "")
            for s in payload["scenes"]
            if isinstance(s, dict)
        ).strip()
    niche_id = str(payload.get("niche_id") or "general").strip()
    preferred_track = payload.get("preferred_track")

    from services.audio_mood_director import audio_mood_director

    result = audio_mood_director.direct_audio_for_script(
        script_text=script_text,
        niche_id=niche_id,
        preferred_track=preferred_track,
    )
    tr = result.get("track")
    rec_track = tr.get("filename") if isinstance(tr, dict) else (str(tr) if tr else "")
    return {"status": "ok", "recommended_mood": result.get("mood"), "recommended_track": rec_track, **result}


@router.post("/api/subtitles/kinetic_pages")
def api_subtitles_kinetic_pages(payload: dict):
    """Converts word timestamps into 1-line mobile-friendly kinetic subtitle cards."""
    words = payload.get("words") or payload.get("word_timings") or []
    max_words_per_page = payload.get("max_words_per_page")
    default_line_len = max(10, int(max_words_per_page) * 6) if max_words_per_page else 22
    line_max_length = int(payload.get("line_max_length") or default_line_len)
    max_distance_ms = int(payload.get("max_distance_ms") or 1000)

    from effects.kinetic_subtitle_pager import KineticSubtitlePager

    pager = KineticSubtitlePager(
        line_max_length=line_max_length,
        max_distance_ms=max_distance_ms,
    )
    pages = pager.create_pages(words)
    ass_dialogues = pager.generate_ass_dialogues(pages)

    return {
        "status": "ok",
        "page_count": len(pages),
        "pages": [p.to_dict() for p in pages],
        "ass_dialogues": ass_dialogues,
    }


@router.post("/api/pacing/guard")
def api_pacing_guard(payload: dict):
    """Audits and balances scene durations, asset reuse, and loop padding."""
    scenes = payload.get("scenes") or []
    padding_back_ms = payload.get("padding_back_ms")

    from services.scene_pacing_guard import scene_pacing_guard

    result = scene_pacing_guard.audit_and_repair(
        scenes=scenes,
        padding_back_ms=int(padding_back_ms) if padding_back_ms is not None else None,
    )

    return {
        "status": "ok",
        "is_valid": result.is_valid,
        "total_duration_sec": result.total_duration_sec,
        "scene_count": result.scene_count,
        "padding_back_sec": result.padding_back_sec,
        "violations": result.violations,
        "warnings": result.violations,
        "repaired_scenes": result.repaired_scenes,
    }


@router.post("/api/affiliate/generate_plan")
def api_affiliate_generate_plan(payload: dict):
    """AFM: Scrapes e-commerce product URL/text and builds a high-converting 9:16 Shorts plan."""
    product_input = str(payload.get("product_input") or payload.get("url") or "").strip()
    affiliate_url = str(payload.get("affiliate_url") or "").strip()
    hook_style = str(payload.get("hook_style") or "life_hack")
    language = str(payload.get("language") or "tr")
    cta_text = str(payload.get("cta_text") or "Link profilde ve ilk yorumda sabitli!")

    if not product_input:
        raise HTTPException(
            status_code=400, detail="Ürün bağlantısı veya ürün açıklaması gereklidir."
        )

    from services.affiliate_product_engine import generate_affiliate_short_plan

    try:
        plan = generate_affiliate_short_plan(
            product_input=product_input,
            affiliate_url=affiliate_url,
            hook_style=hook_style,
            language=language,
            cta_text=cta_text,
        )
        return plan
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AFM ürün planı üretilemedi: {e}")


@router.post("/api/uploader/headless_upload")
def api_headless_upload(payload: dict):
    """Direct quota-free YouTube upload via authenticated browser profile (Firefox / Chrome)."""
    video_path = str(payload.get("video_path") or "").strip()
    title = str(payload.get("title") or "Viral Short").strip()
    description = str(payload.get("description") or "").strip()
    profile_path = payload.get("profile_path")
    browser_type = str(payload.get("browser_type") or "firefox")
    visibility = str(payload.get("visibility") or "unlisted")
    is_for_kids = bool(payload.get("is_for_kids") or False)

    if not video_path:
        raise HTTPException(status_code=400, detail="video_path gereklidir.")

    from services.path_security import UnsafePathError, resolve_safe_media_path

    try:
        video_path = resolve_safe_media_path(video_path)
    except UnsafePathError as exc:
        raise HTTPException(status_code=400, detail=f"Geçersiz video_path: {exc}") from exc

    from services.headless_uploader import upload_video_via_browser

    res = upload_video_via_browser(
        video_path=video_path,
        title=title,
        description=description,
        profile_path=profile_path,
        browser_type=browser_type,
        visibility=visibility,
        is_for_kids=is_for_kids,
        headless=True,
    )
    return res


@router.get("/api/ollama/status")
def api_ollama_status():
    """Returns local Ollama availability, base URL, and list of installed models."""
    from services.ollama_provider import (
        get_preferred_ollama_model,
        is_ollama_available,
        list_ollama_models,
    )

    available = is_ollama_available()
    models = list_ollama_models() if available else []
    pref = get_preferred_ollama_model() if available else None
    return {
        "status": "ok",
        "available": available,
        "models": models,
        "preferred_model": pref,
        "base_url": "http://localhost:11434",
    }


@router.post("/api/syndication/crosspost")
def api_syndication_crosspost(payload: dict):
    """Broadcasts short video to PostBridge multi-platform or custom webhook."""
    cfg = _mr_attr("config", config)
    video_path = str(payload.get("video_path") or "").strip()
    title = str(payload.get("title") or "").strip()
    caption = str(payload.get("caption") or "").strip()
    platforms = payload.get("platforms") or ["tiktok", "instagram_reels", "youtube_shorts"]
    api_key = str(
        payload.get("postbridge_api_key") or getattr(cfg, "POSTBRIDGE_API_KEY", "") or ""
    ).strip()
    account_ids = payload.get("social_account_ids") or []
    webhook_url = str(payload.get("webhook_url") or "").strip()

    if not video_path:
        raise HTTPException(status_code=400, detail="video_path gereklidir.")

    from services.path_security import UnsafePathError, resolve_safe_media_path

    try:
        video_path = resolve_safe_media_path(video_path)
    except UnsafePathError as exc:
        raise HTTPException(status_code=400, detail=f"Geçersiz video_path: {exc}") from exc

    from services.distribution_and_growth_hub import build_cross_platform_export_bundle
    from services.postbridge_syndicator import PostBridgeClient, broadcast_to_webhook

    results = {}

    if webhook_url:
        ok = broadcast_to_webhook(
            webhook_url,
            {
                "video_path": video_path,
                "title": title or caption[:80],
                "caption": caption,
                "platforms": platforms,
                "timestamp": int(time.time()),
            },
        )
        results["webhook"] = {"ok": ok, "url": webhook_url}

    if api_key and account_ids:
        try:
            client = PostBridgeClient(api_key=api_key)
            media_id = client.upload_media(video_path)
            if media_id:
                post_res = client.publish_short(
                    caption=caption, social_account_ids=account_ids, media_id=media_id
                )
                results["postbridge"] = post_res
            else:
                results["postbridge"] = {"error": "Media upload failed"}
        except Exception as e:
            results["postbridge"] = {"error": str(e)}

    export_bundle = build_cross_platform_export_bundle(
        video_path=video_path,
        title=title or caption[:80] or "Viral Shorts",
        description=caption,
        tags=["shorts", "viral", "fyp"],
    )
    results["export_bundle"] = export_bundle
    return {"status": "ok", "platforms": platforms, "export_bundle": export_bundle, "results": results}
