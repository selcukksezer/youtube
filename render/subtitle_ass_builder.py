"""
ASS karaoke event/style formatting, SRT builder, and emphasis overlay ASS generator.
"""
import math as _math
import re
import sys
from typing import Any, Dict, List, Optional
import config
from viral_retention_engine import ViralRetentionEngine

NAMED_COLORS = {
    "white": "FFFFFF",
    "black": "000000",
    "yellow": "00D7FF",
    "red": "0000FF",
    "blue": "FF0000",
    "green": "00FF00",
    "gold": "00D7FF",
}

POWER_WORD_HIGHLIGHTS = {
    "ölümcül": "#FF3333", "deadly": "#FF3333",
    "milyarder": "#FFD700", "billionaire": "#FFD700",
    "gizemli": "#FF3333", "mysterious": "#FF3333",
    "tehlikeli": "#FF3333", "dangerous": "#FF3333",
    "şok": "#FFD700", "shocking": "#FFD700",
}


def _sg_mod():
    return sys.modules.get("subtitle_generator")


def _cfg():
    mod = _sg_mod()
    return getattr(mod, "config", config) if mod else config


def hex_to_ass_color(val, alpha="00", default_black=False):
    """Converts hex color or named color to ASS format &HAABBGGRR&."""
    val_str = str(val).strip().lstrip('#').lower()
    if val_str in NAMED_COLORS:
        val_str = NAMED_COLORS[val_str]
    if len(val_str) == 6:
        r, g, b = val_str[0:2], val_str[2:4], val_str[4:6]
        return f"&H{alpha}{b}{g}{r}&".upper()
    return f"&H{alpha}000000&".upper() if default_black else f"&H{alpha}FFFFFF&".upper()


def ffmpeg_force_style_from_opts(opts: dict = None, play_h: int = None) -> str:
    """SRT fallback uses the same color, weight, stroke, box, size, and margin as the ASS style."""
    opts = opts or {}
    cfg = _cfg()
    if play_h is None:
        play_h = int(getattr(cfg, "get_target_resolution", lambda: (1080, 1920))()[1])
    font_size = int(opts.get("font_size") or getattr(cfg, "SUBTITLE_FONT_SIZE", 54))
    font_name = opts.get("font_name") or "Anton"
    bold = -1 if opts.get("bold", True) else 0
    primary = hex_to_ass_color(opts.get("color") or "#FFFFFF")
    outline = hex_to_ass_color(opts.get("stroke_color") or "#000000", default_black=True)
    border = 3 if opts.get("box") else 1
    back = hex_to_ass_color(opts.get("box_color") or "#000000") if opts.get("box") else "&HFF000000&"
    outline_w = 0 if int(opts.get("stroke_width") or 0) <= 0 else int(opts.get("stroke_width"))
    y_pos = opts.get("y_position")
    margin_v = int(round(0.25 * play_h)) if y_pos is None else int(round((1.0 - float(y_pos)) * play_h))
    return (
        f"FontSize={font_size},FontName={font_name},Bold={bold},"
        f"PrimaryColour={primary},OutlineColour={outline},Outline={outline_w},"
        f"BackColour={back},BorderStyle={border},Alignment=2,MarginV={margin_v}"
    )


def _resolve_subtitle_layout(opts, target_w, target_h):
    """Items 206 & 265: safe zone margins + max words per frame."""
    safe = ViralRetentionEngine.get_subtitles_safe_zone(screen_height=target_h, screen_width=target_w)
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
        y_pos = 0.56 if has_arabic else 1.0 - (bottom_margin / target_h)
    y_pos = max(0.1, min(0.9, float(y_pos)))

    margin_v = int(round((1.0 - y_pos) * target_h))
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
    close_tag = "{" + rf"\r\c{primary_ass}\fscx100\fscy100" + "}"
    return open_tag, close_tag


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


def split_subtitle_pages_on_silence(
    timings: list,
    max_words_per_page: int = 4,
    *,
    break_on_punctuation: bool = True,
    silence_threshold_sec: float = 0.350,
) -> list:
    """Splits subtitle pages at speech pauses (silence >= 300-350ms)."""
    return _group(
        timings,
        max_words_per_page,
        break_on_punctuation=break_on_punctuation,
        max_gap=silence_threshold_sec,
    )


