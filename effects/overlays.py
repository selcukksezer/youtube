"""
Graphic Overlays, Watermarks, Badges, Avatars & UI Cards
Covers items: 59, 60, 75, 82, 87, 92, 105, 118, 125, 126, 131, 138, 212, 232, 238, 246
"""
import os, random, math, subprocess
from typing import Optional, Tuple, Any
from moviepy.editor import (
    VideoFileClip, ColorClip, CompositeVideoClip, ImageClip,
    VideoClip, vfx
)
import numpy as np
import PIL.Image
from PIL import Image, ImageDraw, ImageFont, ImageFilter
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = getattr(PIL.Image, 'Resampling', PIL.Image).LANCZOS

import config

def overlay_watermark(clip: VideoFileClip, watermark_path: str, opacity: float = 0.75) -> VideoFileClip:
    """
    Item 60: Brand logo / watermark overlay on top right/left.
    """
    if not watermark_path or not os.path.exists(watermark_path):
        return clip
    try:
        wm = (
            ImageClip(watermark_path)
            .resize(width=int(clip.w * 0.22))
            .set_opacity(opacity)
            .set_duration(clip.duration)
            .set_position(("right", 40))
        )
        return CompositeVideoClip([clip, wm], size=clip.size)
    except Exception as e:
        print(f"    [Watermark] Error: {e}")
        return clip

def score_frame_thumbnail_quality(frame: np.ndarray) -> float:
    """
    R10 #59/#92: Contrast + mid-bright luminance score for Shorts frame-0 pick.
    Higher = more feed-visible (avoid near-black / flat frames).
    """
    if frame is None or getattr(frame, "size", 0) == 0:
        return 0.0
    arr = frame.astype(np.float32)
    if arr.ndim == 3:
        # Rec.601 luma
        luma = 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]
    else:
        luma = arr
    mean = float(np.mean(luma))
    std = float(np.std(luma))
    # Prefer mid-bright (90–180) with high contrast
    brightness_penalty = abs(mean - 135.0) / 135.0
    contrast = min(1.0, std / 64.0)
    return max(0.0, (contrast * 70.0) + (30.0 * (1.0 - min(1.0, brightness_penalty))))


def select_best_thumbnail_timestamp(
    video_path: str,
    sample_times: Optional[list] = None,
    max_samples: int = 8,
) -> Tuple[float, float]:
    """
    R10 #59/#92: Sample early frames and return (best_t, score).
    Defaults to first ~3s (Shorts feed decision window).
    """
    if not os.path.exists(video_path):
        return 1.0, 0.0
    times = list(sample_times or [])
    if not times:
        times = [0.05, 0.35, 0.7, 1.0, 1.4, 1.8, 2.3, 2.8][:max_samples]
    best_t, best_score = times[0], -1.0
    try:
        with VideoFileClip(video_path, audio=False) as clip:
            dur = float(clip.duration or 1.0)
            for t in times:
                tt = min(max(0.0, float(t)), max(0.0, dur - 0.04))
                try:
                    frame = clip.get_frame(tt)
                    sc = score_frame_thumbnail_quality(frame)
                    if sc > best_score:
                        best_score, best_t = sc, tt
                except Exception:
                    continue
    except Exception:
        return 1.0, 0.0
    return best_t, best_score


