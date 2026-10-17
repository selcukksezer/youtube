"""PIL card drawing primitives, avatars, emoji animations, end cards, and UI element overlays."""
from __future__ import annotations

import math
import os
import random
import sys
import tempfile
from typing import Any

from moviepy.editor import CompositeVideoClip, ImageClip, VideoClip
import numpy as np
import PIL.Image
from PIL import Image, ImageDraw

if not hasattr(PIL.Image, "ANTIALIAS"):
    PIL.Image.ANTIALIAS = getattr(PIL.Image, "Resampling", PIL.Image).LANCZOS

import config


def _oc_config() -> Any:
    mod = sys.modules.get("effects.overlay_cards")
    return getattr(mod, "config", config) if mod is not None else config


def generate_retro_avatar_png(
    output_path: str,
    avatar_style: str = "auto",
    size: int = 160,
    seed: int = None,
) -> str:
    """Item 118 – Konuşmacı İkonu veya Avatar Oluşturma."""
    rng = random.Random(seed or random.randint(0, 9999))

    styles = ["robot", "wizard", "ghost", "astronaut"]
    if avatar_style == "auto":
        avatar_style = rng.choice(styles)

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cell = size // 16
    half = size // 2

    if avatar_style == "robot":
        draw.rounded_rectangle([cell * 3, cell * 4, cell * 13, cell * 14], radius=cell, fill=(60, 65, 75, 240))
        draw.rounded_rectangle([cell * 4, cell * 1, cell * 12, cell * 6], radius=cell, fill=(90, 95, 105, 250))
        eye_color = (80, 200, 255, 255)
        draw.ellipse([cell * 5, cell * 2, cell * 7, cell * 4], fill=eye_color)
        draw.ellipse([cell * 9, cell * 2, cell * 11, cell * 4], fill=eye_color)
        draw.line([cell * 6, cell * 5, cell * 10, cell * 5], fill=(150, 155, 165, 200), width=max(1, cell // 2))
        draw.line([half, cell * 1, half, 0], fill=(120, 125, 135, 220), width=max(1, cell // 2))
        draw.ellipse([half - cell, -cell, half + cell, cell], fill=(80, 200, 255, 255))

    elif avatar_style == "wizard":
        draw.polygon(
            [(cell * 3, size), (cell * 13, size), (cell * 12, cell * 7), (half, cell * 5), (cell * 4, cell * 7)],
            fill=(100, 30, 160, 230),
        )
        draw.ellipse([cell * 5, cell * 3, cell * 11, cell * 9], fill=(220, 180, 140, 255))
        draw.polygon([(half, 0), (cell * 4, cell * 4), (cell * 12, cell * 4)], fill=(60, 10, 100, 255))
        draw.line([cell * 4, cell * 4, cell * 12, cell * 4], fill=(255, 200, 50, 255), width=max(1, cell // 2))
        draw.ellipse([cell * 6, cell * 5, cell * 8, cell * 7], fill=(50, 220, 100, 255))
        draw.ellipse([cell * 9, cell * 5, cell * 11, cell * 7], fill=(50, 220, 100, 255))
        draw.arc([cell * 5, cell * 7, cell * 11, cell * 10], start=0, end=180, fill=(200, 200, 210, 200), width=max(1, cell // 2))

    elif avatar_style == "ghost":
        draw.ellipse([cell * 3, cell * 2, cell * 13, cell * 12], fill=(240, 245, 255, 180))
        draw.rectangle([cell * 3, cell * 7, cell * 13, cell * 14], fill=(240, 245, 255, 160))
        for i in range(5):
            x_start = cell * 3 + i * cell * 2
            draw.arc([x_start, cell * 12, x_start + cell * 2, cell * 15], start=0, end=180, fill=(0, 0, 0, 0), width=cell)
        draw.ellipse([cell * 5, cell * 4, cell * 8, cell * 7], fill=(30, 30, 50, 220))
        draw.ellipse([cell * 9, cell * 4, cell * 12, cell * 7], fill=(30, 30, 50, 220))

    elif avatar_style == "astronaut":
        draw.ellipse([cell * 3, cell * 1, cell * 13, cell * 11], fill=(220, 225, 230, 250))
        draw.ellipse([cell * 5, cell * 3, cell * 11, cell * 9], fill=(30, 100, 200, 180))
        draw.arc([cell * 4, cell * 2, cell * 8, cell * 5], start=210, end=330, fill=(255, 255, 255, 120), width=max(1, cell // 2))
        draw.rounded_rectangle([cell * 4, cell * 9, cell * 12, cell * 15], radius=cell, fill=(80, 85, 95, 240))
        draw.ellipse([cell * 5, cell * 10, cell * 8, cell * 13], fill=(200, 50, 50, 220))

    img.save(output_path, "PNG")
    print(f"    [Item 118] Retro avatar üretildi: style={avatar_style}, size={size}px → {output_path}")
    return output_path


def apply_speaker_avatar_overlay(
    base_clip,
    avatar_path: str = None,
    position: str = "bottom_left",
    avatar_size: int = 140,
    animate_bob: bool = True,
    audio_path: str = None,
    lip_sync: bool = False,
):
    """Item 118 & 324 – Avatar/Maskot Overlay Bindirmesi + Ses Zarfı Lip-Sync Desteği."""
    try:
        if getattr(_oc_config(), "RENDER_SAFE_MODE", True):
            print("    [Item 118] Avatar overlay: RENDER_SAFE_MODE aktif, bypass edildi.")
            return base_clip
    except Exception:
        pass

    if not avatar_path or not os.path.exists(avatar_path):
        tmp_png = tempfile.mktemp(suffix="_avatar.png")
        generate_retro_avatar_png(tmp_png, avatar_style="auto", size=avatar_size)
        avatar_path = tmp_png

    w, h = base_clip.size
    dur = base_clip.duration
    margin = 20

    if position == "bottom_left":
        base_x, base_y = margin, h - avatar_size - margin
    elif position == "bottom_right":
        base_x, base_y = w - avatar_size - margin, h - avatar_size - margin
    elif position == "top_left":
        base_x, base_y = margin, margin
    else:
        base_x, base_y = w - avatar_size - margin, margin

    def avatar_pos(t):
        bob = int(math.sin(2 * math.pi * t * 1.5) * 4) if animate_bob else 0
        return (base_x, base_y + bob)

    if lip_sync or audio_path:
        try:
            from services.avatar_pipeline import (
                compute_audio_mouth_envelope,
                render_talking_avatar_frame,
            )

            base_img = Image.open(avatar_path).convert("RGBA").resize((avatar_size, avatar_size))
            fps_env = 24
            envelope = compute_audio_mouth_envelope(audio_path, dur, fps=fps_env)

            def make_lip_frame(t: float):
                idx = min(len(envelope) - 1, max(0, int(t * fps_env)))
                return render_talking_avatar_frame(base_img, envelope[idx], t=t)

            avatar_clip = VideoClip(make_lip_frame, duration=dur).set_position(
                avatar_pos if animate_bob else (base_x, base_y)
            )
        except Exception:
            avatar_clip = (
                ImageClip(avatar_path, ismask=False)
                .set_duration(dur)
                .resize((avatar_size, avatar_size))
                .set_position(avatar_pos if animate_bob else (base_x, base_y))
            )
    elif animate_bob:
        avatar_clip = (
            ImageClip(avatar_path, ismask=False)
            .set_duration(dur)
            .resize((avatar_size, avatar_size))
            .set_position(avatar_pos)
        )
    else:
        avatar_clip = (
            ImageClip(avatar_path, ismask=False)
            .set_duration(dur)
            .resize((avatar_size, avatar_size))
            .set_position((base_x, base_y))
        )

    composite = CompositeVideoClip([base_clip, avatar_clip], size=(w, h))
    composite.duration = dur
    print(
        f"    [Item 118/324] Avatar overlay: pos={position}, size={avatar_size}px, "
        f"bob={animate_bob}, lip_sync={bool(lip_sync or audio_path)}"
    )
    return composite



_MOOD_EMOJI_MAP = {
    "epic":       ["🔥", "⚡", "💪", "🏆", "🎯"],
    "dramatic":   ["😱", "🤯", "💀", "😤", "🌪️"],
    "mysterious": ["🔍", "👁️", "🌑", "🤫", "🕵️"],
    "calm":       ["✨", "🌿", "💫", "🌙", "🕊️"],
    "energetic":  ["🚀", "⭐", "💥", "🎉", "🙌"],
    "dark":       ["🌑", "⚫", "🖤", "💔", "😔"],
    "bright":     ["🌟", "☀️", "💛", "🌈", "😊"],
    "default":    ["✅", "💡", "🎬", "📌", "🔔"],
}


def get_mood_emoji(mood: str = "default") -> str:
    """Item 125 – Sahne ruh haline göre uygun emoji seçer."""
    pool = _MOOD_EMOJI_MAP.get(mood.lower(), _MOOD_EMOJI_MAP["default"])
    return random.choice(pool)


def generate_emoji_subtitle_overlay(
    width: int,
    height: int,
    duration: float,
    emoji_events: list,
    fps: float = 30.0,
) -> VideoClip:
    """Item 125 – Altyazılarda Emoji Animasyonu."""
    if getattr(_oc_config(), "RENDER_SAFE_MODE", True) or not emoji_events:
        print("    [Item 125] Emoji animasyon katmanı: RENDER_SAFE_MODE aktif, bypass edildi.")
        return None
    emoji_size_base = max(60, width // 12)

    def make_frame(t):
        frame = np.zeros((height, width, 4), dtype=np.uint8)

        for ev in emoji_events:
            ev_time = ev.get("time", 0.0)
            show_dur = ev.get("duration", 0.8)

            if ev_time <= t < ev_time + show_dur:
                elapsed = t - ev_time
                if elapsed < 0.3:
                    scale = elapsed / 0.3
                elif elapsed > show_dur - 0.2:
                    scale = (show_dur - elapsed) / 0.2
                else:
                    scale = 1.0
                scale = max(0.0, min(1.0, scale))

                em_size = int(emoji_size_base * scale)
                if em_size < 10:
                    continue

                y_ratio = ev.get("y_ratio", 0.82)
                x_center = width // 2 + ev.get("x_offset", 0)
                y_center = int(height * y_ratio)

                em_half = em_size // 2
                x1, y1 = max(0, x_center - em_half), max(0, y_center - em_half)
                x2, y2 = min(width, x_center + em_half), min(height, y_center + em_half)

                if x2 > x1 and y2 > y1:
                    alpha = int(220 * scale)
                    frame[y1:y2, x1:x2, :3] = 255
                    frame[y1:y2, x1:x2, 3] = alpha
                    image = Image.fromarray(frame, "RGBA")
                    ImageDraw.Draw(image).text(
                        (x_center, y_center),
                        ev.get("emoji", ""),
                        fill=(20, 20, 30, 255),
                        anchor="mm",
                    )
                    frame = np.array(image)

        return frame

    def make_rgb(t):
        return make_frame(t)[:, :, :3].astype(np.uint8)

    def make_mask(t):
        return make_frame(t)[:, :, 3].astype(float) / 255.0

    mask = VideoClip(make_mask, ismask=True, duration=duration).set_fps(fps)
    clip = VideoClip(make_rgb, ismask=False, duration=duration).set_fps(fps).set_mask(mask)
    print(f"    [Item 125] Emoji animasyon katmanı: {len(emoji_events)} emoji event, {duration:.1f}s")
    return clip


def build_emoji_events_from_timings(word_timings: list, scenes: list = None) -> list:
    """Item 125 – Word timing verisinden emoji event listesi oluşturur."""
    events = []
    scene_map = {}
    if scenes:
        current_offset = 0.0
        for sc in scenes:
            dur = sc.get("duration", 6.0)
            scene_map[current_offset] = sc.get("mood", "default")
            current_offset += dur

    def get_scene_mood_at(t):
        best_mood, best_t = "default", -1
        for start_t, mood in scene_map.items():
            if start_t <= t and start_t > best_t:
                best_t, best_mood = start_t, mood
        return best_mood

    for word in word_timings:
        text = word.get("text", "")
        offset = word.get("offset", 0.0)
        duration = word.get("duration", 0.3)

        if text.strip().endswith((".", "!", "?", "...", ",")):
            mood = get_scene_mood_at(offset)
            events.append({
                "time": offset + duration + 0.05,
                "duration": 0.75,
                "emoji": get_mood_emoji(mood),
                "y_ratio": 0.82,
                "x_offset": random.randint(-80, 80),
            })

    print(f"    [Item 125] {len(events)} emoji event oluşturuldu (cümle sonları)")
    return events


def generate_end_card_overlay(
    width: int,
    height: int,
    duration: float = 3.0,
    fps: float = 30.0,
    channel_name: str = "Kanalımıza Abone Ol",
    cta_text: str = "Takip Et & Zil Simgesine Bas!",
    style: str = "dark",
) -> VideoClip:
    """Item 126 – Kapanışta Ekrana Gelen Kartlar (End Card)."""
    styles = {
        "dark":    {"bg": (0, 0, 0, 200), "primary": (255, 60, 60), "text": (255, 255, 255), "accent": (255, 200, 0)},
        "neon":    {"bg": (10, 0, 30, 210), "primary": (0, 255, 180), "text": (200, 255, 255), "accent": (255, 0, 180)},
        "minimal": {"bg": (255, 255, 255, 180), "primary": (30, 30, 30), "text": (30, 30, 30), "accent": (200, 50, 50)},
        "warm":    {"bg": (40, 15, 5, 200), "primary": (255, 140, 20), "text": (255, 235, 200), "accent": (255, 80, 40)},
    }
    s = styles.get(style, styles["dark"])

    def make_frame(t):
        slide = min(1.0, t / 0.4) if t < 0.4 else 1.0
        pulse = 0.95 + 0.05 * math.sin(2 * math.pi * t * 2.0)

        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        card_h = int(height * 0.28)
        card_top = int(height - card_h * slide)
        draw.rounded_rectangle([0, card_top, width, height], radius=24, fill=s["bg"])

        cx = int(width * 0.18)
        cy = int((card_top + height) / 2)
        radius = int(min(width, card_h) * 0.22 * pulse)
        draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=s["primary"])

        inner_r = int(radius * 0.55)
        draw.ellipse([cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r], fill=s["accent"])

        font_size_large = max(24, width // 18)
        text_x = int(width * 0.36)
        text_y = card_top + int(card_h * 0.2)
        draw.text((text_x, text_y), channel_name, fill=s["text"], font=None)
        draw.text((text_x, text_y + font_size_large + 12), cta_text, fill=s["accent"], font=None)

        alpha_mult = min(1.0, t / 0.3)
        if alpha_mult < 1.0:
            data = np.array(img)
            data[:, :, 3] = (data[:, :, 3] * alpha_mult).astype(np.uint8)
            img = Image.fromarray(data)

        return np.array(img)

    def make_rgb(t):
        return make_frame(t)[:, :, :3].astype(np.uint8)

    def make_mask(t):
        return make_frame(t)[:, :, 3].astype(float) / 255.0

    mask = VideoClip(make_mask, ismask=True, duration=duration).set_fps(fps)
    clip = VideoClip(make_rgb, ismask=False, duration=duration).set_fps(fps).set_mask(mask)
    print(f"    [Item 126] End card overlay: style={style}, {duration:.1f}s, CTA='{cta_text[:30]}'")
    return clip


def apply_end_card_to_video(
    base_clip,
    duration: float = 3.0,
    channel_name: str = "Abone Ol",
    cta_text: str = "Takip Et & Zil Simgesine Bas!",
    style: str = "dark",
):
    """Item 126 – Kapanış kartını videonun son N saniyesine ekler."""
    if getattr(_oc_config(), "RENDER_SAFE_MODE", True):
        print("    [Item 126] End card overlay: RENDER_SAFE_MODE aktif, bypass edildi.")
        return base_clip
    w, h = base_clip.size
    dur = base_clip.duration
    fps = base_clip.fps or 30.0

    end_card_duration = min(duration, dur)
    end_card_start = dur - end_card_duration

    end_card = generate_end_card_overlay(
        w, h, duration=end_card_duration, fps=fps,
        channel_name=channel_name, cta_text=cta_text, style=style,
    ).set_start(end_card_start)

    composite = CompositeVideoClip([base_clip, end_card], size=(w, h))
    composite.duration = dur
    return composite


def generate_ui_element_overlay(
    width: int,
    height: int,
    duration: float,
    ui_type: str = "ios_notification",
    header_text: str = "Önemli Gelişme",
    body_text: str = "Bunu sonuna kadar izlemelisiniz!",
    fps: float = 30.0,
) -> VideoClip:
    """Item 131 – Ekrana Sahte Arayüz (UI) Elemanları Ekleme."""
    def make_rgba(t):
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        slide = min(1.0, t / 0.35)

        if ui_type == "ios_notification":
            box_w = int(width * 0.88)
            box_h = max(70, int(height * 0.08))
            x0 = (width - box_w) // 2
            target_y0 = int(height * 0.08)
            y0 = int(-box_h + (target_y0 + box_h) * slide)

            draw.rounded_rectangle(
                [x0, y0, x0 + box_w, y0 + box_h], radius=18,
                fill=(28, 30, 42, 225), outline=(120, 160, 255, 200), width=2,
            )
            draw.text((x0 + 20, y0 + 14), f"🔔  {header_text}", fill=(255, 255, 255, 255))
            draw.text((x0 + 20, y0 + 38), body_text[:45], fill=(200, 220, 255, 230))

        elif ui_type == "tweet_card":
            box_w = int(width * 0.88)
            box_h = max(85, int(height * 0.10))
            x0 = (width - box_w) // 2
            target_y0 = int(height * 0.12)
            y0 = int(-box_h + (target_y0 + box_h) * slide)

            draw.rounded_rectangle(
                [x0, y0, x0 + box_w, y0 + box_h], radius=16,
                fill=(16, 22, 34, 230), outline=(29, 155, 240, 210), width=2,
            )
            draw.ellipse([x0 + 15, y0 + 12, x0 + 45, y0 + 42], fill=(29, 155, 240, 255))
            draw.text((x0 + 55, y0 + 14), f"{header_text} @official", fill=(255, 255, 255, 255))
            draw.text((x0 + 20, y0 + 48), body_text[:50], fill=(225, 235, 245, 235))

        else:
            box_w = int(width * 0.84)
            box_h = max(55, int(height * 0.06))
            x0 = (width - box_w) // 2
            target_y0 = int(height * 0.10)
            y0 = int(-box_h + (target_y0 + box_h) * slide)

            draw.rounded_rectangle(
                [x0, y0, x0 + box_w, y0 + box_h], radius=box_h // 2,
                fill=(255, 255, 255, 235), outline=(210, 220, 230, 240), width=2,
            )
            draw.text((x0 + 22, y0 + 16), f"🔍  {header_text}...", fill=(40, 45, 55, 230))

        return np.array(img)

    def make_rgb(t):
        return make_rgba(t)[:, :, :3].astype(np.uint8)

    def make_mask(t):
        return make_rgba(t)[:, :, 3].astype(float) / 255.0

    mask = VideoClip(make_mask, ismask=True, duration=duration).set_fps(fps)
    clip = VideoClip(make_rgb, ismask=False, duration=duration).set_fps(fps).set_mask(mask)
    print(f"    [Item 131] UI Element overlay üretildi: type={ui_type}, duration={duration:.1f}s")
    return clip


def apply_ui_element_overlay(
    base_clip,
    ui_type: str = "ios_notification",
    header_text: str = "Önemli Bilgi",
    body_text: str = "Sonuna kadar izleyin!",
    start_time: float = 0.5,
    duration: float = 3.5,
):
    """Item 131 – Belirtilen klibe sahte arayüz grafik katmanı bindirir."""
    w, h = base_clip.size
    dur = min(duration, max(0.5, base_clip.duration - start_time))
    fps = getattr(base_clip, "fps", None) or 30.0

    ui_clip = generate_ui_element_overlay(
        w, h, duration=dur, ui_type=ui_type,
        header_text=header_text, body_text=body_text, fps=fps,
    ).set_start(start_time)

    composite = CompositeVideoClip([base_clip, ui_clip], size=(w, h))
    composite.duration = base_clip.duration
    return composite
