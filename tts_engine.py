"""TTS — Edge TTS (0 TL fallback) with Azure preferred + optional Gemini/ElevenLabs."""
import asyncio, os, re, shutil, subprocess, tempfile, wave
from typing import Tuple
import imageio_ffmpeg
import edge_tts, config


def active_tts_provider() -> str:
    """Human-readable provider label for logs/UI."""
    from tts_voices import is_elevenlabs_voice, voice_label_for_id  # noqa: PLC0415
    if is_elevenlabs_voice(config.TTS_VOICE) and getattr(config, "ELEVENLABS_API_KEY", ""):
        return f"ElevenLabs ({voice_label_for_id(config.TTS_VOICE)})"
    try:
        from azure_tts import is_configured as azure_configured
        if (
            getattr(config, "PREFER_AZURE_TTS", True)
            and azure_configured()
            and not is_elevenlabs_voice(config.TTS_VOICE)
        ):
            return f"Azure Speech ({config.TTS_VOICE})"
    except Exception:
        pass
    if getattr(config, "USE_PIPER_TTS", False) and _piper_binary():
        return f"Piper local ({getattr(config, 'PIPER_MODEL', 'default')})"
    if getattr(config, "USE_GEMINI_TTS", False) and getattr(config, "GEMINI_API_KEY", ""):
        return f"Gemini TTS ({getattr(config, 'GEMINI_TTS_MODEL', 'gemini-2.5-flash-preview-tts')})"
    return f"Edge TTS ({config.TTS_VOICE})"


def _piper_binary() -> str:
    """R10 #45: Resolve Piper CLI if installed locally."""
    return shutil.which("piper") or ""


def piper_tts_available() -> bool:
    return bool(_piper_binary() and getattr(config, "USE_PIPER_TTS", False))


def generate_piper_wav(text: str, output_path: str, model_path: str = "") -> Tuple[bool, str]:
    """
    R10 #45: Offline Piper TTS when `piper` binary + onnx model present.
    Falls back with clear message if missing (Edge remains default).
    """
    import shutil as _sh
    exe = _piper_binary()
    if not exe:
        return False, "piper binary not found (brew/pip install piper-tts)"
    model = model_path or getattr(config, "PIPER_MODEL_PATH", "") or ""
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


def _estimate_word_timings(text: str, duration_sec: float):
    """Even word split when provider does not emit WordBoundary events (Gemini TTS)."""
    words = [w for w in re.split(r"\s+", (text or "").strip()) if w]
    if not words or duration_sec <= 0:
        return []
    w_dur = duration_sec / len(words)
    return [
        {"text": w, "offset": i * w_dur, "duration": w_dur}
        for i, w in enumerate(words)
    ]


def _wav_duration_seconds(wav_path: str) -> float:
    try:
        with wave.open(wav_path, "rb") as wf:
            return wf.getnframes() / float(wf.getframerate())
    except Exception:
        return 0.0


def _generate_elevenlabs_narration(text, output_path, voice_profile=None):
    """Single-pass ElevenLabs TTS with estimated karaoke timings."""
    from elevenlabs_tts import generate_tts_wav
    from tts_voices import is_elevenlabs_voice
    from voice_humanizer import VoiceHumanizer

    if not is_elevenlabs_voice(config.TTS_VOICE):
        raise ValueError("Not an ElevenLabs voice")

    plain = VoiceHumanizer.clean_narration_for_speech(text)
    plain = _strip_ssml_markup(plain)
    if not plain.strip():
        raise ValueError("Empty TTS text")

    ok, msg = generate_tts_wav(plain, output_path, config.TTS_VOICE)
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

    plain = VoiceHumanizer.clean_narration_for_speech(text)
    plain = _strip_ssml_markup(plain)
    if not plain.strip():
        raise ValueError("Empty TTS text")

    rate = config.TTS_RATE
    pitch = getattr(config, "TTS_PITCH", "+0Hz")
    if voice_profile and voice_profile.get("enabled") and voice_profile.get("rate"):
        rate = voice_profile.get("rate")

    ok, msg = generate_tts_wav(
        plain,
        output_path,
        voice=config.TTS_VOICE,
        rate=rate,
        pitch=pitch,
    )
    if not ok:
        raise RuntimeError(msg)

    dur = _wav_duration_seconds(output_path)
    timings = _estimate_word_timings(plain, dur)
    print(f"  [TTS/Azure] {msg} | ~{dur:.1f}s | {len(timings)} kelime (tahmini)")
    return output_path, _sanitize_word_timings(timings)


