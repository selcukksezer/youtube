"""
Karaoke subtitles — ASS (word-by-word highlight) + SRT fallback.
BOTH files are ALWAYS written to guarantee subtitles work.
"""
import config

NAMED_COLORS = {
    "white": "FFFFFF",
    "black": "000000",
    "yellow": "00D7FF",
    "red": "0000FF",
    "blue": "FF0000",
    "green": "00FF00",
    "gold": "00D7FF",
}

def hex_to_ass_color(val, alpha="00", default_black=False):
    """Converts hex color or named color to ASS format &HAABBGGRR&."""
    val_str = str(val).strip().lstrip('#').lower()
    if val_str in NAMED_COLORS:
        val_str = NAMED_COLORS[val_str]
    if len(val_str) == 6:
        r, g, b = val_str[0:2], val_str[2:4], val_str[4:6]
        return f"&H{alpha}{b}{g}{r}&"
    return f"&H{alpha}000000&" if default_black else f"&H{alpha}FFFFFF&"

def create_karaoke_subtitles(timings, path, max_dur=9999.0, style_opts=None):
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
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: K,Arial,{font_size},{primary_ass},{highlight_ass},{stroke_ass},&H80000000,-1,0,0,0,100,100,2,0,1,{stroke_width},2,2,40,40,{margin_v},1

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
                    parts.append(rf"{{\c{highlight_ass}\b1}}" + w["text"] + rf"{{\c{primary_ass}\b0}}")
                else:
                    parts.append(w["text"])
            events.append(f"Dialogue: 0,{_at(ws)},{_at(we)},K,,0,0,0,,{' '.join(parts)}")
    with open(path, "w", encoding="utf-8") as f:
        f.write(ass_header + "\n".join(events) + "\n")
    print(f"  [Subs] Karaoke ASS: {len(events)} events (Highlight: {highlight_hex})")
    return path

def create_srt_file(timings, path, max_dur=9999.0):
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

