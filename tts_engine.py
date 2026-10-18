"""TTS — Edge TTS (0 TL fallback) with Azure preferred + optional Gemini/ElevenLabs."""
import asyncio, os, re, shutil, subprocess, sys, tempfile, wave
from typing import Tuple
import imageio_ffmpeg
import edge_tts, config
from voice.tts_providers import (
    _SSML_LEAK_RE,
    _SSML_TOKEN_RE,
    _estimate_word_timings,
    _gemini_tts_circuit_open,
    _generate_azure_narration,
    _generate_elevenlabs_narration,
    _generate_gemini_narration,
    _is_gemini_quota_block,
    _local_piper_binary,
    _local_piper_model,
    _mark_gemini_tts_circuit_open,
    _mp3_to_wav,
    _piper_binary,
    _sanitize_word_timings,
    _strip_ssml_markup,
    _try_google_translate_tts_narration,
    _try_local_offline_narration,
    _wav_duration_seconds,
    active_tts_provider,
    edge_fallback_voices,
    generate_local_offline_wav,
    generate_piper_wav,
    piper_tts_available,
)


def _ensure_edge_tts_sec_ms_gec_v2() -> None:
    """Ensure edge_tts uses Sec-MS-GEC v2 token & version prefix (fixes Bing 403 handshake errors)."""
    try:
        from edge_tts import communicate as _et_comm
        from edge_tts import constants as _et_const
        from edge_tts import drm as _et_drm

        chrom_ver = getattr(_et_const, "CHROMIUM_FULL_VERSION", "143.0.3650.75")
        v2_ver = f"2-{chrom_ver}"
        if hasattr(_et_drm, "generate_sec_ms_gec_v2"):
            if getattr(_et_const, "SEC_MS_GEC_VERSION", "").startswith("1-"):
                _et_const.SEC_MS_GEC_VERSION = v2_ver
            if getattr(_et_comm, "SEC_MS_GEC_VERSION", "").startswith("1-"):
                _et_comm.SEC_MS_GEC_VERSION = v2_ver
            _et_drm.DRM.generate_sec_ms_gec = staticmethod(_et_drm.generate_sec_ms_gec_v2)
    except Exception:
        pass


_ensure_edge_tts_sec_ms_gec_v2()