def _generate_gemini_narration(text, output_path, voice_profile=None):
    """Single-pass Gemini TTS with estimated karaoke timings."""
    from google_ai_hub import generate_gemini_tts_wav
    from voice_humanizer import VoiceHumanizer

    plain = VoiceHumanizer.clean_narration_for_speech(text)
    plain = _strip_ssml_markup(plain)
    if not plain.strip():
        raise ValueError("Empty TTS text")

    gender = getattr(config, "TTS_GENDER", "male")
    lang = getattr(config, "LANGUAGE", "tr")
    ok, msg = generate_gemini_tts_wav(
        plain,
        output_path,
        language=lang,
        gender=gender,
    )
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
    # Madde 400 / 173: pipeline masters at 48 kHz
    r = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),"-y","-i",mp3,"-ar","48000","-ac","2",wav],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if r.returncode == 0:
        try: os.remove(mp3)
        except: pass
        return wav
    return mp3

def _parse_rate_pct(rate: str) -> int:
    """Parse Edge TTS rate like '+18%' / '-5%' into an int percentage."""
    if not rate:
        return 0
    try:
        return int(str(rate).strip().replace("%", "").replace("+", ""))
    except ValueError:
        return 0

def _compose_rate(segment_rate: str, base_rate: str = None) -> str:
    """
    Blend Item 148 rhythm offset with config.TTS_RATE.
    Segment values are treated as deltas relative to a neutral 0% baseline;
    we shift them so body maps near the global Shorts pace.
    """
    base = _parse_rate_pct(base_rate or getattr(config, "TTS_RATE", "+18%"))
    seg = _parse_rate_pct(segment_rate)
    # Historical SPEECH_RHYTHM used absolute slow rates (+2% body). Rebase so
    # body≈base, hook≈base+8, question≈base-8 while preserving relative shape.
    if seg <= 12:
        # Old-style absolute rates → rebase onto Shorts pace
        delta = {"10": 8, "2": 0, "-5": -8, "0": 0}.get(str(seg), seg - 2)
        combined = base + delta
    else:
        combined = max(seg, base)
    combined = max(-50, min(100, combined))
    return f"+{combined}%" if combined >= 0 else f"{combined}%"

def _segment_pitch(segment: dict) -> str:
    """Items 142/171/178: Edge-TTS pitch per segment style + emphasis jump."""
    style = (segment or {}).get("style", "body")
    text = (segment or {}).get("text", "")
    if style == "hook":
        return "+8Hz"
    if style == "question" or (text or "").strip().endswith("?"):
        return "+5Hz"
    if _segment_has_emphasis(text):
        return "+12Hz"
    return getattr(config, "TTS_PITCH", "+0Hz") or "+0Hz"

_QUOTE_SEGMENT_RE = re.compile(
    r'^[«"“\'].*[»"”\']$|(?:dedi\s+ki|demişti|söyledi|quote:|alıntı:|aslında\s+şöyle\s+demişti|she\s+said|he\s+said)',
    re.I,
)

_ATTRIBUTION_SPLIT_RE = re.compile(
    r"^(?P<intro>.+?)\s+(?P<marker>(?:dedi\s+ki|demişti(?:\s+ki)?|söyledi|quote\s*:|alıntı\s*:|"
    r"aslında\s+şöyle\s+demişti|he\s+said|she\s+said))\s*:?\s*(?P<quote>.+)$",
    re.I | re.DOTALL,
)

_INLINE_QUOTE_CHUNK_RE = re.compile(r'^[«"“\'](.+)[»"”\']\.?$', re.DOTALL)


def _unwrap_outer_quotes(text: str) -> tuple:
    """Return (inner_text, was_wrapped)."""
    t = (text or "").strip()
    for open_q, close_q in (("«", "»"), ('"', '"'), ('"', '"'), ("'", "'")):
        if len(t) >= 2 and t.startswith(open_q) and t.endswith(close_q):
            return t[len(open_q):-len(close_q)].strip(), True
    return t, False


