"""Runtime configuration queries and updates for the dashboard."""
import os
from typing import Any, Dict, Tuple

import config


def mask_api_key(value: str) -> str:
    """Mask secret for UI — never expose full key."""
    v = (value or "").strip()
    if not v:
        return ""
    if len(v) <= 4:
        return "••••"
    return "••••" + v[-4:]


def _key_hints() -> Dict[str, str]:
    return {
        "gemini": mask_api_key(config.GEMINI_API_KEY),
        "openai": mask_api_key(config.OPENAI_API_KEY),
        "deepseek": mask_api_key(config.DEEPSEEK_API_KEY),
        "grok": mask_api_key(config.GROK_API_KEY),
        "pexels": mask_api_key(config.PEXELS_API_KEY),
        "pixabay": mask_api_key(config.PIXABAY_API_KEY),
        "youtube_data": mask_api_key(config.YOUTUBE_DATA_API_KEY),
        "reddit_id": mask_api_key(config.REDDIT_CLIENT_ID),
        "reddit_secret": mask_api_key(config.REDDIT_CLIENT_SECRET),
        "elevenlabs": mask_api_key(getattr(config, "ELEVENLABS_API_KEY", "")),
    }


def _elevenlabs_dashboard_info() -> Dict[str, Any]:
    from elevenlabs_tts import get_subscription_info, is_configured
    configured = is_configured()
    info: Dict[str, Any] = {"configured": configured}
    if configured:
        info["quota"] = get_subscription_info()
    return info


def get_dashboard_config() -> Dict[str, Any]:
    from tts_voices import get_voice_catalog
    from gameplay_pool import list_categories

    voice_dict = config.VOICES.get(config.LANGUAGE, config.VOICES["en"])
    sources = ["Pexels"]
    if config.PIXABAY_API_KEY:
        sources.append("Pixabay")
    sources.extend(["Coverr", "Mixkit", "Videvo"])
    return {
        "language": config.LANGUAGE, "ai_provider": config.AI_PROVIDER, "ai_model": config.AI_MODEL,
        "tts_gender": config.TTS_GENDER, "tts_voice": config.TTS_VOICE,
        "tts_rate": config.TTS_RATE, "tts_pitch": config.TTS_PITCH,
        "voices": voice_dict, "tts_voice_catalog": get_voice_catalog(),
        "gameplay_categories": list_categories(), "active_sources": sources,
        "keys": {
            "gemini": bool(config.GEMINI_API_KEY), "openai": bool(config.OPENAI_API_KEY),
            "deepseek": bool(config.DEEPSEEK_API_KEY), "grok": bool(config.GROK_API_KEY),
            "pexels": bool(config.PEXELS_API_KEY), "pixabay": bool(config.PIXABAY_API_KEY),
            "youtube_data": bool(config.YOUTUBE_DATA_API_KEY),
            "reddit": bool(config.REDDIT_CLIENT_ID and config.REDDIT_CLIENT_SECRET),
            "elevenlabs": bool(getattr(config, "ELEVENLABS_API_KEY", "")),
        },
        "key_hints": _key_hints(),
        "elevenlabs": _elevenlabs_dashboard_info(),
        "subtitle": {"color": config.SUBTITLE_COLOR, "highlight_color": config.SUBTITLE_HIGHLIGHT_COLOR, "font_size": config.SUBTITLE_FONT_SIZE, "y_position": config.SUBTITLE_Y_POSITION},
        "audio": {"enable_bgm": config.ENABLE_BGM, "bgm_volume": config.BGM_VOLUME, "default_bgm_track": config.DEFAULT_BGM_TRACK},
        "google_ai": {
            "gemini_model": getattr(config, "GEMINI_MODEL", ""),
            "gemini_image_model": getattr(config, "GEMINI_IMAGE_MODEL", ""),
            "gemini_video_model": getattr(config, "GEMINI_VIDEO_MODEL", ""),
            "gemini_tts_model": getattr(config, "GEMINI_TTS_MODEL", ""),
            "use_gemini_image_gen": getattr(config, "USE_GEMINI_IMAGE_GEN", True),
            "use_gemini_video_gen": getattr(config, "USE_GEMINI_VIDEO_GEN", False),
            "use_gemini_tts": getattr(config, "USE_GEMINI_TTS", False),
            "use_gemini_grounding": getattr(config, "USE_GEMINI_GROUNDING", False),
            "use_gemini_embeddings": getattr(config, "USE_GEMINI_EMBEDDINGS", False),
            "prefer_gemini_scene_images": getattr(config, "PREFER_GEMINI_SCENE_IMAGES", False),
            "auto_fetch_royalty_free_bgm": getattr(config, "AUTO_FETCH_ROYALTY_FREE_BGM", True),
        },
    }


