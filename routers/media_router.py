"""
Background music (BGM), TTS preview, stock visual search, and subtitle presets router.
"""
from concurrent.futures import ThreadPoolExecutor
import os
import re
import shutil
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

import config
from api_models import TtsPreviewRequest
from bgm_manager import list_bgm_tracks, list_bgm_tracks_detailed
from routers.media_voice_bgm_routes import (
    ALLOWED_BGM_EXTS,
    _tts_preview_lock,
    api_affiliate_generate_plan,
    api_headless_upload,
    api_music_mood_match,
    api_ollama_status,
    api_pacing_guard,
    api_subtitles_kinetic_pages,
    api_syndication_crosspost,
    delete_bgm_track,
    get_bgm_catalog,
    get_bgm_list,
    get_subtitle_presets,
    get_tts_voices,
    router as _voice_bgm_router,
    tts_preview,
    upload_bgm,
)
from stock_providers import search_coverr, search_mixkit, search_pexels, search_pixabay
from subtitle_generator import SUBTITLE_PRESETS

router = APIRouter(tags=["Media"])
router.include_router(_voice_bgm_router)


class FetchStockScenesRequest(BaseModel):
    scenes: List[Dict[str, Any]]
    niche_id: Optional[str] = None


def _paid_stock_keys_present() -> bool:
    return bool(getattr(config, "PEXELS_API_KEY", "") or getattr(config, "PIXABAY_API_KEY", ""))


def _candidate_to_selected(best: Dict[str, Any], query: str) -> Dict[str, Any]:
    source = str(best.get("source") or "stock").strip().casefold()
    source_id = str(best.get("id") or "")
    provider_id = source_id.split("_", 1)[-1] if "_" in source_id else source_id
    source_urls = {
        "pexels": f"https://www.pexels.com/video/{provider_id}/",
        "pixabay": f"https://pixabay.com/videos/video-{provider_id}/",
    }
    license_urls = {
        "pexels": "https://www.pexels.com/license/",
        "pixabay": "https://pixabay.com/service/license-summary/",
        "coverr": "https://coverr.co/license",
    }
    return {
        "id": source_id,
        "source": source,
        "url": best.get("url", ""),
        "thumbnail": best.get("thumbnail") or best.get("url") or "",
        "duration": best.get("duration", 10),
        "width": best.get("width", 1080),
        "height": best.get("height", 1920),
        "query": query,
        "kind": best.get("kind", "video"),
        "title": best.get("title", ""),
        "contributor": best.get("contributor", ""),
        "license": best.get("license"),
        "attribution": best.get("attribution", ""),
        "source_url": best.get("source_url") or source_urls.get(source, ""),
        "license_url": best.get("license_url") or license_urls.get(source, ""),
    }


def _search_legacy_stock(query: str) -> List[Dict[str, Any]]:
    for fn in (search_pexels, search_pixabay, search_coverr, search_mixkit):
        try:
            hits = fn(query) or []
        except Exception:
            hits = []
        if hits:
            return hits
    return []


def _search_keyless_visuals(
    queries: List[str], niche_id: str = ""
) -> Optional[Dict[str, Any]]:
    """Openverse / Wikimedia when Pexels+Pixabay keys empty. Prefer openverse (less 429) and require subject match."""
    try:
        from visuals.query_builder import keyless_seed_queries
        from visuals.registry import ordered_providers, score_candidate, search_provider
    except Exception as exc:
        print(f"  [AutoStock] keyless import note: {exc}")
        return None

    seeds = keyless_seed_queries(niche_id=niche_id or "", queries=queries, max_seeds=5)
    providers = ordered_providers(niche_id or "")
    preferred = [s for s in providers if s.key in ("openverse", "wikimedia_img", "wikimedia")]
    if not preferred:
        preferred = providers

    best_entry: Optional[Dict[str, Any]] = None
    best_score = -1e9
    for q in seeds:
        for spec in preferred:
            try:
                cands = search_provider(spec, q, per_page=6) or []
            except Exception as exc:
                print(f"  [AutoStock:{spec.key}] {exc}")
                continue
            for cand in cands:
                url = getattr(cand, "url", "") or ""
                if not url:
                    continue
                sc_val = score_candidate(cand, q)
                if sc_val <= 0:
                    continue
                if sc_val > best_score:
                    best_score = sc_val
                    best_entry = {
                        "id": cand.id,
                        "source": cand.source,
                        "url": url,
                        "thumbnail": cand.thumbnail or url,
                        "duration": float(cand.duration or 8),
                        "width": int(cand.width or 1080),
                        "height": int(cand.height or 1920),
                        "kind": getattr(cand, "kind", "image") or "image",
                        "title": getattr(cand, "title", "") or "",
                        "query": q,
                    }
        if best_entry and best_score >= 45:
            return best_entry
    return best_entry


