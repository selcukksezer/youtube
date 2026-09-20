"""
Layout, Sizing & Cropping Effects
Covers items: 3, 40, 49, 77, 95, 97, 106, 124
"""
import os, random, subprocess
from typing import Optional, Tuple, Any
from moviepy.editor import (
    VideoFileClip, ColorClip, CompositeVideoClip, ImageClip,
    vfx
)
import numpy as np
from PIL import Image, ImageFilter
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = getattr(Image, 'Resampling', Image).LANCZOS

import imageio_ffmpeg
import config

def apply_smart_crop(clip: VideoFileClip, target_w: int, target_h: int, blur_intensity: float = 0.40) -> VideoFileClip:
    """
    Item 77 & 40: Yatay Kaynakları 9:16 Yaparken Akıllı Kırpma (Smart Crop).
    16:9 klibin arkasına %40 bulanıklaştırılmış (Gaussian blur) kopyası yerleştirilmeli;
    asla siyah boşluk bırakılmamalıdır.
    """
    w, h = clip.size
    aspect = w / h
    target_aspect = target_w / target_h

    # If already roughly 9:16 portrait, simply resize to fill
    if abs(aspect - target_aspect) < 0.05:
        c_fill = clip.resize(height=target_h) if clip.h != target_h else clip
        return c_fill.crop(x_center=c_fill.w / 2, y_center=c_fill.h / 2, width=target_w, height=target_h)

    # Horizontal or square video: blurred background + centered crisp video
    try:
        # Extract a static frame for blurred background to avoid running a second FFmpeg reader process
        mid_t = min(clip.duration / 2.0, max(0.0, clip.duration - 0.1))
        frame_raw = clip.get_frame(mid_t)
        img = Image.fromarray(frame_raw.astype(np.uint8))

        # Scale to cover target_w, target_h
        img_w, img_h = img.size
        scale = max(target_w / img_w, target_h / img_h)
        scaled_w, scaled_h = int(img_w * scale), int(img_h * scale)
        img_scaled = img.resize((scaled_w, scaled_h), Image.BILINEAR)
        left = (scaled_w - target_w) // 2
        top = (scaled_h - target_h) // 2
        img_cropped = img_scaled.crop((left, top, left + target_w, top + target_h))

        blurred_bg = img_cropped.filter(ImageFilter.GaussianBlur(radius=25))
        bg = ImageClip(np.array(blurred_bg)).set_duration(clip.duration)

        # Center foreground: fits horizontally within target_w without distortion
        fg = clip.resize(width=target_w) if clip.w != target_w else clip
        if fg.h > target_h:
            fg = fg.resize(height=target_h)

        fg = fg.set_position("center")
        composite = CompositeVideoClip([bg, fg], size=(target_w, target_h))
        composite.duration = clip.duration
        return composite
    except Exception as e:
        print(f"    [SmartCrop] Fallback due to: {e}")
        c_fill = clip.resize(height=target_h) if clip.h != target_h else clip
        return c_fill.crop(x_center=c_fill.w / 2, y_center=c_fill.h / 2, width=target_w, height=target_h)