def _emphasis_overlay_events(groups, font_size, target_w, target_h, uppercase, max_dur):
    """Puts numbers and proof words on a second layer with a cap of 3."""
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


def create_karaoke_subtitles(timings, path, max_dur=9999.0, style_opts=None):
    mod = _sg_mod()
    cfg = _cfg()
    clean_fn = getattr(mod, "_clean_timings")
    align_fn = getattr(mod, "align_words_whisper")
    clamp_fn = getattr(mod, "_clamp_word_display_durations")
    session_font_fn = getattr(mod, "get_session_subtitle_font")

    opts = style_opts or {}
    timings = clean_fn(timings or [])
    timings = align_fn(
        timings,
        audio_path=opts.get("audio_path"),
        enabled=opts.get("whisper_align"),
        language=opts.get("language"),
    )
    if opts.get("clamp_word_durations", False):
        timings = clamp_fn(timings)
    else:
        timings = [{**t, "duration": max(0.10, float(t.get("duration") or 0.25))} for t in timings]
    target_w = int(opts.get("video_width") or getattr(cfg, "VIDEO_WIDTH", 1080))
    target_h = int(opts.get("video_height") or getattr(cfg, "VIDEO_HEIGHT", 1920))
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

    font_size = opts.get("font_size", getattr(cfg, "SUBTITLE_FONT_SIZE", 54))
    primary_hex = opts.get("color", getattr(cfg, "SUBTITLE_COLOR", "#FFFFFF"))
    highlight_hex = opts.get("highlight_color", getattr(cfg, "SUBTITLE_HIGHLIGHT_COLOR", "#FFD700"))
    stroke_hex = opts.get("stroke_color", getattr(cfg, "SUBTITLE_STROKE_COLOR", "#000000"))
    stroke_width = opts.get("stroke_width", getattr(cfg, "SUBTITLE_STROKE_WIDTH", 4))
    uppercase = opts.get("uppercase", False)
    glow = opts.get("glow", False)
    bounce = opts.get("bounce", True)
    font_name = opts.get("font_name") or session_font_fn()
    shadow_depth = float(opts["shadow_depth"]) if ("shadow_depth" in opts and opts.get("shadow_depth") is not None) else 0.0
    shadow_prefix = ""
    if opts.get("shadow_angle") is not None and shadow_depth > 0:
        shadow_angle = int(opts["shadow_angle"])
        _rad = _math.radians(shadow_angle)
        shadow_x = round(shadow_depth * _math.cos(_rad), 2)
        shadow_y = round(shadow_depth * _math.sin(_rad), 2)
        shadow_prefix = f"{{\\xshad{shadow_x}\\yshad{shadow_y}}}"
        print(f"  [Item 116] Drop shadow: açı={shadow_angle}°, derinlik={shadow_depth}px")
    print(f"  [Item 107] Altyazı fontu: {font_name}")

    target_w, target_h = getattr(cfg, "get_target_resolution", lambda: (cfg.VIDEO_WIDTH, cfg.VIDEO_HEIGHT))()
    scale_factor = target_h / 1920.0
    scaled_font_size = max(18, int(font_size * scale_factor))
    scaled_stroke_width = 0 if int(stroke_width) <= 0 else max(1, int(float(stroke_width) * scale_factor))
    scaled_shadow_depth = 0 if shadow_depth <= 0 else max(1, int(shadow_depth * scale_factor))
    border_style = 3 if opts.get("box") else 1
    back_colour = hex_to_ass_color(opts.get("box_color") or "#000000") if opts.get("box") else "&HFF000000&"
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

    groups = split_subtitle_pages_on_silence(
        timings,
        max_words_per_page=max_words,
        break_on_punctuation=not bool(opts.get("words_per_page")),
        silence_threshold_sec=0.350,
    )
    events = []

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
        if g[0]["offset"] >= max_dur:
            break
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
            if ws >= max_dur:
                break
            if wi + 1 < len(g):
                next_ws = g[wi + 1]["offset"]
                if next_ws > ws:
                    we = next_ws if next_ws - ws <= 1.2 else min(next_ws, ws + max(float(active.get("duration", 0.3)), 0.35))
                else:
                    we = ws + max(0.15, float(active.get("duration", 0.3)))
            else:
                natural_end = ws + max(0.20, float(active.get("duration", 0.3)))
                if next_group_start > natural_end and (next_group_start - natural_end) < 0.35:
                    we = min(next_group_start, natural_end + 0.25)
                else:
                    we = min(natural_end, next_group_start)

            we = min(we, max_dur, next_group_start)
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
    if opts.get("embed_legacy_emphasis", False):
        events.extend(_emphasis_overlay_events(groups, scaled_font_size, target_w, target_h, uppercase, max_dur))
    with open(path, "w", encoding="utf-8") as f:
        f.write(ass_header + "\n".join(events) + "\n")
    print(f"  [Subs] Karaoke ASS (Vector Engine Item 94): {len(events)} events (Highlight: {highlight_hex} Item 91)")
    return path


