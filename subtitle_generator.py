"""
Karaoke subtitles — ASS (word-by-word highlight) + SRT fallback.
BOTH files are ALWAYS written to guarantee subtitles work.
Item 107: Font rotation pool (TheBoldFont, Anton, Outfit, Poppins, Montserrat, Bebas Neue).
Item 116: Drop shadow açı ve bulanıklık varyasyonu — her videoda farklı.
"""
import json
import os
import re
import config
import random
from viral_retention_engine import ViralRetentionEngine
from typing import Any, Dict, List, Optional

# ─── ITEM 107: Altyazı Yazı Tipi Rotasyonu ──────────────────────────────────
# TheBoldFont, Anton, Outfit ve Poppins arasında geçiş; asla aynı font kalmaz.
SUBTITLE_FONT_POOL = [
    "Anton",          # Çok kalın, kompakt
    "Outfit",         # Modern, temiz
    "Poppins",        # Yuvarlak, yumuşak
    "Bebas Neue",     # Sinematik, dar büyük harf
    "Montserrat",     # Klasik profesyonel
    "Oswald",         # Sıkışık başlık fontu
    "Rajdhani",       # Teknolojik görünüm
    "Barlow Condensed", # Haber tipi kompakt
]

_SESSION_FONT: str = random.choice(SUBTITLE_FONT_POOL)  # Oturum başına sabit

# ─── ITEM 116: Drop Shadow Açı Varyasyonu ────────────────────────────────
# Her video oturumunda gölgenin açısı (135°-225°) ve derinliği (1.5-3.5px) rastgele değişir.
_SESSION_SHADOW_DEPTH: float = round(random.uniform(1.5, 3.5), 1)
_SESSION_SHADOW_ANGLE: int = random.randint(135, 225)  # ASS'te Shadow açısı dolaylı (x/y offset)

# ASS'te shadow doğrudan açı değil x/y kaydırması olarak çalışır; biz ShadowX/ShadowY override kullanırız.
import math as _math
_SHADOW_RAD: float = _math.radians(_SESSION_SHADOW_ANGLE)
_SESSION_SHADOW_X: float = round(_SESSION_SHADOW_DEPTH * _math.cos(_SHADOW_RAD), 2)
_SESSION_SHADOW_Y: float = round(_SESSION_SHADOW_DEPTH * _math.sin(_SHADOW_RAD), 2)

def get_session_shadow_params() -> dict:
    """
    Item 116 – Altyazı Gölge Parametreleri.
    Her oturumda farklı açı ve derinlik döndürür.
    Returns:
        {"depth": float, "angle": int, "shadow_x": float, "shadow_y": float}
    """
    return {
        "depth": _SESSION_SHADOW_DEPTH,
        "angle": _SESSION_SHADOW_ANGLE,
        "shadow_x": _SESSION_SHADOW_X,
        "shadow_y": _SESSION_SHADOW_Y
    }

def get_session_subtitle_font(override: str = None) -> str:
    """
    Item 107 – Altyazı Yazı Tipi Rotasyonu.
    Her bot oturumunda havuzdan rastgele bir font seçer.
    override parametresiyle dışarıdan da zorlanabilir.
    """
    if override:
        return override
    return _SESSION_FONT

NAMED_COLORS = {
    "white": "FFFFFF",
    "black": "000000",
    "yellow": "00D7FF",
    "red": "0000FF",
    "blue": "FF0000",
    "green": "00FF00",
    "gold": "00D7FF",
}

# Item 230: Önemli sıfatlar neon kırmızı/altın vurgu
POWER_WORD_HIGHLIGHTS = {
    "ölümcül": "#FF3333", "deadly": "#FF3333",
    "milyarder": "#FFD700", "billionaire": "#FFD700",
    "gizemli": "#FF3333", "mysterious": "#FF3333",
    "tehlikeli": "#FF3333", "dangerous": "#FF3333",
    "şok": "#FFD700", "shocking": "#FFD700",
}

