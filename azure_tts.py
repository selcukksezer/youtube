"""Azure AI Speech TTS — REST synthesizer (preferred when keys present)."""
from __future__ import annotations

import logging
import os
import re
import subprocess
import xml.sax.saxutils
from typing import Optional, Tuple

import imageio_ffmpeg
import requests

logger = logging.getLogger(__name__)

# Matches Edge Neural names (tr-TR-AhmetNeural, en-US-JennyNeural, …)
_VOICE_LOCALE_RE = re.compile(r"^([a-z]{2}-[A-Z]{2})-")


def is_configured() -> bool:
    import config as cfg

    return bool(
        getattr(cfg, "AZURE_SPEECH_KEY", "")
        and getattr(cfg, "AZURE_SPEECH_REGION", "")
    )


def _locale_from_voice(voice: str) -> str:
    m = _VOICE_LOCALE_RE.match((voice or "").strip())
    if m:
        return m.group(1)
    lang = getattr(__import__("config"), "LANGUAGE", "tr") or "tr"
    return "tr-TR" if str(lang).lower().startswith("tr") else "en-US"


def _mp3_to_wav(mp3_path: str, wav_path: str) -> str:
    r = subprocess.run(
        [
            imageio_ffmpeg.get_ffmpeg_exe(),
            "-y",
            "-i",
            mp3_path,
            "-ar",
            "48000",
            "-ac",
            "2",
            wav_path,
        ],
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


def _build_ssml(text: str, voice: str, rate: str = "+0%", pitch: str = "+0Hz") -> str:
    locale = _locale_from_voice(voice)
    safe = xml.sax.saxutils.escape((text or "").strip())
    rate = rate or "+0%"
    pitch = pitch or "+0Hz"
    return (
        f"<speak version='1.0' xml:lang='{locale}'>"
        f"<voice name='{xml.sax.saxutils.escape(voice)}'>"
        f"<prosody rate='{xml.sax.saxutils.escape(rate)}' "
        f"pitch='{xml.sax.saxutils.escape(pitch)}'>{safe}</prosody>"
        f"</voice></speak>"
    )


def generate_tts_wav(
    text: str,
    output_path: str,
    voice: Optional[str] = None,
    rate: Optional[str] = None,
    pitch: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Synthesize via Azure Speech REST → 48 kHz stereo WAV.
    Returns (ok, message).
    """
    if not is_configured():
        return False, "AZURE_SPEECH_KEY/REGION not configured"

    import config as cfg

    plain = (text or "").strip()
    if not plain:
        return False, "Empty TTS text"

    voice_name = (voice or getattr(cfg, "TTS_VOICE", "") or "tr-TR-AhmetNeural").strip()
    if voice_name.startswith("elevenlabs:"):
        return False, "Azure cannot synthesize ElevenLabs voice ids"

    region = cfg.AZURE_SPEECH_REGION.strip()
    url = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"
    ssml = _build_ssml(
        plain,
        voice_name,
        rate=rate or getattr(cfg, "TTS_RATE", "+18%"),
        pitch=pitch or getattr(cfg, "TTS_PITCH", "+0Hz"),
    )
    headers = {
        "Ocp-Apim-Subscription-Key": cfg.AZURE_SPEECH_KEY,
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3",
        "User-Agent": "youtubeoto-azure-tts",
    }

    try:
        resp = requests.post(url, headers=headers, data=ssml.encode("utf-8"), timeout=60)
        if resp.status_code == 401:
            return False, "Azure Speech 401: invalid key/region"
        if resp.status_code == 429:
            return False, "Azure Speech 429: quota exceeded"
        if resp.status_code != 200:
            detail = (resp.text or "")[:240] or f"HTTP {resp.status_code}"
            return False, f"Azure Speech error: {detail}"

        mp3_path = output_path if output_path.endswith(".mp3") else output_path + ".tmp.mp3"
        with open(mp3_path, "wb") as f:
            f.write(resp.content)
        if not os.path.getsize(mp3_path):
            return False, "Azure Speech returned empty audio"

        wav_path = output_path if output_path.endswith(".wav") else output_path.rsplit(".", 1)[0] + ".wav"
        result = _mp3_to_wav(mp3_path, wav_path)
        if not result.endswith(".wav") or not os.path.isfile(wav_path):
            return False, "MP3→WAV conversion failed"

        return True, f"Azure Speech {voice_name} | {len(plain)} chars"
    except requests.RequestException as exc:
        logger.warning("Azure TTS request failed: %s", exc)
        return False, f"Azure Speech request failed: {exc}"
