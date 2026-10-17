"""
Karaoke subtitles — ASS (word-by-word highlight) + SRT fallback.
BOTH files are ALWAYS written to guarantee subtitles work.
Item 107: Font rotation pool (TheBoldFont, Anton, Outfit, Poppins, Montserrat, Bebas Neue).
Item 116: Drop shadow açı ve bulanıklık varyasyonu — her videoda farklı.
"""
import json
import math as _math
import os
import random
import re
from typing import Any, Dict, List, Optional
import config
from viral_retention_engine import ViralRetentionEngine
from render.subtitle_ass_builder import (
    NAMED_COLORS,
    POWER_WORD_HIGHLIGHTS,
    _active_word_tags,
    _at,
    _emphasis_overlay_events,
    _format_word,
    _group,
    _resolve_subtitle_layout,
    _st,
    create_emphasis_overlay_ass,
    create_karaoke_subtitles,
    create_srt_file,
    create_subtitle_files,
    ffmpeg_force_style_from_opts,
    hex_to_ass_color,
    split_subtitle_pages_on_silence,
)

# ─── ITEM 107: Altyazı Yazı Tipi Rotasyonu ──────────────────────────────────
SUBTITLE_FONT_POOL = [
    "Anton",
    "Outfit",
    "Poppins",
    "Bebas Neue",
    "Montserrat",
    "Oswald",
    "Rajdhani",
    "Barlow Condensed",
]

_SESSION_FONT: str = random.choice(SUBTITLE_FONT_POOL)

# ─── ITEM 116: Drop Shadow Açı Varyasyonu ────────────────────────────────
_SESSION_SHADOW_DEPTH: float = round(random.uniform(1.5, 3.5), 1)
_SESSION_SHADOW_ANGLE: int = random.randint(135, 225)
_SHADOW_RAD: float = _math.radians(_SESSION_SHADOW_ANGLE)
_SESSION_SHADOW_X: float = round(_SESSION_SHADOW_DEPTH * _math.cos(_SHADOW_RAD), 2)
_SESSION_SHADOW_Y: float = round(_SESSION_SHADOW_DEPTH * _math.sin(_SHADOW_RAD), 2)


def get_session_shadow_params() -> dict:
    """Item 116 – Altyazı Gölge Parametreleri."""
    return {
        "depth": _SESSION_SHADOW_DEPTH,
        "angle": _SESSION_SHADOW_ANGLE,
        "shadow_x": _SESSION_SHADOW_X,
        "shadow_y": _SESSION_SHADOW_Y,
    }


def get_session_subtitle_font(override: str = None) -> str:
    """Item 107 – Altyazı Yazı Tipi Rotasyonu."""
    return override if override else _SESSION_FONT


_STYLE_TOKEN_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "static", "js", "subtitle-style-tokens.json",
)
_STYLE_LOCK_KEYS = frozenset({
    "color", "highlight_color", "stroke_color", "stroke_width",
    "font_name", "uppercase", "glow", "bold", "box", "box_color",
    "font_size", "preview_background", "clamp_word_durations", "double_outline",
    "words_per_page",
})


def load_subtitle_style_tokens() -> dict:
    with open(_STYLE_TOKEN_PATH, encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict) or "capcut_yellow" not in data or "mrbeast_style" not in data:
        raise RuntimeError(f"Subtitle style tokens missing required presets: {_STYLE_TOKEN_PATH}")
    return data


SUBTITLE_STYLE_TOKENS = load_subtitle_style_tokens()
SUBTITLE_PRESETS = {key: dict(value) for key, value in SUBTITLE_STYLE_TOKENS.items()}


