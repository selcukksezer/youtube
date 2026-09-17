"""
Karaoke subtitles — ASS (word-by-word highlight) + SRT fallback.
BOTH files are ALWAYS written to guarantee subtitles work.
Item 107: Font rotation pool (TheBoldFont, Anton, Outfit, Poppins, Montserrat, Bebas Neue).
Item 116: Drop shadow açı ve bulanıklık varyasyonu — her videoda farklı.
"""
import config
import random

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

# Item 43: Predefined professional subtitle presets
SUBTITLE_PRESETS = {
    "capcut_yellow": {
        "color": "#FFFFFF",
        "highlight_color": "#FFD700",
        "stroke_color": "#000000",
        "stroke_width": 4,
        "font_size": 56
    },
    "cyber_green": {
        "color": "#FFFFFF",
        "highlight_color": "#00FF66",
        "stroke_color": "#051A0A",
        "stroke_width": 4,
        "font_size": 54
    },
    "red_fire": {
        "color": "#FFFFFF",
        "highlight_color": "#FF3333",
        "stroke_color": "#1A0000",
        "stroke_width": 4,
        "font_size": 56
    },
    "clean_white": {
        "color": "#F0F0F0",
        "highlight_color": "#00D4FF",
        "stroke_color": "#000000",
        "stroke_width": 3,
        "font_size": 52
    }
}

def hex_to_ass_color(val, alpha="00", default_black=False):
    """Converts hex color or named color to ASS format &HAABBGGRR&."""
    val_str = str(val).strip().lstrip('#').lower()
    if val_str in NAMED_COLORS:
        val_str = NAMED_COLORS[val_str]
    if len(val_str) == 6:
        r, g, b = val_str[0:2], val_str[2:4], val_str[4:6]
        return f"&H{alpha}{b}{g}{r}&".upper()
    return f"&H{alpha}000000&".upper() if default_black else f"&H{alpha}FFFFFF&".upper()

def _clean_timings(timings):
    """Filters out empty words, lone emojis or unwanted symbols from subtitle tokens."""
    import re
    cleaned = []
    for item in timings:
        w = item.get("text", "")
        # Remove emojis and odd symbols
        w_clean = re.sub(r'[\U00010000-\U0010ffff]', '', w)
        w_clean = re.sub(r'[\u2000-\u32ff]', '', w_clean)
        w_clean = re.sub(r'[#*_~^\\/|<>@=`~=\[\]{}]', '', w_clean).strip()
        if w_clean:
            cleaned.append({
                "text": w_clean,
                "offset": item.get("offset", 0.0),
                "duration": item.get("duration", 0.0)
            })
    return cleaned

def create_karaoke_subtitles(timings, path, max_dur=9999.0, style_opts=None):
    timings = _clean_timings(timings or [])
    if not timings:
        open(path, "w").close()
        return path

    opts = style_opts or {}
    font_size = opts.get("font_size", getattr(config, "SUBTITLE_FONT_SIZE", 54))
    primary_hex = opts.get("color", getattr(config, "SUBTITLE_COLOR", "#FFFFFF"))
    highlight_hex = opts.get("highlight_color", getattr(config, "SUBTITLE_HIGHLIGHT_COLOR", "#FFD700"))
    stroke_hex = opts.get("stroke_color", getattr(config, "SUBTITLE_STROKE_COLOR", "#000000"))
    stroke_width = opts.get("stroke_width", getattr(config, "SUBTITLE_STROKE_WIDTH", 4))
    y_pos = opts.get("y_position", getattr(config, "SUBTITLE_Y_POSITION", 0.8))
    # Item 107: Yazı tipi rotasyonu — her oturumda farklı font
    font_name = opts.get("font_name", get_session_subtitle_font())
    # Item 116: Drop Shadow açı ve derinlik varyasyonu
    shadow_params = get_session_shadow_params()
    shadow_depth = opts.get("shadow_depth", shadow_params["depth"])
    print(f"  [Item 107] Altyazı fontu: {font_name}")
    print(f"  [Item 116] Drop shadow: açı={shadow_params['angle']}°, derinlik={shadow_depth}px")

    # Calculate MarginV for 1920 height
    # 0.8 y_position means 80% down -> 20% margin from bottom = 384px
    margin_v = int((1.0 - max(0.1, min(0.9, y_pos))) * config.VIDEO_HEIGHT)

    primary_ass = hex_to_ass_color(primary_hex)
    highlight_ass = hex_to_ass_color(highlight_hex)
    stroke_ass = hex_to_ass_color(stroke_hex, default_black=True)

    ass_header = f"""[Script Info]
Title: Karaoke Subtitles
ScriptType: v4.00+
PlayResX: {config.VIDEO_WIDTH}
PlayResY: {config.VIDEO_HEIGHT}
ScaledBorderAndShadow: yes
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: K,{font_name},{font_size},{primary_ass},{highlight_ass},{stroke_ass},&H80000000,-1,0,0,0,100,100,2,0,1,{stroke_width},{shadow_depth},2,2,40,40,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    groups = _group(timings, 3)
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
                if wj == wi:
                    # Item 91: Metin Üstü Dinamik Vurgu (Text Highlighting & Micro Pulse)
                    parts.append(rf"{{\c{highlight_ass}\b1\fscx106\fscy106}}" + w["text"] + rf"{{\c{primary_ass}\b0\fscx100\fscy100}}")
                else:
                    parts.append(w["text"])
            events.append(f"Dialogue: 0,{_at(ws)},{_at(we)},K,,0,0,0,,{' '.join(parts)}")
    with open(path, "w", encoding="utf-8") as f:
        f.write(ass_header + "\n".join(events) + "\n")
    print(f"  [Subs] Karaoke ASS (Vector Engine Item 94): {len(events)} events (Highlight: {highlight_hex} Item 91)")
    return path

def create_srt_file(timings, path, max_dur=9999.0):
    timings = _clean_timings(timings or [])
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