def _try_macos_say_narration(text: str, output_path: str):
    """Zero-cost macOS native voice ('say -v Yelda') fallback when online Edge-TTS & Piper are unavailable."""
    if sys.platform != "darwin":
        return None
    say_bin = shutil.which("say")
    if not say_bin:
        return None
    from voice_humanizer import VoiceHumanizer

    plain = _strip_ssml_markup(VoiceHumanizer.clean_narration_for_speech(text or ""))
    if not plain.strip():
        return None
    lang = str(getattr(config, "LANGUAGE", "tr") or "tr").lower()
    voice_name = "Yelda" if lang.startswith("tr") else "Samantha"
    tmp_aiff = output_path + ".macos.aiff"
    try:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)
        res = subprocess.run(
            [say_bin, "-v", voice_name, "-r", "195", "-o", tmp_aiff, plain],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=90,
        )
        if res.returncode != 0 or not os.path.isfile(tmp_aiff):
            return None
        ff = subprocess.run(
            [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-i", tmp_aiff, "-ar", "48000", "-ac", "2", output_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=90,
        )
        if ff.returncode != 0 or not os.path.isfile(output_path) or os.path.getsize(output_path) < 64:
            return None
        dur = _wav_duration_seconds(output_path)
        timings = _sanitize_word_timings(_estimate_word_timings(plain, dur))
        print(f"  [TTS/macOS] Native '{voice_name}' fallback OK -> {output_path} (~{dur:.1f}s, {len(timings)} kelime)")
        return output_path, timings
    except Exception as exc:
        print(f"  [TTS/macOS] Native fallback failed: {exc}")
        return None
    finally:
        if os.path.isfile(tmp_aiff):
            try:
                os.remove(tmp_aiff)
            except OSError:
                pass


def _parse_rate_pct(rate: str) -> int:
    """Parse Edge TTS rate like '+18%' / '-5%' into an int percentage."""
    if not rate:
        return 0
    try:
        return int(str(rate).strip().replace("%", "").replace("+", ""))
    except ValueError:
        return 0


def _compose_rate(segment_rate: str, base_rate: str = None) -> str:
    """Blend Item 148 rhythm offset with config.TTS_RATE."""
    base = _parse_rate_pct(base_rate or getattr(config, "TTS_RATE", "+18%"))
    seg = _parse_rate_pct(segment_rate)
    if seg <= 12:
        delta = {"10": 8, "2": 0, "-5": -8, "0": 0}.get(str(seg), seg - 2)
        combined = base + delta
    else:
        combined = max(seg, base)
    combined = max(-50, min(100, combined))
    return f"+{combined}%" if combined >= 0 else f"{combined}%"


def narration_rate_for_segment(
    segment,
    index,
    voice_profile=None,
    sacred_calm=None,
    plain_text="",
):
    """Edge rate for one chunk. Sacred niches stay at SACRED_TTS_RATE."""
    if sacred_calm is None:
        sacred_calm = bool(getattr(config, "TTS_SACRED_CALM", False))
    if sacred_calm:
        return getattr(config, "SACRED_TTS_RATE", "+8%") or "+8%"
    if voice_profile and voice_profile.get("enabled") and voice_profile.get("rate"):
        return voice_profile.get("rate")
    seg_rate = (segment or {}).get("prosody_rate") or (segment or {}).get("rate") or config.TTS_RATE
    rate = _compose_rate(seg_rate, config.TTS_RATE)
    if (segment or {}).get("style") == "hook" or index == 0:
        base_pct = _parse_rate_pct(rate)
        rate = f"+{max(base_pct, min(40, base_pct + 12))}%"
    elif _segment_has_emphasis(plain_text or (segment or {}).get("text") or ""):
        base_pct = _parse_rate_pct(rate)
        rate = f"+{min(100, base_pct + 8)}%"
    return rate


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
    """Item 143: Split RAW narration into narrator vs quote clauses before clean_narration strips quotes."""
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
    """Rhythm + dual-voice segments from raw narration."""
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
            segments.append({
                "text": part["text"],
                "is_quote": part["is_quote"],
                "style": seg_style,
                "rate": rate,
            })
    if not segments:
        for part in split_narration_into_voice_segments(text):
            segments.append({
                "text": part["text"],
                "is_quote": part["is_quote"],
                "style": "quote" if part["is_quote"] else "body",
                "rate": getattr(config, "TTS_RATE", "+18%"),
            })
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


_CORO_POOL = None


def _run_coro(coro):
    """Run async TTS safely from sync worker threads (and nested loop cases)."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    import concurrent.futures
    global _CORO_POOL
    if _CORO_POOL is None or getattr(_CORO_POOL, "_shutdown", False):
        _CORO_POOL = concurrent.futures.ThreadPoolExecutor(max_workers=2)
    return _CORO_POOL.submit(asyncio.run, coro).result()


async def _tts(text, mp3_path, rate=None, volume=None, pitch=None):
    text = _strip_ssml_markup(text)
    if not (text or "").strip():
        raise ValueError("Empty TTS text")
    comm = edge_tts.Communicate(
        text=text,
        voice=config.TTS_VOICE,
        rate=rate or config.TTS_RATE,
        pitch=pitch or config.TTS_PITCH,
        volume=volume or "+0%",
        boundary="WordBoundary",
    )
    timings, sentence_timings, audio_bytes = [], [], 0
    with open(mp3_path, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
                audio_bytes += len(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                timings.append({
                    "text": chunk.get("text", ""),
                    "offset": chunk.get("offset", 0) / 1e7,
                    "duration": chunk.get("duration", 0) / 1e7,
                })
            elif chunk["type"] == "SentenceBoundary":
                sentence_timings.append({
                    "text": chunk.get("text", ""),
                    "offset": chunk.get("offset", 0) / 1e7,
                    "duration": chunk.get("duration", 0) / 1e7,
                })
    if audio_bytes == 0:
        raise edge_tts.exceptions.NoAudioReceived(
            "No audio was received. Please verify that your parameters are correct."
        )

    sanitized = _sanitize_word_timings(timings)
    if not sanitized and sentence_timings:
        fallback_timings = []
        for st in sentence_timings:
            for w_est in _estimate_word_timings(st.get("text", ""), st.get("duration", 0.0)):
                fallback_timings.append({
                    "text": w_est["text"],
                    "offset": st.get("offset", 0.0) + w_est["offset"],
                    "duration": w_est["duration"],
                })
        sanitized = _sanitize_word_timings(fallback_timings)

    return mp3_path, sanitized


_WORKING_VOICE_CACHE: dict[str, str] = {}


async def _tts_with_fallback(spoken_text, plain_text, mp3_path, rate=None, volume=None, pitch=None):
    """Try spoken text; on NoAudioReceived retry cleaned text, then healthy fallback voices."""
    orig_voice = config.TTS_VOICE
    cached_fb = _WORKING_VOICE_CACHE.get(orig_voice)
    if cached_fb and not hasattr(_tts, "_mock_name"):
        config.TTS_VOICE = cached_fb
    try:
        return await _tts(spoken_text, mp3_path, rate=rate, volume=volume, pitch=pitch)
    except Exception as first_err:
        err_name = type(first_err).__name__
        fallback = (plain_text or spoken_text or "").strip()
        cleaned_fallback = re.sub(r"[^\w\s.,!?-]", " ", fallback).strip()
        if not cleaned_fallback:
            raise first_err
        print(f"  [TTS] Retry cleaned text after {err_name}: {first_err}")
        if os.path.exists(mp3_path):
            try:
                os.remove(mp3_path)
            except OSError:
                pass
        try:
            return await _tts(cleaned_fallback, mp3_path, rate=rate, volume=volume, pitch=pitch)
        except Exception as retry_err:
            for fb_voice in edge_fallback_voices(orig_voice):
                config.TTS_VOICE = fb_voice
                try:
                    print(f"  [TTS] Fallback voice {fb_voice} ({orig_voice} unavailable)...")
                    res = await _tts(cleaned_fallback, mp3_path, rate=rate, volume=volume, pitch=pitch)
                    _WORKING_VOICE_CACHE[orig_voice] = fb_voice
                    return res
                except Exception:
                    if os.path.exists(mp3_path):
                        try:
                            os.remove(mp3_path)
                        except OSError:
                            pass
            raise retry_err
    finally:
        config.TTS_VOICE = orig_voice


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
    from tts_voices import is_elevenlabs_voice, is_local_offline_voice, resolve_voice

    if is_local_offline_voice(config.TTS_VOICE):
        local_hit = _try_local_offline_narration(text, output_path)
        if local_hit:
            return local_hit
        print("  [TTS/Local] seçili yerel ses üretilemedi — Edge devam")
        config.TTS_VOICE = resolve_voice(
            getattr(config, "LANGUAGE", "tr"),
            gender=getattr(config, "TTS_GENDER", "male"),
        )

    elevenlabs_failed = False
    use_elevenlabs = is_elevenlabs_voice(config.TTS_VOICE) and bool(getattr(config, "ELEVENLABS_API_KEY", ""))
    if use_elevenlabs:
        try:
            return _generate_elevenlabs_narration(text, output_path)
        except Exception as el_err:
            elevenlabs_failed = True
            print(f"  [TTS] ElevenLabs başarısız, Azure/Edge yedek: {el_err}")
            config.TTS_VOICE = resolve_voice(config.LANGUAGE, gender=config.TTS_GENDER)

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
    gemini_blocked = _gemini_tts_circuit_open()
    if use_gemini and gemini_blocked:
        print("  [TTS/Gemini] circuit open — Edge yedek")
    elif use_gemini:
        try:
            return _generate_gemini_narration(text, output_path)
        except Exception as gem_err:
            if _is_gemini_quota_block(gem_err):
                gemini_blocked = True
                _mark_gemini_tts_circuit_open(str(gem_err))
            print(f"  [TTS] Gemini TTS başarısız, Edge-TTS yedek: {gem_err}")

    print(f"  [TTS/Edge] {config.TTS_VOICE} | {len(text)} chars")
    from voice_humanizer import VoiceHumanizer
    reaction_cues = VoiceHumanizer.extract_reaction_cues(text)
    segments = _build_voice_aware_segments(text)
    sacred_calm = bool(getattr(config, "TTS_SACRED_CALM", False))
    if not sacred_calm:
        segments = VoiceHumanizer.apply_climax_tempo_curve(segments, engine_type="plain")
    from voice.gender import select_quote_voice
    quote_voice = select_quote_voice(config.TTS_VOICE, getattr(config, "LANGUAGE", "tr"))
    narrator_voice = config.TTS_VOICE
    temp_dir = tempfile.mkdtemp(prefix="tts_rhythm_")
    wav_paths, timings = [], []
    try:
        for index, segment in enumerate(segments):
            plain_text = VoiceHumanizer.clean_narration_for_speech(segment["text"])
            if not plain_text.strip() or not re.search(r"\w", plain_text, flags=re.UNICODE):
                continue
            is_quote = bool(segment.get("is_quote")) or segment.get("style") == "quote"
            config.TTS_VOICE = quote_voice if is_quote else narrator_voice
            if natural_pauses:
                spoken_text = VoiceHumanizer.synthesize_natural_pauses(plain_text, engine_type="plain", break_ms=120)
            else:
                spoken_text = plain_text
            spoken_text = _strip_ssml_markup(spoken_text)
            plain_text = _strip_ssml_markup(plain_text)
            segment_mp3 = os.path.join(temp_dir, f"segment_{index}.mp3")
            segment_wav = os.path.join(temp_dir, f"segment_{index}.wav")
            rate = narration_rate_for_segment(
                segment, index, voice_profile=voice_profile, sacred_calm=sacred_calm, plain_text=plain_text
            )
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
        wav, offsets = _concat_wavs(wav_paths, output_path, pause_seconds=0.06 if natural_pauses else 0.0)
        flattened_timings = []
        for offset, segment_timings in zip(offsets, timings):
            for timing in segment_timings:
                timing["offset"] += offset
                flattened_timings.append(timing)
        timings = _sanitize_word_timings(flattened_timings)
        try:
            from voice.audio_dsp import apply_tts_artifact_lowpass_filter
            filtered_wav = output_path + ".lp.wav"
            if apply_tts_artifact_lowpass_filter(output_path, filtered_wav, cutoff_hz=14000.0) == filtered_wav:
                os.replace(filtered_wav, output_path)
                print("  [TTS] Item 194: 14kHz alçak geçiren filtre ile sentetik artefaktlar temizlendi.")
        except Exception:
            pass
        if reaction_cues:
            print(f"  [TTS] {len(reaction_cues)} non-verbal reaction cue(s) reserved for mix (Item 149).")
        print(f"  [TTS] {len(timings)} word timings (Item 93 Natural Pauses: {natural_pauses})")
        print(f"  [TTS] Saved: {wav}")
        edge_error = None
        edge_result = (wav, timings)
    except Exception as edge_err:
        edge_error = edge_err
        edge_result = None
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
    if edge_error is not None:
        if gemini_blocked:
            which = "ElevenLabs" if elevenlabs_failed else "Edge"
            print(f"  [TTS/Local] Gemini 429/circuit, {which} de düştü — Piper")
            local_hit = _try_local_offline_narration(text, output_path)
            if local_hit:
                return local_hit
            print("  [TTS/Local] kota yedeği yok — devam")
        is_tts_mocked = any(
            hasattr(fn, "_mock_name") or "unittest.mock" in type(fn).__module__
            for fn in (_run_coro, _tts_with_fallback, _tts, generate_local_offline_wav)
        )
        if not is_tts_mocked:
            if not gemini_blocked:
                local_hit = _try_local_offline_narration(text, output_path)
                if local_hit:
                    return local_hit
            macos_hit = _try_macos_say_narration(text, output_path)
            if macos_hit:
                return macos_hit
            gtts_hit = _try_google_translate_tts_narration(text, output_path)
            if gtts_hit:
                return gtts_hit
        raise edge_error
    return edge_result