def merge_studio_subtitle_opts(
    preset_name: str = "",
    *,
    base: dict = None,
    font_size=None,
    y_position=None,
    color: str = None,
    highlight_color: str = None,
    craft_opts: dict = None,
) -> dict:
    """Preset tokens, then lab sliders. Craft must not replace a locked style or slider Y."""
    if base is not None:
        opts = dict(base)
    elif preset_name and preset_name in SUBTITLE_PRESETS:
        opts = dict(SUBTITLE_PRESETS[preset_name])
    else:
        opts = {}
    preset_locked = bool(preset_name and preset_name in SUBTITLE_PRESETS)
    if color:
        opts["color"] = color
    if highlight_color:
        opts["highlight_color"] = highlight_color
    if font_size is not None:
        opts["font_size"] = int(font_size)
    if y_position is not None:
        opts["y_position"] = float(y_position)
        opts["honor_y_position"] = True
    if craft_opts:
        for key, value in craft_opts.items():
            if opts.get("honor_y_position") and key == "y_position":
                continue
            if preset_locked and key in _STYLE_LOCK_KEYS:
                continue
            if key in (
                "y_position", "max_words_per_line", "max_words_per_frame",
                "human_craft", "allow_mid_frame",
            ) or key not in opts:
                opts[key] = value
        if opts.get("honor_y_position") and y_position is not None:
            opts["y_position"] = float(y_position)
            opts["honor_y_position"] = True
    return opts


def get_niche_subtitle_preset(niche_key: str = "") -> dict:
    """Chapter 4.5 & 7.5: Resolves one of the 16 subtitle presets tailored to target niche."""
    key = (niche_key or "").lower().strip()
    try:
        from services.niche_profiles import resolve_niche_profile
        prof = resolve_niche_profile(key)
        preset_name = prof.get("subtitle_preset")
        if preset_name and preset_name in SUBTITLE_PRESETS:
            return dict(SUBTITLE_PRESETS[preset_name])
    except Exception:
        pass

    if any(k in key for k in ("crypto", "btc", "money", "finance")):
        return dict(SUBTITLE_PRESETS["crypto_gold"])
    if any(k in key for k in ("luxury", "rich", "lifestyle")):
        return dict(SUBTITLE_PRESETS["luxury_elegance"])
    if any(k in key for k in ("horror", "dark", "creepy", "crime", "mysterious")):
        return dict(SUBTITLE_PRESETS["horror_blood"])
    if any(k in key for k in ("history", "tarih", "battle", "war", "bizarre")):
        return dict(SUBTITLE_PRESETS["history_sepia"])
    if any(k in key for k in ("space", "uzay", "cosmos", "future")):
        return dict(SUBTITLE_PRESETS["space_neon_blue"])
    if any(k in key for k in ("fitness", "workout", "biohack", "gym")):
        return dict(SUBTITLE_PRESETS["fitness_punch"])
    if any(k in key for k in ("psychology", "mind", "persuasion", "ikna")):
        return dict(SUBTITLE_PRESETS["psychology_violet"])
    if any(k in key for k in ("stoic", "felsefe", "wisdom", "islamic")):
        return dict(SUBTITLE_PRESETS["wisdom_emerald"])
    if any(k in key for k in ("news", "breaking", "haber", "son dakika")):
        return dict(SUBTITLE_PRESETS["high_contrast_retention"])
    if any(k in key for k in ("reddit", "story", "confession")):
        return dict(SUBTITLE_PRESETS["tiktok_bold"])
    if any(k in key for k in ("quiz", "duel", "facts", "bilgi")):
        return dict(SUBTITLE_PRESETS["mrbeast_style"])
    if any(k in key for k in ("cyber", "ai", "tech")):
        return dict(SUBTITLE_PRESETS["cyber_green"])
    if any(k in key for k in ("parenting", "child", "family")):
        return dict(SUBTITLE_PRESETS["clean_white"])
    if any(k in key for k in ("survival", "danger", "myth")):
        return dict(SUBTITLE_PRESETS["red_fire"])
    return dict(SUBTITLE_PRESETS["capcut_yellow"])


AB_SUBTITLE_STYLE_MAP = {
    "karaoke_bold_neon": "red_fire",
    "minimal_white_shadow": "clean_white",
}


def resolve_ab_subtitle_preset(variation_attempt: int, topic: str) -> dict:
    """Item 310: pick A/B subtitle preset from growth_tactics variants."""
    try:
        from growth_tactics import generate_ab_test_variants
    except ImportError:
        return {}
    variants = generate_ab_test_variants(topic or "Shorts")
    if not variants:
        return {}
    variant = variants[variation_attempt % len(variants)]
    style_key = variant["subtitle_style_a"] if variation_attempt % 2 == 0 else variant["subtitle_style_b"]
    preset_key = AB_SUBTITLE_STYLE_MAP.get(style_key, "red_fire")
    opts = dict(SUBTITLE_PRESETS.get(preset_key, SUBTITLE_PRESETS["red_fire"]))
    opts["ab_test_variant"] = variant.get("variant", "")
    return opts


