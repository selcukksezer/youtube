"""
Background music (BGM), TTS preview, and subtitle presets router.
"""
import os
import shutil
import uuid
from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
import config
from api_models import TtsPreviewRequest
from bgm_manager import list_bgm_tracks, list_bgm_tracks_detailed
from subtitle_generator import SUBTITLE_PRESETS

router = APIRouter(tags=["Media"])

ALLOWED_BGM_EXTS = {'.mp3', '.wav', '.m4a', '.aac', '.ogg'}


@router.get("/api/bgm/list")
def get_bgm_list(include_catalog: bool = True):
    tracks = list_bgm_tracks_detailed(include_catalog=include_catalog)
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
    sample = (req.text or "Merhaba, bu kısa ses önizlemesidir.").strip()[:280]
    lang = (req.language or config.LANGUAGE or "tr").lower()
    gender = req.voice_gender or "male"
    if gender == "auto":
        from voice_humanizer import select_voice_gender
        gender = select_voice_gender("", sample)

    from tts_voices import resolve_voice, voice_gender_for_id

    orig_lang = config.LANGUAGE
    orig_voice = config.TTS_VOICE
    orig_gender = config.TTS_GENDER
    try:
        config.LANGUAGE = lang
        config.TTS_VOICE = resolve_voice(lang, voice_id=req.tts_voice, gender=gender)
        config.TTS_GENDER = voice_gender_for_id(config.TTS_VOICE, lang)

        out_dir = os.path.join(config.AUDIO_DIR, "previews")
        os.makedirs(out_dir, exist_ok=True)
        wav_path = os.path.join(out_dir, f"preview_{uuid.uuid4().hex[:10]}.wav")

        from tts_engine import generate_narration_with_timing, active_tts_provider
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
        config.LANGUAGE = orig_lang
        config.TTS_VOICE = orig_voice
        config.TTS_GENDER = orig_gender


@router.post("/api/bgm/upload")
async def upload_bgm(file: UploadFile = File(...)):
    safe_name = os.path.basename(file.filename or "")
    ext = os.path.splitext(safe_name)[1].lower()
    if not safe_name or ext not in ALLOWED_BGM_EXTS:
        raise HTTPException(
            status_code=400, 
            detail=f"Desteklenmeyen dosya formatı ({ext}). Yalnızca MP3, WAV, M4A, AAC ve OGG kabul edilir."
        )
    os.makedirs(config.BGM_DIR, exist_ok=True)
    file_path = os.path.join(config.BGM_DIR, safe_name)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"status": "ok", "filename": safe_name}


@router.delete("/api/bgm/{filename}")
def delete_bgm_track(filename: str):
    safe_name = os.path.basename(filename)
    fp = os.path.realpath(os.path.join(config.BGM_DIR, safe_name))
    bgm_dir_real = os.path.realpath(config.BGM_DIR)
    if not fp.startswith(bgm_dir_real) or not os.path.exists(fp):
        raise HTTPException(status_code=404, detail="Müzik dosyası bulunamadı.")
    try:
        os.remove(fp)
        return {"status": "ok", "message": f"{safe_name} silindi."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from stock_providers import search_pexels, search_pixabay, search_coverr, search_mixkit
import config


class FetchStockScenesRequest(BaseModel):
    scenes: List[Dict[str, Any]]
    niche_id: Optional[str] = None


@router.get("/api/subtitle_presets")
def get_subtitle_presets():
    """Returns preset subtitle styles including CapCut yellow & cyber green (Item 43)."""
    return {"presets": SUBTITLE_PRESETS}


def _paid_stock_keys_present() -> bool:
    return bool(getattr(config, "PEXELS_API_KEY", "") or getattr(config, "PIXABAY_API_KEY", ""))


def _candidate_to_selected(best: Dict[str, Any], query: str) -> Dict[str, Any]:
    return {
        "id": best.get("id", ""),
        "source": best.get("source", "stock"),
        "url": best.get("url", ""),
        "thumbnail": best.get("thumbnail") or best.get("url") or "",
        "duration": best.get("duration", 10),
        "width": best.get("width", 1080),
        "height": best.get("height", 1920),
        "query": query,
        "kind": best.get("kind", "video"),
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


def _search_keyless_visuals(queries: List[str], niche_id: str = "") -> Optional[Dict[str, Any]]:
    """Openverse / Wikimedia when Pexels+Pixabay keys empty. Prefer openverse (less 429)."""
    try:
        from visuals.registry import ordered_providers, search_provider
        from visuals.query_builder import keyless_seed_queries
    except Exception as exc:
        print(f"  [AutoStock] keyless import note: {exc}")
        return None

    seeds = keyless_seed_queries(niche_id=niche_id or "", queries=queries, max_seeds=5)
    providers = ordered_providers(niche_id or "")
    # Prefer image/openverse first when keys missing — faster + more hits for religious niche
    preferred = [s for s in providers if s.key in ("openverse", "wikimedia_img", "wikimedia")]
    if not preferred:
        preferred = providers

    for q in seeds:
        for spec in preferred:
            try:
                cands = search_provider(spec, q, per_page=4) or []
            except Exception as exc:
                print(f"  [AutoStock:{spec.key}] {exc}")
                continue
            for cand in cands:
                url = getattr(cand, "url", "") or ""
                if not url:
                    continue
                return {
                    "id": cand.id,
                    "source": cand.source,
                    "url": url,
                    "thumbnail": cand.thumbnail or url,
                    "duration": float(cand.duration or 8),
                    "width": int(cand.width or 1080),
                    "height": int(cand.height or 1920),
                    "kind": getattr(cand, "kind", "image") or "image",
                    "query": q,
                }
    return None


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
                results.extend(pb[:limit - len(results)])
        if len(results) < limit:
            cv = search_coverr(query)
            if cv:
                results.extend(cv[:limit - len(results)])
        if len(results) < limit:
            mx = search_mixkit(query)
            if mx:
                results.extend(mx[:limit - len(results)])
        if len(results) < limit:
            keyless = _search_keyless_visuals([query], niche_id=niche_id)
            if keyless:
                results.append(keyless)
    except Exception as e:
        print(f"  [StockSearch] Error: {e}")
    return {"status": "ok", "query": query, "results": results[:limit]}


from concurrent.futures import ThreadPoolExecutor


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
    return sc_copy


def auto_fetch_videos_for_scenes(
    scenes: List[Dict[str, Any]],
    niche_id: str = "",
) -> List[Dict[str, Any]]:
    """Associate top stock / keyless visual candidates with scenes."""
    if not scenes:
        return []
    try:
        # Fewer workers when relying on Openverse/Wikimedia — avoids 429 storms
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
    assigned = sum(1 for s in updated if s.get("selected_video") and s["selected_video"].get("url"))
    return {
        "status": "ok",
        "scenes": updated,
        "assigned": assigned,
        "total": len(updated),
        "paid_keys": _paid_stock_keys_present(),
    }