# One definition for the studio cards and the ASS/ffmpeg burn-in.
# static/js/subtitle-style-tokens.json is that file. Cards, simulator, and
# create_karaoke_subtitles all read it. Do not keep a second palette.
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


def ffmpeg_force_style_from_opts(opts: dict = None, play_h: int = None) -> str:
    """SRT fallback uses the same color, weight, stroke, box, size, and margin as the ASS style."""
    opts = opts or {}
    if play_h is None:
        play_h = int(getattr(config, "get_target_resolution", lambda: (1080, 1920))()[1])
    font_size = int(opts.get("font_size") or getattr(config, "SUBTITLE_FONT_SIZE", 54))
    font_name = opts.get("font_name") or "Anton"
    bold = -1 if opts.get("bold", True) else 0
    primary = hex_to_ass_color(opts.get("color") or "#FFFFFF")
    outline = hex_to_ass_color(opts.get("stroke_color") or "#000000", default_black=True)
    border = 3 if opts.get("box") else 1
    if opts.get("box"):
        back = hex_to_ass_color(opts.get("box_color") or "#000000")
    else:
        back = "&HFF000000&"
    outline_w = 0 if int(opts.get("stroke_width") or 0) <= 0 else int(opts.get("stroke_width"))
    y_pos = opts.get("y_position")
    if y_pos is None:
        margin_v = int(round(0.2 * play_h))
    else:
        margin_v = int(round((1.0 - float(y_pos)) * play_h))
    return (
        f"FontSize={font_size},FontName={font_name},Bold={bold},"
        f"PrimaryColour={primary},OutlineColour={outline},Outline={outline_w},"
        f"BackColour={back},BorderStyle={border},Alignment=2,MarginV={margin_v}"
    )


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


# Item 310: A/B subtitle style name → preset key
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

def hex_to_ass_color(val, alpha="00", default_black=False):
    """Converts hex color or named color to ASS format &HAABBGGRR&."""
    val_str = str(val).strip().lstrip('#').lower()
    if val_str in NAMED_COLORS:
        val_str = NAMED_COLORS[val_str]
    if len(val_str) == 6:
        r, g, b = val_str[0:2], val_str[2:4], val_str[4:6]
        return f"&H{alpha}{b}{g}{r}&".upper()
    return f"&H{alpha}000000&".upper() if default_black else f"&H{alpha}FFFFFF&".upper()

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
    # Bare attribute crumbs: version="1.0" xml:lang="tr-TR"
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
    scaled = []
    for item in timings:
        scaled.append({
            **item,
            "offset": round(float(item.get("offset", 0.0)) * scale, 4),
            "duration": round(float(item.get("duration", 0.0)) * scale, 4),
        })
    return scaled


def _rescale_timings_to_audio_duration(timings: list, audio_path: str) -> list:
    """
    Lock word spans to the narration file.
    A short tail is silence: stretch only the last word (agnes cue clamp).
    A large gap is clock drift: scale every word by AudioDuration / LastWordEnd.
    Words that run past the file clamp the last end. They are not compressed
    unless the last word already starts after the file.
    """
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
        out[-1] = {
            **out[-1],
            "duration": round(float(out[-1].get("duration", 0.0)) + delta, 4),
        }
        return out
    return _scale_timings(timings, audio_dur / span_end)


def _norm_word(text: str) -> str:
    return re.sub(r"[^\wÀ-ÿ]", "", str(text or ""), flags=re.UNICODE).casefold()


def merge_continuation_words(words: list) -> list:
    """
    openshorts: a token without a leading space is a fragment of the previous word.
    Strip only after the merge, or "-Kanal" becomes its own karaoke token.
    """
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
    """
    Keep the narration words. Copy Whisper times onto matching tokens.
    youtube-shorts-pipeline replaces the script with the transcript. A Turkish
    miss then burns the wrong word. Unmatched gaps are split between anchors.
    Returns [] when fewer than 55% of script words match.
    """
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
            out.append({
                **item,
                "offset": round(float(w["offset"]), 4),
                "duration": round(float(w["duration"]), 4),
            })
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