_SSML_TOKEN_RE = re.compile(
    r"(?i)^(speak|xmlns|xml:?lang|synthesis|prosody|break|version=?|"
    r"http|https|www\.|w3\.org|1\.0|tr-TR|en-US|ms/?|time=?|"
    r"rate=?|pitch=?|volume=?|xml|lang)$"
)
_SSML_FRAGMENT_RE = re.compile(
    r"(?i)(xmlns|xml:lang|<speak|</speak>|<break|<prosody|synthesis|"
    r"http://www\.w3\.org|version\s*=\s*[\"']?1\.0)"
)


def _is_ssml_junk_token(text: str) -> bool:
    """True if Edge WordBoundary leaked SSML markup into karaoke timings."""
    t = (text or "").strip().strip("\"'`=<>/")
    if not t:
        return True
    if _SSML_TOKEN_RE.match(t.replace('"', "").replace("'", "")):
        return True
    if _SSML_FRAGMENT_RE.search(t):
        return True
    low = t.lower()
    if any(k in low for k in ("xmlns", "xml:lang", "w3.org", "<speak", "</speak", "<break")):
        return True
    return False


def _probe_audio_duration_sec(audio_path: str) -> float:
    """FFmpeg duration parse for subtitle drift guard (Items 413/184)."""
    if not audio_path or not os.path.isfile(audio_path):
        return 0.0
    try:
        import subprocess
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        res = subprocess.run(
            [exe, "-i", audio_path, "-hide_banner"],
            stderr=subprocess.PIPE, stdout=subprocess.PIPE, timeout=8,
        )
        err = (res.stderr or b"").decode("utf-8", errors="replace")
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", err)
        if m:
            return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    except Exception:
        pass
    return 0.0


def _scale_timings(timings: list, scale: float) -> list:
    return [
        {
            **item,
            "offset": round(float(item.get("offset", 0.0)) * scale, 4),
            "duration": round(float(item.get("duration", 0.0)) * scale, 4),
        }
        for item in timings
    ]


def _rescale_timings_to_audio_duration(timings: list, audio_path: str) -> list:
    """Lock word spans to the narration file."""
    if not timings or not audio_path:
        return timings or []
    audio_dur = _probe_audio_duration_sec(audio_path)
    if audio_dur <= 0:
        return timings
    last = timings[-1]
    last_offset = float(last.get("offset", 0.0))
    span_end = last_offset + float(last.get("duration", 0.0))
    if span_end <= 0.05:
        return timings
    delta = audio_dur - span_end
    if abs(delta) < 0.02:
        return timings
    if delta < 0:
        if last_offset >= audio_dur - 0.05:
            return _scale_timings(timings, audio_dur / span_end)
        out = [dict(item) for item in timings]
        out[-1] = {**out[-1], "duration": round(max(0.05, audio_dur - last_offset), 4)}
        return out
    tail_limit = max(0.45, audio_dur * 0.04)
    if delta <= tail_limit:
        out = [dict(item) for item in timings]
        out[-1] = {**out[-1], "duration": round(float(out[-1].get("duration", 0.0)) + delta, 4)}
        return out
    return _scale_timings(timings, audio_dur / span_end)


def _norm_word(text: str) -> str:
    return re.sub(r"[^\wÀ-ÿ]", "", str(text or ""), flags=re.UNICODE).casefold()


def merge_continuation_words(words: list) -> list:
    """openshorts: a token without a leading space is a fragment of the previous word."""
    merged = []
    for word in words or []:
        raw = word.get("text", word.get("word", ""))
        text = raw if isinstance(raw, str) else str(raw or "")
        offset = round(float(word.get("offset", word.get("start", 0.0)) or 0.0), 4)
        if "duration" in word and word.get("duration") is not None:
            duration = float(word.get("duration") or 0.0)
        else:
            duration = float(word.get("end", offset) or offset) - offset
        duration = round(max(0.05, duration), 4)
        if merged and text and not text.startswith(" "):
            prev = merged[-1]
            prev["text"] = f"{prev.get('text', '')}{text}".strip()
            end = offset + duration
            start = float(prev.get("offset", 0.0))
            prev["duration"] = round(max(0.05, end - start), 4)
            continue
        merged.append({"text": text.strip(), "offset": offset, "duration": duration})
    return merged