@router.get("/api/stock/search")
def api_stock_search(query: str, limit: int = 6, niche_id: str = ""):
    """Searches stock video providers and returns candidate video clips."""
    results = []
    try:
        px = search_pexels(query)
        if px:
            results.extend(px[:limit])
        if len(results) < limit:
            pb = search_pixabay(query)
            if pb:
                results.extend(pb[: limit - len(results)])
        if len(results) < limit:
            cv = search_coverr(query)
            if cv:
                results.extend(cv[: limit - len(results)])
        if len(results) < limit:
            mx = search_mixkit(query)
            if mx:
                results.extend(mx[: limit - len(results)])
        if len(results) < limit:
            keyless = _search_keyless_visuals([query], niche_id=niche_id)
            if keyless:
                results.append(keyless)
    except Exception as e:
        print(f"  [StockSearch] Error: {e}")
    return {"status": "ok", "query": query, "results": results[:limit]}


def _fetch_single_scene_video(args):
    i, sc, niche_id = args
    sc_copy = dict(sc)
    niche = (
        niche_id
        or sc.get("niche_id")
        or (sc.get("visual_intent") or {}).get("niche_id")
        or ""
    )
    queries = list(sc.get("search_queries") or [])
    if not queries and sc.get("scene_description"):
        queries = [sc["scene_description"]]
    if not queries:
        queries = ["architectural detail soft light", "nature aerial calm"]

    best_video = None
    matched_query = queries[0]
    for q in queries[:3]:
        try:
            candidates = _search_legacy_stock(q)
            if candidates:
                best_video = candidates[0]
                matched_query = q
                break
        except Exception:
            continue

    if not best_video and _paid_stock_keys_present():
        try:
            fallbacks = search_pexels("nature sunrise soft light") or []
            if fallbacks:
                best_video = fallbacks[i % len(fallbacks)]
                matched_query = "nature sunrise soft light"
        except Exception:
            pass

    if not best_video:
        keyless = _search_keyless_visuals(queries, niche_id=niche)
        if keyless:
            best_video = keyless
            matched_query = keyless.get("query") or matched_query

    if best_video:
        sc_copy["selected_video"] = _candidate_to_selected(best_video, matched_query)
        sc_copy["video_url"] = best_video.get("url") or ""
        sc_copy.pop("path", None)
        sc_copy.pop("video_path", None)
    return sc_copy


def auto_fetch_videos_for_scenes(
    scenes: List[Dict[str, Any]],
    niche_id: str = "",
) -> List[Dict[str, Any]]:
    """Associate top stock / keyless visual candidates with scenes."""
    if not scenes:
        return []
    try:
        workers = min(3 if not _paid_stock_keys_present() else 8, max(1, len(scenes)))
        payload = [(i, sc, niche_id) for i, sc in enumerate(scenes)]
        with ThreadPoolExecutor(max_workers=workers) as executor:
            return list(executor.map(_fetch_single_scene_video, payload))
    except Exception as e:
        print(f"  [AutoStockParallel] {e}")
        return scenes


@router.post("/api/stock/fetch_for_scenes")
def api_fetch_stock_for_scenes(req: FetchStockScenesRequest):
    """Fetches matched stock videos for all scenes in a plan."""
    niche = req.niche_id or ""
    if not niche and req.scenes:
        niche = str(req.scenes[0].get("niche_id") or "")
    updated = auto_fetch_videos_for_scenes(req.scenes, niche_id=niche)
    assigned = sum(
        1 for s in updated if s.get("selected_video") and s["selected_video"].get("url")
    )
    return {
        "status": "ok",
        "scenes": updated,
        "assigned": assigned,
        "total": len(updated),
        "paid_keys": _paid_stock_keys_present(),
    }


