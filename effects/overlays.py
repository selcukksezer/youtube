"""
Graphic Overlays, Watermarks, Badges, Avatars & UI Cards
Covers items: 59, 60, 75, 82, 87, 92, 105, 118, 125, 126, 131, 138
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

def extract_frame0_thumbnail(video_path: str, output_thumb_path: str) -> bool:
    """
    Items 59, 92: Extract Frame 0 / Peak curiosity frame for Shorts thumbnail.
    """
    if not os.path.exists(video_path):
        return False
    try:
        cmd = [
            "ffmpeg", "-y", "-ss", "00:00:01", "-i", video_path,
            "-frames:v", "1", "-q:v", "2", output_thumb_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return res.returncode == 0
    except Exception:
        return False

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
    fps = base_clip.fps or 30.0

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