def refresh_ai_provider() -> None:
    """Uses current runtime values rather than the startup-time provider tuple."""
    providers = [
        ("Gemini", config.GEMINI_API_KEY, "https://generativelanguage.googleapis.com/v1beta/openai/", config.GEMINI_MODEL),
        ("DeepSeek", config.DEEPSEEK_API_KEY, "https://api.deepseek.com", config.DEEPSEEK_MODEL),
        ("OpenAI", config.OPENAI_API_KEY, "https://api.openai.com/v1", config.OPENAI_MODEL),
        ("Grok", config.GROK_API_KEY, "https://api.x.ai/v1", config.GROK_MODEL),
    ]
    for name, api_key, base_url, model in providers:
        if api_key:
            config.AI_PROVIDER, config.AI_API_KEY, config.AI_BASE_URL, config.AI_MODEL = name, api_key, base_url, model
            return
    config.AI_PROVIDER, config.AI_API_KEY, config.AI_BASE_URL, config.AI_MODEL = "Yerel Fallback", "", "", "procedural"


def apply_dashboard_config(data: Any) -> None:
    for field, target in {
        "gemini_key": "GEMINI_API_KEY", "openai_key": "OPENAI_API_KEY", "deepseek_key": "DEEPSEEK_API_KEY",
        "grok_key": "GROK_API_KEY", "pexels_key": "PEXELS_API_KEY", "pixabay_key": "PIXABAY_API_KEY",
        "youtube_data_key": "YOUTUBE_DATA_API_KEY", "reddit_client_id": "REDDIT_CLIENT_ID",
        "reddit_client_secret": "REDDIT_CLIENT_SECRET", "elevenlabs_key": "ELEVENLABS_API_KEY",
        "subtitle_color": "SUBTITLE_COLOR",
        "subtitle_highlight_color": "SUBTITLE_HIGHLIGHT_COLOR", "subtitle_font_size": "SUBTITLE_FONT_SIZE",
        "subtitle_y_position": "SUBTITLE_Y_POSITION", "enable_bgm": "ENABLE_BGM", "bgm_volume": "BGM_VOLUME",
        "default_bgm_track": "DEFAULT_BGM_TRACK",
        "gemini_model": "GEMINI_MODEL",
        "gemini_image_model": "GEMINI_IMAGE_MODEL",
        "gemini_video_model": "GEMINI_VIDEO_MODEL",
        "gemini_tts_model": "GEMINI_TTS_MODEL",
        "use_gemini_image_gen": "USE_GEMINI_IMAGE_GEN",
        "use_gemini_video_gen": "USE_GEMINI_VIDEO_GEN",
        "use_gemini_tts": "USE_GEMINI_TTS",
        "use_gemini_grounding": "USE_GEMINI_GROUNDING",
        "use_gemini_embeddings": "USE_GEMINI_EMBEDDINGS",
        "prefer_gemini_scene_images": "PREFER_GEMINI_SCENE_IMAGES",
        "auto_fetch_royalty_free_bgm": "AUTO_FETCH_ROYALTY_FREE_BGM",
    }.items():
        value = getattr(data, field, None)
        if value is not None:
            setattr(config, target, value)
            os.environ[target] = str(value)
            if target == "ELEVENLABS_API_KEY":
                from tts_voices import clear_elevenlabs_voice_cache
                clear_elevenlabs_voice_cache()
    if data.language:
        config.LANGUAGE = data.language
    tts_voice = getattr(data, "tts_voice", None)
    if tts_voice:
        from tts_voices import resolve_voice, voice_gender_for_id
        config.TTS_VOICE = resolve_voice(config.LANGUAGE, voice_id=tts_voice)
        config.TTS_GENDER = voice_gender_for_id(config.TTS_VOICE, config.LANGUAGE)
    elif data.tts_gender:
        from tts_voices import resolve_voice
        config.TTS_GENDER = data.tts_gender
        config.TTS_VOICE = resolve_voice(config.LANGUAGE, gender=data.tts_gender)
    if data.tts_rate:
        config.TTS_RATE = data.tts_rate
    if data.tts_pitch:
        config.TTS_PITCH = data.tts_pitch
    # Keep AI_MODEL in sync when Gemini is active
    if getattr(data, "gemini_model", None) and config.GEMINI_API_KEY:
        config.AI_MODEL = config.GEMINI_MODEL
    refresh_ai_provider()
    ok, err = _save_to_env_file()
    if not ok:
        raise RuntimeError(f".env dosyasına yazılamadı: {err}")


def _env_file_path() -> str:
    return os.path.join(config.BASE_DIR, ".env")