def split_narration_into_voice_segments(text: str):
    """
    Item 143: Split RAW narration into narrator vs quote clauses before clean_narration strips quotes.
    Returns [{"text": str, "is_quote": bool}, ...].
    """
    raw = (text or "").strip()
    if not raw:
        return []

    inner, was_wrapped = _unwrap_outer_quotes(raw)

    match = _ATTRIBUTION_SPLIT_RE.match(inner)
    if match:
        intro = match.group("intro").strip()
        marker = match.group("marker").strip()
        quote = _unwrap_outer_quotes(match.group("quote").strip())[0]
        segments = [{"text": f"{intro} {marker}:", "is_quote": False}]
        if quote:
            segments.append({"text": quote, "is_quote": True})
        return segments

    if was_wrapped:
        return [{"text": inner, "is_quote": True}]

    if re.search(r'[«"“\']', inner):
        parts = re.split(r'([«"“\'](?:[^»"”\']+)[»"”\'])', inner)
        segments = []
        for part in parts:
            part = part.strip()
            if not part:
                continue
            quoted = _INLINE_QUOTE_CHUNK_RE.match(part)
            if quoted:
                segments.append({"text": quoted.group(1).strip(), "is_quote": True})
            else:
                segments.append({"text": part, "is_quote": False})
        if segments:
            return segments

    return [{"text": inner, "is_quote": False}]


def _build_voice_aware_segments(text: str):
    """Rhythm + dual-voice segments from raw narration (quotes preserved until per-clause clean)."""
    from voice.script_humanizer import SPEECH_RHYTHM

    raw_sentences = re.findall(r"[^.!?]+[.!?]+|[^.!?]+$", text or "")
    segments = []
    for index, raw_sentence in enumerate(raw_sentences):
        raw_sentence = raw_sentence.strip()
        if not raw_sentence:
            continue
        style = "question" if raw_sentence.rstrip().endswith("?") else "hook" if index == 0 else "body"
        rate = SPEECH_RHYTHM[style]
        for part in split_narration_into_voice_segments(raw_sentence):
            seg_style = "quote" if part["is_quote"] else style
            segments.append(
                {
                    "text": part["text"],
                    "is_quote": part["is_quote"],
                    "style": seg_style,
                    "rate": rate,
                }
            )
    if not segments:
        for part in split_narration_into_voice_segments(text):
            segments.append(
                {
                    "text": part["text"],
                    "is_quote": part["is_quote"],
                    "style": "quote" if part["is_quote"] else "body",
                    "rate": getattr(config, "TTS_RATE", "+18%"),
                }
            )
    return segments


def _is_quote_segment(text: str) -> bool:
    """Item 143: detect quoted / attributed speech for dual-voice TTS."""
    t = (text or "").strip()
    if not t:
        return False
    if _QUOTE_SEGMENT_RE.search(t):
        return True
    if t.startswith(('"', '"', '«', "'")) and t.endswith(('"', '"', '»', "'")):
        return True
    return any(part.get("is_quote") for part in split_narration_into_voice_segments(t))


def _segment_has_emphasis(text: str) -> bool:
    from voice.script_humanizer import EMPHASIS_KEYWORDS_TR, EMPHASIS_KEYWORDS_EN
    words = {re.sub(r"[^\w]", "", w).casefold() for w in (text or "").split()}
    emphasis = {k.casefold() for k in EMPHASIS_KEYWORDS_TR} | {k.casefold() for k in EMPHASIS_KEYWORDS_EN}
    return bool(words & emphasis)

