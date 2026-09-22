"""
Configuration and API key testing router.
"""
from fastapi import APIRouter, HTTPException
import requests
from api_models import ConfigUpdateModel, KeyTestRequest
from settings_service import apply_dashboard_config, get_dashboard_config, _key_hints

router = APIRouter(tags=["Config"])


@router.get("/api/config")
def get_config():
    return get_dashboard_config()


@router.post("/api/config")
def update_config(data: ConfigUpdateModel):
    try:
        apply_dashboard_config(data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    saved = []
    if data.elevenlabs_key:
        saved.append("elevenlabs")
    return {
        "status": "ok",
        "message": "Configuration updated successfully",
        "saved_keys": saved,
        "key_hints": _key_hints(),
    }


@router.post("/api/keys/test")
def test_api_key(req: KeyTestRequest):
    p = req.provider.lower()
    k = req.api_key.strip()
    if not k:
        raise HTTPException(status_code=400, detail="API anahtarı boş olamaz.")
    
    try:
        if p == "gemini":
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={k}"
            r = requests.get(url, timeout=8)
            if r.status_code == 200:
                return {"status": "ok", "message": "Gemini API bağlantısı başarılı!"}
            raise HTTPException(status_code=400, detail=f"Gemini API hatası: HTTP {r.status_code}")
        elif p == "openai":
            r = requests.get("https://api.openai.com/v1/models", headers={"Authorization": f"Bearer {k}"}, timeout=8)
            if r.status_code == 200:
                return {"status": "ok", "message": "OpenAI API bağlantısı başarılı!"}
            raise HTTPException(status_code=400, detail=f"OpenAI API hatası: HTTP {r.status_code}")
        elif p == "pexels":
            r = requests.get("https://api.pexels.com/v1/curated?per_page=1", headers={"Authorization": k}, timeout=8)
            if r.status_code == 200:
                return {"status": "ok", "message": "Pexels API bağlantısı başarılı!"}
            raise HTTPException(status_code=400, detail=f"Pexels API hatası: HTTP {r.status_code}")
        elif p == "pixabay":
            r = requests.get(f"https://pixabay.com/api/?key={k}&q=nature", timeout=8)
            if r.status_code == 200:
                return {"status": "ok", "message": "Pixabay API bağlantısı başarılı!"}
            raise HTTPException(status_code=400, detail=f"Pixabay API hatası: HTTP {r.status_code}")
        else:
            raise HTTPException(status_code=400, detail="Bilinmeyen sağlayıcı")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bağlantı hatası: {str(e)}")
