"""
Google AI Pro Hub media & TTS helper routines (Nano Banana image, Veo video, Gemini TTS).
Extracted from google_ai_hub.py for modularity.
"""
from __future__ import annotations

import base64
import os
import time
from typing import Any, Dict, Optional, Tuple

import requests

import config

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"

# Prebuilt Gemini TTS voices (see ai.google.dev/gemini-api/docs/speech-generation)
GEMINI_TTS_VOICE_MAP = {
    ("tr", "male"): "Charon",
    ("tr", "female"): "Aoede",
    ("en", "male"): "Charon",
    ("en", "female"): "Aoede",
    ("tr", "auto"): "Kore",
    ("en", "auto"): "Kore",
}


def _api_key() -> str:
    return (getattr(config, "GEMINI_API_KEY", "") or "").strip()


def generate_image_bytes(
    prompt: str,
    model: Optional[str] = None,
    aspect_hint: str = "vertical 9:16 portrait",
    force: bool = False,
) -> Tuple[bool, Optional[bytes], str]:
    """
    Nano Banana / Gemini native image via generateContent + responseModalities IMAGE.
    Returns (ok, png_or_jpeg_bytes, message).
    Item 416: circuit-breaker on 429 so render pipeline does not spam quota.
    """
    if not force and not getattr(config, "USE_GEMINI_IMAGE_GEN", False):
        return False, None, "USE_GEMINI_IMAGE_GEN kapalı — stok video kullanılıyor"

    try:
        from system_resilience import circuit_breaker
        if not circuit_breaker.can_execute("gemini_image"):
            return False, None, "circuit_open: gemini_image (429 kota — stok videoya geç)"
    except Exception:
        circuit_breaker = None

    key = _api_key()
    if not key:
        return False, None, "GEMINI_API_KEY yok"
    model = model or getattr(config, "GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")
    full = (
        f"{prompt}. {aspect_hint}, cinematic lighting, no watermark, no UI text overlays, "
        f"photorealistic stock-broll style suitable for YouTube Shorts."
    )
    body = {
        "contents": [{"role": "user", "parts": [{"text": full}]}],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
        },
    }
    url = f"{GEMINI_BASE}/models/{model}:generateContent?key={key}"
    try:
        r = requests.post(url, json=body, timeout=120)
        if r.status_code != 200:
            msg = f"HTTP {r.status_code}: {r.text[:400]}"
            if circuit_breaker is not None and r.status_code in (429, 500, 503):
                # Free-tier image often reports limit:0 — trip fast, long cool-down
                cool = 1800.0 if r.status_code == 429 else 60.0
                circuit_breaker.record_failure("gemini_image", msg, custom_timeout=cool)
                if r.status_code == 429:
                    # Trip immediately on quota (don't wait for 3 failures)
                    s = circuit_breaker._get_service("gemini_image")
                    s["failure_count"] = circuit_breaker.failure_threshold
                    s["state"] = circuit_breaker.STATE_OPEN
                    print(
                        f"  [CircuitBreaker] gemini_image AÇILDI (HTTP 429 kota). "
                        f"{int(cool)}s stok videoya düşülüyor."
                    )
            # Fallback older model id only if not quota
            if r.status_code != 429 and model != "gemini-2.5-flash-image":
                return generate_image_bytes(prompt, model="gemini-2.5-flash-image", aspect_hint=aspect_hint)
            return False, None, msg
        data = r.json()
        parts = (((data.get("candidates") or [{}])[0].get("content") or {}).get("parts") or [])
        for p in parts:
            inline = p.get("inlineData") or p.get("inline_data")
            if inline and inline.get("data"):
                raw = base64.b64decode(inline["data"])
                try:
                    from quota_manager import quota_manager
                    quota_manager.record_call("Gemini")
                except Exception:
                    pass
                if circuit_breaker is not None:
                    circuit_breaker.record_success("gemini_image")
                return True, raw, inline.get("mimeType") or inline.get("mime_type") or "image/png"
        return False, None, "Yanıtta görsel verisi yok (model bu anahtarda image desteklemiyor olabilir)"
    except Exception as e:
        if circuit_breaker is not None:
            circuit_breaker.record_failure("gemini_image", str(e))
        return False, None, str(e)


def save_generated_image(
    prompt: str,
    output_path: str,
    model: Optional[str] = None,
    force: bool = False,
) -> Optional[str]:
    ok, data, msg = generate_image_bytes(prompt, model=model, force=force)
    if not ok or not data:
        print(f"  [GoogleAI] Image fail: {msg}")
        return None
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    ext = ".png" if "png" in (msg or "") else ".jpg"
    if not output_path.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
        output_path = output_path + ext
    with open(output_path, "wb") as f:
        f.write(data)
    print(f"  [GoogleAI] Image saved → {output_path}")
    return output_path


