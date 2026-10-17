"""
Provider synthesis helpers (Piper local, ElevenLabs, Azure Speech, Gemini TTS) and timing/SSML sanitizers.
"""
import os
import re
import shutil
import subprocess
import sys
import wave
from typing import Tuple
import imageio_ffmpeg
import config


def _tts_mod():
    return sys.modules.get("tts_engine")


def _cfg():
    mod = _tts_mod()
    return getattr(mod, "config", config) if mod else config


def active_tts_provider() -> str:
    """Human-readable provider label for logs/UI."""
    from tts_voices import is_elevenlabs_voice, is_local_offline_voice, voice_label_for_id
    cfg = _cfg()
    if is_local_offline_voice(cfg.TTS_VOICE):
        return f"Piper local ({voice_label_for_id(cfg.TTS_VOICE)})"
    if is_elevenlabs_voice(cfg.TTS_VOICE) and getattr(cfg, "ELEVENLABS_API_KEY", ""):
        return f"ElevenLabs ({voice_label_for_id(cfg.TTS_VOICE)})"
    try:
        from azure_tts import is_configured as azure_configured
        if getattr(cfg, "PREFER_AZURE_TTS", True) and azure_configured() and not is_elevenlabs_voice(cfg.TTS_VOICE):
            return f"Azure Speech ({cfg.TTS_VOICE})"
    except Exception:
        pass
    piper_bin_fn = getattr(_tts_mod(), "_piper_binary", _piper_binary)
    if getattr(cfg, "USE_PIPER_TTS", False) and piper_bin_fn():
        return f"Piper local ({getattr(cfg, 'PIPER_MODEL', 'default')})"
    if getattr(cfg, "USE_GEMINI_TTS", False) and getattr(cfg, "GEMINI_API_KEY", ""):
        return f"Gemini TTS ({getattr(cfg, 'GEMINI_TTS_MODEL', 'gemini-2.5-flash-preview-tts')})"
    return f"Edge TTS ({cfg.TTS_VOICE})"


def _piper_binary() -> str:
    """R10 #45: Resolve Piper CLI if installed locally."""
    return shutil.which("piper") or ""


def piper_tts_available() -> bool:
    cfg = _cfg()
    piper_bin_fn = getattr(_tts_mod(), "_piper_binary", _piper_binary)
    return bool(piper_bin_fn() and getattr(cfg, "USE_PIPER_TTS", False))


def generate_piper_wav(text: str, output_path: str, model_path: str = "") -> Tuple[bool, str]:
    """Offline Piper TTS when `piper` binary + onnx model present."""
    cfg = _cfg()
    piper_bin_fn = getattr(_tts_mod(), "_piper_binary", _piper_binary)
    exe = piper_bin_fn()
    if not exe:
        return False, "piper binary not found (brew/pip install piper-tts)"
    model = model_path or getattr(cfg, "PIPER_MODEL_PATH", "") or ""
    if not model or not os.path.exists(model):
        return False, "PIPER_MODEL_PATH missing — set path to .onnx voice model"
    plain = (text or "").strip()
    if not plain:
        return False, "empty text"
    try:
        cmd = [exe, "--model", model, "--output_file", output_path]
        proc = subprocess.run(
            cmd, input=plain.encode("utf-8"),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120,
        )
        if proc.returncode == 0 and os.path.exists(output_path):
            return True, f"Piper OK → {output_path}"
        return False, (proc.stderr or b"").decode("utf-8", errors="ignore")[:300]
    except Exception as e:
        return False, str(e)


def _local_piper_binary() -> str:
    """Piper exe on F: only. Never look inside F:\\MiniMax-H3."""
    cfg = _cfg()
    roots = []
    extra = getattr(cfg, "LOCAL_PIPER_DIR", "") or ""
    if extra:
        roots.append(extra)
    roots.append(r"F:\local-tts\piper")
    for root in roots:
        norm = os.path.normpath(root)
        if "MiniMax-H3" in norm:
            continue
        for rel in ("piper.exe", os.path.join("piper", "piper.exe")):
            cand = os.path.join(norm, rel)
            if os.path.isfile(cand):
                return cand
    return ""


def _local_piper_model() -> str:
    cfg = _cfg()
    env = getattr(cfg, "PIPER_MODEL_PATH", "") or ""
    if env and os.path.isfile(env) and "MiniMax-H3" not in os.path.normpath(env):
        return env
    cand = r"F:\local-tts\piper\voices\tr_TR-dfki-medium.onnx"
    if os.path.isfile(cand):
        return cand
    return ""


