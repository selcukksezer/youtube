"""
Background music (BGM) and subtitle presets router.
"""
import os
import shutil
from fastapi import APIRouter, File, UploadFile, HTTPException
import config
from bgm_manager import list_bgm_tracks
from subtitle_generator import SUBTITLE_PRESETS

router = APIRouter(tags=["Media"])

ALLOWED_BGM_EXTS = {'.mp3', '.wav', '.m4a', '.aac', '.ogg'}


@router.get("/api/bgm/list")
def get_bgm_list():
    tracks = list_bgm_tracks()
    return {"tracks": tracks}


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
from stock_providers import search_pexels, search_pixabay, search_coverr


class FetchStockScenesRequest(BaseModel):
    scenes: List[Dict[str, Any]]


@router.get("/api/subtitle_presets")
def get_subtitle_presets():
    """Returns preset subtitle styles including CapCut yellow & cyber green (Item 43)."""
    return {"presets": SUBTITLE_PRESETS}


@router.get("/api/stock/search")
def api_stock_search(query: str, limit: int = 6):
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
    except Exception as e:
        print(f"  [StockSearch] Error: {e}")
    return {"status": "ok", "query": query, "results": results[:limit]}


from concurrent.futures import ThreadPoolExecutor


def _fetch_single_scene_video(args):
    i, sc = args
    sc_copy = dict(sc)
    queries = sc.get("search_queries", [])
    if not queries and sc.get("scene_description"):
        queries = [sc["scene_description"]]
    if not queries:
        queries = ["cinematic aerial drone", "dramatic lighting"]

    best_video = None
    for q in queries[:2]:
        try:
            candidates = search_pexels(q)
            if not candidates:
                candidates = search_pixabay(q)
            if not candidates:
                candidates = search_coverr(q)

            if candidates:
                best_video = candidates[0]
                break
        except Exception:
            continue

    if not best_video:
        try:
            fallbacks = search_pexels("cinematic drone nature")
            if fallbacks:
                best_video = fallbacks[i % len(fallbacks)]
        except Exception:
            pass

    if best_video:
        sc_copy["selected_video"] = {
            "id": best_video["id"],
            "source": best_video["source"],
            "url": best_video["url"],
            "thumbnail": best_video.get("thumbnail", ""),
            "duration": best_video.get("duration", 10),
            "width": best_video.get("width", 1080),
            "height": best_video.get("height", 1920),
            "query": queries[0] if queries else ""
        }
    return sc_copy


def auto_fetch_videos_for_scenes(scenes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Helper to associate top stock video candidates with scenes in parallel."""
    if not scenes:
        return []
    try:
        with ThreadPoolExecutor(max_workers=min(8, len(scenes))) as executor:
            return list(executor.map(_fetch_single_scene_video, enumerate(scenes)))
    except Exception as e:
        print(f"  [AutoStockParallel] {e}")
        return scenes


@router.post("/api/stock/fetch_for_scenes")
def api_fetch_stock_for_scenes(req: FetchStockScenesRequest):
    """Fetches matched stock videos for all scenes in a plan."""
    updated = auto_fetch_videos_for_scenes(req.scenes)
    return {"status": "ok", "scenes": updated}
