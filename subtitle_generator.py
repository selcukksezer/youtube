"""
Karaoke subtitles — ASS (word-by-word highlight) + SRT fallback.
BOTH files are ALWAYS written to guarantee subtitles work.
Item 107: Font rotation pool (TheBoldFont, Anton, Outfit, Poppins, Montserrat, Bebas Neue).
Item 116: Drop shadow açı ve bulanıklık varyasyonu — her videoda farklı.
"""
import os
import re
import config
import random
from viral_retention_engine import ViralRetentionEngine

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

# Item 43: Predefined professional subtitle presets
SUBTITLE_PRESETS = {
    "capcut_yellow": {
        "color": "#FFFFFF",
        "highlight_color": "#FFD700",
        "stroke_color": "#000000",
        "stroke_width": 4,
        "font_size": 56,
        "font_name": "Anton",
        "uppercase": True,
        "glow": True,
        "y_position": 0.75,
    },
    "cyber_green": {
        "color": "#FFFFFF",
        "highlight_color": "#00FF66",
        "stroke_color": "#051A0A",
        "stroke_width": 4,
        "font_size": 54,
        "font_name": "Bebas Neue",
        "uppercase": True,
        "glow": True,
        "y_position": 0.75,
    },
    "red_fire": {
        "color": "#FFFFFF",
        "highlight_color": "#FF3333",
        "stroke_color": "#1A0000",
        "stroke_width": 4,
        "font_size": 56,
        "font_name": "Anton",
        "uppercase": True,
        "glow": True,
        "y_position": 0.75,
    },
    "clean_white": {
        "color": "#F0F0F0",
        "highlight_color": "#00D4FF",
        "stroke_color": "#000000",
        "stroke_width": 3,
        "font_size": 52,
        "font_name": "Montserrat",
        "uppercase": True,
        "glow": True,
        "y_position": 0.75,
    },
    "high_contrast_retention": {
        "color": "#FFFFFF",
        "highlight_color": "#FFFF00",
        "stroke_color": "#000000",
        "stroke_width": 5,
        "font_size": 58,
        "font_name": "Anton",
        "uppercase": True,
        "glow": True,
        "y_position": 0.72,
    },
}

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


def _rescale_timings_to_audio_duration(timings: list, audio_path: str) -> list:
    """Item 184/413: lock karaoke word spans to narration audio duration."""
    if not timings or not audio_path:
        return timings or []
    audio_dur = _probe_audio_duration_sec(audio_path)
    if audio_dur <= 0:
        return timings
    last = timings[-1]
    span_end = float(last.get("offset", 0.0)) + float(last.get("duration", 0.0))
    if span_end <= 0.05 or abs(span_end - audio_dur) < 0.08:
        return timings
    scale = audio_dur / span_end
    scaled = []
    for item in timings:
        scaled.append({
            **item,
            "offset": round(float(item.get("offset", 0.0)) * scale, 4),
            "duration": round(float(item.get("duration", 0.0)) * scale, 4),
        })
    return scaled


def align_words_whisper(timings: list, audio_path: str = None) -> list:
    """
    Item 413: Whisper word-level alignment + ffmpeg duration lock.
    WHISPER_ALIGN=false: duration rescale only (default path, Item 184 sync).
    WHISPER_ALIGN=true: faster-whisper when installed, else duration rescale.
    """
    timings = list(timings or [])
    if audio_path:
        timings = _rescale_timings_to_audio_duration(timings, audio_path)
    if not getattr(config, "WHISPER_ALIGN", False):
        return timings
    try:
        from faster_whisper import WhisperModel  # type: ignore
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        segments, _ = model.transcribe(audio_path, word_timestamps=True)
        whisper_words = []
        for seg in segments:
            for w in seg.words or []:
                whisper_words.append({
                    "text": w.word.strip(),
                    "offset": round(float(w.start), 4),
                    "duration": round(max(0.05, float(w.end) - float(w.start)), 4),
                })
        if whisper_words:
            return whisper_words
    except Exception:
        pass
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


def _clean_timings(timings):
    """Filters empty words, emojis, SSML leaks, and junk symbols from subtitle tokens."""
    cleaned = []
    for item in timings:
        w = item.get("text", "")
        if _is_ssml_junk_token(w):
            continue
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
        cleaned.append({
            "text": w_clean,
            "offset": item.get("offset", 0.0),
            "duration": item.get("duration", 0.0)
        })
    return cleaned

def _resolve_subtitle_layout(opts, target_w, target_h):
    """Items 206 & 265: safe zone margins + max words per frame."""
    safe = ViralRetentionEngine.get_subtitles_safe_zone(
        screen_height=target_h, screen_width=target_w
    )
    max_words = safe.get("max_words_per_frame", 4)
    bottom_margin = safe["bottom_ui_margin"]

    y_pos = opts.get("y_position")
    if y_pos is None:
        y_pos = 1.0 - (bottom_margin / target_h)  # default: top of safe bottom zone (~0.75)
    y_pos = max(0.1, min(0.9, float(y_pos)))

    margin_v = int((1.0 - y_pos) * target_h)
    margin_v = max(margin_v, bottom_margin)  # enforce bottom 25% UI margin
    return max_words, margin_v


def _format_word(text, uppercase=False):
    return text.upper() if uppercase else text