def _dashboard_env_updates() -> Dict[str, str]:
    return {
        "GEMINI_API_KEY": config.GEMINI_API_KEY or "",
        "GEMINI_MODEL": getattr(config, "GEMINI_MODEL", "gemini-flash-lite-latest") or "",
        "GEMINI_IMAGE_MODEL": getattr(config, "GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image") or "",
        "GEMINI_VIDEO_MODEL": getattr(config, "GEMINI_VIDEO_MODEL", "veo-3.1-fast-generate-preview") or "",
        "GEMINI_TTS_MODEL": getattr(config, "GEMINI_TTS_MODEL", "") or "",
        "USE_GEMINI_IMAGE_GEN": str(getattr(config, "USE_GEMINI_IMAGE_GEN", True)).lower(),
        "USE_GEMINI_VIDEO_GEN": str(getattr(config, "USE_GEMINI_VIDEO_GEN", False)).lower(),
        "USE_GEMINI_TTS": str(getattr(config, "USE_GEMINI_TTS", False)).lower(),
        "USE_GEMINI_GROUNDING": str(getattr(config, "USE_GEMINI_GROUNDING", False)).lower(),
        "USE_GEMINI_EMBEDDINGS": str(getattr(config, "USE_GEMINI_EMBEDDINGS", False)).lower(),
        "PREFER_GEMINI_SCENE_IMAGES": str(getattr(config, "PREFER_GEMINI_SCENE_IMAGES", False)).lower(),
        "AUTO_FETCH_ROYALTY_FREE_BGM": str(getattr(config, "AUTO_FETCH_ROYALTY_FREE_BGM", True)).lower(),
        "OPENAI_API_KEY": config.OPENAI_API_KEY or "",
        "DEEPSEEK_API_KEY": config.DEEPSEEK_API_KEY or "",
        "GROK_API_KEY": config.GROK_API_KEY or "",
        "PEXELS_API_KEY": config.PEXELS_API_KEY or "",
        "PIXABAY_API_KEY": config.PIXABAY_API_KEY or "",
        "YOUTUBE_DATA_API_KEY": config.YOUTUBE_DATA_API_KEY or "",
        "REDDIT_CLIENT_ID": config.REDDIT_CLIENT_ID or "",
        "REDDIT_CLIENT_SECRET": config.REDDIT_CLIENT_SECRET or "",
        "ELEVENLABS_API_KEY": getattr(config, "ELEVENLABS_API_KEY", "") or "",
        "ELEVENLABS_MODEL_ID": getattr(config, "ELEVENLABS_MODEL_ID", "eleven_multilingual_v2") or "",
        "LANGUAGE": config.LANGUAGE or "tr",
        "TTS_GENDER": config.TTS_GENDER or "male",
        "TTS_VOICE": config.TTS_VOICE or "",
        "ENABLE_BGM": str(config.ENABLE_BGM).lower(),
        "BGM_VOLUME": str(config.BGM_VOLUME),
        "RENDER_SAFE_MODE": str(getattr(config, "RENDER_SAFE_MODE", True)).lower(),
        "RENDER_RESOLUTION_MODE": str(getattr(config, "RENDER_RESOLUTION_MODE", "1080p")),
        "RENDER_THREADS": str(getattr(config, "RENDER_THREADS", 8)),
        "USE_GPU_ACCELERATION": str(getattr(config, "USE_GPU_ACCELERATION", True)).lower(),
    }


def _save_to_env_file() -> Tuple[bool, str]:
    """Merge dashboard keys into .env (preserve unrelated entries)."""
    from dotenv import dotenv_values, set_key

    env_path = _env_file_path()
    updates = _dashboard_env_updates()
    try:
        env_dir = os.path.dirname(env_path)
        if env_dir:
            os.makedirs(env_dir, exist_ok=True)
        if not os.path.isfile(env_path):
            with open(env_path, "a", encoding="utf-8"):
                pass
        for key, value in updates.items():
            set_key(env_path, key, value if value is not None else "", quote_mode="never")
        # Verify write when ElevenLabs key is configured
        el_key = getattr(config, "ELEVENLABS_API_KEY", "") or ""
        if el_key:
            saved = (dotenv_values(env_path).get("ELEVENLABS_API_KEY") or "").strip()
            if saved != el_key:
                return False, "ELEVENLABS_API_KEY .env içinde doğrulanamadı"
        print(f"  [BILGI] Yapilandirma .env dosyasina kaydedildi: {env_path}")
        return True, env_path
    except OSError as exc:
        print(f"  [UYARI] .env dosyasi kaydedilemedi: {exc}")
        return False, str(exc)
    except Exception as exc:
        print(f"  [UYARI] .env dosyasi kaydedilemedi: {exc}")
        return False, str(exc)