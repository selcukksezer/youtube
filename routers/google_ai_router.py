"""
Google AI Pro hub + royalty-free / VoiceLab-style audio routes.
"""
import os
import tempfile
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

import config
from api_models import (
    GoogleAIGenerateImageRequest,
    GoogleAIGenerateVideoRequest,
    RoyaltyFreeBgmRequest,
)
from google_ai_hub import get_plan_and_quota_snapshot, list_live_models, save_generated_image, generate_veo_video
from royalty_free_audio import (
    list_voicelab_library,
    fetch_royalty_free_bgm,
    search_pixabay_music,
    search_mixkit,
    seed_voicelab_pack,
)

router = APIRouter(tags=["GoogleAI"])


@router.get("/api/google-ai/plan")
def api_google_ai_plan():
    """Plan info + model catalog + live quota snapshot for Settings UI."""
    return get_plan_and_quota_snapshot()


@router.get("/api/google-ai/models")
def api_google_ai_models():
    return list_live_models()


@router.post("/api/google-ai/generate-image")
def api_google_ai_generate_image(req: GoogleAIGenerateImageRequest):
    if not config.GEMINI_API_KEY:
        raise HTTPException(400, "Gemini API anahtari gerekli")
    out_dir = os.path.join(config.OUTPUT_DIR, "google_ai")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"img_{abs(hash(req.prompt)) % 10_000_000}.png")
    saved = save_generated_image(req.prompt, path, model=req.model, force=True)
    if not saved:
        raise HTTPException(502, "Gorsel uretilemedi — model/kota veya billing kontrol edin")
    return {
        "status": "ok",
        "path": saved,
        "url": f"/output/google_ai/{os.path.basename(saved)}",
        "model": req.model or config.GEMINI_IMAGE_MODEL,
    }


@router.post("/api/google-ai/generate-video")
def api_google_ai_generate_video(req: GoogleAIGenerateVideoRequest):
    if not config.GEMINI_API_KEY:
        raise HTTPException(400, "Gemini API anahtari gerekli")
    out_dir = os.path.join(config.OUTPUT_DIR, "google_ai")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"veo_{abs(hash(req.prompt)) % 10_000_000}.mp4")
    saved = generate_veo_video(
        req.prompt,
        path,
        model=req.model,
        duration_seconds=req.duration_seconds or 6,
    )
    if not saved:
        raise HTTPException(
            502,
            "Veo video uretilemedi — ucretli Gemini API / Veo kotasi gerekir (Google AI Pro chat kotasi yeterli olmayabilir)",
        )
    return {
        "status": "ok",
        "path": saved,
        "url": f"/output/google_ai/{os.path.basename(saved)}",
        "model": req.model or config.GEMINI_VIDEO_MODEL,
    }


@router.get("/api/voicelab/library")
def api_voicelab_library():
    return list_voicelab_library()


@router.post("/api/voicelab/seed")
def api_voicelab_seed():
    files = seed_voicelab_pack()
    return {"status": "ok", "files": files, "count": len(files)}


@router.get("/api/audio/royalty-free/search")
def api_rf_search(query: str = "ambient", prefer: str = "auto"):
    pix = search_pixabay_music(query) if prefer in ("auto", "pixabay") else []
    mix = search_mixkit(query)
    return {"status": "ok", "pixabay": pix[:15], "mixkit": mix[:15], "query": query}


@router.post("/api/audio/royalty-free/fetch")
def api_rf_fetch(req: RoyaltyFreeBgmRequest):
    name = fetch_royalty_free_bgm(req.query or "ambient cinematic", prefer=req.prefer or "auto")
    if not name:
        raise HTTPException(404, "Telifsiz BGM bulunamadi")
    return {"status": "ok", "filename": name, "path": os.path.join(config.BGM_DIR, name)}