def snap_script_to_whisper(script: list, whisper_words: list) -> list:
    """Keep the narration words. Copy Whisper times onto matching tokens."""
    script = list(script or [])
    heard = merge_continuation_words(whisper_words)
    if not script or not heard:
        return []
    wi = 0
    anchors = {}
    for i, item in enumerate(script):
        key = _norm_word(item.get("text"))
        if not key:
            continue
        found = None
        for j in range(wi, min(wi + 4, len(heard))):
            if _norm_word(heard[j].get("text")) == key:
                found = j
                break
        if found is None:
            continue
        anchors[i] = heard[found]
        wi = found + 1
    if len(anchors) / len(script) < 0.55:
        return []
    out = []
    for i, item in enumerate(script):
        if i in anchors:
            w = anchors[i]
            out.append({**item, "offset": round(float(w["offset"]), 4), "duration": round(float(w["duration"]), 4)})
        else:
            out.append(dict(item))
    anchor_idx = [-1] + sorted(anchors) + [len(script)]
    for left, right in zip(anchor_idx, anchor_idx[1:]):
        gap = list(range(left + 1, right))
        if not gap:
            continue
        left_end = 0.0 if left < 0 else float(out[left]["offset"]) + float(out[left]["duration"])
        if right >= len(script):
            cursor = left_end
            for i in gap:
                dur = max(0.05, float(out[i].get("duration") or 0.2))
                off = max(cursor, float(out[i].get("offset") or cursor))
                out[i] = {**out[i], "offset": round(off, 4), "duration": round(dur, 4)}
                cursor = off + dur
            continue
        right_start = float(out[right]["offset"])
        span = max(0.05 * len(gap), right_start - left_end)
        weights = [max(0.05, float(script[i].get("duration") or 0.2)) for i in gap]
        total_w = sum(weights) or 1.0
        cursor = left_end
        for i, weight in zip(gap, weights):
            dur = span * (weight / total_w)
            out[i] = {**out[i], "offset": round(cursor, 4), "duration": round(max(0.05, dur), 4)}
            cursor += dur
    cursor = 0.0
    for i, item in enumerate(out):
        off = max(cursor, float(item.get("offset") or 0.0))
        dur = max(0.05, float(item.get("duration") or 0.05))
        out[i] = {**item, "offset": round(off, 4), "duration": round(dur, 4)}
        cursor = off + dur
    return out


_WHISPER_MODEL = None
_WHISPER_MODEL_KEY = None


def _whisper_language(code) -> str:
    raw = str(code or "tr").strip().lower()
    aliases = {"turkish": "tr", "english": "en", "german": "de", "arabic": "ar"}
    if raw in aliases:
        return aliases[raw]
    return raw[:2] if len(raw) >= 2 else "tr"


def _transcribe_whisper_words(audio_path: str, language: str = "tr", initial_prompt: str = "") -> list:
    """openshorts decode: beam 5, VAD on, previous-text conditioning off."""
    global _WHISPER_MODEL, _WHISPER_MODEL_KEY
    from faster_whisper import WhisperModel  # type: ignore
    size = os.getenv("WHISPER_MODEL", "small")
    device = os.getenv("WHISPER_DEVICE", "cpu")
    compute = os.getenv("WHISPER_COMPUTE", "int8")
    key = (size, device, compute)
    if _WHISPER_MODEL is None or _WHISPER_MODEL_KEY != key:
        _WHISPER_MODEL = WhisperModel(size, device=device, compute_type=compute)
        _WHISPER_MODEL_KEY = key
    segments = _WHISPER_MODEL.transcribe(
        audio_path,
        language=_whisper_language(language),
        word_timestamps=True,
        beam_size=5,
        vad_filter=True,
        condition_on_previous_text=False,
        initial_prompt=initial_prompt.strip() or None,
    )[0]
    raw = []
    for seg in segments:
        for w in seg.words or []:
            raw.append({
                "text": w.word,
                "offset": float(w.start),
                "duration": max(0.05, float(w.end) - float(w.start)),
            })
    return merge_continuation_words(raw)