def create_split_screen_clip(
    top_clip: VideoFileClip,
    bottom_clip_path: str,
    target_w: int,
    target_h: int,
    divider_color: Tuple[int, int, int] = (0, 255, 204),
    divider_thickness: int = 2
) -> VideoFileClip:
    """
    Items 3, 49 & 97: Ekranın Üst ve Altını Doldurma (Split-Screen 58/42 + Neon Ayırıcı Çizgi).
    - Üst %58: Ana sahne klibi (akıllı kırpılmış ve mükemmel hizalanmış)
    - Alt %42: İkincil oynanış/arka plan klibi
    - Araya tam birleşim noktasına 2 piksellik neon ayırıcı çizgi çekilir.
    """
    top_h = int(target_h * 0.58)
    bottom_h = target_h - top_h

    # Prepare top clip (58%)
    prep_top = apply_smart_crop(top_clip, target_w, top_h).set_position(("center", 0))

    # Prepare bottom gameplay/b-roll clip (42%)
    prep_bottom = None
    if os.path.exists(bottom_clip_path):
        try:
            bot_raw = VideoFileClip(bottom_clip_path)
            if bot_raw.w > target_w * 1.2 or bot_raw.h > bottom_h * 1.5:
                bot_raw = bot_raw.resize(width=target_w)
            # Loop or trim to match top clip duration
            if bot_raw.duration < top_clip.duration:
                bot_raw = bot_raw.fx(vfx.loop, duration=top_clip.duration)
            else:
                bot_raw = bot_raw.subclip(0, top_clip.duration)
            prep_bottom = apply_smart_crop(bot_raw, target_w, bottom_h).set_position(("center", top_h))
        except Exception as e:
            print(f"    [SplitScreen] Error loading bottom clip: {e}")

    if prep_bottom is None:
        # Fallback bottom clip: dark gradient ambient background if path is missing
        prep_bottom = ColorClip(size=(target_w, bottom_h), color=(15, 20, 30), duration=top_clip.duration).set_position(("center", top_h))

    # Item 97: 2 piksellik neon ayırıcı çizgi
    divider = (
        ColorClip(size=(target_w, divider_thickness), color=divider_color, duration=top_clip.duration)
        .set_position(("center", top_h - (divider_thickness // 2)))
    )

    composite = CompositeVideoClip([prep_top, prep_bottom, divider], size=(target_w, target_h))
    composite.duration = top_clip.duration
    return composite

def apply_pip_overlay(
    main_clip: VideoFileClip,
    pip_clip_or_path: Optional[str] = None,
    position: Tuple[Any, Any] = ("right", 60),
    scale: float = 0.28,
    duration: Optional[float] = None
) -> VideoFileClip:
    """
    Item 95: Çift Stok Katmanı (Picture-in-Picture / PIP).
    Bazı sahnelerde ana görüntünün köşesinde küçük bir açıklayıcı grafik,
    grafik kartı veya ikincil B-roll penceresi açılır.
    """
    try:
        mw, mh = main_clip.size
        pip_w = int(mw * scale)
        dur = duration if duration is not None else min(main_clip.duration, 3.5)

        if pip_clip_or_path and os.path.exists(pip_clip_or_path):
            pip_clip = (
                VideoFileClip(pip_clip_or_path)
                .resize(width=pip_w)
                .set_duration(dur)
                .set_position(position)
            )
            return CompositeVideoClip([main_clip, pip_clip], size=main_clip.size)

        from PIL import ImageDraw, ImageFont
        card_w, card_h = pip_w, int(pip_w * 0.58)
        img = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([(2, 2), (card_w - 2, card_h - 2)], radius=18, fill=(10, 15, 25, 220), outline=(0, 255, 127, 230), width=2)
        try:
            font = ImageFont.load_default()
        except Exception:
            font = None
        draw.text((16, 14), "📊 ANALİTİK KART", fill=(0, 255, 127, 255), font=font)
        for i, h_bar in enumerate([12, 22, 16, 30, 26, 38, 20, 32, 28]):
            draw.line([(20 + i * 14, card_h - 18), (20 + i * 14, card_h - 18 - h_bar)], fill=(255, 215, 0, 230), width=4)

        arr = np.array(img)
        card_clip = (
            ImageClip(arr, ismask=False, transparent=True)
            .set_duration(dur)
            .set_position(position)
        )
        return CompositeVideoClip([main_clip, card_clip], size=main_clip.size)
    except Exception as e:
        print(f"    [PIPOverlay] Notice: {e}")
        return main_clip

def apply_corner_radius_to_clip(clip, radius: int = 40):
    """
    Item 106 – Görsel Kenar Yuvarlama (Corner Radius).
    Bir MoviePy klibinin köşelerini yuvarlatılmış dörtgen alfa maskesiyle maskeler.
    Standart dikdörtgen YouTube şablonlarından ayrışmayı sağlar.
    """
    from PIL import Image, ImageDraw

    # Her render'da hafif varyasyon (38-44 px arası)
    r = radius + random.randint(-2, 4)
    r = max(10, r)

    w, h = clip.size

    def make_mask_frame(t):
        mask_img = Image.new("L", (w, h), 0)
        draw = ImageDraw.Draw(mask_img)
        draw.rounded_rectangle([0, 0, w - 1, h - 1], radius=r, fill=255)
        return np.array(mask_img) / 255.0

    from moviepy.editor import ImageClip as _IC
    mask_clip = _IC(make_mask_frame(0), ismask=True).set_duration(clip.duration)
    result = clip.set_mask(mask_clip)
    print(f"    [Item 106] Corner radius={r}px uygulandı ({w}x{h} clip)")
    return result

def apply_corner_radius_ffmpeg(input_path: str, output_path: str, radius: int = 40) -> str:
    """
    Item 106 – FFmpeg tabanlı köşe yuvarlama (geçici PNG maske yöntemi).
    MoviePy kullanmak istemediğinizde bu alternatifi kullanın.
    FFmpeg'in alphamerge + geom_mask zincirleme filtresini kullanır.
    """
    import tempfile
    from PIL import Image, ImageDraw

    r = radius + random.randint(-2, 4)
    r = max(10, r)

    # Probe to get dimensions
    probe_cmd = [
        imageio_ffmpeg.get_ffmpeg_exe(), "-i", input_path,
        "-hide_banner", "-loglevel", "error"
    ]
    try:
        result = subprocess.run(probe_cmd, capture_output=True, text=True)
        # Parse dimensions from stderr
        import re
        match = re.search(r'(\d{3,4})x(\d{3,4})', result.stderr)
        if match:
            w, h = int(match.group(1)), int(match.group(2))
        else:
            w, h = 1080, 1920
    except Exception:
        w, h = 1080, 1920

    # Create rounded-rect mask PNG
    mask_img = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask_img)
    draw.rounded_rectangle([0, 0, w - 1, h - 1], radius=r, fill=255)

    tmp_mask = tempfile.mktemp(suffix="_corner_mask.png")
    mask_img.save(tmp_mask)

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg, "-y",
        "-i", input_path,
        "-i", tmp_mask,
        "-filter_complex",
        "[0:v]format=rgba[base];[1:v]format=gray,alphaextract[mask];[base][mask]alphamerge[out]",
        "-map", "[out]",
        "-map", "0:a?",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuva420p",
        output_path
    ]
    subprocess.run(cmd, check=True, capture_output=True)

    try:
        os.remove(tmp_mask)
    except Exception:
        pass

    print(f"    [Item 106] FFmpeg corner radius={r}px → {output_path}")
    return output_path

def apply_micro_resolution_crop(input_path: str, output_path: str,
                                  base_w: int = 1080, base_h: int = 1920,
                                  micro_pixels: int = None) -> str:
    """
    Item 124 – Görsel Çözünürlük Manipülasyonu.
    1080x1920 video içine konan stokların render anında 1082x1924 gibi
    mikro-oranla büyütülüp yeniden kırpılması.
    """
    if micro_pixels is None:
        micro_pixels = random.randint(1, 4)

    expanded_w = base_w + micro_pixels * 2
    expanded_h = base_h + micro_pixels * 2

    crop_filter = (
        f"scale={expanded_w}:{expanded_h}:flags=lanczos,"
        f"crop={base_w}:{base_h}:{micro_pixels}:{micro_pixels}"
    )

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg, "-y",
        "-i", input_path,
        "-vf", crop_filter,
        "-c:v", "libx264", "-preset", "fast", "-crf", "17",
        "-c:a", "copy",
        output_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"    [Item 124] Mikro çözünürlük: +{micro_pixels}px → {expanded_w}x{expanded_h} → crop {base_w}x{base_h}")
            return output_path
        else:
            print(f"    [Item 124] FFmpeg hatası: {result.stderr[:200]}")
    except Exception as e:
        print(f"    [Item 124] Hata: {e}")
    return input_path