def _transcribe_whisper_words(audio_path: str, language: str = "tr") -> list:
    """
    openshorts decode: beam 5, VAD on, previous-text conditioning off.
    Model stays cached. Continuation fragments are merged before strip.
    """
    global _WHISPER_MODEL, _WHISPER_MODEL_KEY
    from faster_whisper import WhisperModel  # type: ignore
    size = os.getenv("WHISPER_MODEL", "small")
    device = os.getenv("WHISPER_DEVICE", "cpu")
    compute = os.getenv("WHISPER_COMPUTE", "int8")
    key = (size, device, compute)
    if _WHISPER_MODEL is None or _WHISPER_MODEL_KEY != key:
        _WHISPER_MODEL = WhisperModel(size, device=device, compute_type=compute)
        _WHISPER_MODEL_KEY = key
    segments, _info = _WHISPER_MODEL.transcribe(
        audio_path,
        language=_whisper_language(language),
        word_timestamps=True,
        beam_size=5,
        vad_filter=True,
        condition_on_previous_text=False,
    )
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
    """
    Duration lock always runs. Whisper runs only when enabled is true, or when
    enabled is omitted and config.WHISPER_ALIGN is true.
    A match keeps the script text and takes Whisper times. A weak match keeps
    the scaled Edge or estimated times.
    """
    timings = list(timings or [])
    if audio_path:
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
    """
    Item 258: Hızlı Kelime Geçişi — kelime ekranda kalma süresi 0.25–0.40s aralığında.
    """
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
    cleaned = []
    for item in timings:
        raw_text = item.get("text") if item.get("text") is not None else item.get("word", "")
        w = SENSEVOICE_TAG_RE.sub("", str(raw_text))
        if _is_ssml_junk_token(w):
            continue
        w = _EMOJI_RE.sub("", w)
        # Remove emojis and odd symbols
        w_clean = re.sub(r'[\U00010000-\U0010ffff]', '', w)
        w_clean = re.sub(r'[\u2000-\u32ff]', '', w_clean)
        w_clean = re.sub(r'[#*_~^\\/|<>@=`~=\[\]{}]', '', w_clean).strip()
        w_clean = re.sub(r'(?i)\b(xmlns|xml:lang|speak|prosody|synthesis)\b', '', w_clean).strip()
        if _is_ssml_junk_token(w_clean) or not w_clean:
            continue
        # Drop tokens that are mostly punctuation / markup debris
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
        cleaned.append({
            "text": w_clean,
            "offset": float(offset or 0.0),
            "duration": float(dur or 0.0)
        })
    return cleaned

def _resolve_subtitle_layout(opts, target_w, target_h):
    """Items 206 & 265: safe zone margins + max words per frame.

    Human-craft karaoke_mid_frame: allow center Y (Shorts UI covers bottom —
    mute viewers read mid captions). When opts.human_craft / allow_mid_frame,
    do not force bottom_ui_margin.
    """
    safe = ViralRetentionEngine.get_subtitles_safe_zone(
        screen_height=target_h, screen_width=target_w
    )
    max_words = int(
        opts.get("words_per_page")
        or opts.get("max_words_per_line")
        or opts.get("max_words_per_frame")
        or safe.get("max_words_per_frame", 4)
    )
    max_words = max(2, min(5, max_words))
    bottom_margin = safe["bottom_ui_margin"]

    has_arabic = bool(opts.get("arabic_overlays"))
    mid_ok = bool(opts.get("human_craft") or opts.get("allow_mid_frame") or has_arabic)

    y_pos = opts.get("y_position")
    if y_pos is None:
        if has_arabic:
            y_pos = 0.56
        else:
            y_pos = 1.0 - (bottom_margin / target_h)
    y_pos = max(0.1, min(0.9, float(y_pos)))

    margin_v = int(round((1.0 - y_pos) * target_h))
    # Lab slider sets honor_y_position. Safe-zone floor must not move that margin.
    if not mid_ok and not opts.get("honor_y_position"):
        margin_v = max(margin_v, bottom_margin)
    return max_words, margin_v


