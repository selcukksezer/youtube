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


@router.get("/api/subtitle_presets")
def get_subtitle_presets():
    """Returns preset subtitle styles including CapCut yellow & cyber green (Item 43)."""
    return {"presets": SUBTITLE_PRESETS}