def extract_frame0_thumbnail(video_path: str, output_thumb_path: str) -> bool:
    """
    Items 59, 92 / R10 #59/#92: Peak-curiosity thumbnail via contrast/brightness scan.
    Falls back to t=1s still if scoring fails.
    """
    if not os.path.exists(video_path):
        return False
    try:
        best_t, score = select_best_thumbnail_timestamp(video_path)
        ss = max(0.0, float(best_t))
        cmd = [
            "ffmpeg", "-y", "-ss", f"{ss:.3f}", "-i", video_path,
            "-frames:v", "1", "-q:v", "2", output_thumb_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0 and os.path.exists(output_thumb_path):
            meta_path = output_thumb_path.rsplit(".", 1)[0] + "_thumb_meta.txt"
            try:
                with open(meta_path, "w", encoding="utf-8") as fh:
                    fh.write(f"t={ss:.3f}\nscore={score:.2f}\nrule=r10_59_92\n")
            except Exception:
                pass
            return True
        # Legacy fallback
        cmd = [
            "ffmpeg", "-y", "-ss", "00:00:01", "-i", video_path,
            "-frames:v", "1", "-q:v", "2", output_thumb_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return res.returncode == 0
    except Exception:
        return False


def generate_intro_hook_card(
    width: int,
    height: int,
    hook_text: str,
    duration: float = 1.2,
    bg_color: Tuple[int, int, int] = (12, 12, 20),
    accent: Tuple[int, int, int] = (255, 220, 40),
):
    """
    R10 #61: 1–1.5s branded intro card before main timeline (text hook + accent bar).
    Returns an ImageClip or None.
    """
    try:
        img = Image.new("RGB", (width, height), bg_color)
        draw = ImageDraw.Draw(img)
        bar_h = max(8, height // 80)
        draw.rectangle([0, 0, width, bar_h], fill=accent)
        draw.rectangle([0, height - bar_h, width, height], fill=accent)
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", size=max(36, width // 18))
        except Exception:
            font = ImageFont.load_default()
        text = (hook_text or "İZLE").strip()[:72]
        # word-wrap rough
        words = text.split()
        lines, cur = [], ""
        for w in words:
            trial = (cur + " " + w).strip()
            if len(trial) > 22 and cur:
                lines.append(cur)
                cur = w
            else:
                cur = trial
        if cur:
            lines.append(cur)
        lines = lines[:4] or ["İZLE"]
        y = height // 2 - (len(lines) * 48) // 2
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            tw = bbox[2] - bbox[0]
            draw.text(((width - tw) // 2, y), line, fill=(255, 255, 255), font=font)
            y += 52
        arr = np.array(img)
        return ImageClip(arr).set_duration(max(0.6, float(duration)))
    except Exception as e:
        print(f"    [IntroHookCard] Notice: {e}")
        return None


def apply_keyword_pop_text(
    clip: VideoFileClip,
    text: str,
    start: float = 0.0,
    duration: float = 0.85,
    color: Tuple[int, int, int] = (255, 255, 80),
) -> VideoFileClip:
    """
    R10 #74: Keyword pop — short emphasis text scales in over base clip.
    """
    try:
        w, h = clip.size
        card = generate_intro_hook_card(w, h // 5, text, duration=duration, bg_color=(0, 0, 0), accent=color)
        if card is None:
            return clip
        # Transparent-ish band at mid
        band = (
            card.resize(height=max(80, h // 6))
            .set_opacity(0.92)
            .set_start(max(0.0, float(start)))
            .set_duration(max(0.4, float(duration)))
            .set_position(("center", h // 2 - 40))
        )
        out = CompositeVideoClip([clip, band], size=clip.size)
        out.duration = clip.duration
        if clip.audio:
            out = out.set_audio(clip.audio)
        return out
    except Exception as e:
        print(f"    [KeywordPop] Notice: {e}")
        return clip

def apply_multi_layer_overlay(clip: VideoFileClip, opacity: float = 0.10, overlay_type: str = "light_leak") -> VideoFileClip:
    """
    Item 75: Görsel Katmanlama (Multi-Layer B-Roll).
    Tek bir stok video kullanılmamalı; ana videonun üzerine %10 opaklıkta toz,
    ışık sızıntısı (light leak) veya doku katmanı bindirilmelidir.
    """
    if getattr(config, 'RENDER_SAFE_MODE', True):
        return clip
    try:
        w, h = clip.size
        asset_file = os.path.join(config.ASSETS_DIR, f"{overlay_type}.mp4")
        if os.path.exists(asset_file):
            layer = VideoFileClip(asset_file).resize((w, h)).set_opacity(opacity).set_duration(clip.duration)
            if layer.duration < clip.duration:
                layer = layer.fx(vfx.loop, duration=clip.duration)
            return CompositeVideoClip([clip, layer], size=(w, h))

        # Procedural cinematic warm light leak layer at exactly 10% opacity
        leak_color = random.choice([(255, 235, 190), (255, 215, 160), (245, 225, 205)])
        glow_layer = (
            ColorClip(size=(w, h), color=leak_color)
            .set_opacity(opacity)
            .set_duration(clip.duration)
        )
        composite = CompositeVideoClip([clip, glow_layer], size=(w, h))
        composite.duration = clip.duration
        return composite
    except Exception as e:
        print(f"    [MultiLayerOverlay] Notice: {e}")
        return clip

def overlay_graphic_badge(
    clip: VideoFileClip,
    label: str = "#1 ADIM",
    icon: str = "💡",
    position: Optional[Tuple[Any, Any]] = None,
    duration: Optional[float] = None
) -> VideoFileClip:
    """
    Item 82: Metin İçi Görsel Çıkartmalar (Stickers / Badges / Counters).
    """
    if not label or getattr(config, 'RENDER_SAFE_MODE', True):
        return clip
    try:
        badge_w, badge_h = 320, 76
        img = PIL.Image.new("RGBA", (badge_w, badge_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Draw sleek pill background with rounded rectangle
        draw.rounded_rectangle([(2, 2), (badge_w - 2, badge_h - 2)], radius=24, fill=(20, 24, 36, 215), outline=(255, 215, 0, 230), width=3)

        display_text = f"{icon}  {label}".strip()
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None

        draw.text((24, 26), display_text, fill=(255, 255, 255, 255), font=font)

        badge_arr = np.array(img)
        badge_clip = ImageClip(badge_arr, ismask=False, transparent=True)
        badge_dur = duration if duration is not None else min(clip.duration, 3.0)
        badge_clip = badge_clip.set_duration(badge_dur)

        pos = position if position is not None else ("center", 120)
        badge_clip = badge_clip.set_position(pos)

        composite = CompositeVideoClip([clip, badge_clip], size=clip.size)
        composite.duration = clip.duration
        return composite
    except Exception as e:
        print(f"    [GraphicBadge] Notice: {e}")
        return clip

def overlay_micro_brand_signature(clip: VideoFileClip, duration: float = 0.40, logo_path: Optional[str] = None) -> VideoFileClip:
    """
    Item 87: Özgün İntro/Outro İmzası.
    Kanalın tüm Shorts videolarında ortak 0.4 saniyelik mikro logo veya marka motifi bulunur.
    """
    try:
        w, h = clip.size
        sig_w, sig_h = int(w * 0.28), 54
        img = PIL.Image.new("RGBA", (sig_w, sig_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([(1, 1), (sig_w - 2, sig_h - 2)], radius=16, fill=(15, 20, 30, 180), outline=(255, 215, 0, 200), width=2)
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None
        draw.text((16, 18), "⚡ OFFICIAL SHORT", fill=(255, 255, 255, 240), font=font)

        sig_arr = np.array(img)
        sig_clip = (
            ImageClip(sig_arr, ismask=False, transparent=True)
            .set_duration(duration)
            .set_position(("center", int(h * 0.08)))
        )
        return CompositeVideoClip([clip, sig_clip], size=clip.size)
    except Exception as e:
        print(f"    [MicroBrandSignature] Notice: {e}")
        return clip

def apply_affiliate_3d_mockup(
    product_img_or_clip: Any,
    target_w: int = 1080,
    target_h: int = 1920,
    shadow_offset: Tuple[int, int] = (14, 20),
    tilt_angle: float = -4.5
) -> VideoFileClip:
    """
    Item 105: Affiliate Ürün Görsellerini Yeniden Boyutlandırma & 3D Mock-up.
    Amazon/Temu/E-ticaret ürün fotoğrafları doğrudan ham kullanılmaz;
    3D gölgeli, eğimli (tilt) ve estetik yuvarlatılmış mock-up kartı içine yerleştirilir.
    """
    try:
        if isinstance(product_img_or_clip, str) and os.path.exists(product_img_or_clip):
            prod_img = PIL.Image.open(product_img_or_clip).convert("RGBA")
        else:
            prod_img = PIL.Image.new("RGBA", (640, 640), (245, 245, 250, 255))
            draw_p = ImageDraw.Draw(prod_img)
            draw_p.rounded_rectangle([(10, 10), (630, 630)], radius=24, outline=(220, 220, 225), width=3)
            draw_p.text((120, 300), "⭐ PREMIUM PRODUCT", fill=(20, 20, 30, 255))

        pw, ph = prod_img.size
        scale = min(680 / pw, 680 / ph)
        nw, nh = int(pw * scale), int(ph * scale)
        prod_resized = prod_img.resize((nw, nh), PIL.Image.ANTIALIAS)

        canvas_w = target_w
        canvas_h = target_h
        canvas = PIL.Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))

        shadow_w, shadow_h = nw + 20, nh + 20
        shadow = PIL.Image.new("RGBA", (shadow_w, shadow_h), (0, 0, 0, 90))
        shadow = shadow.filter(ImageFilter.GaussianBlur(16))

        rotated_prod = prod_resized.rotate(tilt_angle, resample=PIL.Image.BICUBIC, expand=True)
        rw, rh = rotated_prod.size

        cx = (canvas_w - rw) // 2
        cy = (canvas_h - rh) // 2

        canvas.paste(shadow, (cx + shadow_offset[0], cy + shadow_offset[1]), mask=shadow)
        canvas.paste(rotated_prod, (cx, cy), mask=rotated_prod)

        card_arr = np.array(canvas)
        return ImageClip(card_arr, ismask=False, transparent=True)
    except Exception as e:
        print(f"    [AffiliateMockup] Notice: {e}")
        return ColorClip(size=(target_w, target_h), color=(0, 0, 0, 0), duration=3.0)

def generate_retro_avatar_png(output_path: str, avatar_style: str = "auto",
                               size: int = 160, seed: int = None) -> str:
    """
    Item 118 – Konuşmacı İkonu veya Avatar Oluşturma.
    Ekrana hikayeyi anlatan küçük bir retro piksel sanat tarzı karakter veya maskot üretir.
    """
    rng = random.Random(seed or random.randint(0, 9999))

    styles = ["robot", "wizard", "ghost", "astronaut"]
    if avatar_style == "auto":
        avatar_style = rng.choice(styles)

    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cell = size // 16
    half = size // 2

    if avatar_style == "robot":
        draw.rounded_rectangle([cell*3, cell*4, cell*13, cell*14], radius=cell, fill=(60, 65, 75, 240))
        draw.rounded_rectangle([cell*4, cell*1, cell*12, cell*6], radius=cell, fill=(90, 95, 105, 250))
        eye_color = (80, 200, 255, 255)
        draw.ellipse([cell*5, cell*2, cell*7, cell*4], fill=eye_color)
        draw.ellipse([cell*9, cell*2, cell*11, cell*4], fill=eye_color)
        draw.line([cell*6, cell*5, cell*10, cell*5], fill=(150, 155, 165, 200), width=max(1, cell//2))
        draw.line([half, cell*1, half, 0], fill=(120, 125, 135, 220), width=max(1, cell//2))
        draw.ellipse([half-cell, -cell, half+cell, cell], fill=(80, 200, 255, 255))

    elif avatar_style == "wizard":
        draw.polygon([(cell*3, size), (cell*13, size), (cell*12, cell*7), (half, cell*5), (cell*4, cell*7)],
                     fill=(100, 30, 160, 230))
        draw.ellipse([cell*5, cell*3, cell*11, cell*9], fill=(220, 180, 140, 255))
        draw.polygon([(half, 0), (cell*4, cell*4), (cell*12, cell*4)], fill=(60, 10, 100, 255))
        draw.line([cell*4, cell*4, cell*12, cell*4], fill=(255, 200, 50, 255), width=max(1, cell//2))
        draw.ellipse([cell*6, cell*5, cell*8, cell*7], fill=(50, 220, 100, 255))
        draw.ellipse([cell*9, cell*5, cell*11, cell*7], fill=(50, 220, 100, 255))
        draw.arc([cell*5, cell*7, cell*11, cell*10], start=0, end=180, fill=(200, 200, 210, 200), width=max(1, cell//2))

    elif avatar_style == "ghost":
        draw.ellipse([cell*3, cell*2, cell*13, cell*12], fill=(240, 245, 255, 180))
        draw.rectangle([cell*3, cell*7, cell*13, cell*14], fill=(240, 245, 255, 160))
        for i in range(5):
            x_start = cell*3 + i * cell*2
            draw.arc([x_start, cell*12, x_start + cell*2, cell*15], start=0, end=180, fill=(0, 0, 0, 0), width=cell)
        draw.ellipse([cell*5, cell*4, cell*8, cell*7], fill=(30, 30, 50, 220))
        draw.ellipse([cell*9, cell*4, cell*12, cell*7], fill=(30, 30, 50, 220))

    elif avatar_style == "astronaut":
        draw.ellipse([cell*3, cell*1, cell*13, cell*11], fill=(220, 225, 230, 250))
        draw.ellipse([cell*5, cell*3, cell*11, cell*9], fill=(30, 100, 200, 180))
        draw.arc([cell*4, cell*2, cell*8, cell*5], start=210, end=330, fill=(255, 255, 255, 120), width=max(1, cell//2))
        draw.rounded_rectangle([cell*4, cell*9, cell*12, cell*15], radius=cell, fill=(80, 85, 95, 240))
        draw.ellipse([cell*5, cell*10, cell*8, cell*13], fill=(200, 50, 50, 220))

    img.save(output_path, "PNG")
    print(f"    [Item 118] Retro avatar üretildi: style={avatar_style}, size={size}px → {output_path}")
    return output_path

def apply_speaker_avatar_overlay(base_clip, avatar_path: str = None,
                                  position: str = "bottom_left",
                                  avatar_size: int = 140,
                                  animate_bob: bool = True):
    """
    Item 118 – Avatar/Maskot Overlay Bindirmesi.
    Retro piksel sanat karakterini videonun köşesine yerleştirir.
    NOT: RENDER_SAFE_MODE=True iken bypass edilir (animated position → her kare hesaplama).
    """
    try:
        import config as _cfg
        if getattr(_cfg, 'RENDER_SAFE_MODE', True):
            print(f"    [Item 118] Avatar overlay: RENDER_SAFE_MODE aktif, bypass edildi.")
            return base_clip
    except Exception:
        pass

    import tempfile

    if not avatar_path or not os.path.exists(avatar_path):
        tmp_png = tempfile.mktemp(suffix="_avatar.png")
        generate_retro_avatar_png(tmp_png, avatar_style="auto", size=avatar_size)
        avatar_path = tmp_png

    w, h = base_clip.size
    dur = base_clip.duration
    margin = 20

    if position == "bottom_left":
        base_x = margin
        base_y = h - avatar_size - margin
    elif position == "bottom_right":
        base_x = w - avatar_size - margin
        base_y = h - avatar_size - margin
    elif position == "top_left":
        base_x = margin
        base_y = margin
    else:
        base_x = w - avatar_size - margin
        base_y = margin

    if animate_bob:
        def avatar_pos(t):
            bob = int(math.sin(2 * math.pi * t * 1.5) * 4)
            return (base_x, base_y + bob)
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
    print(f"    [Item 118] Avatar overlay: pos={position}, size={avatar_size}px, bob={animate_bob}")
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

def generate_emoji_subtitle_overlay(width: int, height: int, duration: float,
                                     emoji_events: list, fps: float = 30.0) -> VideoClip:
    """
    Item 125 – Altyazılarda Emoji Animasyonu.
    """
    if getattr(config, 'RENDER_SAFE_MODE', True) or not emoji_events:
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
                x1 = max(0, x_center - em_half)
                y1 = max(0, y_center - em_half)
                x2 = min(width, x_center + em_half)
                y2 = min(height, y_center + em_half)

                if x2 > x1 and y2 > y1:
                    alpha = int(220 * scale)
                    frame[y1:y2, x1:x2, 0] = 255
                    frame[y1:y2, x1:x2, 1] = 255
                    frame[y1:y2, x1:x2, 2] = 255
                    frame[y1:y2, x1:x2, 3] = alpha
                    image = Image.fromarray(frame, "RGBA")
                    ImageDraw.Draw(image).text(
                        (x_center, y_center),
                        ev.get("emoji", ""),
                        fill=(20, 20, 30, 255),
                        anchor="mm"
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
    """
    Item 125 – Word timing verisinden emoji event listesi oluşturur.
    """
    events = []
    scene_map = {}
    if scenes:
        current_offset = 0.0
        for sc in scenes:
            dur = sc.get("duration", 6.0)
            mood = sc.get("mood", "default")
            scene_map[current_offset] = mood
            current_offset += dur

    def get_scene_mood_at(t):
        best_mood = "default"
        best_t = -1
        for start_t, mood in scene_map.items():
            if start_t <= t and start_t > best_t:
                best_t = start_t
                best_mood = mood
        return best_mood

    for word in word_timings:
        text = word.get("text", "")
        offset = word.get("offset", 0.0)
        duration = word.get("duration", 0.3)

        if text.strip().endswith((".", "!", "?", "...", ",")):
            mood = get_scene_mood_at(offset)
            emoji = get_mood_emoji(mood)
            events.append({
                "time": offset + duration + 0.05,
                "duration": 0.75,
                "emoji": emoji,
                "y_ratio": 0.82,
                "x_offset": random.randint(-80, 80)
            })

    print(f"    [Item 125] {len(events)} emoji event oluşturuldu (cümle sonları)")
    return events

def generate_end_card_overlay(width: int, height: int, duration: float = 3.0,
                               fps: float = 30.0,
                               channel_name: str = "Kanalımıza Abone Ol",
                               cta_text: str = "Takip Et & Zil Simgesine Bas!",
                               style: str = "dark") -> VideoClip:
    """
    Item 126 – Kapanışta Ekrana Gelen Kartlar (End Card).
    """
    styles = {
        "dark":    {"bg": (0, 0, 0, 200), "primary": (255, 60, 60), "text": (255, 255, 255), "accent": (255, 200, 0)},
        "neon":    {"bg": (10, 0, 30, 210), "primary": (0, 255, 180), "text": (200, 255, 255), "accent": (255, 0, 180)},
        "minimal": {"bg": (255, 255, 255, 180), "primary": (30, 30, 30), "text": (30, 30, 30), "accent": (200, 50, 50)},
        "warm":    {"bg": (40, 15, 5, 200), "primary": (255, 140, 20), "text": (255, 235, 200), "accent": (255, 80, 40)},
    }
    s = styles.get(style, styles["dark"])

    def make_frame(t):
        progress = t / duration

        if progress < 0.4 / duration * duration:
            slide = t / 0.4
        else:
            slide = 1.0
        slide = min(1.0, slide)

        pulse = 0.95 + 0.05 * math.sin(2 * math.pi * t * 2.0)

        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        card_h = int(height * 0.28)
        card_top = int(height - card_h * slide)
        draw.rounded_rectangle(
            [0, card_top, width, height],
            radius=24,
            fill=s["bg"]
        )

        cx = int(width * 0.18)
        cy = int((card_top + height) / 2)
        radius = int(min(width, card_h) * 0.22 * pulse)
        draw.ellipse([cx-radius, cy-radius, cx+radius, cy+radius],
                     fill=s["primary"])

        inner_r = int(radius * 0.55)
        draw.ellipse([cx-inner_r, cy-inner_r, cx+inner_r, cy+inner_r],
                     fill=s["accent"])

        font_size_large = max(24, width // 18)
        text_x = int(width * 0.36)
        text_y = card_top + int(card_h * 0.2)
        draw.text((text_x, text_y), channel_name,
                  fill=s["text"], font=None)

        font_size_small = max(18, width // 26)
        cta_y = text_y + font_size_large + 12
        draw.text((text_x, cta_y), cta_text,
                  fill=s["accent"], font=None)

        alpha_mult = min(1.0, t / 0.3)
        if alpha_mult < 1.0:
            data = np.array(img)
            data[:,:,3] = (data[:,:,3] * alpha_mult).astype(np.uint8)
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

def apply_end_card_to_video(base_clip, duration: float = 3.0,
                             channel_name: str = "Abone Ol",
                             cta_text: str = "Takip Et & Zil Simgesine Bas!",
                             style: str = "dark"):
    """
    Item 126 – Kapanış kartını videonun son N saniyesine ekler.
    """
    if getattr(config, 'RENDER_SAFE_MODE', True):
        print(f"    [Item 126] End card overlay: RENDER_SAFE_MODE aktif, bypass edildi.")
        return base_clip
    w, h = base_clip.size
    dur = base_clip.duration
    fps = base_clip.fps or 30.0

    end_card_duration = min(duration, dur)
    end_card_start = dur - end_card_duration

    end_card = generate_end_card_overlay(
        w, h, duration=end_card_duration, fps=fps,
        channel_name=channel_name, cta_text=cta_text, style=style
    ).set_start(end_card_start)

    composite = CompositeVideoClip([base_clip, end_card], size=(w, h))
    composite.duration = dur
    return composite

def generate_ui_element_overlay(width: int, height: int, duration: float,
                                ui_type: str = "ios_notification",
                                header_text: str = "Önemli Gelişme",
                                body_text: str = "Bunu sonuna kadar izlemelisiniz!",
                                fps: float = 30.0) -> VideoClip:
    """
    Item 131 – Ekrana Sahte Arayüz (UI) Elemanları Ekleme.
    """
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
                [x0, y0, x0 + box_w, y0 + box_h],
                radius=18,
                fill=(28, 30, 42, 225),
                outline=(120, 160, 255, 200),
                width=2
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
                [x0, y0, x0 + box_w, y0 + box_h],
                radius=16,
                fill=(16, 22, 34, 230),
                outline=(29, 155, 240, 210),
                width=2
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
                [x0, y0, x0 + box_w, y0 + box_h],
                radius=box_h // 2,
                fill=(255, 255, 255, 235),
                outline=(210, 220, 230, 240),
                width=2
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

def apply_ui_element_overlay(base_clip, ui_type: str = "ios_notification",
                             header_text: str = "Önemli Bilgi",
                             body_text: str = "Sonuna kadar izleyin!",
                             start_time: float = 0.5,
                             duration: float = 3.5):
    """
    Item 131 – Belirtilen klibe sahte arayüz grafik katmanı bindirir.
    """
    w, h = base_clip.size
    dur = min(duration, max(0.5, base_clip.duration - start_time))
    fps = getattr(base_clip, "fps", None) or 30.0

    ui_clip = generate_ui_element_overlay(
        w, h, duration=dur, ui_type=ui_type,
        header_text=header_text, body_text=body_text, fps=fps
    ).set_start(start_time)

    composite = CompositeVideoClip([base_clip, ui_clip], size=(w, h))
    composite.duration = base_clip.duration
    return composite

def generate_dynamic_progress_bar(width: int, height: int, duration: float,
                                  bar_height: int = 4,
                                  color: tuple = (0, 255, 204),
                                  position: str = "bottom",
                                  fps: float = 30.0) -> VideoClip:
    """
    Item 138 – Dinamik İlerleme Çubuğu.
    Ekranın en altına veya üstüne videonun bittiğini hissettirmeyen ince neon bir
    ilerleme çubuğu koyar. Süre boyunca soldan sağa akıcı bir şekilde dolar.
    """
    def make_rgb(t):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        prog = min(1.0, max(0.0, t / max(0.1, duration)))
        fill_w = int(width * prog)
        y0 = height - bar_height if position == "bottom" else 0
        y1 = height if position == "bottom" else bar_height
        if fill_w > 0:
            frame[y0:y1, 0:fill_w] = color
        return frame

    def make_mask(t):
        mask = np.zeros((height, width), dtype=float)
        prog = min(1.0, max(0.0, t / max(0.1, duration)))
        fill_w = int(width * prog)
        y0 = height - bar_height if position == "bottom" else 0
        y1 = height if position == "bottom" else bar_height
        if fill_w > 0:
            mask[y0:y1, 0:fill_w] = 0.90
        return mask

    mask_clip = VideoClip(make_mask, ismask=True, duration=duration).set_fps(fps)
    bar_clip = VideoClip(make_rgb, ismask=False, duration=duration).set_fps(fps).set_mask(mask_clip)
    print(f"    [Item 138] Dinamik neon ilerleme çubuğu üretildi: pos={position}, h={bar_height}px, {duration:.1f}s")
    return bar_clip

def apply_share_cta_overlay(
    base_clip,
    cta_text: str = "Arkadaşına gönder",
    start_at: float = 0.0,
    duration: float = 3.0,
):
    """Item 235: Paylaşma güdüsü — alt-sol neon paylaş CTA bandı."""
    try:
        w, h = base_clip.size
        dur = base_clip.duration
        show_dur = min(duration, max(0.5, dur - start_at))
        if show_dur <= 0:
            return base_clip
        bar_h = 48
        img = Image.new("RGBA", (int(w * 0.62), bar_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([(0, 0), (img.width - 1, bar_h - 1)], radius=14, fill=(20, 120, 255, 220))
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None
        draw.text((14, 14), f"↗ {cta_text[:36]}", fill=(255, 255, 255, 255), font=font)
        banner = (
            ImageClip(np.array(img), ismask=False, transparent=True)
            .set_duration(show_dur)
            .set_start(start_at)
            .set_position((16, int(h * 0.72)))
        )
        composite = CompositeVideoClip([base_clip, banner], size=(w, h))
        composite.duration = dur
        print(f"    [Item 235] Share CTA overlay @ {start_at:.1f}s")
        return composite
    except Exception as e:
        print(f"    [ShareCTA] Notice: {e}")
        return base_clip


def apply_bookmark_cta_overlay(
    base_clip,
    cta_text: str = "Videoyu kaydet",
    start_at: float = 0.0,
    duration: float = 3.0,
):
    """Item 236: Kaydetme güdüsü — alt-sağ bookmark CTA bandı."""
    try:
        w, h = base_clip.size
        dur = base_clip.duration
        show_dur = min(duration, max(0.5, dur - start_at))
        if show_dur <= 0:
            return base_clip
        bar_h = 48
        img = Image.new("RGBA", (int(w * 0.58), bar_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([(0, 0), (img.width - 1, bar_h - 1)], radius=14, fill=(255, 180, 0, 225))
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None
        draw.text((14, 14), f"🔖 {cta_text[:34]}", fill=(20, 20, 30, 255), font=font)
        banner = (
            ImageClip(np.array(img), ismask=False, transparent=True)
            .set_duration(show_dur)
            .set_start(start_at)
            .set_position((int(w * 0.38), int(h * 0.78)))
        )
        composite = CompositeVideoClip([base_clip, banner], size=(w, h))
        composite.duration = dur
        print(f"    [Item 236] Bookmark CTA overlay @ {start_at:.1f}s")
        return composite
    except Exception as e:
        print(f"    [BookmarkCTA] Notice: {e}")
        return base_clip


def apply_sticky_hook_banner_overlay(
    base_clip,
    banner_text: str = "⚠️ ASLA BUNU YAPMAYIN",
    bar_height: int = 52,
):
    """
    Item 232: Ekranın Üst Kısmına Sabit Kanca Yazısı.
    Video boyunca üstte sabit uyarı/kanca bandı.
    """
    try:
        import config as _cfg
        if getattr(_cfg, "RENDER_SAFE_MODE", True):
            print("    [Item 232] Sticky hook banner: RENDER_SAFE_MODE aktif, bypass edildi.")
            return base_clip
    except Exception:
        pass
    try:
        w, h = base_clip.size
        dur = base_clip.duration
        img = Image.new("RGBA", (w, bar_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rectangle([(0, 0), (w, bar_height)], fill=(180, 0, 0, 210))
        draw.rectangle([(0, bar_height - 3), (w, bar_height)], fill=(255, 230, 0, 255))
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None
        draw.text((16, 16), banner_text[:48], fill=(255, 255, 255, 255), font=font)
        banner = (
            ImageClip(np.array(img), ismask=False, transparent=True)
            .set_duration(dur)
            .set_position(("center", 0))
        )
        composite = CompositeVideoClip([base_clip, banner], size=(w, h))
        composite.duration = dur
        print(f"    [Item 232] Sticky hook banner: {banner_text[:32]}")
        return composite
    except Exception as e:
        print(f"    [StickyHookBanner] Notice: {e}")
        return base_clip


def apply_micro_animated_sticker_overlay(
    base_clip,
    sticker: str = "arrow",
    duration: float = 2.5,
):
    """
    Item 238: Mikro-Animasyonlu Çıkartmalar.
    Zıplayan ok / işaret parmağı ikonu ilgiyi diri tutar.
    """
    try:
        import config as _cfg
        if getattr(_cfg, "RENDER_SAFE_MODE", True):
            print("    [Item 238] Micro animated sticker: RENDER_SAFE_MODE aktif, bypass edildi.")
            return base_clip
    except Exception:
        pass
    try:
        w, h = base_clip.size
        dur = min(duration, base_clip.duration)
        icons = {"arrow": "⬇️", "point": "👆", "circle": "⭕"}
        icon = icons.get(sticker, "⬇️")
        sticker_w, sticker_h = 96, 96
        img = Image.new("RGBA", (sticker_w, sticker_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None
        draw.text((20, 20), icon, fill=(255, 255, 255, 255), font=font)
        arr = np.array(img)

        def bounce_pos(t):
            bounce = int(12 * abs(math.sin(t * 5.0)))
            return (int(w * 0.78), int(h * 0.38) + bounce)

        sticker_clip = (
            ImageClip(arr, ismask=False, transparent=True)
            .set_duration(dur)
            .set_position(bounce_pos)
        )
        composite = CompositeVideoClip([base_clip, sticker_clip], size=(w, h))
        composite.duration = base_clip.duration
        print(f"    [Item 238] Micro animated sticker: {sticker}")
        return composite
    except Exception as e:
        print(f"    [MicroAnimatedSticker] Notice: {e}")
        return base_clip


def apply_dynamic_progress_bar(base_clip, bar_height: int = 4,
                               color: tuple = (0, 255, 204),
                               position: str = "bottom"):
    """
    Item 138 – Temel klibin üzerine dinamik neon ilerleme çubuğu bindirir.
    NOT: RENDER_SAFE_MODE=True iken bypass edilir (tüm video süresince per-frame çizim).
    """
    try:
        import config as _cfg
        if getattr(_cfg, 'RENDER_SAFE_MODE', True):
            print(f"    [Item 138] Dinamik ilerleme çubuğu: RENDER_SAFE_MODE aktif, bypass edildi.")
            return base_clip
    except Exception:
        pass

    w, h = base_clip.size
    dur = base_clip.duration
    fps = base_clip.fps or 30.0

    bar = generate_dynamic_progress_bar(
        w, h, duration=dur, bar_height=bar_height,
        color=color, position=position, fps=fps
    )
    composite = CompositeVideoClip([base_clip, bar], size=(w, h))
    composite.duration = dur
    return composite

def generate_neon_countdown_overlay(
    width: int,
    height: int,
    duration: float = 3.0,
    position: str = "top_right",
    fps: float = 30.0,
    lang: str = "tr",
) -> VideoClip:
    """
    Item 212: Geri Sayım Sayacı (Countdown Timer).
    Köşede 3..2..1 neon sayaç; quiz/merak formatlarında retention kancası.
    """
    countdown_nums = [3, 2, 1]
    sec_per_num = duration / len(countdown_nums)
    neon_rgb = (0, 255, 102)
    glow_rgb = (255, 230, 0)

    def make_rgba(t):
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        if t >= duration:
            return np.array(img)

        idx = min(int(t / sec_per_num), len(countdown_nums) - 1)
        num = countdown_nums[idx]
        local_t = t - idx * sec_per_num
        pulse = 0.88 + 0.12 * math.sin(2 * math.pi * local_t * 4.0)

        box = int(min(width, height) * 0.11 * pulse)
        margin = int(width * 0.05)
        if position == "top_left":
            x0, y0 = margin, int(height * 0.07)
        else:
            x0, y0 = width - margin - box, int(height * 0.07)

        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle(
            [x0, y0, x0 + box, y0 + box],
            radius=max(8, box // 5),
            fill=(8, 12, 24, 215),
            outline=glow_rgb + (255,),
            width=3,
        )
        inner = max(8, box // 6)
        draw.rounded_rectangle(
            [x0 + inner, y0 + inner, x0 + box - inner, y0 + box - inner],
            radius=max(6, box // 7),
            outline=neon_rgb + (180,),
            width=2,
        )
        draw.text(
            (x0 + box // 2, y0 + box // 2),
            str(num),
            fill=neon_rgb + (255,),
            anchor="mm",
        )
        if idx == 0 and local_t < 0.35:
            hint = "GÖSTERİLİYOR" if lang == "tr" else "REVEAL"
            draw.text(
                (x0 + box // 2, y0 + box + 18),
                hint,
                fill=glow_rgb + (220,),
                anchor="mm",
            )
        return np.array(img)

    def make_rgb(t):
        return make_rgba(t)[:, :, :3].astype(np.uint8)

    def make_mask(t):
        return make_rgba(t)[:, :, 3].astype(float) / 255.0

    mask = VideoClip(make_mask, ismask=True, duration=duration).set_fps(fps)
    clip = VideoClip(make_rgb, ismask=False, duration=duration).set_fps(fps).set_mask(mask)
    print(f"    [Item 212] Neon countdown overlay: {duration:.1f}s, pos={position}")
    return clip

def apply_neon_countdown_overlay(
    base_clip,
    duration: float = 3.0,
    position: str = "top_right",
    lang: str = "tr",
):
    """
    Item 212 – Videonun ilk N saniyesine neon geri sayım bindirir.
    """
    try:
        import config as _cfg
        if getattr(_cfg, 'RENDER_SAFE_MODE', True):
            print("    [Item 212] Neon countdown: RENDER_SAFE_MODE aktif, bypass edildi.")
            return base_clip
    except Exception:
        pass

    w, h = base_clip.size
    dur = min(duration, base_clip.duration)
    fps = base_clip.fps or 30.0
    overlay = generate_neon_countdown_overlay(
        w, h, duration=dur, position=position, fps=fps, lang=lang
    ).set_start(0)
    composite = CompositeVideoClip([base_clip, overlay], size=(w, h))
    composite.duration = base_clip.duration
    return composite


def generate_neon_curiosity_opening_graphic(
    width: int,
    height: int,
    duration: float = 2.5,
    symbol: str = "?",
    fps: float = 30.0,
) -> VideoClip:
    """
    Item 246: Merak Tetikleyici Açılış Grafiği — neon soru/ünlem işareti parlaması.
    """
    neon_rgb = (255, 0, 255)
    glow_rgb = (0, 255, 255)

    def make_rgba(t):
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        if t >= duration:
            return np.array(img)
        fade = 1.0 if t < duration * 0.85 else max(0.0, 1.0 - (t - duration * 0.85) / (duration * 0.15))
        pulse = 0.82 + 0.18 * math.sin(2 * math.pi * t * 3.5)
        size = int(min(width, height) * 0.18 * pulse * fade)
        cx, cy = width // 2, int(height * 0.42)
        draw = ImageDraw.Draw(img)
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", size)
        except Exception:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), symbol, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x0, y0 = cx - tw // 2, cy - th // 2
        for offset, alpha in ((4, 90), (2, 140), (0, 255)):
            draw.text(
                (x0 + offset, y0 + offset),
                symbol,
                font=font,
                fill=glow_rgb + (int(alpha * fade),),
            )
        draw.text((x0, y0), symbol, font=font, fill=neon_rgb + (int(255 * fade),))
        return np.array(img)

    clip = VideoClip(make_frame=lambda t: make_rgba(t)[:, :, :3], duration=duration)
    clip = clip.set_fps(fps).set_mask(
        VideoClip(make_frame=lambda t: make_rgba(t)[:, :, 3] / 255.0, ismask=True, duration=duration).set_fps(fps)
    )
    print(f"    [Item 246] Neon curiosity opening graphic: symbol={symbol}, {duration:.1f}s")
    return clip


def apply_neon_curiosity_opening_graphic(
    base_clip,
    duration: float = 2.5,
    symbol: str = "?",
):
    """
    Item 246 – Videonun açılışına neon soru/ünlem grafiği bindirir.
    """
    try:
        import config as _cfg
        if getattr(_cfg, 'RENDER_SAFE_MODE', True):
            print("    [Item 246] Neon curiosity graphic: RENDER_SAFE_MODE aktif, bypass edildi.")
            return base_clip
    except Exception:
        pass

    w, h = base_clip.size
    dur = min(duration, base_clip.duration)
    fps = base_clip.fps or 30.0
    overlay = generate_neon_curiosity_opening_graphic(
        w, h, duration=dur, symbol=symbol, fps=fps
    ).set_start(0)
    composite = CompositeVideoClip([base_clip, overlay], size=(w, h))
    composite.duration = base_clip.duration
    return composite


def apply_keyword_white_flash_overlay(
    base_clip,
    timestamp: float = 0.0,
    duration: float = 0.18,
    peak_alpha: float = 0.82,
):
    """
    Item 260: Görsel Aydınlanma Anı (Flash of Light).
    Kilit kelime anında ekrandan beyaz ışık süzmesi — kısa fade-in/out overlay.
    """
    try:
        import config as _cfg
        if getattr(_cfg, "RENDER_SAFE_MODE", True):
            print("    [Item 260] White flash: RENDER_SAFE_MODE aktif, bypass edildi.")
            return base_clip
    except Exception:
        pass

    w, h = base_clip.size
    # ColorClip and some ImageClips omit .fps until set_fps(); getattr avoids AttributeError.
    fps = getattr(base_clip, "fps", None) or 30.0
    flash_dur = min(duration, max(0.05, base_clip.duration - timestamp))
    if flash_dur <= 0 or timestamp >= base_clip.duration:
        return base_clip

    def make_rgba(t):
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        local = t / flash_dur if flash_dur > 0 else 0.0
        if local <= 0.5:
            alpha = peak_alpha * (local / 0.5)
        else:
            alpha = peak_alpha * (1.0 - (local - 0.5) / 0.5)
        alpha = max(0.0, min(1.0, alpha))
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, 0, w, h], fill=(255, 255, 255, int(alpha * 255)))
        return np.array(img)

    def make_rgb(t):
        return make_rgba(t)[:, :, :3].astype(np.uint8)

    def make_mask(t):
        return make_rgba(t)[:, :, 3].astype(float) / 255.0

    mask = VideoClip(make_mask, ismask=True, duration=flash_dur).set_fps(fps)
    overlay = VideoClip(make_rgb, ismask=False, duration=flash_dur).set_fps(fps).set_mask(mask)
    overlay = overlay.set_start(timestamp)
    composite = CompositeVideoClip([base_clip, overlay], size=(w, h))
    composite.duration = base_clip.duration
    print(f"    [Item 260] Keyword white flash @ {timestamp:.2f}s ({flash_dur:.2f}s)")
    return composite


def apply_infinite_spiral_overlay(
    base_clip,
    duration: float = 4.0,
    opacity: float = 0.35,
    rotation_speed: float = 0.8,
):
    """
    Item 224: Sonsuz Sarmal Animasyonu — merkezde dönen hipnotik spiral overlay.
    """
    try:
        import config as _cfg
        if getattr(_cfg, "RENDER_SAFE_MODE", True):
            print("    [Item 224] Infinite spiral: RENDER_SAFE_MODE aktif, bypass edildi.")
            return base_clip
    except Exception:
        pass

    w, h = base_clip.size
    fps = getattr(base_clip, "fps", None) or 30.0
    dur = min(duration, base_clip.duration)
    cx, cy = w // 2, h // 2
    max_r = int(min(w, h) * 0.45)

    def make_rgba(t):
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        angle_offset = t * rotation_speed * 360.0
        for arm in range(3):
            base_angle = angle_offset + arm * 120.0
            for step in range(40):
                r = max_r * (step / 40.0)
                theta = math.radians(base_angle + step * 18.0)
                x = cx + r * math.cos(theta)
                y = cy + r * math.sin(theta)
                alpha = int(255 * opacity * (1.0 - step / 40.0))
                draw.ellipse([x - 3, y - 3, x + 3, y + 3], fill=(180, 220, 255, alpha))
        return np.array(img)

    def make_rgb(t):
        return make_rgba(t)[:, :, :3].astype(np.uint8)

    def make_mask(t):
        return make_rgba(t)[:, :, 3].astype(float) / 255.0

    mask = VideoClip(make_mask, ismask=True, duration=dur).set_fps(fps)
    overlay = VideoClip(make_rgb, ismask=False, duration=dur).set_fps(fps).set_mask(mask).set_start(0)
    composite = CompositeVideoClip([base_clip, overlay], size=(w, h))
    composite.duration = base_clip.duration
    print(f"    [Item 224] Infinite spiral overlay ({dur:.1f}s, opacity={opacity})")
    return composite


def apply_time_tunnel_overlay(
    base_clip,
    duration: float = 3.5,
    streak_count: int = 24,
    opacity: float = 0.42,
):
    """
    Item 261: Zaman Tüneli Hissi — radial streak / zoom warp overlay.
    """
    try:
        import config as _cfg
        if getattr(_cfg, "RENDER_SAFE_MODE", True):
            print("    [Item 261] Time tunnel: RENDER_SAFE_MODE aktif, bypass edildi.")
            return base_clip
    except Exception:
        pass

    w, h = base_clip.size
    fps = getattr(base_clip, "fps", None) or 30.0
    dur = min(duration, base_clip.duration)
    cx, cy = w // 2, h // 2

    def make_rgba(t):
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        pulse = 0.5 + 0.5 * math.sin(t * 4.0)
        for i in range(streak_count):
            angle = (360.0 / streak_count) * i + t * 120.0
            rad = math.radians(angle)
            inner = int(min(w, h) * 0.08)
            outer = int(min(w, h) * (0.35 + 0.25 * pulse))
            x0 = cx + inner * math.cos(rad)
            y0 = cy + inner * math.sin(rad)
            x1 = cx + outer * math.cos(rad)
            y1 = cy + outer * math.sin(rad)
            alpha = int(255 * opacity * (0.4 + 0.6 * pulse))
            draw.line([x0, y0, x1, y1], fill=(120, 200, 255, alpha), width=3)
        draw.ellipse(
            [cx - inner, cy - inner, cx + inner, cy + inner],
            fill=(255, 255, 255, int(80 * opacity)),
        )
        return np.array(img)

    def make_rgb(t):
        return make_rgba(t)[:, :, :3].astype(np.uint8)

    def make_mask(t):
        return make_rgba(t)[:, :, 3].astype(float) / 255.0

    mask = VideoClip(make_mask, ismask=True, duration=dur).set_fps(fps)
    overlay = VideoClip(make_rgb, ismask=False, duration=dur).set_fps(fps).set_mask(mask).set_start(0)
    composite = CompositeVideoClip([base_clip, overlay], size=(w, h))
    composite.duration = base_clip.duration
    print(f"    [Item 261] Time tunnel overlay ({dur:.1f}s)")
    return composite


def _overlay_safe_mode_bypass(base_clip, item_label: str):
    try:
        if getattr(config, "RENDER_SAFE_MODE", True):
            print(f"    [{item_label}] RENDER_SAFE_MODE aktif, bypass edildi.")
            return base_clip
    except Exception:
        pass
    return None


def _make_procedural_rgba_clip(base_clip, duration: float, frame_fn):
    w, h = base_clip.size
    fps = getattr(base_clip, "fps", None) or 30.0
    dur = min(duration, base_clip.duration)

    def make_rgb(t):
        return frame_fn(t)[:, :, :3].astype(np.uint8)

    def make_mask(t):
        return frame_fn(t)[:, :, 3].astype(float) / 255.0

    mask = VideoClip(make_mask, ismask=True, duration=dur).set_fps(fps)
    overlay = VideoClip(make_rgb, ismask=False, duration=dur).set_fps(fps).set_mask(mask).set_start(0)
    composite = CompositeVideoClip([base_clip, overlay], size=(w, h))
    composite.duration = base_clip.duration
    return composite


def apply_hybrid_frame_overlay(
    base_clip,
    label: str = "",
    bg_style: str = "",
    accent_rgb: Tuple[int, int, int] = (0, 255, 200),
    opacity: float = 0.85,
):
    """
    B5 generic hybrid frame — niche label bar + accent border (Items 289–345 fallback).
    """
    bypass = _overlay_safe_mode_bypass(base_clip, "B5 hybrid_frame")
    if bypass is not None:
        return bypass

    w, h = base_clip.size
    fps = getattr(base_clip, "fps", None) or 30.0
    dur = base_clip.duration
    display = (label or bg_style or "HYBRID")[:42]
    accent = accent_rgb

    def make_rgba(t):
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        pulse = 0.65 + 0.35 * math.sin(t * 3.0)
        border = int(3 + pulse * 2)
        draw.rectangle([8, 8, w - 8, h - 8], outline=(*accent, int(220 * opacity)), width=border)
        bar_h = int(h * 0.07)
        draw.rectangle([0, h - bar_h, w, h], fill=(10, 12, 20, int(200 * opacity)))
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", max(18, w // 28))
        except Exception:
            font = ImageFont.load_default()
        draw.text((24, h - bar_h + 8), display.upper(), fill=(*accent, 255), font=font)
        return np.array(img)

    out = _make_procedural_rgba_clip(base_clip, dur, make_rgba)
    print(f"    [B5] Hybrid frame overlay ({display[:24]})")
    return out


def apply_neon_frame_overlay(base_clip, opacity: float = 0.9):
    """Item 276: cyberpunk neon corner brackets."""
    bypass = _overlay_safe_mode_bypass(base_clip, "Item 276 neon_frame")
    if bypass is not None:
        return bypass

    w, h = base_clip.size
    dur = base_clip.duration
    colors = [(0, 255, 220), (255, 0, 180)]

    def make_rgba(t):
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        seg = int(min(w, h) * 0.12)
        for idx, col in enumerate(colors):
            off = int(12 + 4 * math.sin(t * 4 + idx))
            x0, y0 = off, off
            x1, y1 = w - off, h - off
            draw.line([x0, y0, x0 + seg, y0], fill=(*col, int(230 * opacity)), width=4)
            draw.line([x0, y0, x0, y0 + seg], fill=(*col, int(230 * opacity)), width=4)
            draw.line([x1, y0, x1 - seg, y0], fill=(*col, int(230 * opacity)), width=4)
            draw.line([x1, y0, x1, y0 + seg], fill=(*col, int(230 * opacity)), width=4)
            draw.line([x0, y1, x0 + seg, y1], fill=(*col, int(230 * opacity)), width=4)
            draw.line([x0, y1, x0, y1 - seg], fill=(*col, int(230 * opacity)), width=4)
            draw.line([x1, y1, x1 - seg, y1], fill=(*col, int(230 * opacity)), width=4)
            draw.line([x1, y1, x1, y1 - seg], fill=(*col, int(230 * opacity)), width=4)
        return np.array(img)

    out = _make_procedural_rgba_clip(base_clip, dur, make_rgba)
    print("    [Item 276] Neon frame overlay applied.")
    return out


def apply_epic_vignette_overlay(base_clip, opacity: float = 0.55):
    """Item 282: cinematic gold-edge vignette."""
    bypass = _overlay_safe_mode_bypass(base_clip, "Item 282 epic_vignette")
    if bypass is not None:
        return bypass

    w, h = base_clip.size
    dur = base_clip.duration

    def make_rgba(t):
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, 0, w, h], fill=(0, 0, 0, int(90 * opacity)))
        inset = int(min(w, h) * 0.06)
        draw.rectangle(
            [inset, inset, w - inset, h - inset],
            outline=(255, 210, 120, int(180 * opacity)),
            width=3,
        )
        return np.array(img)

    out = _make_procedural_rgba_clip(base_clip, dur, make_rgba)
    print("    [Item 282] Epic vignette overlay applied.")
    return out


def apply_soft_vignette_overlay(base_clip, opacity: float = 0.35):
    """Item 285: warm soft vignette for spiritual/rain niches."""
    bypass = _overlay_safe_mode_bypass(base_clip, "Item 285 soft_vignette")
    if bypass is not None:
        return bypass

    w, h = base_clip.size
    dur = base_clip.duration

    def make_rgba(t):
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, 0, w, h], fill=(255, 245, 230, int(40 * opacity)))
        draw.rectangle([0, h - int(h * 0.18), w, h], fill=(20, 30, 50, int(120 * opacity)))
        return np.array(img)

    out = _make_procedural_rgba_clip(base_clip, dur, make_rgba)
    print("    [Item 285] Soft vignette overlay applied.")
    return out


def apply_countdown_wheel_overlay(base_clip, duration: float = 4.0, opacity: float = 0.75):
    """Item 327: spinning stop-wheel game overlay."""
    bypass = _overlay_safe_mode_bypass(base_clip, "Item 327 countdown_wheel")
    if bypass is not None:
        return bypass

    w, h = base_clip.size
    dur = min(duration, base_clip.duration)
    cx, cy = w // 2, int(h * 0.62)
    radius = int(min(w, h) * 0.22)

    def make_rgba(t):
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        angle = t * 220.0
        for i in range(8):
            a = math.radians(angle + i * 45)
            x = cx + radius * math.cos(a)
            y = cy + radius * math.sin(a)
            col = (255, 60, 60) if i % 2 == 0 else (60, 120, 255)
            draw.polygon(
                [cx, cy, x, y, cx + radius * 0.3 * math.cos(a + 0.4), cy + radius * 0.3 * math.sin(a + 0.4)],
                fill=(*col, int(200 * opacity)),
            )
        draw.ellipse([cx - 12, cy - 12, cx + 12, cy + 12], fill=(255, 255, 255, int(240 * opacity)))
        draw.text((cx - 28, cy - 10), "DUR!", fill=(20, 20, 30, 255))
        return np.array(img)

    out = _make_procedural_rgba_clip(base_clip, dur, make_rgba)
    print(f"    [Item 327] Countdown wheel overlay ({dur:.1f}s)")
    return out


def apply_eq_bar_overlay(base_clip, duration: float = None, bar_count: int = 16, opacity: float = 0.8):
    """Item 325: subtitle-area EQ visualizer bars."""
    bypass = _overlay_safe_mode_bypass(base_clip, "Item 325 eq_bar")
    if bypass is not None:
        return bypass

    w, h = base_clip.size
    dur = min(duration or base_clip.duration, base_clip.duration)
    base_y = int(h * 0.82)
    bar_w = max(4, w // (bar_count * 2))

    def make_rgba(t):
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        for i in range(bar_count):
            x = int(w * 0.1) + i * (bar_w + 4)
            level = abs(math.sin(t * 6.0 + i * 0.7)) * 0.85 + 0.1
            bh = int(h * 0.08 * level)
            col = (0, 255, 180) if i % 3 else (120, 200, 255)
            draw.rectangle([x, base_y - bh, x + bar_w, base_y], fill=(*col, int(220 * opacity)))
        return np.array(img)

    out = _make_procedural_rgba_clip(base_clip, dur, make_rgba)
    print(f"    [Item 325] EQ bar overlay ({dur:.1f}s)")
    return out


def apply_split_choice_overlay(base_clip, header: str = "SEÇ", body: str = "Kırmızı vs Mavi", duration: float = 3.5):
    """Items 280/284: red vs blue split choice panel."""
    bypass = _overlay_safe_mode_bypass(base_clip, "split_choice")
    if bypass is not None:
        return bypass

    w, h = base_clip.size
    dur = min(duration, base_clip.duration)

    def make_rgba(t):
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        mid = w // 2
        draw.rectangle([0, int(h * 0.55), mid, int(h * 0.78)], fill=(220, 40, 40, 180))
        draw.rectangle([mid, int(h * 0.55), w, int(h * 0.78)], fill=(40, 80, 220, 180))
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", max(20, w // 24))
        except Exception:
            font = ImageFont.load_default()
        draw.text((w // 4 - 20, int(h * 0.58)), "A", fill=(255, 255, 255, 255), font=font)
        draw.text((mid + w // 4 - 20, int(h * 0.58)), "B", fill=(255, 255, 255, 255), font=font)
        draw.text((24, int(h * 0.50)), header[:24], fill=(255, 255, 255, 230), font=font)
        return np.array(img)

    out = _make_procedural_rgba_clip(base_clip, dur, make_rgba)
    print("    [B5] Split choice overlay applied.")
    return out


def apply_subtitle_bar_overlay(base_clip, header: str = "Dizi", body: str = "Kelime...", duration: float = 4.0):
    """Item 288: TV subtitle bar overlay."""
    bypass = _overlay_safe_mode_bypass(base_clip, "subtitle_bar")
    if bypass is not None:
        return bypass

    w, h = base_clip.size
    dur = min(duration, base_clip.duration)

    def make_rgba(t):
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        bar_y = int(h * 0.72)
        draw.rectangle([40, bar_y, w - 40, bar_y + int(h * 0.08)], fill=(0, 0, 0, 190))
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", max(18, w // 30))
        except Exception:
            font = ImageFont.load_default()
        draw.text((56, bar_y + 8), f"{header}: {body}"[:48], fill=(255, 255, 100, 255), font=font)
        return np.array(img)

    out = _make_procedural_rgba_clip(base_clip, dur, make_rgba)
    print("    [Item 288] Subtitle bar overlay applied.")
    return out


def apply_hybrid_render_overlay(base_clip, overlay_spec: dict):
    """Dispatch B5 hybrid overlay spec → concrete MoviePy overlay."""
    if not overlay_spec:
        return base_clip
    kind = overlay_spec.get("overlay")
    ui_type = overlay_spec.get("ui_type")
    if ui_type == "split_choice":
        return apply_split_choice_overlay(
            base_clip,
            header=overlay_spec.get("header", "SEÇ"),
            body=overlay_spec.get("body", ""),
        )
    if ui_type == "subtitle_bar":
        return apply_subtitle_bar_overlay(
            base_clip,
            header=overlay_spec.get("header", "Dizi"),
            body=overlay_spec.get("body", ""),
        )
    if kind == "neon_frame":
        return apply_neon_frame_overlay(base_clip)
    if kind == "epic_vignette":
        return apply_epic_vignette_overlay(base_clip)
    if kind == "soft_vignette":
        return apply_soft_vignette_overlay(base_clip)
    if kind == "spiral":
        return apply_infinite_spiral_overlay(base_clip)
    if kind == "time_tunnel":
        return apply_time_tunnel_overlay(base_clip)
    if kind == "countdown_wheel":
        return apply_countdown_wheel_overlay(base_clip)
    if kind == "eq_bar":
        return apply_eq_bar_overlay(base_clip)
    if kind == "hybrid_frame":
        label = str(
            overlay_spec.get("label")
            or overlay_spec.get("item")
            or overlay_spec.get("hybrid_id")
            or ""
        )
        return apply_hybrid_frame_overlay(
            base_clip,
            label=label,
            bg_style=overlay_spec.get("bg_style", ""),
        )
    return base_clip