def generate_veo_video(
    prompt: str,
    output_path: str,
    model: Optional[str] = None,
    duration_seconds: int = 6,
    poll_timeout: int = 180,
) -> Optional[str]:
    """
    Veo long-running video generation. Requires paid Gemini API access.
    P3-31: circuit-breaker on 429 so render pipeline does not spam quota.
    """
    try:
        from system_resilience import circuit_breaker
        if not circuit_breaker.can_execute("gemini_veo"):
            print("  [GoogleAI/Veo] circuit_open (429 kota) — stok videoya geç")
            return None
    except Exception:
        circuit_breaker = None

    key = _api_key()
    if not key:
        print("  [GoogleAI] Veo: API key yok")
        return None
    model = model or getattr(config, "GEMINI_VIDEO_MODEL", "veo-3.1-fast-generate-preview")
    if getattr(config, "GEMINI_VEO_PREVIEW_ONLY", True) and "preview" not in model.lower():
        print(f"  [GoogleAI/Veo] Preview-only mod: '{model}' reddedildi")
        return None
    # predictLongRunning endpoint
    url = f"{GEMINI_BASE}/models/{model}:predictLongRunning?key={key}"
    body = {
        "instances": [{"prompt": prompt}],
        "parameters": {
            "aspectRatio": "9:16",
            "durationSeconds": max(4, min(8, int(duration_seconds))),
        },
    }
    try:
        r = requests.post(url, json=body, timeout=60)
        if r.status_code not in (200, 201):
            print(f"  [GoogleAI] Veo start fail HTTP {r.status_code}: {r.text[:300]}")
            if circuit_breaker is not None and r.status_code in (429, 403, 500, 503):
                cool = 3600.0 if r.status_code == 429 else 300.0
                circuit_breaker.recovery_timeout = cool
                s = circuit_breaker._get_service("gemini_veo")
                s["failure_count"] = circuit_breaker.failure_threshold
                s["state"] = circuit_breaker.STATE_OPEN
                print(
                    f"  [CircuitBreaker] gemini_veo AÇILDI (HTTP {r.status_code}). "
                    f"{int(cool)}s stok videoya düşülüyor."
                )
            return None
        op = r.json()
        op_name = op.get("name")
        if not op_name:
            # Some responses embed video immediately
            return _extract_veo_file(op, output_path)

        deadline = time.time() + poll_timeout
        while time.time() < deadline:
            pr = requests.get(f"{GEMINI_BASE}/{op_name}?key={key}", timeout=30)
            if pr.status_code != 200:
                if circuit_breaker is not None and pr.status_code in (429, 403):
                    cool = 3600.0 if pr.status_code == 429 else 300.0
                    circuit_breaker.recovery_timeout = cool
                    s = circuit_breaker._get_service("gemini_veo")
                    s["failure_count"] = circuit_breaker.failure_threshold
                    s["state"] = circuit_breaker.STATE_OPEN
                    print(
                        f"  [CircuitBreaker] gemini_veo AÇILDI (poll HTTP {pr.status_code}). "
                        f"{int(cool)}s stok videoya düşülüyor."
                    )
                    return None
                time.sleep(3)
                continue
            pdata = pr.json()
            if pdata.get("done"):
                if pdata.get("error"):
                    err = pdata["error"]
                    print(f"  [GoogleAI] Veo error: {err}")
                    err_code = err.get("code") if isinstance(err, dict) else None
                    if circuit_breaker is not None and err_code in (429, 403, 8):
                        circuit_breaker.recovery_timeout = 3600.0
                        s = circuit_breaker._get_service("gemini_veo")
                        s["failure_count"] = circuit_breaker.failure_threshold
                        s["state"] = circuit_breaker.STATE_OPEN
                        print("  [CircuitBreaker] gemini_veo AÇILDI (kota hatası) — stok videoya geç")
                    return None
                path = _extract_veo_file(pdata, output_path)
                try:
                    from quota_manager import quota_manager
                    quota_manager.record_call("Gemini")
                except Exception:
                    pass
                return path
            time.sleep(4)
        print("  [GoogleAI] Veo timeout")
        return None
    except Exception as e:
        print(f"  [GoogleAI] Veo exception: {e}")
        return None


def resolve_gemini_tts_voice(language: str = "tr", gender: str = "male") -> str:
    lang = (language or "tr").lower()[:2]
    g = (gender or "male").lower()
    return GEMINI_TTS_VOICE_MAP.get((lang, g)) or GEMINI_TTS_VOICE_MAP.get((lang, "male")) or "Kore"