def _format_word(text, uppercase=False):
    return text.upper() if uppercase else text


def _active_word_tags(highlight_ass, primary_ass, glow=False, word: str = "", bounce: bool = True, allow_power: bool = True):
    """Item 91: karaoke highlight + micro-pulse; Item 230 neon power-word colors; MoneyPrinter bounce/pop."""
    glow_tags = r"\blur3\shad2\be1" if glow else ""
    word_key = (word or "").strip().lower().strip(".,!?;:")
    power_hex = POWER_WORD_HIGHLIGHTS.get(word_key) if allow_power else None
    active_color = hex_to_ass_color(power_hex) if power_hex else highlight_ass
    if power_hex and glow:
        glow_tags = r"\blur4\shad3\be2"
    bounce_tag = r"\t(0,70,\fscx115\fscy115)\t(70,140,\fscx106\fscy106)" if bounce else ""
    open_tag = "{" + rf"\c{active_color}\b1\fscx106\fscy106" + bounce_tag + glow_tags + "}"
    # Restore the event style, including weight, glow, shadow and animations.
    # Merely restoring color/scale lets blur and transforms affect later words.
    close_tag = "{" + rf"\r\c{primary_ass}\fscx100\fscy100" + "}"
    return open_tag, close_tag


def create_karaoke_subtitles(timings, path, max_dur=9999.0, style_opts=None):
    opts = style_opts or {}
    timings = _clean_timings(timings or [])
    timings = align_words_whisper(
        timings,
        audio_path=opts.get("audio_path"),
        enabled=opts.get("whisper_align"),
        language=opts.get("language"),
    )
    if opts.get("clamp_word_durations", False):
        timings = _clamp_word_display_durations(timings)
    else:
        # Guarantee valid positive duration without artificially truncating natural speech
        timings = [
            {**t, "duration": max(0.10, float(t.get("duration") or 0.25))}
            for t in timings
        ]
    target_w = int(opts.get("video_width") or getattr(config, "VIDEO_WIDTH", 1080))
    target_h = int(opts.get("video_height") or getattr(config, "VIDEO_HEIGHT", 1920))
    if not timings:
        with open(path, "w", encoding="utf-8") as f:
            f.write(
                "[Script Info]\n"
                "ScriptType: v4.00+\n"
                f"PlayResX: {target_w}\n"
                f"PlayResY: {target_h}\n\n"
                "[V4+ Styles]\n"
                "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n\n"
                "[Events]\n"
                "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
            )
        return path

    font_size = opts.get("font_size", getattr(config, "SUBTITLE_FONT_SIZE", 54))
    primary_hex = opts.get("color", getattr(config, "SUBTITLE_COLOR", "#FFFFFF"))
    highlight_hex = opts.get("highlight_color", getattr(config, "SUBTITLE_HIGHLIGHT_COLOR", "#FFD700"))
    stroke_hex = opts.get("stroke_color", getattr(config, "SUBTITLE_STROKE_COLOR", "#000000"))
    stroke_width = opts.get("stroke_width", getattr(config, "SUBTITLE_STROKE_WIDTH", 4))
    uppercase = opts.get("uppercase", False)
    glow = opts.get("glow", False)
    bounce = opts.get("bounce", True)
    # Item 107: preset font_name overrides session rotation
    font_name = opts.get("font_name") or get_session_subtitle_font()
    # Card tokens own the shadow. A random session offset would not match the lab card.
    if "shadow_depth" in opts and opts.get("shadow_depth") is not None:
        shadow_depth = float(opts["shadow_depth"])
    else:
        shadow_depth = 0.0
    shadow_prefix = ""
    if opts.get("shadow_angle") is not None and shadow_depth > 0:
        shadow_angle = int(opts["shadow_angle"])
        _rad = _math.radians(shadow_angle)
        shadow_x = round(shadow_depth * _math.cos(_rad), 2)
        shadow_y = round(shadow_depth * _math.sin(_rad), 2)
        shadow_prefix = f"{{\\xshad{shadow_x}\\yshad{shadow_y}}}"
        print(f"  [Item 116] Drop shadow: açı={shadow_angle}°, derinlik={shadow_depth}px")
    print(f"  [Item 107] Altyazı fontu: {font_name}")

    # Target resolution scaling (1080p, 720p, 540p)
    target_w, target_h = getattr(config, "get_target_resolution", lambda: (config.VIDEO_WIDTH, config.VIDEO_HEIGHT))()
    scale_factor = target_h / 1920.0
    scaled_font_size = max(18, int(font_size * scale_factor))
    if int(stroke_width) <= 0:
        scaled_stroke_width = 0
    else:
        scaled_stroke_width = max(1, int(float(stroke_width) * scale_factor))
    if shadow_depth <= 0:
        scaled_shadow_depth = 0
    else:
        scaled_shadow_depth = max(1, int(shadow_depth * scale_factor))
    border_style = 3 if opts.get("box") else 1
    if opts.get("box"):
        back_colour = hex_to_ass_color(opts.get("box_color") or "#000000")
    else:
        back_colour = "&HFF000000&"
    bold_flag = -1 if opts.get("bold", True) else 0
    max_words, margin_v = _resolve_subtitle_layout(opts, target_w, target_h)

    primary_ass = hex_to_ass_color(primary_hex)
    highlight_ass = hex_to_ass_color(highlight_hex)
    stroke_ass = hex_to_ass_color(stroke_hex, default_black=True)

    arabic_overlays = opts.get("arabic_overlays") or []
    extra_styles = ""
    if arabic_overlays:
        scaled_ar_size = max(24, int(54 * scale_factor))
        scaled_cit_size = max(16, int(28 * scale_factor))
        scaled_cit_stroke = max(1, int(2 * scale_factor))
        margin_ar_top = max(40, int(170 * scale_factor))
        margin_cit_bot = max(24, int(90 * scale_factor))
        gold_shadow = "&H0000D7FF"
        extra_styles = (
            f"\nStyle: ArabicTop,Segoe UI,{scaled_ar_size},&H00FFFFFF,&H0000D7FF,&H00000000,{gold_shadow},-1,0,0,0,100,100,0,0,1,{scaled_stroke_width},{scaled_shadow_depth},8,30,30,{margin_ar_top},1\n"
            f"Style: CitationBottom,Outfit,{scaled_cit_size},&H00E8E8E8,&H0000D7FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,{scaled_cit_stroke},1,2,30,30,{margin_cit_bot},1"
        )

    ass_header = f"""[Script Info]
Title: Karaoke Subtitles
ScriptType: v4.00+
PlayResX: {target_w}
PlayResY: {target_h}
ScaledBorderAndShadow: yes
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: K,{font_name},{scaled_font_size},{primary_ass},{highlight_ass},{stroke_ass},{back_colour},{bold_flag},0,0,0,100,100,2,0,{border_style},{scaled_stroke_width},{scaled_shadow_depth},2,40,40,{margin_v},1{extra_styles}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    groups = _group(
        timings, max_words,
        break_on_punctuation=not bool(opts.get("words_per_page")),
        max_gap=1.2,
    )
    events = []

    # Emit multi-layer Arabic header + bottom citation overlays (Layer 1)
    if arabic_overlays:
        for it in arabic_overlays:
            st = max(0.0, float(it.get("start", 0.0)))
            en = min(max_dur, float(it.get("end", st + 3.0)))
            if en <= st:
                en = st + 3.0
            if st >= max_dur:
                continue
            ar = (it.get("arabic_text") or "").strip()
            cit = (it.get("source_citation") or "").strip()
            if ar:
                events.append(f"Dialogue: 1,{_at(st)},{_at(en)},ArabicTop,,0,0,0,,{{\\fad(250,200)}}{ar}")
            if cit:
                events.append(f"Dialogue: 1,{_at(st)},{_at(en)},CitationBottom,,0,0,0,,{{\\fad(250,200)}}{cit}")

    for gi, g in enumerate(groups):
        if g[0]["offset"] >= max_dur: break
        next_group_start = groups[gi + 1][0]["offset"] if gi + 1 < len(groups) else max_dur

        if opts.get("double_outline"):
            plain = " ".join(_format_word(w["text"], uppercase) for w in g)
            outer = scaled_stroke_width + max(2, int(3 * scale_factor))
            gs = float(g[0]["offset"])
            ge = min(max_dur, float(g[-1]["offset"]) + float(g[-1].get("duration") or 0.3))
            if ge > gs and plain:
                events.append(
                    f"Dialogue: 0,{_at(gs)},{_at(ge)},K,,0,0,0,,"
                    f"{{\\bord{outer}\\shad0\\1a&HFF&\\3c&H000000&}}{plain}"
                )

        for wi, active in enumerate(g):
            ws = active["offset"]
            if ws >= max_dur: break

            # Word highlight end time:
            # Seamless transition to next word in group without gap or flicker
            if wi + 1 < len(g):
                next_ws = g[wi + 1]["offset"]
                if next_ws > ws:
                    if next_ws - ws <= 1.2:
                        we = next_ws
                    else:
                        we = min(next_ws, ws + max(float(active.get("duration", 0.3)), 0.35))
                else:
                    we = ws + max(0.15, float(active.get("duration", 0.3)))
            else:
                # Last word in the group
                natural_end = ws + max(0.20, float(active.get("duration", 0.3)))
                if next_group_start > natural_end and (next_group_start - natural_end) < 0.35:
                    we = min(next_group_start, natural_end + 0.25)
                else:
                    we = min(natural_end, next_group_start)

            we = min(we, max_dur, next_group_start)
            # ASS has centisecond precision. Never extend a short cue into the
            # next word/page or beyond the video just to meet a display floor.
            if round(we * 100) <= round(ws * 100):
                continue
            parts = []
            for wj, w in enumerate(g):
                word = _format_word(w["text"], uppercase)
                if wj == wi:
                    open_tag, close_tag = _active_word_tags(
                        highlight_ass, primary_ass, glow=glow, word=w["text"], bounce=bounce,
                        allow_power=bool(opts.get("power_word_colors", False)),
                    )
                    parts.append(open_tag + word + close_tag + shadow_prefix)
                else:
                    parts.append(word)
            events.append(f"Dialogue: 0,{_at(ws)},{_at(we)},K,,0,0,0,,{shadow_prefix}{' '.join(parts)}")
    # Plan Item P6: Speech subtitles stay clean; dedicated emphasis overlays go to emphasis.ass
    if opts.get("embed_legacy_emphasis", False):
        events.extend(_emphasis_overlay_events(groups, scaled_font_size, target_w, target_h, uppercase, max_dur))
    with open(path, "w", encoding="utf-8") as f:
        f.write(ass_header + "\n".join(events) + "\n")
    print(f"  [Subs] Karaoke ASS (Vector Engine Item 94): {len(events)} events (Highlight: {highlight_hex} Item 91)")
    return path

def create_srt_file(timings, path, max_dur=9999.0, audio_path: str = None):
    timings = _clean_timings(timings or [])
    timings = align_words_whisper(timings, audio_path=audio_path)
    if not timings:
        open(path, "w").close()
        return path
    groups = _group(timings, 4)
    lines, idx = [], 1
    for gi, g in enumerate(groups):
        s = g[0]["offset"]
        if s >= max_dur: break
        last_dur = max(0.20, float(g[-1].get("duration") or 0.3))
        natural_end = g[-1]["offset"] + last_dur
        if gi + 1 < len(groups):
            next_start = groups[gi + 1][0]["offset"]
            if next_start > s and (next_start - natural_end) < 0.35:
                e = min(next_start, natural_end + 0.25)
            else:
                e = min(natural_end, next_start)
        else:
            e = natural_end
        e = min(e, max_dur)
        if e - s < 0.2: e = s + 0.3
        lines += [str(idx), f"{_st(s)} --> {_st(e)}", " ".join(w["text"] for w in g), ""]
        idx += 1
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  [Subs] SRT: {idx-1} lines")
    return path

def _at(s):
    total_cs = max(0, int(round(float(s) * 100)))
    cs = total_cs % 100
    total_s = total_cs // 100
    sec = total_s % 60
    total_m = total_s // 60
    minute = total_m % 60
    hour = total_m // 60
    return f"{hour}:{minute:02d}:{sec:02d}.{cs:02d}"

def _st(s):
    total_ms = max(0, int(round(float(s) * 1000)))
    ms = total_ms % 1000
    total_s = total_ms // 1000
    sec = total_s % 60
    total_m = total_s // 60
    minute = total_m % 60
    hour = total_m // 60
    return f"{hour:02d}:{minute:02d}:{sec:02d},{ms:03d}"
def split_subtitle_pages_on_silence(
    timings: list,
    max_words_per_page: int = 4,
    *,
    break_on_punctuation: bool = True,
    silence_threshold_sec: float = 0.350,
) -> list:
    """
    Bolum 2.1 (Madde 7) ve Bolum 28.7 (saard00_shorts_generator pattern):
    Altyazi satirlarini ses dalgasinda sessizlik ve duraksama (silence >= 300-350ms)
    noktalarinda otomatik boler. Konusma nefes aralarinda ekranda donuk altyazi kalmasini onler.
    """
    return _group(
        timings,
        max_words_per_page,
        break_on_punctuation=break_on_punctuation,
        max_gap=silence_threshold_sec,
    )


def _group(t, n, *, break_on_punctuation=True, max_gap=0.350):
    gs, c = [], []
    for w in t:
        if c and max_gap is not None:
            previous_end = float(c[-1]["offset"]) + float(c[-1].get("duration") or 0.0)
            if float(w["offset"]) - previous_end >= max_gap:
                gs.append(c)
                c = []
        c.append(w)
        if len(c) >= n or (break_on_punctuation and w["text"].strip() and w["text"].strip()[-1] in ".!?,;:"):
            gs.append(c)
            c = []
    if c:
        gs.append(c)
    return gs



def _emphasis_overlay_events(groups, font_size, target_w, target_h, uppercase, max_dur):
    """
    video-autopilot-kit build_emphasis_overlay_ass puts numbers and proof
    words on a second layer with a budget. Spoken karaoke lines stay. Cap is
    3 so a digit-heavy script cannot cover the frame.
    """
    extra = []
    budget = 3
    pos_x = max(1, int(target_w) // 2)
    pos_y = max(1, int(float(target_h) * 0.18))
    big = max(int(font_size) + 8, int(float(font_size) * 1.65))
    for group in groups:
        for word in group:
            if len(extra) >= budget:
                return extra
            raw = str(word.get("text") or "").strip()
            key = raw.lower().strip(".,!?;:")
            if key not in POWER_WORD_HIGHLIGHTS and not re.search(r"\d", raw):
                continue
            start = float(word.get("offset") or 0.0)
            if start >= max_dur:
                continue
            end = min(max_dur, start + min(1.2, max(0.6, float(word.get("duration") or 0.8))))
            if end - start < 0.2:
                end = start + 0.4
            shown = _format_word(raw, uppercase)
            extra.append(
                f"Dialogue: 1,{_at(start)},{_at(end)},K,,0,0,0,,"
                f"{{\\an8\\pos({pos_x},{pos_y})\\fs{big}\\b1}}{shown}"
            )
    return extra



def create_emphasis_overlay_ass(
    timings: List[Dict[str, Any]],
    path: str,
    target_w: int = 1080,
    target_h: int = 1920,
    font_name: str = "Arial Black",
    font_size: int = 110,
    max_dur: float = 9999.0,
    budget: int = 3,
    uppercase: bool = True,
) -> Optional[str]:
    """
    Master Plan Section 33.3 P6 (adapted from video-autopilot-kit build_emphasis_overlay_ass):
    Generates a dedicated secondary emphasis.ass overlay file.
    - Capped at `budget` (max 3 items per video).
    - Duration contract: 0.8s - 1.4s per emphasis item.
    - Content: numbers (digits/percents/currencies) or power keywords.
    - Position: Upper safe-zone above spoken subtitles (an5, Y=0.36*H).
    - Pop/bounce kinetic typography with gold/neon accent.
    Returns path if at least one emphasis item is generated, else None.
    """
    clean = _clean_timings(timings or [])
    if not clean:
        return None
    # P6 is a hard video-level budget. Callers may not raise it through the
    # optional argument, and zero explicitly disables the secondary layer.
    budget = max(0, min(3, int(budget)))
    if budget == 0:
        return None

    try:
        from voice.script_humanizer import EMPHASIS_KEYWORDS_TR, EMPHASIS_KEYWORDS_EN
        global_emphasis = {k.casefold() for k in EMPHASIS_KEYWORDS_TR} | {k.casefold() for k in EMPHASIS_KEYWORDS_EN}
    except Exception:
        global_emphasis = set()

    pos_x = max(1, int(target_w) // 2)
    pos_y = max(1, int(float(target_h) * 0.36))
    fs = max(70, int(font_size))

    header = (
        "[Script Info]\n"
        "Title: ShortsAI Emphasis Overlay (P6)\n"
        "ScriptType: v4.00+\n"
        f"PlayResX: {target_w}\n"
        f"PlayResY: {target_h}\n"
        "WrapStyle: 2\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: EMPHASIS,{font_name},{fs},&H0000D7FF,&H000000FF,&H00101014,&H60000000,"
        "-1,0,0,0,100,100,1,0,1,10,6,5,40,40,0,1\n\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )

    candidates = []
    for word in clean:
        raw = str(word.get("text") or "").strip()
        clean_word = raw.lower().strip(".,!?;:\"'()[]{}*#-")
        is_number = bool(re.search(r"\d", raw))
        is_power = (
            clean_word in POWER_WORD_HIGHLIGHTS
            or clean_word in global_emphasis
            or clean_word in {"asla", "dikkat", "şok", "gerçek", "sır", "hata", "tehlike", "yalan", "kanıt", "kural"}
        )
        if not is_number and not is_power:
            continue
        start = float(word.get("offset") or 0.0)
        if start >= max_dur:
            continue
        raw_dur = float(word.get("duration") or 1.0)
        dur = max(0.8, min(1.4, raw_dur))
        end = min(max_dur, start + dur)
        if end <= start:
            continue
        priority = 6 if is_number else 4
        candidates.append({
            "start": start,
            "end": end,
            "text": _format_word(raw, uppercase),
            "priority": priority,
            "is_number": is_number,
        })

    # Sort candidates by priority and then start time
    selected = []
    for cand in sorted(candidates, key=lambda c: (-c["priority"], c["start"])):
        if any(abs(cand["start"] - s["start"]) < 2.0 for s in selected):
            continue
        selected.append(cand)
        if len(selected) >= budget:
            break

    if not selected:
        return None

    selected.sort(key=lambda c: c["start"])
    events = []
    for c in selected:
        start_ts = _at(c["start"])
        end_ts = _at(c["end"])
        text = c["text"]
        accent = "&H0000D7FF&" if c["is_number"] else "&H0000E5FF&"
        pop_fx = (
            "{\\an5\\pos(%d,%d)\\fad(60,100)\\fscx75\\fscy75"
            "\\t(0,120,\\fscx118\\fscy118)\\t(120,240,\\fscx100\\fscy100)\\c%s}" % (pos_x, pos_y, accent)
        )
        events.append(f"Dialogue: 0,{start_ts},{end_ts},EMPHASIS,,0,0,0,,{pop_fx}{text}")

    with open(path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events) + "\n")
    return path
