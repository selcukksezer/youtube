"""Runtime configuration queries and updates for the dashboard."""
from typing import Any, Dict

import config


def get_dashboard_config() -> Dict[str, Any]:
    voice_dict = config.VOICES.get(config.LANGUAGE, config.VOICES["en"])
    sources = ["Pexels"]
    if config.PIXABAY_API_KEY:
        sources.append("Pixabay")
    sources.extend(["Coverr", "Mixkit", "Videvo"])
    return {
        "language": config.LANGUAGE, "ai_provider": config.AI_PROVIDER, "ai_model": config.AI_MODEL,
        "tts_gender": config.TTS_GENDER, "tts_rate": config.TTS_RATE, "tts_pitch": config.TTS_PITCH,
        "voices": voice_dict, "active_sources": sources,
        "keys": {
            "gemini": bool(config.GEMINI_API_KEY), "openai": bool(config.OPENAI_API_KEY),
            "deepseek": bool(config.DEEPSEEK_API_KEY), "grok": bool(config.GROK_API_KEY),
            "pexels": bool(config.PEXELS_API_KEY), "pixabay": bool(config.PIXABAY_API_KEY),
            "youtube_data": bool(config.YOUTUBE_DATA_API_KEY),
            "reddit": bool(config.REDDIT_CLIENT_ID and config.REDDIT_CLIENT_SECRET),
        },
        "subtitle": {"color": config.SUBTITLE_COLOR, "highlight_color": config.SUBTITLE_HIGHLIGHT_COLOR, "font_size": config.SUBTITLE_FONT_SIZE, "y_position": config.SUBTITLE_Y_POSITION},
        "audio": {"enable_bgm": config.ENABLE_BGM, "bgm_volume": config.BGM_VOLUME, "default_bgm_track": config.DEFAULT_BGM_TRACK},
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
        "reddit_client_secret": "REDDIT_CLIENT_SECRET", "subtitle_color": "SUBTITLE_COLOR",
        "subtitle_highlight_color": "SUBTITLE_HIGHLIGHT_COLOR", "subtitle_font_size": "SUBTITLE_FONT_SIZE",
        "subtitle_y_position": "SUBTITLE_Y_POSITION", "enable_bgm": "ENABLE_BGM", "bgm_volume": "BGM_VOLUME",
        "default_bgm_track": "DEFAULT_BGM_TRACK",
    }.items():
        value = getattr(data, field, None)
        if value is not None:
            setattr(config, target, value)
    if data.language:
        config.LANGUAGE = data.language
    if data.tts_gender:
        config.TTS_GENDER = data.tts_gender
        config.TTS_VOICE = config.VOICES.get(config.LANGUAGE, config.VOICES["en"])[data.tts_gender]
    if data.tts_rate:
        config.TTS_RATE = data.tts_rate
    if data.tts_pitch:
        config.TTS_PITCH = data.tts_pitch
    refresh_ai_provider()
    _save_to_env_file()


def _save_to_env_file() -> None:
    import os
    env_path = os.path.join(config.BASE_DIR, ".env")
    env_vars = {
        "GEMINI_API_KEY": config.GEMINI_API_KEY or "",
        "OPENAI_API_KEY": config.OPENAI_API_KEY or "",
        "DEEPSEEK_API_KEY": config.DEEPSEEK_API_KEY or "",
        "GROK_API_KEY": config.GROK_API_KEY or "",
        "PEXELS_API_KEY": config.PEXELS_API_KEY or "",
        "PIXABAY_API_KEY": config.PIXABAY_API_KEY or "",
        "YOUTUBE_DATA_API_KEY": config.YOUTUBE_DATA_API_KEY or "",
        "REDDIT_CLIENT_ID": config.REDDIT_CLIENT_ID or "",
        "REDDIT_CLIENT_SECRET": config.REDDIT_CLIENT_SECRET or "",
        "LANGUAGE": config.LANGUAGE or "tr",
        "TTS_GENDER": config.TTS_GENDER or "male",
        "ENABLE_BGM": str(config.ENABLE_BGM).lower(),
        "BGM_VOLUME": str(config.BGM_VOLUME),
    }
    lines = [f"{k}={v}" for k, v in env_vars.items()]
    try:
        with open(env_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        print(f"  [BİLGİ] Yapılandırma .env dosyasına başarıyla kaydedildi: {env_path}")
    except Exception as e:
        print(f"  [UYARI] .env dosyası kaydedilemedi: {e}")