def _run_coro(coro):
    """Run async TTS safely from sync worker threads (and nested loop cases)."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    # Already inside an event loop: run in a fresh thread with its own loop
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, coro).result()

async def _tts(text, mp3_path, rate=None, volume=None, pitch=None):
    text = _strip_ssml_markup(text)
    if not (text or "").strip():
        raise ValueError("Empty TTS text")
    comm = edge_tts.Communicate(text=text, voice=config.TTS_VOICE,
                                 rate=rate or config.TTS_RATE,
                                 pitch=pitch or config.TTS_PITCH,
                                 volume=volume or "+0%")
    timings = []
    audio_bytes = 0
    with open(mp3_path, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
                audio_bytes += len(chunk["data"])
            elif chunk["type"] in ("WordBoundary", "SentenceBoundary"):
                text_val = chunk.get("text", "")
                offset_s = chunk.get("offset", 0) / 1e7
                dur_s = chunk.get("duration", 0) / 1e7
                if chunk["type"] == "WordBoundary":
                    timings.append({"text": text_val, "offset": offset_s, "duration": dur_s})
                else:
                    words = text_val.split()
                    if words:
                        w_dur = dur_s / max(1, len(words))
                        for idx, w in enumerate(words):
                            timings.append({"text": w, "offset": offset_s + idx * w_dur, "duration": w_dur})
    if audio_bytes == 0:
        raise edge_tts.exceptions.NoAudioReceived(
            "No audio was received. Please verify that your parameters are correct."
        )
    return mp3_path, _sanitize_word_timings(timings)

async def _tts_with_fallback(spoken_text, plain_text, mp3_path, rate=None, volume=None, pitch=None):
    """Try spoken text; on NoAudioReceived retry plain cleaned text once."""
    try:
        return await _tts(spoken_text, mp3_path, rate=rate, volume=volume, pitch=pitch)
    except Exception as first_err:
        err_name = type(first_err).__name__
        if err_name not in ("NoAudioReceived", "ValueError") and "NoAudioReceived" not in str(first_err):
            # Network blip: one plain retry still helps
            if "No audio" not in str(first_err) and err_name not in ("ClientResponseError", "WSServerHandshakeError"):
                raise
        fallback = (plain_text or spoken_text or "").strip()
        if not fallback or fallback == spoken_text:
            raise
        print(f"  [TTS] Retry plain text after {err_name}: {first_err}")
        if os.path.exists(mp3_path):
            try:
                os.remove(mp3_path)
            except OSError:
                pass
        return await _tts(fallback, mp3_path, rate=rate, volume=volume, pitch=pitch)

def _concat_wavs(wav_paths, output_path, pause_seconds=0.28):
    """Concatenates matching PCM WAV files while preserving a deterministic duration."""
    if not wav_paths:
        return "", []
    elapsed = 0.0
    offsets = []
    with wave.open(wav_paths[0], "rb") as first:
        params = first.getparams()
        with wave.open(output_path, "wb") as merged:
            merged.setparams(params)
            for index, wav_path in enumerate(wav_paths):
                offsets.append(elapsed)
                with wave.open(wav_path, "rb") as source:
                    if source.getparams()[:3] != params[:3]:
                        raise ValueError("TTS segment formats do not match")
                    frames = source.readframes(source.getnframes())
                    merged.writeframes(frames)
                    elapsed += source.getnframes() / float(source.getframerate())
                if index < len(wav_paths) - 1 and pause_seconds > 0:
                    silence_frames = int(params.framerate * pause_seconds)
                    merged.writeframes(b'\x00' * silence_frames * params.nchannels * params.sampwidth)
                    elapsed += pause_seconds
    return output_path, offsets

def generate_narration_with_timing(text, output_path, natural_pauses=True, voice_profile=None):
    from tts_voices import is_elevenlabs_voice

    use_elevenlabs = (
        is_elevenlabs_voice(config.TTS_VOICE)
        and bool(getattr(config, "ELEVENLABS_API_KEY", ""))
    )
    if use_elevenlabs:
        try:
            return _generate_elevenlabs_narration(text, output_path, voice_profile=voice_profile)
        except Exception as el_err:
            print(f"  [TTS] ElevenLabs başarısız, Azure/Edge yedek: {el_err}")
            from tts_voices import resolve_voice
            config.TTS_VOICE = resolve_voice(config.LANGUAGE, gender=config.TTS_GENDER)

    # Azure preferred when keys present (production ToS path); Edge remains zero-config fallback
    try:
        from azure_tts import is_configured as azure_configured
        use_azure = (
            getattr(config, "PREFER_AZURE_TTS", True)
            and azure_configured()
            and not is_elevenlabs_voice(config.TTS_VOICE)
        )
    except Exception:
        use_azure = False
    if use_azure:
        try:
            return _generate_azure_narration(text, output_path, voice_profile=voice_profile)
        except Exception as az_err:
            print(f"  [TTS] Azure Speech başarısız, Edge-TTS yedek: {az_err}")

    use_gemini = (
        getattr(config, "USE_GEMINI_TTS", False)
        and bool(getattr(config, "GEMINI_API_KEY", ""))
        and not is_elevenlabs_voice(config.TTS_VOICE)
    )
    if use_gemini:
        try:
            return _generate_gemini_narration(text, output_path, voice_profile=voice_profile)
        except Exception as gem_err:
            print(f"  [TTS] Gemini TTS başarısız, Edge-TTS yedek: {gem_err}")

    print(f"  [TTS/Edge] {config.TTS_VOICE} | {len(text)} chars")
    from voice_humanizer import VoiceHumanizer
    reaction_cues = VoiceHumanizer.extract_reaction_cues(text)
    # Item 143: split narrator vs quote on RAW text before clean_narration strips quotes
    segments = _build_voice_aware_segments(text)
    # Item 175: Doruk noktasında kademeli %115 tempo eğrisi
    segments = VoiceHumanizer.apply_climax_tempo_curve(segments, engine_type="plain")
    from voice.gender import select_quote_voice
    quote_voice = select_quote_voice(config.TTS_VOICE, getattr(config, "LANGUAGE", "tr"))
    narrator_voice = config.TTS_VOICE
    temp_dir = tempfile.mkdtemp(prefix="tts_rhythm_")
    wav_paths, timings = [], []
    try:
        for index, segment in enumerate(segments):
            plain_text = VoiceHumanizer.clean_narration_for_speech(segment["text"])
            # Punctuation-only segments ("...", "—") make Edge TTS raise NoAudioReceived
            if not plain_text.strip() or not re.search(r"\w", plain_text, flags=re.UNICODE):
                continue
            is_quote = bool(segment.get("is_quote")) or segment.get("style") == "quote"
            if is_quote:
                config.TTS_VOICE = quote_voice
            else:
                config.TTS_VOICE = narrator_voice
            if natural_pauses:
                # Item 93: use plain ellipsis pauses — Edge TTS reads SSML <break>
                # tags as spoken words and roughly doubles duration.
                spoken_text = VoiceHumanizer.synthesize_natural_pauses(
                    plain_text, engine_type="plain", break_ms=120
                )
            else:
                spoken_text = plain_text
            spoken_text = _strip_ssml_markup(spoken_text)
            plain_text = _strip_ssml_markup(plain_text)
            segment_mp3 = os.path.join(temp_dir, f"segment_{index}.mp3")
            segment_wav = os.path.join(temp_dir, f"segment_{index}.wav")
            if voice_profile and voice_profile.get("enabled") and voice_profile.get("rate"):
                rate = voice_profile.get("rate")
            else:
                seg_rate = segment.get("prosody_rate") or segment.get("rate") or config.TTS_RATE
                rate = _compose_rate(seg_rate, config.TTS_RATE)
                # Item 223: hook ≈2× hız hissi (+35% delta on top of composed rate)
                if segment.get("style") == "hook" or index == 0:
                    base_pct = _parse_rate_pct(rate)
                    rate = f"+{min(100, base_pct + 35)}%"
                # Item 171: vurgu kelimeli segmentlerde ek tempo
                elif _segment_has_emphasis(plain_text):
                    base_pct = _parse_rate_pct(rate)
                    rate = f"+{min(100, base_pct + 8)}%"
            pitch = _segment_pitch(segment)
            volume = "-22%" if voice_profile and voice_profile.get("enabled") else None
            _, segment_timings = _run_coro(
                _tts_with_fallback(spoken_text, plain_text, segment_mp3, rate=rate, volume=volume, pitch=pitch)
            )
            _mp3_to_wav(segment_mp3, segment_wav)
            if not os.path.exists(segment_wav) or os.path.getsize(segment_wav) < 64:
                raise RuntimeError(f"TTS segment {index} produced no audio")
            wav_paths.append(segment_wav)
            timings.append(segment_timings)
            config.TTS_VOICE = narrator_voice
        if not wav_paths:
            raise RuntimeError("TTS produced no segments")
        # Short inter-sentence gap; Item 93 pauses already live inside each segment
        wav, offsets = _concat_wavs(wav_paths, output_path, pause_seconds=0.06 if natural_pauses else 0.0)
        flattened_timings = []
        for offset, segment_timings in zip(offsets, timings):
            for timing in segment_timings:
                timing["offset"] += offset
                flattened_timings.append(timing)
        timings = _sanitize_word_timings(flattened_timings)
        # Item 194: Sentetik Ses Artefaktlarını Filtreleme (Low-pass @ 14kHz)
        try:
            from voice.audio_dsp import apply_tts_artifact_lowpass_filter
            filtered_wav = output_path + ".lp.wav"
            if apply_tts_artifact_lowpass_filter(output_path, filtered_wav, cutoff_hz=14000.0) == filtered_wav:
                os.replace(filtered_wav, output_path)
                print("  [TTS] Item 194: 14kHz alçak geçiren filtre ile sentetik artefaktlar temizlendi.")
        except Exception:
            pass
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
    if reaction_cues:
        print(f"  [TTS] {len(reaction_cues)} non-verbal reaction cue(s) reserved for mix (Item 149).")
    print(f"  [TTS] {len(timings)} word timings (Item 93 Natural Pauses: {natural_pauses})")
    print(f"  [TTS] Saved: {wav}")
    return wav, timings
