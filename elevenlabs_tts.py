"""ElevenLabs TTS — free-tier pre-made voices via API v1."""
from __future__ import annotations

import logging
import os
import subprocess
from typing import Any, Dict, List, Optional, Tuple

import imageio_ffmpeg
import requests

logger = logging.getLogger(__name__)

ELEVENLABS_API_BASE = "https://api.elevenlabs.io/v1"
DEFAULT_MODEL_ID = "eleven_multilingual_v2"

_last_quota: Dict[str, Any] = {}


def is_valid_api_key(value: Any) -> bool:
    """Treat non-empty configured value as candidate; API validates key."""
    key = str(value or "").strip()
    return bool(key)


def is_configured() -> bool:
    import config as cfg
    return is_valid_api_key(getattr(cfg, "ELEVENLABS_API_KEY", ""))


def parse_voice_id(voice_id: str) -> str:
    from tts_voices import ELEVENLABS_VOICE_PREFIX
    if voice_id and str(voice_id).startswith(ELEVENLABS_VOICE_PREFIX):
        return voice_id.split(":", 1)[1]
    return voice_id


def _api_headers() -> Dict[str, str]:
    import config as cfg
    return {
        "xi-api-key": getattr(cfg, "ELEVENLABS_API_KEY", ""),
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }


def _mp3_to_wav(mp3_path: str, wav_path: str) -> str:
    r = subprocess.run(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-i", mp3_path, "-ar", "48000", "-ac", "2", wav_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if r.returncode == 0:
        try:
            os.remove(mp3_path)
        except OSError:
            pass
        return wav_path
    return mp3_path


def _store_quota_from_headers(headers: Dict[str, str]) -> None:
    global _last_quota
    for key in ("character-cost", "character-limit", "character-remaining"):
        val = headers.get(key) or headers.get(key.replace("-", "_"))
        if val is not None:
            _last_quota[key] = val


def get_last_quota_headers() -> Dict[str, Any]:
    return dict(_last_quota)


def _normalize_gender(raw: Any) -> str:
    g = str(raw or "male").lower()
    return g if g in ("male", "female") else "male"


def fetch_voices_from_api() -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Live catalog from GET /v1/voices.
    Returns (voice entries for UI, error message or None).
    """
    if not is_configured():
        return [], None
    try:
        import config as cfg

        resp = requests.get(
            f"{ELEVENLABS_API_BASE}/voices",
            headers={"xi-api-key": cfg.ELEVENLABS_API_KEY},
            timeout=10,
        )
        if resp.status_code == 401:
            return [], "Geçersiz API key"
        if resp.status_code != 200:
            detail = resp.text[:200] if resp.text else f"HTTP {resp.status_code}"
            return [], f"API hatası ({resp.status_code}): {detail}"

        voices: List[Dict[str, Any]] = []
        for item in resp.json().get("voices", []):
            raw_id = item.get("voice_id") or item.get("id")
            if not raw_id:
                continue
            labels = item.get("labels") or {}
            category = item.get("category") or "premade"
            voices.append(
                {
                    "id": f"elevenlabs:{raw_id}",
                    "voice_id": raw_id,
                    "label": item.get("name") or raw_id,
                    "gender": _normalize_gender(labels.get("gender")),
                    "quality": category.replace("_", " ").title(),
                    "native": False,
                    "provider": "elevenlabs",
                }
            )
        return voices, None
    except requests.RequestException as exc:
        logger.warning("ElevenLabs voices fetch failed: %s", exc)
        return [], f"Bağlantı hatası: {exc}"


def get_subscription_info(force: bool = False) -> Optional[Dict[str, Any]]:
    """Fetch character quota from /v1/user/subscription."""
    if not is_configured():
        return None
    try:
        import config as cfg
        resp = requests.get(
            f"{ELEVENLABS_API_BASE}/user/subscription",
            headers={"xi-api-key": cfg.ELEVENLABS_API_KEY},
            timeout=8,
        )
        if resp.status_code != 200:
            return {"error": resp.status_code, "message": resp.text[:200]}
        data = resp.json()
        char_count = data.get("character_count", 0)
        char_limit = data.get("character_limit", 10000)
        remaining = max(0, int(char_limit) - int(char_count))
        tier = data.get("tier", "free")
        return {
            "tier": tier,
            "character_count": char_count,
            "character_limit": char_limit,
            "character_remaining": remaining,
            "can_extend_character_limit": data.get("can_extend_character_limit", False),
        }
    except Exception as exc:
        logger.warning("ElevenLabs subscription fetch failed: %s", exc)
        return {"error": "connection", "message": str(exc)}


def generate_tts_wav(
    text: str,
    output_path: str,
    voice_id: str,
    model_id: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Synthesize speech via ElevenLabs API → 48 kHz stereo WAV.
    Returns (ok, message).
    """
    if not is_configured():
        return False, "ELEVENLABS_API_KEY not configured"
    plain = (text or "").strip()
    if not plain:
        return False, "Empty TTS text"

    raw_voice = parse_voice_id(voice_id)
    url = f"{ELEVENLABS_API_BASE}/text-to-speech/{raw_voice}"
    payload = {
        "text": plain,
        "model_id": model_id or getattr(__import__("config"), "ELEVENLABS_MODEL_ID", DEFAULT_MODEL_ID),
    }

    try:
        resp = requests.post(url, headers=_api_headers(), json=payload, timeout=60)
        _store_quota_from_headers(dict(resp.headers))

        if resp.status_code == 401:
            return False, "ElevenLabs 401: invalid API key"
        if resp.status_code == 429:
            remaining = resp.headers.get("character-remaining", "?")
            return False, f"ElevenLabs 429: quota exceeded (remaining={remaining})"
        if resp.status_code != 200:
            detail = resp.text[:240] if resp.text else f"HTTP {resp.status_code}"
            return False, f"ElevenLabs error: {detail}"

        mp3_path = output_path if output_path.endswith(".mp3") else output_path + ".tmp.mp3"
        with open(mp3_path, "wb") as f:
            f.write(resp.content)
        if not os.path.getsize(mp3_path):
            return False, "ElevenLabs returned empty audio"

        wav_path = output_path if output_path.endswith(".wav") else output_path.rsplit(".", 1)[0] + ".wav"
        result = _mp3_to_wav(mp3_path, wav_path)
        if not result.endswith(".wav") or not os.path.isfile(wav_path):
            return False, "MP3→WAV conversion failed"

        remaining = resp.headers.get("character-remaining")
        msg = f"ElevenLabs {raw_voice} | {len(plain)} chars"
        if remaining is not None:
            msg += f" | quota remaining: {remaining}"
            logger.info("  [ElevenLabs] character-remaining: %s", remaining)
        return True, msg
    except requests.RequestException as exc:
        return False, f"ElevenLabs request failed: {exc}"