def generate_local_offline_wav(text: str, output_path: str) -> Tuple[bool, str]:
    """Offline Piper Turkish (tr_TR-dfki-medium). No API key."""
    mod = _tts_mod()
    bin_fn = getattr(mod, "_local_piper_binary", _local_piper_binary)
    model_fn = getattr(mod, "_local_piper_model", _local_piper_model)
    exe = bin_fn()
    model = model_fn()
    if not exe:
        msg = (
            "Piper binary missing (expected F:\\local-tts\\piper\\piper.exe). "
            "Continuing without local voice."
        )
        print(f"  [TTS/Local] {msg}")
        return False, msg
    if not model:
        msg = (
            "Piper Turkish model missing "
            "(expected F:\\local-tts\\piper\\voices\\tr_TR-dfki-medium.onnx). "
            "Continuing without local voice."
        )
        print(f"  [TTS/Local] {msg}")
        return False, msg
    plain = (text or "").strip()
    if not plain:
        return False, "empty text"
    try:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)
        proc = subprocess.run(
            [exe, "--model", model, "--output_file", output_path],
            input=plain.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120,
        )
        if proc.returncode == 0 and os.path.isfile(output_path) and os.path.getsize(output_path) > 64:
            return True, f"Piper TR OK → {output_path}"
        err = (proc.stderr or b"").decode("utf-8", errors="ignore")[:300]
        print(f"  [TTS/Local] Piper failed, continuing: {err}")
        return False, err or "piper failed"
    except Exception as e:
        print(f"  [TTS/Local] Piper error, continuing: {e}")
        return False, str(e)


def _gemini_tts_circuit_open() -> bool:
    try:
        from system_resilience import circuit_breaker
        return not circuit_breaker.can_execute("gemini_tts")
    except Exception:
        return False


def _mark_gemini_tts_circuit_open(msg: str) -> None:
    try:
        import time
        from system_resilience import circuit_breaker
        service = circuit_breaker._get_service("gemini_tts")
        service["failure_count"] = circuit_breaker.failure_threshold
        service["state"] = circuit_breaker.STATE_OPEN
        service["last_failure_time"] = time.time()
        print(f"  [TTS/Gemini] circuit open: {str(msg)[:160]}")
    except Exception:
        pass


def _is_gemini_quota_block(err: BaseException) -> bool:
    text = str(err).lower()
    return "429" in text or "circuit_open" in text or "circuit open" in text


def _try_local_offline_narration(text: str, output_path: str):
    """Run Piper. None when the binary is missing or synthesis fails."""
    from voice_humanizer import VoiceHumanizer
    mod = _tts_mod()
    gen_local_fn = getattr(mod, "generate_local_offline_wav", generate_local_offline_wav)

    plain = VoiceHumanizer.clean_narration_for_speech(text or "")
    plain = _strip_ssml_markup(plain)
    if not plain.strip():
        print("  [TTS/Local] empty text — continuing")
        return None
    ok, msg = gen_local_fn(plain, output_path)
    if not ok:
        print(f"  [TTS/Local] {msg}")
        return None
    dur = _wav_duration_seconds(output_path)
    timings = _sanitize_word_timings(_estimate_word_timings(plain, dur))
    print(f"  [TTS/Local] {msg} | ~{dur:.1f}s | {len(timings)} kelime")
    return output_path, timings


def _estimate_word_timings(text: str, duration_sec: float):
    """Weighted word split when provider does not emit WordBoundary events."""
    words = [w for w in re.split(r"\s+", (text or "").strip()) if w]
    if not words or duration_sec <= 0:
        return []

    weights = []
    for w in words:
        clean = re.sub(r"[^\wÀ-ÿ]", "", w, flags=re.UNICODE)
        w_len = max(2.0, float(len(clean)))
        stripped = w.strip()
        if stripped and stripped[-1] in ".!?:;":
            w_len += 3.5
        elif stripped and stripped[-1] in ",-–":
            w_len += 1.8
        weights.append(w_len)

    total_weight = sum(weights) or float(len(words))
    timings = []
    current_offset = 0.0
    for w, wt in zip(words, weights):
        dur = max(0.08, (wt / total_weight) * duration_sec)
        timings.append({
            "text": w,
            "offset": round(current_offset, 3),
            "duration": round(dur, 3),
        })
        current_offset += dur

    return timings


def _wav_duration_seconds(wav_path: str) -> float:
    try:
        with wave.open(wav_path, "rb") as wf:
            return wf.getnframes() / float(wf.getframerate())
    except Exception:
        return 0.0