def _active_word_tags(highlight_ass, primary_ass, glow=False, word: str = ""):
    """Item 91: karaoke highlight + micro-pulse; Item 230 neon power-word colors."""
    glow_tags = r"\blur3\shad2\be1" if glow else ""
    word_key = (word or "").strip().lower().strip(".,!?;:")
    power_hex = POWER_WORD_HIGHLIGHTS.get(word_key)
    active_color = hex_to_ass_color(power_hex) if power_hex else highlight_ass
    if power_hex and glow:
        glow_tags = r"\blur4\shad3\be2"
    open_tag = "{" + rf"\c{active_color}\b1\fscx106\fscy106" + glow_tags + "}"
    close_tag = "{" + rf"\c{primary_ass}\b0\fscx100\fscy100" + "}"
    return open_tag, close_tag


def create_karaoke_subtitles(timings, path, max_dur=9999.0, style_opts=None):
    opts = style_opts or {}
    timings = _clean_timings(timings or [])
    timings = align_words_whisper(timings, audio_path=opts.get("audio_path"))
    timings = _clamp_word_display_durations(timings)
    if not timings:
        open(path, "w").close()
        return path

    font_size = opts.get("font_size", getattr(config, "SUBTITLE_FONT_SIZE", 54))
    primary_hex = opts.get("color", getattr(config, "SUBTITLE_COLOR", "#FFFFFF"))
    highlight_hex = opts.get("highlight_color", getattr(config, "SUBTITLE_HIGHLIGHT_COLOR", "#FFD700"))
    stroke_hex = opts.get("stroke_color", getattr(config, "SUBTITLE_STROKE_COLOR", "#000000"))
    stroke_width = opts.get("stroke_width", getattr(config, "SUBTITLE_STROKE_WIDTH", 4))
    uppercase = opts.get("uppercase", False)
    glow = opts.get("glow", False)
    # Item 107: preset font_name overrides session rotation
    font_name = opts.get("font_name") or get_session_subtitle_font()
    # Item 116: Drop Shadow açı ve derinlik varyasyonu
    shadow_params = get_session_shadow_params()
    shadow_depth = opts.get("shadow_depth", shadow_params["depth"])
    print(f"  [Item 107] Altyazı fontu: {font_name}")
    print(f"  [Item 116] Drop shadow: açı={shadow_params['angle']}°, derinlik={shadow_depth}px")

    # Target resolution scaling (1080p, 720p, 540p)
    target_w, target_h = getattr(config, "get_target_resolution", lambda: (config.VIDEO_WIDTH, config.VIDEO_HEIGHT))()
    scale_factor = target_h / 1920.0
    scaled_font_size = max(18, int(font_size * scale_factor))
    scaled_stroke_width = max(1, int(stroke_width * scale_factor))
    scaled_shadow_depth = max(1, int(shadow_depth * scale_factor))
    max_words, margin_v = _resolve_subtitle_layout(opts, target_w, target_h)

    primary_ass = hex_to_ass_color(primary_hex)
    highlight_ass = hex_to_ass_color(highlight_hex)
    stroke_ass = hex_to_ass_color(stroke_hex, default_black=True)

    ass_header = f"""[Script Info]
Title: Karaoke Subtitles
ScriptType: v4.00+
PlayResX: {target_w}
PlayResY: {target_h}
ScaledBorderAndShadow: yes
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: K,{font_name},{scaled_font_size},{primary_ass},{highlight_ass},{stroke_ass},&H80000000,-1,0,0,0,100,100,2,0,3,{scaled_stroke_width},{scaled_shadow_depth},2,2,40,40,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    groups = _group(timings, max_words)
    events = []
    for g in groups:
        if g[0]["offset"] >= max_dur: break
        for wi, active in enumerate(g):
            ws, we = active["offset"], active["offset"] + active["duration"]
            if ws >= max_dur: break
            we = min(we, max_dur)
            if we - ws < 0.1: we = ws + 0.15
            parts = []
            for wj, w in enumerate(g):
                word = _format_word(w["text"], uppercase)
                if wj == wi:
                    open_tag, close_tag = _active_word_tags(
                        highlight_ass, primary_ass, glow=glow, word=w["text"]
                    )
                    parts.append(open_tag + word + close_tag)
                else:
                    parts.append(word)
            events.append(f"Dialogue: 0,{_at(ws)},{_at(we)},K,,0,0,0,,{' '.join(parts)}")
    with open(path, "w", encoding="utf-8") as f:
        f.write(ass_header + "\n".join(events) + "\n")
    print(f"  [Subs] Karaoke ASS (Vector Engine Item 94): {len(events)} events (Highlight: {highlight_hex} Item 91)")
    return path

def create_srt_file(timings, path, max_dur=9999.0, audio_path: str = None):
    timings = _clean_timings(timings or [])
    timings = align_words_whisper(timings, audio_path=audio_path)
    timings = _clamp_word_display_durations(timings)
    if not timings:
        open(path, "w").close()
        return path
    groups = _group(timings, 4)
    lines, idx = [], 1
    for g in groups:
        s, e = g[0]["offset"], g[-1]["offset"] + g[-1]["duration"]
        if s >= max_dur: break
        e = min(e, max_dur)
        if e - s < 0.2: e = s + 0.3
        lines += [str(idx), f"{_st(s)} --> {_st(e)}", " ".join(w["text"] for w in g), ""]
        idx += 1
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  [Subs] SRT: {idx-1} lines")
    return path

def _at(s):
    return f"{int(s//3600)}:{int(s%3600//60):02d}:{int(s%60):02d}.{int(s%1*100):02d}"
def _st(s):
    return f"{int(s//3600):02d}:{int(s%3600//60):02d}:{int(s%60):02d},{int(s%1*1000):03d}"
def _group(t, n):
    gs, c = [], []
    for w in t:
        c.append(w)
        if len(c) >= n or (w["text"].strip() and w["text"].strip()[-1] in ".!?,;:"):
            gs.append(c); c = []
    if c: gs.append(c)
    return gs