@router.post("/api/thumbnail/custom_generate")
def api_thumbnail_custom_generate(payload: dict):
    """Generates high-CTR 9:16 or 16:9 thumbnail with gradient, shadow, and word accents."""
    title = str(payload.get("title") or "Viral Shorts Cover").strip()
    aspect_ratio = str(payload.get("aspect_ratio") or "9:16")
    accent_text = payload.get("accent_text")
    bg_path = payload.get("background_path")
    if bg_path:
        from services.path_security import UnsafePathError, resolve_safe_media_path

        try:
            bg_path = resolve_safe_media_path(str(bg_path))
        except UnsafePathError as exc:
            raise HTTPException(
                status_code=400, detail=f"Geçersiz arka plan yolu: {exc}"
            ) from exc

    from services.thumbnail_generator import generate_thumbnail

    out_dir = os.path.join(config.BASE_DIR, "output", "thumbnails")
    os.makedirs(out_dir, exist_ok=True)
    slug = re.sub(r"[^\w]", "_", title)[:30]
    out_file = os.path.join(out_dir, f"thumb_{slug}_{aspect_ratio.replace(':', 'x')}.jpg")

    try:
        path = generate_thumbnail(
            title=title,
            output_path=out_file,
            background_path=bg_path,
            aspect_ratio=aspect_ratio,
            accent_text=accent_text,
        )
        return {
            "status": "ok",
            "thumbnail_path": path,
            "url": f"/output/thumbnails/{os.path.basename(path)}",
            "aspect_ratio": aspect_ratio,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Thumbnail oluşturulamadı: {e}")


@router.post("/api/seo/translate_39")
def api_seo_translate_39(payload: dict):
    """Translates title and description into 39 official YouTube localization languages."""
    title = str(payload.get("title") or "").strip()
    description = str(payload.get("description") or "").strip()
    source_lang = str(payload.get("source_lang") or "tr")

    if not title:
        raise HTTPException(status_code=400, detail="Başlık boş olamaz.")

    from services.multilang_seo_translator import MultilangSEOTranslator

    try:
        translator = MultilangSEOTranslator()
        res = translator.translate_to_39_languages(
            title=title,
            description=description,
            source_lang=source_lang,
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"39 dil çevirisi başarısız: {e}")


@router.post("/api/visual/generate_ai_scene")
def api_generate_ai_scene_visual(payload: dict):
    """Generates an instant 0 TL Pollinations Flux 9:16 visual clip with Ken Burns motion."""
    prompt = str(payload.get("scene_description") or payload.get("prompt") or "").strip()
    duration = float(payload.get("duration") or 4.0)
    scene_idx = int(payload.get("scene_index") or 0)

    if not prompt:
        raise HTTPException(status_code=400, detail="Görsel promptu boş olamaz.")

    from services.pollinations_ai_visual import create_scene_ai_clip

    out_dir = os.path.join(config.BASE_DIR, "output", "ai_clips")
    os.makedirs(out_dir, exist_ok=True)
    clip_file = os.path.join(out_dir, f"ai_clip_{uuid.uuid4().hex[:8]}.mp4")

    try:
        path = create_scene_ai_clip(
            scene_description=prompt,
            output_video_path=clip_file,
            duration=duration,
            scene_index=scene_idx,
        )
        if not path or not os.path.exists(path):
            raise RuntimeError("Pollinations AI görsel motoru klip oluşturamadı.")
        return {
            "status": "ok",
            "video_path": path,
            "url": f"/output/ai_clips/{os.path.basename(path)}",
            "duration": duration,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI klip üretimi hatası: {e}")


@router.post("/api/whiteboard/preview")
def api_whiteboard_preview(payload: dict):
    """Generates a whiteboard line-art sketch animation clip with FFmpeg wipe reveal."""
    prompt = str(payload.get("scene_description") or payload.get("prompt") or "").strip()
    narration = str(payload.get("narration") or "").strip()
    duration = float(payload.get("duration") or 4.0)
    scene_idx = int(payload.get("scene_index") or 0)

    if not prompt:
        raise HTTPException(status_code=400, detail="Çizim promptu boş olamaz.")

    from services.whiteboard_animator import create_whiteboard_scene_clip

    out_dir = os.path.join(config.BASE_DIR, "output", "whiteboard_clips")
    os.makedirs(out_dir, exist_ok=True)
    clip_file = os.path.join(out_dir, f"wb_clip_{uuid.uuid4().hex[:8]}.mp4")

    try:
        path = create_whiteboard_scene_clip(
            scene_description=prompt,
            output_video_path=clip_file,
            duration=duration,
            scene_index=scene_idx,
            narration=narration,
        )
        if not path or not os.path.exists(path):
            raise RuntimeError("Whiteboard çizim motoru klip oluşturamadı.")
        return {
            "status": "ok",
            "video_path": path,
            "url": f"/output/whiteboard_clips/{os.path.basename(path)}",
            "duration": duration,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Whiteboard klip üretimi hatası: {e}")
