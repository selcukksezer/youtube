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
    if data.sonilo_key:
        saved.append("sonilo")
    return {
        "status": "ok",
        "message": "Configuration updated successfully",
        "saved_keys": saved,
        "key_hints": _key_hints(),
    }


@router.post("/api/keys/test")
def test_api_key(req: KeyTestRequest):
    import config
    p = req.provider.lower().strip()
    k = (req.api_key or "").strip()
    if not k:
        fallback_map = {
            "gemini": getattr(config, "GEMINI_API_KEY", ""),
            "openai": getattr(config, "OPENAI_API_KEY", ""),
            "deepseek": getattr(config, "DEEPSEEK_API_KEY", ""),
            "grok": getattr(config, "GROK_API_KEY", ""),
            "pexels": getattr(config, "PEXELS_API_KEY", ""),
            "pixabay": getattr(config, "PIXABAY_API_KEY", ""),
            "elevenlabs": getattr(config, "ELEVENLABS_API_KEY", ""),
            "youtube_data": getattr(config, "YOUTUBE_DATA_API_KEY", ""),
        }
        k = (fallback_map.get(p) or "").strip()
    if not k:
        raise HTTPException(status_code=400, detail="API anahtarı boş olamaz.")

    def _ok(msg: str) -> dict:
        return {"status": "ok", "valid": True, "message": msg, "detail": msg}

    try:
        if p == "gemini":
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={k}"
            r = requests.get(url, timeout=8)
            if r.status_code == 200:
                return _ok("Gemini API bağlantısı başarılı!")
            raise HTTPException(status_code=400, detail=f"Gemini API hatası: HTTP {r.status_code}")
        elif p == "openai":
            r = requests.get("https://api.openai.com/v1/models", headers={"Authorization": f"Bearer {k}"}, timeout=8)
            if r.status_code == 200:
                return _ok("OpenAI API bağlantısı başarılı!")
            raise HTTPException(status_code=400, detail=f"OpenAI API hatası: HTTP {r.status_code}")
        elif p == "deepseek":
            r = requests.get("https://api.deepseek.com/models", headers={"Authorization": f"Bearer {k}"}, timeout=8)
            if r.status_code == 200:
                return _ok("DeepSeek API bağlantısı başarılı!")
            raise HTTPException(status_code=400, detail=f"DeepSeek API hatası: HTTP {r.status_code}")
        elif p == "grok":
            r = requests.get("https://api.x.ai/v1/models", headers={"Authorization": f"Bearer {k}"}, timeout=8)
            if r.status_code == 200:
                return _ok("Grok (xAI) API bağlantısı başarılı!")
            raise HTTPException(status_code=400, detail=f"Grok API hatası: HTTP {r.status_code}")
        elif p == "pexels":
            r = requests.get("https://api.pexels.com/v1/curated?per_page=1", headers={"Authorization": k}, timeout=8)
            if r.status_code == 200:
                return _ok("Pexels API bağlantısı başarılı!")
            raise HTTPException(status_code=400, detail=f"Pexels API hatası: HTTP {r.status_code}")
        elif p == "pixabay":
            r = requests.get(f"https://pixabay.com/api/?key={k}&q=nature", timeout=8)
            if r.status_code == 200:
                return _ok("Pixabay API bağlantısı başarılı!")
            raise HTTPException(status_code=400, detail=f"Pixabay API hatası: HTTP {r.status_code}")
        elif p == "elevenlabs":
            r = requests.get("https://api.elevenlabs.io/v1/user", headers={"xi-api-key": k}, timeout=8)
            if r.status_code == 200:
                return _ok("ElevenLabs API bağlantısı başarılı!")
            raise HTTPException(status_code=400, detail=f"ElevenLabs API hatası: HTTP {r.status_code}")
        elif p == "youtube_data":
            r = requests.get(f"https://www.googleapis.com/youtube/v3/videos?part=id&chart=mostPopular&maxResults=1&key={k}", timeout=8)
            if r.status_code == 200:
                return _ok("YouTube Data API v3 bağlantısı başarılı!")
            raise HTTPException(status_code=400, detail=f"YouTube Data API hatası: HTTP {r.status_code}")
        else:
            raise HTTPException(status_code=400, detail=f"Bilinmeyen sağlayıcı: {p}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bağlantı hatası: {str(e)}")
