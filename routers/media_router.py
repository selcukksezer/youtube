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
from stock_providers import (
    search_coverr,
    search_mixkit,
    search_pexels,
    search_pixabay,
    simplify_stock_queries,
)
from subtitle_generator import SUBTITLE_PRESETS

router = APIRouter(tags=["Media"])
router.include_router(_voice_bgm_router)


class FetchStockScenesRequest(BaseModel):
    scenes: List[Dict[str, Any]]
    niche_id: Optional[str] = None
    preferred_source: Optional[str] = None


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


def _interleave_lists(list_a: List[Dict[str, Any]], list_b: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    max_len = max(len(list_a), len(list_b))
    for idx in range(max_len):
        if idx < len(list_a):
            merged.append(list_a[idx])
        if idx < len(list_b):
            merged.append(list_b[idx])
    return merged


def _search_legacy_stock(query: str, preferred_source: str = "pexels_pixabay") -> List[Dict[str, Any]]:
    pref = (preferred_source or "pexels_pixabay").strip().lower()
    if pref == "pexels":
        order = (search_pexels, search_pixabay)
    elif pref == "pixabay":
        order = (search_pixabay, search_pexels)
    elif pref == "coverr":
        order = (search_coverr, search_pexels, search_pixabay)
    elif pref == "mixkit":
        order = (search_mixkit, search_pexels, search_pixabay)
    elif pref == "all":
        order = (search_pexels, search_pixabay, search_coverr, search_mixkit)
    else:
        # Default: Pexels + Pixabay interleaved first
        px = []
        pb = []
        try:
            px = search_pexels(query) or []
        except Exception:
            px = []
        try:
            pb = search_pixabay(query) or []
        except Exception:
            pb = []
        combined = _interleave_lists(px, pb)
        if combined:
            return combined
        order = (search_coverr,)

    for fn in order:
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
def api_stock_search(query: str, limit: int = 12, niche_id: str = "", source: str = "pexels_pixabay"):
    """Searches stock video providers with user-selectable source filter (pexels_pixabay, pexels, pixabay, coverr, mixkit, all)."""
    results: List[Dict[str, Any]] = []
    src = (source or "pexels_pixabay").strip().lower()
    try:
        if src == "pexels":
            results.extend((search_pexels(query) or [])[:limit])
        elif src == "pixabay":
            results.extend((search_pixabay(query) or [])[:limit])
        elif src == "coverr":
            results.extend((search_coverr(query) or [])[:limit])
        elif src == "mixkit":
            results.extend((search_mixkit(query) or [])[:limit])
        else:
            px = search_pexels(query) or []
            pb = search_pixabay(query) or []
            results.extend(_interleave_lists(px, pb)[:limit])
            if len(results) < limit and src in ("all", "pexels_pixabay", "auto", ""):
                cv = search_coverr(query) or []
                results.extend(cv[: limit - len(results)])
            if len(results) < limit and src == "all":
                mx = search_mixkit(query) or []
                results.extend(mx[: limit - len(results)])
        if len(results) < limit:
            keyless = _search_keyless_visuals([query], niche_id=niche_id)
            if keyless:
                results.append(keyless)
    except Exception as e:
        print(f"  [StockSearch] Error: {e}")
    return {"status": "ok", "query": query, "source": src, "results": results[:limit]}


def _fetch_single_scene_video(args):
    i, sc, niche_id, preferred_source = args if len(args) == 4 else (*args, "pexels_pixabay")
    sc_copy = dict(sc)
    niche = (
        niche_id
        or sc.get("niche_id")
        or (sc.get("visual_intent") or {}).get("niche_id")
        or ""
    )
    queries = [str(q).strip() for q in (sc.get("search_queries") or []) if str(q).strip()]
    if sc.get("scene_description") and sc["scene_description"] not in queries:
        queries.append(str(sc["scene_description"]).strip())
    if not queries:
        queries = ["architectural detail soft light", "nature aerial calm"]
    if len(queries) < 2:
        for alt_q in simplify_stock_queries(queries[0]) + ["cinematic atmospheric light", "nature aerial calm"]:
            if alt_q and alt_q not in queries:
                queries.append(alt_q)
            if len(queries) >= 2:
                break
    sc_copy["search_queries"] = queries[:4]

    raw_candidates: List[tuple] = []
    seen_keys: set = set()
    for q in queries[:4]:
        try:
            candidates = _search_legacy_stock(q, preferred_source=preferred_source)
            for cand in candidates:
                key = (str(cand.get("id") or ""), str(cand.get("url") or ""))
                if key not in seen_keys and cand.get("url"):
                    seen_keys.add(key)
                    raw_candidates.append((cand, q))
            if len(raw_candidates) >= 6:
                break
        except Exception:
            continue

    if not raw_candidates and _paid_stock_keys_present():
        try:
            fallbacks = _interleave_lists(
                search_pexels("cinematic nature") or [],
                search_pixabay("nature clouds") or [],
            )
            for cand in fallbacks:
                key = (str(cand.get("id") or ""), str(cand.get("url") or ""))
                if key not in seen_keys and cand.get("url"):
                    seen_keys.add(key)
                    raw_candidates.append((cand, "cinematic nature"))
        except Exception:
            pass

    if not raw_candidates:
        keyless = _search_keyless_visuals(queries, niche_id=niche)
        if keyless and keyless.get("url"):
            raw_candidates.append((keyless, keyless.get("query") or queries[0]))

    sc_copy["_raw_candidates"] = raw_candidates
    if raw_candidates:
        best_video, matched_query = raw_candidates[i % len(raw_candidates)]
        sc_copy["selected_video"] = _candidate_to_selected(best_video, matched_query)
        sc_copy["video_url"] = best_video.get("url") or ""
        sc_copy["stock_candidates"] = [
            _candidate_to_selected(c, mq) for c, mq in raw_candidates[:4]
        ]
        sc_copy.pop("path", None)
        sc_copy.pop("video_path", None)
    return sc_copy


def auto_fetch_videos_for_scenes(
    scenes: List[Dict[str, Any]],
    niche_id: str = "",
    preferred_source: str = "pexels_pixabay",
) -> List[Dict[str, Any]]:
    """Associate top Pexels / Pixabay / stock visual candidates with scenes with cross-scene deduplication."""
    if not scenes:
        return []
    try:
        workers = min(3 if not _paid_stock_keys_present() else 8, max(1, len(scenes)))
        payload = [(i, sc, niche_id, preferred_source) for i, sc in enumerate(scenes)]
        with ThreadPoolExecutor(max_workers=workers) as executor:
            fetched = list(executor.map(_fetch_single_scene_video, payload))
        used_ids: set = set()
        used_urls: set = set()
        for idx, sc in enumerate(fetched):
            raw_cands = sc.pop("_raw_candidates", None) or []
            if not raw_cands:
                continue
            chosen_pair = None
            for cand, mq in raw_cands:
                cid = str(cand.get("id") or "")
                curl = str(cand.get("url") or "")
                if (not cid or cid not in used_ids) and (not curl or curl not in used_urls):
                    chosen_pair = (cand, mq)
                    break
            if not chosen_pair:
                chosen_pair = raw_cands[idx % len(raw_cands)]
            best_cand, best_q = chosen_pair
            if best_cand.get("id"):
                used_ids.add(str(best_cand["id"]))
            if best_cand.get("url"):
                used_urls.add(str(best_cand["url"]))
            selected_obj = _candidate_to_selected(best_cand, best_q)
            sc["selected_video"] = selected_obj
            sc["video_url"] = best_cand.get("url") or ""
            alt_list = [selected_obj]
            for cand, mq in raw_cands:
                if len(alt_list) >= 4:
                    break
                alt_obj = _candidate_to_selected(cand, mq)
                if alt_obj.get("url") and alt_obj.get("url") != selected_obj.get("url"):
                    alt_list.append(alt_obj)
            sc["stock_candidates"] = alt_list
        return fetched
    except Exception as e:
        print(f"  [AutoStockParallel] {e}")
        return scenes


@router.post("/api/stock/fetch_for_scenes")
def api_fetch_stock_for_scenes(req: FetchStockScenesRequest):
    """Fetches matched stock videos for all scenes in a plan using the selected provider."""
    niche = req.niche_id or ""
    if not niche and req.scenes:
        niche = str(req.scenes[0].get("niche_id") or "")
    pref_src = (req.preferred_source or "pexels_pixabay").strip().lower()
    updated = auto_fetch_videos_for_scenes(req.scenes, niche_id=niche, preferred_source=pref_src)
    assigned = sum(
        1 for s in updated if s.get("selected_video") and s["selected_video"].get("url")
    )
    return {
        "status": "ok",
        "scenes": updated,
        "assigned": assigned,
        "total": len(updated),
        "preferred_source": pref_src,
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