def create_srt_file(timings, path, max_dur=9999.0, audio_path: str = None, style_opts=None):
    mod = _sg_mod()
    clean_fn = getattr(mod, "_clean_timings")
    align_fn = getattr(mod, "align_words_whisper")

    opts = style_opts or {}
    timings = clean_fn(timings or [])
    timings = align_fn(
        timings,
        audio_path=audio_path or opts.get("audio_path"),
        enabled=opts.get("whisper_align"),
        language=opts.get("language"),
    )
    if not timings:
        open(path, "w").close()
        return path
    groups = _group(timings, 4)
    lines, idx = [], 1
    for gi, g in enumerate(groups):
        s = g[0]["offset"]
        if s >= max_dur:
            break
        last_dur = max(0.20, float(g[-1].get("duration") or 0.3))
        natural_end = g[-1]["offset"] + last_dur
        if gi + 1 < len(groups):
            next_start = groups[gi + 1][0]["offset"]
            e = min(next_start, natural_end + 0.25) if (next_start > s and (next_start - natural_end) < 0.35) else min(natural_end, next_start)
        else:
            e = natural_end
        e = min(e, max_dur)
        if e - s < 0.2:
            e = s + 0.3
        lines += [str(idx), f"{_st(s)} --> {_st(e)}", " ".join(w["text"] for w in g), ""]
        idx += 1
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  [Subs] SRT: {idx-1} lines")
    return path


def create_subtitle_files(timings, ass_path, srt_path, max_dur=9999.0, style_opts=None):
    mod = _sg_mod()
    clean_fn = getattr(mod, "_clean_timings")
    align_fn = getattr(mod, "align_words_whisper")
    ass_fn = getattr(mod, "create_karaoke_subtitles", create_karaoke_subtitles)
    srt_fn = getattr(mod, "create_srt_file", create_srt_file)

    opts = dict(style_opts or {})
    aligned_timings = align_fn(
        clean_fn(timings or []),
        audio_path=opts.get("audio_path"),
        enabled=opts.get("whisper_align"),
        language=opts.get("language"),
    )
    render_opts = {**opts, "audio_path": None, "whisper_align": False}
    ass_result = ass_fn(aligned_timings, ass_path, max_dur=max_dur, style_opts=render_opts)
    srt_result = srt_fn(aligned_timings, srt_path, max_dur=max_dur, style_opts=render_opts)
    return ass_result, srt_result


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
    """Generates a dedicated secondary emphasis.ass overlay file (Master Plan P6)."""
    mod = _sg_mod()
    clean_fn = getattr(mod, "_clean_timings")
    clean = clean_fn(timings or [])
    if not clean:
        return None
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
        candidates.append({
            "start": start,
            "end": end,
            "text": _format_word(raw, uppercase),
            "priority": 6 if is_number else 4,
            "is_number": is_number,
        })

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
        accent = "&H0000D7FF&" if c["is_number"] else "&H0000E5FF&"
        pop_fx = (
            "{\\an5\\pos(%d,%d)\\fad(60,100)\\fscx75\\fscy75"
            "\\t(0,120,\\fscx118\\fscy118)\\t(120,240,\\fscx100\\fscy100)\\c%s}" % (pos_x, pos_y, accent)
        )
        events.append(f"Dialogue: 0,{_at(c['start'])},{_at(c['end'])},EMPHASIS,,0,0,0,,{pop_fx}{c['text']}")

    with open(path, "w", encoding="utf-8") as f:
        f.write(header + "\n".join(events) + "\n")
    return path