def generate_gemini_tts_wav(
    text: str,
    output_wav: str,
    *,
    model: Optional[str] = None,
    voice_name: Optional[str] = None,
    language: str = "tr",
    gender: str = "male",
) -> Tuple[bool, str]:
    """
    Gemini native TTS via generateContent + responseModalities AUDIO.
    Returns (ok, message). Falls back message explains billing/quota issues.
    Output is resampled to 48 kHz stereo WAV for the render pipeline.
    """
    key = _api_key()
    if not key:
        return False, "GEMINI_API_KEY yok"
    if not (text or "").strip():
        return False, "Boş metin"

    model = model or getattr(config, "GEMINI_TTS_MODEL", "gemini-2.5-flash-preview-tts")
    voice = voice_name or resolve_gemini_tts_voice(language, gender)
    body: Dict[str, Any] = {
        "contents": [{"parts": [{"text": text.strip()}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {"voiceName": voice},
                }
            },
        },
    }
    url = f"{GEMINI_BASE}/models/{model}:generateContent?key={key}"
    try:
        r = requests.post(url, json=body, timeout=120)
        if r.status_code != 200:
            return False, f"HTTP {r.status_code}: {r.text[:300]}"
        data = r.json()
        parts = (((data.get("candidates") or [{}])[0].get("content") or {}).get("parts") or [])
        pcm_bytes = None
        mime = "audio/L16;rate=24000"
        for p in parts:
            inline = p.get("inlineData") or p.get("inline_data")
            if inline and inline.get("data"):
                raw = inline["data"]
                pcm_bytes = base64.b64decode(raw) if isinstance(raw, str) else raw
                mime = inline.get("mimeType") or inline.get("mime_type") or mime
                break
        if not pcm_bytes:
            return False, "Yanıtta ses verisi yok (TTS modeli bu anahtarda açık olmayabilir)"

        import re as _re
        import wave
        rate = 24000
        m = _re.search(r"rate=(\d+)", mime or "")
        if m:
            rate = int(m.group(1))

        os.makedirs(os.path.dirname(output_wav) or ".", exist_ok=True)
        tmp_pcm = output_wav + ".pcm"
        with open(tmp_pcm, "wb") as pf:
            pf.write(pcm_bytes)
        tmp_mono = output_wav + ".mono.wav"
        with wave.open(tmp_mono, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(rate)
            wf.writeframes(pcm_bytes)

        import imageio_ffmpeg
        import subprocess
        ff = imageio_ffmpeg.get_ffmpeg_exe()
        res = subprocess.run(
            [ff, "-y", "-i", tmp_mono, "-ar", "48000", "-ac", "2", output_wav],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        for p in (tmp_pcm, tmp_mono):
            try:
                os.remove(p)
            except OSError:
                pass
        if res.returncode != 0 or not os.path.exists(output_wav):
            return False, f"FFmpeg PCM→WAV hatası: {res.stderr.decode('utf-8', errors='ignore')[:200]}"

        try:
            from quota_manager import quota_manager
            quota_manager.record_call("Gemini")
        except Exception:
            pass
        print(f"  [GoogleAI/TTS] {voice} @ {model} → {output_wav}")
        return True, voice
    except Exception as e:
        return False, str(e)


def _extract_veo_file(payload: Dict[str, Any], output_path: str) -> Optional[str]:
    """Pull base64 or URI video from Veo operation response."""
    def walk(obj):
        if isinstance(obj, dict):
            if "bytesBase64Encoded" in obj:
                return base64.b64decode(obj["bytesBase64Encoded"]), None
            if "video" in obj and isinstance(obj["video"], dict):
                v = obj["video"]
                if v.get("uri"):
                    return None, v["uri"]
                if v.get("bytesBase64Encoded"):
                    return base64.b64decode(v["bytesBase64Encoded"]), None
            for v in obj.values():
                found = walk(v)
                if found and (found[0] or found[1]):
                    return found
        elif isinstance(obj, list):
            for it in obj:
                found = walk(it)
                if found and (found[0] or found[1]):
                    return found
        return None, None

    data, uri = walk(payload.get("response") or payload)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    if data:
        with open(output_path, "wb") as f:
            f.write(data)
        return output_path
    if uri:
        key = _api_key()
        dl = uri if "key=" in uri else (f"{uri}{'&' if '?' in uri else '?'}key={key}")
        rr = requests.get(dl, timeout=120)
        if rr.status_code == 200 and len(rr.content) > 1000:
            with open(output_path, "wb") as f:
                f.write(rr.content)
            return output_path
    return None