def align_words_whisper(timings: list, audio_path: str = None, enabled=None, language: str = None) -> list:
    """Duration lock always runs. Whisper runs only when enabled or config.WHISPER_ALIGN is true."""
    timings = list(timings or [])
    if audio_path:
        audio_dur = _probe_audio_duration_sec(audio_path)
        if audio_dur > 0 and timings:
            try:
                from services.forced_alignment import calculate_alignment_drift
                words_for_drift = [{"end": float(t.get("offset", 0.0)) + float(t.get("duration", 0.0))} for t in timings]
                drift = calculate_alignment_drift(words_for_drift, audio_dur)
                if abs(drift) > 0.15:
                    print(f"  [ForcedAlignment] FunClip drift detected ({drift:+.3f}s) -> rescaling to {audio_dur:.2f}s", flush=True)
            except Exception:
                pass
        timings = _rescale_timings_to_audio_duration(timings, audio_path)
    if enabled is None:
        enabled = getattr(config, "WHISPER_ALIGN", False)
    if not enabled or not audio_path:
        return timings
    try:
        heard = _transcribe_whisper_words(audio_path, language=language or "tr")
        snapped = snap_script_to_whisper(timings, heard)
        if snapped:
            print(f"  [Whisper] {len(snapped)} kelime senaryoya oturtuldu", flush=True)
            return snapped
    except Exception as exc:
        print(f"  [Whisper] hizalama düştü, süre ölçeği kaldı: {exc}", flush=True)
    return timings


def _clamp_word_display_durations(timings, min_d: float = 0.25, max_d: float = 0.40):
    """Item 258: Hızlı Kelime Geçişi — kelime ekranda kalma süresi 0.25–0.40s aralığında."""
    clamped = []
    for item in timings or []:
        dur = float(item.get("duration") or 0.0)
        if dur <= 0:
            dur = min_d
        dur = max(min_d, min(max_d, dur))
        clamped.append({**item, "duration": round(dur, 3)})
    return clamped


SENSEVOICE_TAG_RE = re.compile(r"<\|[^|>]+\|>")
_EMOJI_RE = re.compile(
    "["
    "\U0001F000-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U0001F1E6-\U0001F1FF"
    "\U00002B00-\U00002BFF"
    "\U0000FE0E\U0000FE0F"
    "\U0000200D"
    "\U000020E3"
    "]+"
)


def _clean_timings(timings):
    """Filters empty words, emojis, SSML leaks, and junk symbols from subtitle tokens."""
    try:
        from render.encoding_optimizer import strip_unsupported_emojis
    except Exception:
        strip_unsupported_emojis = None
    cleaned = []
    for item in timings:
        raw_text = item.get("text") if item.get("text") is not None else item.get("word", "")
        w = SENSEVOICE_TAG_RE.sub("", str(raw_text))
        if strip_unsupported_emojis is not None:
            w = strip_unsupported_emojis(w)
        if _is_ssml_junk_token(w):
            continue
        w = _EMOJI_RE.sub("", w)
        w_clean = re.sub(r'[\U00010000-\U0010ffff]', '', w)
        w_clean = re.sub(r'[\u2000-\u32ff]', '', w_clean)
        w_clean = re.sub(r'[#*_~^\\/|<>@=`~=\[\]{}]', '', w_clean).strip()
        w_clean = re.sub(r'(?i)\b(xmlns|xml:lang|speak|prosody|synthesis)\b', '', w_clean).strip()
        if _is_ssml_junk_token(w_clean) or not w_clean:
            continue
        letters = re.sub(r"[^\wÀ-ÿ]", "", w_clean, flags=re.UNICODE)
        if len(letters) < 1:
            continue
        offset = item.get("offset")
        if offset is None:
            offset = item.get("start", 0.0)
        dur = item.get("duration")
        if dur is None:
            if "end" in item and "start" in item:
                dur = max(0.05, float(item["end"]) - float(item["start"]))
            else:
                dur = 0.25
        cleaned.append({"text": w_clean, "offset": float(offset or 0.0), "duration": float(dur or 0.0)})
    return cleaned
