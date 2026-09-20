"""Edge TTS + ElevenLabs free-tier voice catalog for dashboard UI."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

ELEVENLABS_VOICE_PREFIX = "elevenlabs:"

# Pre-made voices on ElevenLabs free tier — multilingual model handles TR narration well.
ELEVENLABS_FREE_VOICES: List[Dict[str, Any]] = [
    {"id": "elevenlabs:21m00Tcm4TlvDq8ikWAM", "voice_id": "21m00Tcm4TlvDq8ikWAM", "label": "Rachel", "gender": "female", "quality": "Multilingual v2", "native": False, "provider": "elevenlabs"},
    {"id": "elevenlabs:pNInz6obpgDQGcFmaJgB", "voice_id": "pNInz6obpgDQGcFmaJgB", "label": "Adam", "gender": "male", "quality": "Multilingual v2", "native": False, "provider": "elevenlabs"},
    {"id": "elevenlabs:EXAVITQu4vr4xnSDxMaL", "voice_id": "EXAVITQu4vr4xnSDxMaL", "label": "Bella", "gender": "female", "quality": "Multilingual v2", "native": False, "provider": "elevenlabs"},
    {"id": "elevenlabs:ErXwobaYiN019PkySvjV", "voice_id": "ErXwobaYiN019PkySvjV", "label": "Antoni", "gender": "male", "quality": "Multilingual v2", "native": False, "provider": "elevenlabs"},
    {"id": "elevenlabs:TxGEqnHWrfWFTfGW9XjX", "voice_id": "TxGEqnHWrfWFTfGW9XjX", "label": "Josh", "gender": "male", "quality": "Multilingual v2", "native": False, "provider": "elevenlabs"},
    {"id": "elevenlabs:MF3mGyEYCl7XYWbV9V6O", "voice_id": "MF3mGyEYCl7XYWbV9V6O", "label": "Elli", "gender": "female", "quality": "Multilingual v2", "native": False, "provider": "elevenlabs"},
    {"id": "elevenlabs:VR6AewLTigWG4xSOukaG", "voice_id": "VR6AewLTigWG4xSOukaG", "label": "Arnold", "gender": "male", "quality": "Multilingual v2", "native": False, "provider": "elevenlabs"},
    {"id": "elevenlabs:XB0fDUnXU5powFXDhCwa", "voice_id": "XB0fDUnXU5powFXDhCwa", "label": "Charlotte", "gender": "female", "quality": "Multilingual v2", "native": False, "provider": "elevenlabs"},
    {"id": "elevenlabs:XrExE9yKIg1WjnnlVkGX", "voice_id": "XrExE9yKIg1WjnnlVkGX", "label": "Matilda", "gender": "female", "quality": "Multilingual v2", "native": False, "provider": "elevenlabs"},
    {"id": "elevenlabs:yoZ06aMxZJJ28mfd3POQ", "voice_id": "yoZ06aMxZJJ28mfd3POQ", "label": "Sam", "gender": "male", "quality": "Multilingual v2", "native": False, "provider": "elevenlabs"},
]

# Each entry: id (Edge ShortName), label (UI), gender, quality, native (True = locale-native)
EDGE_TTS_VOICE_CATALOG: Dict[str, List[Dict[str, Any]]] = {
    "tr": [
        {"id": "tr-TR-AhmetNeural", "label": "Ahmet", "gender": "male", "quality": "Neural", "native": True, "provider": "edge"},
        {"id": "tr-TR-EmelNeural", "label": "Emel", "gender": "female", "quality": "Neural", "native": True, "provider": "edge"},
        {"id": "en-US-AndrewMultilingualNeural", "label": "Andrew (çok dilli)", "gender": "male", "quality": "Multilingual Neural", "native": False, "provider": "edge"},
        {"id": "en-US-AvaMultilingualNeural", "label": "Ava (çok dilli)", "gender": "female", "quality": "Multilingual Neural", "native": False, "provider": "edge"},
        {"id": "en-US-BrianMultilingualNeural", "label": "Brian (çok dilli)", "gender": "male", "quality": "Multilingual Neural", "native": False, "provider": "edge"},
        {"id": "en-US-EmmaMultilingualNeural", "label": "Emma (çok dilli)", "gender": "female", "quality": "Multilingual Neural", "native": False, "provider": "edge"},
        {"id": "en-AU-WilliamMultilingualNeural", "label": "William (çok dilli)", "gender": "male", "quality": "Multilingual Neural", "native": False, "provider": "edge"},
        {"id": "de-DE-FlorianMultilingualNeural", "label": "Florian (çok dilli)", "gender": "male", "quality": "Multilingual Neural", "native": False, "provider": "edge"},
        {"id": "de-DE-SeraphinaMultilingualNeural", "label": "Seraphina (çok dilli)", "gender": "female", "quality": "Multilingual Neural", "native": False, "provider": "edge"},
        {"id": "fr-FR-RemyMultilingualNeural", "label": "Remy (çok dilli)", "gender": "male", "quality": "Multilingual Neural", "native": False, "provider": "edge"},
        {"id": "fr-FR-VivienneMultilingualNeural", "label": "Vivienne (çok dilli)", "gender": "female", "quality": "Multilingual Neural", "native": False, "provider": "edge"},
        {"id": "it-IT-GiuseppeMultilingualNeural", "label": "Giuseppe (çok dilli)", "gender": "male", "quality": "Multilingual Neural", "native": False, "provider": "edge"},
        {"id": "ko-KR-HyunsuMultilingualNeural", "label": "Hyunsu (çok dilli)", "gender": "male", "quality": "Multilingual Neural", "native": False, "provider": "edge"},
        {"id": "pt-BR-ThalitaMultilingualNeural", "label": "Thalita (çok dilli)", "gender": "female", "quality": "Multilingual Neural", "native": False, "provider": "edge"},
    ],
    "en": [
        {"id": "en-US-GuyNeural", "label": "Guy (US)", "gender": "male", "quality": "Neural", "native": True, "provider": "edge"},
        {"id": "en-US-JennyNeural", "label": "Jenny (US)", "gender": "female", "quality": "Neural", "native": True, "provider": "edge"},
        {"id": "en-US-AriaNeural", "label": "Aria (US)", "gender": "female", "quality": "Neural", "native": True, "provider": "edge"},
        {"id": "en-US-AndrewNeural", "label": "Andrew (US)", "gender": "male", "quality": "Neural", "native": True, "provider": "edge"},
        {"id": "en-US-BrianNeural", "label": "Brian (US)", "gender": "male", "quality": "Neural", "native": True, "provider": "edge"},
        {"id": "en-US-EmmaNeural", "label": "Emma (US)", "gender": "female", "quality": "Neural", "native": True, "provider": "edge"},
        {"id": "en-US-ChristopherNeural", "label": "Christopher (US)", "gender": "male", "quality": "Neural", "native": True, "provider": "edge"},
        {"id": "en-US-EricNeural", "label": "Eric (US)", "gender": "male", "quality": "Neural", "native": True, "provider": "edge"},
        {"id": "en-US-MichelleNeural", "label": "Michelle (US)", "gender": "female", "quality": "Neural", "native": True, "provider": "edge"},
        {"id": "en-GB-SoniaNeural", "label": "Sonia (UK)", "gender": "female", "quality": "Neural", "native": True, "provider": "edge"},
        {"id": "en-GB-RyanNeural", "label": "Ryan (UK)", "gender": "male", "quality": "Neural", "native": True, "provider": "edge"},
        {"id": "en-AU-NatashaNeural", "label": "Natasha (AU)", "gender": "female", "quality": "Neural", "native": True, "provider": "edge"},
        {"id": "en-CA-ClaraNeural", "label": "Clara (CA)", "gender": "female", "quality": "Neural", "native": True, "provider": "edge"},
        {"id": "en-CA-LiamNeural", "label": "Liam (CA)", "gender": "male", "quality": "Neural", "native": True, "provider": "edge"},
    ],
}

_DEFAULT_BY_LANG_GENDER = {
    "tr": {"male": "tr-TR-AhmetNeural", "female": "tr-TR-EmelNeural"},
    "en": {"male": "en-US-GuyNeural", "female": "en-US-JennyNeural"},
}

_el_voice_cache: Dict[str, Any] = {
    "api_key": "",
    "voices": [],
    "error": None,
    "source": "none",
}


def is_elevenlabs_voice(voice_id: str) -> bool:
    return bool(voice_id) and str(voice_id).startswith(ELEVENLABS_VOICE_PREFIX)


def _elevenlabs_configured() -> bool:
    import config as cfg
    return bool(getattr(cfg, "ELEVENLABS_API_KEY", ""))


def clear_elevenlabs_voice_cache() -> None:
    """Invalidate cached ElevenLabs voice list (e.g. after API key change)."""
    _el_voice_cache.update({"api_key": "", "voices": [], "error": None, "source": "none"})


def _merge_elevenlabs_voices(
    api_voices: List[Dict[str, Any]],
    fallback: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    seen = {v["voice_id"] for v in api_voices}
    merged = list(api_voices)
    for entry in fallback:
        if entry["voice_id"] not in seen:
            merged.append(entry)
    return merged


def _is_auth_error(error: Optional[str]) -> bool:
    if not error:
        return False
    low = error.lower()
    return "401" in low or "geçersiz api key" in low or "invalid api key" in low


def list_elevenlabs_voices(force_refresh: bool = False) -> List[Dict[str, Any]]:
    """Return ElevenLabs voices — live API when key configured, fallback on network errors."""
    import config as cfg

    key = getattr(cfg, "ELEVENLABS_API_KEY", "") or ""
    if not key:
        return []

    if (
        not force_refresh
        and _el_voice_cache["api_key"] == key
        and (_el_voice_cache["voices"] or _el_voice_cache["error"])
    ):
        return list(_el_voice_cache["voices"])

    from elevenlabs_tts import fetch_voices_from_api

    api_voices, error = fetch_voices_from_api()
    if error and _is_auth_error(error):
        _el_voice_cache.update({"api_key": key, "voices": [], "error": error, "source": "none"})
        return []

    if api_voices:
        merged = _merge_elevenlabs_voices(api_voices, ELEVENLABS_FREE_VOICES)
        _el_voice_cache.update({"api_key": key, "voices": merged, "error": error, "source": "api"})
        return list(merged)

    fallback = list(ELEVENLABS_FREE_VOICES)
    _el_voice_cache.update(
        {
            "api_key": key,
            "voices": fallback,
            "error": error,
            "source": "fallback" if error else "fallback",
        }
    )
    return fallback


def get_elevenlabs_catalog_meta() -> Dict[str, Any]:
    """Status block for UI — configured flag, error, source, count."""
    configured = _elevenlabs_configured()
    meta: Dict[str, Any] = {
        "configured": configured,
        "error": None,
        "source": _el_voice_cache.get("source", "none"),
        "count": 0,
    }
    if not configured:
        return meta
    voices = list_elevenlabs_voices()
    meta["count"] = len(voices)
    meta["error"] = _el_voice_cache.get("error")
    meta["source"] = _el_voice_cache.get("source", "none")
    return meta


def list_voices_for_language(lang: str) -> List[Dict[str, Any]]:
    """Return Edge TTS catalog entries for a language code."""
    return list(EDGE_TTS_VOICE_CATALOG.get((lang or "tr").lower(), EDGE_TTS_VOICE_CATALOG["tr"]))


def get_voice_catalog(force_refresh: bool = False) -> Dict[str, Any]:
    """Full catalog for API/UI — Edge TR + EN + optional ElevenLabs group."""
    if force_refresh:
        clear_elevenlabs_voice_cache()

    catalog: Dict[str, Any] = {
        "tr": list(EDGE_TTS_VOICE_CATALOG["tr"]),
        "en": list(EDGE_TTS_VOICE_CATALOG["en"]),
    }
    el_voices = list_elevenlabs_voices(force_refresh=force_refresh)
    if el_voices:
        catalog["elevenlabs"] = el_voices
    catalog["elevenlabs_meta"] = get_elevenlabs_catalog_meta()
    return catalog


def _all_elevenlabs_entries() -> List[Dict[str, Any]]:
    if _elevenlabs_configured():
        cached = list(_el_voice_cache.get("voices") or [])
        if cached:
            return cached
        return list_elevenlabs_voices()
    return list(ELEVENLABS_FREE_VOICES)


def _is_valid_elevenlabs_voice(voice_id: str) -> bool:
    return any(v["id"] == voice_id for v in _all_elevenlabs_entries())


def is_valid_voice(voice_id: str, lang: Optional[str] = None) -> bool:
    """True if voice_id exists in catalog (optionally scoped to lang)."""
    if not voice_id:
        return False
    if is_elevenlabs_voice(voice_id):
        return _elevenlabs_configured() and _is_valid_elevenlabs_voice(voice_id)
    langs = [lang.lower()] if lang else list(EDGE_TTS_VOICE_CATALOG.keys())
    for code in langs:
        if any(v["id"] == voice_id for v in EDGE_TTS_VOICE_CATALOG.get(code, [])):
            return True
    return False


def resolve_voice(
    lang: str,
    voice_id: Optional[str] = None,
    gender: Optional[str] = "male",
) -> str:
    """
    Pick TTS voice id (Edge or elevenlabs: prefix).
    Priority: explicit voice_id → gender default → lang male default.
    """
    lang = (lang or "tr").lower()
    if voice_id and is_valid_voice(voice_id, lang):
        return voice_id
    g = (gender or "male").lower()
    if g in ("auto", ""):
        g = "male"
    defaults = _DEFAULT_BY_LANG_GENDER.get(lang, _DEFAULT_BY_LANG_GENDER["tr"])
    return defaults.get(g, defaults["male"])


def voice_gender_for_id(voice_id: str, lang: str = "tr") -> str:
    """Infer gender from catalog entry."""
    if is_elevenlabs_voice(voice_id):
        for entry in _all_elevenlabs_entries():
            if entry["id"] == voice_id:
                return entry.get("gender", "male")
    for entry in list_voices_for_language(lang):
        if entry["id"] == voice_id:
            return entry.get("gender", "male")
    return "male"


def voice_label_for_id(voice_id: str) -> str:
    """Human label for logs/UI."""
    if is_elevenlabs_voice(voice_id):
        for entry in _all_elevenlabs_entries():
            if entry["id"] == voice_id:
                return entry.get("label", voice_id)
    for voices in EDGE_TTS_VOICE_CATALOG.values():
        for entry in voices:
            if entry["id"] == voice_id:
                return entry.get("label", voice_id)
    return voice_id