def _generate_elevenlabs_narration(text, output_path):
    """Single-pass ElevenLabs TTS with estimated karaoke timings."""
    from elevenlabs_tts import generate_tts_wav
    from tts_voices import is_elevenlabs_voice
    from voice_humanizer import VoiceHumanizer
    cfg = _cfg()

    if not is_elevenlabs_voice(cfg.TTS_VOICE):
        raise ValueError("Not an ElevenLabs voice")

    plain = _strip_ssml_markup(VoiceHumanizer.clean_narration_for_speech(text))
    if not plain.strip():
        raise ValueError("Empty TTS text")

    ok, msg = generate_tts_wav(plain, output_path, cfg.TTS_VOICE)
    if not ok:
        raise RuntimeError(msg)

    dur = _wav_duration_seconds(output_path)
    timings = _estimate_word_timings(plain, dur)
    print(f"  [TTS/ElevenLabs] {msg} | ~{dur:.1f}s | {len(timings)} kelime (tahmini)")
    return output_path, _sanitize_word_timings(timings)


def _generate_azure_narration(text, output_path, voice_profile=None):
    """Single-pass Azure Speech TTS with estimated karaoke timings."""
    from azure_tts import generate_tts_wav
    from voice_humanizer import VoiceHumanizer
    cfg = _cfg()

    plain = _strip_ssml_markup(VoiceHumanizer.clean_narration_for_speech(text))
    if not plain.strip():
        raise ValueError("Empty TTS text")

    rate = cfg.TTS_RATE
    pitch = getattr(cfg, "TTS_PITCH", "+0Hz")
    if voice_profile and voice_profile.get("enabled") and voice_profile.get("rate"):
        rate = voice_profile.get("rate")

    ok, msg = generate_tts_wav(plain, output_path, voice=cfg.TTS_VOICE, rate=rate, pitch=pitch)
    if not ok:
        raise RuntimeError(msg)

    dur = _wav_duration_seconds(output_path)
    timings = _estimate_word_timings(plain, dur)
    print(f"  [TTS/Azure] {msg} | ~{dur:.1f}s | {len(timings)} kelime (tahmini)")
    return output_path, _sanitize_word_timings(timings)


def _generate_gemini_narration(text, output_path):
    """Single-pass Gemini TTS with estimated karaoke timings."""
    from google_ai_hub import generate_gemini_tts_wav
    from voice_humanizer import VoiceHumanizer
    cfg = _cfg()

    plain = _strip_ssml_markup(VoiceHumanizer.clean_narration_for_speech(text))
    if not plain.strip():
        raise ValueError("Empty TTS text")

    gender = getattr(cfg, "TTS_GENDER", "male")
    lang = getattr(cfg, "LANGUAGE", "tr")
    ok, msg = generate_gemini_tts_wav(plain, output_path, language=lang, gender=gender)
    if not ok:
        raise RuntimeError(f"Gemini TTS: {msg}")

    dur = _wav_duration_seconds(output_path)
    timings = _estimate_word_timings(plain, dur)
    print(f"  [TTS/Gemini] {msg} | {len(plain)} chars | ~{dur:.1f}s | {len(timings)} kelime (tahmini)")
    return output_path, _sanitize_word_timings(timings)


_SSML_LEAK_RE = re.compile(
    r"(?i)(</?speak\b[^>]*>|</?prosody\b[^>]*>|</?break\b[^>]*/?>|"
    r"xmlns[^=]*=\s*[\"'][^\"']*[\"']|xml:lang\s*=\s*[\"'][^\"']*[\"']|"
    r"http://www\.w3\.org/[^\"'\s]*)"
)
_SSML_TOKEN_RE = re.compile(
    r"(?i)^(speak|xmlns|xml:?lang|synthesis|prosody|break|version=?|"
    r"http|https|www\.|w3\.org|1\.0|tr-TR|en-US|ms/?|time=?|"
    r"rate=?|pitch=?|volume=?|xml|lang)$"
)


def _strip_ssml_markup(text: str) -> str:
    """Remove any SSML tags/attrs so Edge never speaks markup (Item 93)."""
    t = _SSML_LEAK_RE.sub(" ", text or "")
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _sanitize_word_timings(timings):
    """Drop WordBoundary tokens that are SSML debris (prevents ASS leak)."""
    cleaned = []
    for item in timings or []:
        w = (item.get("text") or "").strip()
        if not w or _SSML_TOKEN_RE.match(w.strip("\"'`=<>/")):
            continue
        if _SSML_LEAK_RE.search(w):
            continue
        low = w.lower()
        if any(k in low for k in ("xmlns", "xml:lang", "w3.org", "<speak", "</speak", "<break", "prosody")):
            continue
        letters = re.sub(r"[^\wÀ-ÿ]", "", w, flags=re.UNICODE)
        if len(letters) < 1:
            continue
        cleaned.append(item)
    return cleaned


def _mp3_to_wav(mp3, wav):
    r = subprocess.run(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-i", mp3, "-ar", "48000", "-ac", "2", wav],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    if r.returncode == 0:
        try:
            os.remove(mp3)
        except Exception:
            pass
        return wav
    return mp3
