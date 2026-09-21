"""
Visual Filters, Noise, Color Grading & Procedural FX
Covers items: 71, 72, 84, 86, 92, 111, 115, 123
"""
import random, math, subprocess
from typing import Tuple
from moviepy.editor import VideoFileClip, VideoClip, CompositeVideoClip, vfx
import numpy as np
import imageio_ffmpeg

def inject_pixel_noise(clip: VideoFileClip, intensity: float = 0.005) -> VideoFileClip:
    """
    Item 71: Perceptual Hashing (pHash) Modülasyonu.
    Hafif uint8 piksel modülasyonu ile hash benzerliği kırılır, devasa float32 RAM tahsisleri engellenir.
    """
    try:
        def add_noise(frame):
            noise = np.random.randint(-1, 2, frame.shape, dtype=np.int16)
            return np.clip(frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        return clip.fl_image(add_noise)
    except Exception as e:
        return clip

def apply_color_grading_jitter(clip: VideoFileClip, jitter_range: float = 0.015) -> VideoFileClip:
    """
    Item 72: FFmpeg Renk Derecelendirme (Color Grading LUT / Jitter).
    Hafif doygunluk modülasyonu (ek olarak _merge aşamasında FFmpeg donanım eq filtresi uygulanır).
    """
    try:
        sat_shift = 1.0 + random.uniform(-jitter_range, jitter_range)
        return clip.fx(vfx.colorx, sat_shift)
    except Exception as e:
        return clip

def apply_color_jitter(clip: VideoFileClip) -> VideoFileClip:
    """Backward-compatible alias for Item 72."""
    return apply_color_grading_jitter(clip, jitter_range=0.015)

def get_color_grading_ffmpeg_filter(jitter_range: float = 0.015) -> str:
    """Generates FFmpeg eq filter string with ±1.5% randomized gamma, contrast and saturation."""
    gamma = 1.0 + random.uniform(-jitter_range, jitter_range)
    contrast = 1.0 + random.uniform(-jitter_range, jitter_range)
    sat = 1.0 + random.uniform(-jitter_range, jitter_range)
    return f"eq=gamma={gamma:.4f}:contrast={contrast:.4f}:saturation={sat:.4f}"


def get_scene_brightness_alternation_filter(scene_index: int, pulse_range: float = 0.10) -> str:
    """
    Item 272: Görsel Parlaklık Dalgalanması.
    Karanlık↔parlak sahne alternasyonu retinayı uyarmak için gamma/contrast kaydırır.
    """
    jitter = random.uniform(0, pulse_range * 0.25)
    if scene_index % 2 == 0:
        gamma = 0.88 - jitter
        contrast = 0.96
        brightness = -0.04
    else:
        gamma = 1.10 + jitter
        contrast = 1.06
        brightness = 0.05
    return f"eq=gamma={gamma:.4f}:contrast={contrast:.4f}:brightness={brightness:.4f}"


def apply_scene_brightness_alternation(clip: VideoFileClip, scene_index: int = 0) -> VideoFileClip:
    """Item 272: MoviePy yolunda sahne bazlı parlaklık alternasyonu."""
    try:
        factor = 0.90 if scene_index % 2 == 0 else 1.12
        return clip.fx(vfx.colorx, factor)
    except Exception:
        return clip


def get_phash_ffmpeg_noise_filter() -> str:
    """Item 71: Ultra-fast FFmpeg noise filter (0.5% pixel noise)."""
    return "noise=alls=1:allf=t+u"

def get_unsharp_filter(luma_matrix: int = 5, luma_amount: float = 0.8) -> str:
    """
    Item 84: FFmpeg Unsharp Filtresi.
    Her renderda unsharp=5:5:0.8:5:5:0.0 filtresiyle kenar keskinliği değiştirilerek
    video dijital imzası tamamen yenilenir.
    """
    jitter = random.uniform(-0.04, 0.04)
    amount = max(0.5, min(1.2, luma_amount + jitter))
    return f"unsharp={luma_matrix}:{luma_matrix}:{amount:.2f}:{luma_matrix}:{luma_matrix}:0.0"

def get_ffmpeg_static_grain_filter() -> str:
    """
    Item 86: Piksel Gürültüsü Enjeksiyonu.
    noise=c1s=3:c0f=u filtresiyle videoya hissedilmez statik gren eklenir.
    """
    return "noise=c1s=3:c0f=u"

def get_ffmpeg_vignette_filter(angle: float = 0.18) -> str:
    """
    Item 92: Kenar Çerçevesi (Border Vignette).
    Videonun köşelerine çok hafif (%4) siyah degrade (vignette) atılarak
    piksel blok haritası bozulur.
    """
    return f"vignette={angle:.3f}"

def generate_particle_overlay_frames(
    width: int,
    height: int,
    duration: float,
    fps: float = 30.0,
    particle_type: str = "snow",
    particle_count: int = 80,
) -> VideoClip:
    """
    Item 111 – Görsel Üzerine Parçacık Efekti.
    Kar, yağmur veya ateş kıvılcımı gibi alfa kanallı parçacıkları
    videonun tamamına bindirir.
    """
    rng = np.random.default_rng(seed=42)

    px = rng.uniform(0, width, particle_count)
    py = rng.uniform(0, height, particle_count)
    psz = rng.uniform(1.5, 4.5, particle_count)
    palpha = rng.uniform(0.3, 0.8, particle_count)
    pvx = rng.uniform(-0.5, 0.5, particle_count)

    if particle_type == "snow":
        color_rgb = (220, 235, 255)
        speed_y = rng.uniform(1.5, 4.0, particle_count)
        speed_mul = 1.0
    elif particle_type == "rain":
        color_rgb = (140, 180, 255)
        speed_y = rng.uniform(12.0, 22.0, particle_count)
        pvx = rng.uniform(0.8, 1.5, particle_count)
        psz = rng.uniform(0.8, 2.0, particle_count)
        speed_mul = 1.0
    elif particle_type == "spark":
        color_rgb = (255, 150, 30)
        speed_y = rng.uniform(-5.0, -1.0, particle_count)
        pvx = rng.uniform(-2.0, 2.0, particle_count)
        speed_mul = 1.0
    else:
        color_rgb = (255, 255, 255)
        speed_y = rng.uniform(1.5, 3.5, particle_count)
        speed_mul = 1.0

    # Precompute a 1-second cyclic buffer (e.g. 30 frames) for instant O(1) rendering
    num_loop_frames = max(1, int(fps))
    loop_frames = []
    loop_masks = []
    for f_idx in range(num_loop_frames):
        t_sim = f_idx / float(fps)
        f_rgb = np.zeros((height, width, 3), dtype=np.uint8)
        f_mask = np.zeros((height, width), dtype=np.float32)
        for i in range(particle_count):
            cy = int((py[i] + speed_y[i] * speed_mul * t_sim * fps) % (height + 20) - 10)
            cx = int((px[i] + pvx[i] * t_sim * fps) % (width + 10) - 5)
            sz = max(1, int(psz[i]))
            alpha = float(palpha[i])
            y1, y2 = max(0, cy - sz), min(height, cy + sz + 1)
            x1, x2 = max(0, cx - sz), min(width, cx + sz + 1)
            if y2 > y1 and x2 > x1:
                f_rgb[y1:y2, x1:x2] = color_rgb
                f_mask[y1:y2, x1:x2] = alpha
        loop_frames.append(f_rgb)
        loop_masks.append(f_mask)

    def make_rgb(t):
        idx = int(t * fps) % len(loop_frames)
        return loop_frames[idx]

    def make_mask(t):
        idx = int(t * fps) % len(loop_masks)
        return loop_masks[idx]

    mask = VideoClip(make_mask, ismask=True, duration=duration).set_fps(fps)
    clip = VideoClip(make_rgb, ismask=False, duration=duration).set_fps(fps).set_mask(mask)
    print(f"    [Item 111] Parçacık efekti: {particle_type} ({particle_count} parçacık, {duration:.1f}s)")
    return clip

def apply_particle_overlay(base_clip, particle_type: str = "snow", particle_count: int = 80):
    """
    Item 111 – Ana klibe parçacık efekti bindirir.
    NOT: RENDER_SAFE_MODE=True iken bypass edilir (tüm video kareleri için bellek yükü oluşturur).
    """
    try:
        import config as _cfg
        if getattr(_cfg, 'RENDER_SAFE_MODE', True):
            print(f"    [Item 111] Parçacık efekti: RENDER_SAFE_MODE aktif, bypass edildi.")
            return base_clip
    except Exception:
        pass

    w, h = base_clip.size
    dur = base_clip.duration
    fps = base_clip.fps or 30.0

    particles = generate_particle_overlay_frames(
        w, h, dur, fps=fps,
        particle_type=particle_type,
        particle_count=particle_count
    )
    composite = CompositeVideoClip([base_clip, particles], size=(w, h))
    composite.duration = dur
    return composite

def apply_color_splash_ffmpeg(input_path: str, output_path: str,
                               keep_hue_range: tuple = (90, 140),
                               hue_tolerance: int = 20) -> str:
    """
    Item 115 – Siyah-Beyaz + Tek Renk Vurgusu (Color Splash).
    Sahnenin tamamını siyah-beyaza çevirirken belirli renk aralığındaki
    nesneleri canlı bırakır.
    """
    min_hue, max_hue = keep_hue_range
    center_hue = (min_hue + max_hue) / 2.0
    similarity = min(0.9, hue_tolerance / 180.0)

    h = center_hue / 60.0
    x = 1 - abs(h % 2 - 1)
    sector = int(h)
    rgb_map = [(1,x,0),(x,1,0),(0,1,x),(0,x,1),(x,0,1),(1,0,x)]
    r, g, b = rgb_map[min(sector, 5)]
    color_hex = f"0x{int(r*255):02X}{int(g*255):02X}{int(b*255):02X}"

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    filter_str = (
        f"[0:v]colorhold=color={color_hex}:similarity={similarity:.3f}:blend=0.1[splash]"
    )

    cmd = [
        ffmpeg, "-y",
        "-i", input_path,
        "-filter_complex", filter_str,
        "-map", "[splash]",
        "-map", "0:a?",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "copy",
        output_path
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"    [Item 115] Color Splash: hue center={center_hue:.0f}° sim={similarity:.2f} → {output_path}")
            return output_path
        else:
            print(f"    [Item 115] colorhold filtresi bulunamadı, grayscale fallback...")
            fallback_cmd = [
                ffmpeg, "-y", "-i", input_path,
                "-vf", "hue=s=0",
                "-map", "0:a?",
                "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                "-c:a", "copy",
                output_path
            ]
            subprocess.run(fallback_cmd, check=True, capture_output=True)
            print(f"    [Item 115] Grayscale fallback → {output_path}")
            return output_path
    except Exception as e:
        print(f"    [Item 115] Color Splash hatası: {e}")
        return input_path

def apply_color_splash_moviepy(clip, keep_hue_center: float = 120.0, tolerance: float = 30.0):
    """
    Item 115 – Color Splash (MoviePy frame-by-frame yaklaşımı).
    """
    def process_frame(frame):
        img = frame.astype(np.float32) / 255.0
        r, g, b = img[:,:,0], img[:,:,1], img[:,:,2]

        luma = 0.299 * r + 0.587 * g + 0.114 * b
        gray = np.stack([luma, luma, luma], axis=-1)

        c_max = np.maximum(np.maximum(r, g), b)
        c_min = np.minimum(np.minimum(r, g), b)
        delta = c_max - c_min

        hue = np.zeros_like(r)
        mask_r = (c_max == r) & (delta > 0)
        mask_g = (c_max == g) & (delta > 0)
        mask_b = (c_max == b) & (delta > 0)
        hue[mask_r] = 60.0 * (((g[mask_r] - b[mask_r]) / delta[mask_r]) % 6)
        hue[mask_g] = 60.0 * ((b[mask_g] - r[mask_g]) / delta[mask_g] + 2)
        hue[mask_b] = 60.0 * ((r[mask_b] - g[mask_b]) / delta[mask_b] + 4)

        diff = np.abs(hue - keep_hue_center)
        diff = np.minimum(diff, 360.0 - diff)
        in_range = diff <= tolerance

        result = np.where(in_range[:,:,np.newaxis], img, gray)
        return (np.clip(result, 0, 1) * 255).astype(np.uint8)

    result_clip = clip.fl_image(process_frame)
    print(f"    [Item 115] Color Splash (MoviePy): hue_center={keep_hue_center:.0f}° ±{tolerance:.0f}°")
    return result_clip

def generate_fluid_gradient_background(width: int, height: int, duration: float,
                                        fps: float = 30.0,
                                        color_scheme: str = "auto") -> VideoClip:
    """
    Item 123 – Video Arka Planına Bulanık Akışkan Gradient.
    """
    schemes = {
        "warm": [(180, 60, 20), (220, 120, 40), (160, 40, 80), (200, 100, 30)],
        "cool": [(20, 60, 180), (40, 120, 200), (60, 40, 160), (30, 100, 220)],
        "neon": [(180, 20, 220), (20, 220, 180), (220, 180, 20), (20, 80, 220)],
        "monochrome": [(20, 20, 20), (60, 60, 70), (40, 40, 50), (80, 80, 90)],
    }
    if color_scheme == "auto":
        color_scheme = random.choice(list(schemes.keys()))
    colors = schemes.get(color_scheme, schemes["cool"])

    num_points = len(colors)
    cx = [width * (i + 0.5) / num_points for i in range(num_points)]
    cy = [height * 0.5] * num_points

    yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)

    def make_frame(t):
        frame = np.zeros((height, width, 3), dtype=np.float32)
        total_weight = np.zeros((height, width), dtype=np.float32)

        for i, (r, g, b) in enumerate(colors):
            px = cx[i] + math.sin(t * 0.3 + i * 1.2) * width * 0.15
            py = cy[i] + math.cos(t * 0.25 + i * 0.8) * height * 0.12

            dx = xx - px
            dy = yy - py
            sigma = max(width, height) * 0.45
            w = np.exp(-(dx**2 + dy**2) / (2 * sigma**2))

            frame[:,:,0] += w * r
            frame[:,:,1] += w * g
            frame[:,:,2] += w * b
            total_weight += w

        total_weight = np.maximum(total_weight, 1e-8)
        frame /= total_weight[:,:,np.newaxis]
        return np.clip(frame, 0, 255).astype(np.uint8)

    clip = VideoClip(make_frame, duration=duration).set_fps(fps)
    print(f"    [Item 123] Fluid gradient: {color_scheme}, {duration:.1f}s")
    return clip

def apply_fluid_gradient_background(base_clip, color_scheme: str = "auto",
                                     overlay_opacity: float = 0.25):
    """
    Item 123 – Stok klibinin arkasına akışkan gradient katmanı yerleştirir.
    """
    w, h = base_clip.size
    dur = base_clip.duration
    fps = base_clip.fps or 30.0

    gradient = generate_fluid_gradient_background(w, h, dur, fps=fps, color_scheme=color_scheme)
    composite = CompositeVideoClip(
        [gradient.set_opacity(1.0), base_clip.set_opacity(1.0 - overlay_opacity * 0.3)],
        size=(w, h)
    )
    composite.duration = dur
    return composite
