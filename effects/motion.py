"""
Camera Motion, Dynamic Pans, Zooms & Transitions
Covers items: 41, 73, 78, 79, 99, 100, 103, 114, 132
"""
import os, random, math
from typing import Optional
from moviepy.editor import VideoFileClip, CompositeVideoClip, vfx
import numpy as np
from PIL import Image

def apply_ken_burns(
    clip: VideoFileClip,
    zoom_start: float = 1.00,
    zoom_end: float = 1.04,
    zoom_ratio: Optional[float] = None
) -> VideoFileClip:
    """
    Items 41 & 73: Mikro-Zoom (Ken Burns Jitter).
    Sabit sahnelerde 1.00x'den 1.04x'e (veya verilen zoom_ratio'ya) kadar
    hafif, sinematik yaklaşma hareketi verir.
    """
    try:
        dur = max(clip.duration, 0.1)
        if zoom_ratio is not None:
            return clip.fx(vfx.resize, lambda t: 1 + (zoom_ratio - 1) * (t / dur))
        return clip.fx(vfx.resize, lambda t: zoom_start + (zoom_end - zoom_start) * (t / dur))
    except Exception:
        return clip

def apply_horizontal_flip(clip: VideoFileClip, force: bool = True) -> VideoFileClip:
    """
    Item 78: Görsel Aynalama (Horizontal Flip).
    Genel stok veya film kesitleri yatayda ters çevrilerek görsel Content ID veritabanından kaçırılır.
    """
    try:
        if force:
            return clip.fx(vfx.mirror_x)
        return clip
    except Exception as e:
        print(f"    [HorizontalFlip] Error: {e}")
        return clip

def apply_speed_ramp(clip: VideoFileClip, speed_factor: Optional[float] = None) -> VideoFileClip:
    """
    Item 79: Hız Varyasyonu (Speed Ramp).
    Kliplerin oynatma hızı %100 yerine %103 veya %97 olarak hafifçe modüle edilir.
    """
    try:
        factor = speed_factor if speed_factor is not None else random.choice([0.97, 1.03])
        return clip.fx(vfx.speedx, factor)
    except Exception as e:
        print(f"    [SpeedRamp] Error: {e}")
        return clip

def apply_handheld_camera_shake(
    clip: VideoFileClip,
    intensity: float = 6.0,
    speed: float = 2.4
) -> VideoFileClip:
    """
    Item 99: Dinamik Kamera Sallantısı (Handheld Camera Shake).
    FFmpeg/MoviePy filtreleriyle sabit fotoğraflara ve durağan planlara
    doğal el kamerası mikro titreşimi (pan/tilt jitter) verilerek dijital imza ve statiklik kırılır.
    """
    try:
        w, h = clip.size
        # Slightly scale up to prevent black border peeking during shake
        padded = clip.resize(1.05)
        pw, ph = padded.size
        dx_max = (pw - w) / 2
        dy_max = (ph - h) / 2

        def shake_pos(t):
            # Smooth Perlin-like pseudo-random trajectory using irrational sine wave superposition
            off_x = math.sin(t * speed * 2.1) * (intensity * 0.7) + math.cos(t * speed * 4.3) * (intensity * 0.3)
            off_y = math.cos(t * speed * 1.9) * (intensity * 0.7) + math.sin(t * speed * 3.7) * (intensity * 0.3)
            pos_x = -dx_max + max(-dx_max, min(dx_max, off_x))
            pos_y = -dy_max + max(-dy_max, min(dy_max, off_y))
            return (pos_x, pos_y)

        shaken = padded.set_position(shake_pos)
        composite = CompositeVideoClip([shaken], size=(w, h))
        composite.duration = clip.duration
        return composite
    except Exception as e:
        print(f"    [HandheldShake] Notice: {e}")
        return clip

def get_ffmpeg_camera_shake_filter(intensity: int = 5, speed: float = 2.0) -> str:
    """
    Item 99: Pure FFmpeg crop expression for Handheld Camera Shake.
    Generates dynamic crop jitter without re-encoding frames in Python memory.
    """
    return f"crop=w=in_w-16:h=in_h-16:x='8+{intensity}*sin(t*{speed})':y='8+{intensity}*cos(t*{speed*1.3})',scale=1080:1920"

def apply_mask_wipe_transition(
    clip: VideoFileClip,
    direction: str = "horizontal",
    transition_dur: float = 0.45
) -> VideoFileClip:
    """
    Item 100: Görsel Maskeleme (Wipe Transition Mask Overlay).
    Sahne giriş ve çıkışlarında yatay veya dairesel silme maskeleri (wipe transitions)
    kullanılarak geçiş yumuşatılır ve görsel dinamizm artırılır.
    """
    try:
        w, h = clip.size
        dur = max(0.1, min(transition_dur, clip.duration / 2))

        def make_wipe_frame(t):
            if t >= dur:
                return np.ones((h, w), dtype=np.float32)
            prog = max(0.0, min(1.0, t / dur))
            mask = np.zeros((h, w), dtype=np.float32)
            if direction == "horizontal":
                cut = int(w * prog)
                mask[:, :cut] = 1.0
            else:  # circular wipe
                cx, cy = w // 2, h // 2
                max_radius = math.sqrt(cx**2 + cy**2)
                r = max_radius * prog
                y_coords, x_coords = np.ogrid[:h, :w]
                dist_from_center = np.sqrt((x_coords - cx)**2 + (y_coords - cy)**2)
                mask[dist_from_center <= r] = 1.0
            return mask

        from moviepy.video.VideoClip import VideoClip
        mask_clip = VideoClip(make_frame=make_wipe_frame, ismask=True, duration=clip.duration)
        wiped_clip = clip.set_mask(mask_clip)
        return CompositeVideoClip([wiped_clip], size=(w, h))
    except Exception as e:
        print(f"    [WipeTransition] Notice: {e}")
        return clip

def apply_out_of_focus_reveal(clip: VideoFileClip, blur_duration: float = 0.35) -> VideoFileClip:
    """
    Item 103: Ekran Dışı Odak (Out-of-Focus Hook Reveal).
    Videonun ilk karesinde görselin merkezindeki nesne hafif bulanık başlayıp
    0.3 - 0.4 saniye içinde hızla netleşir.
    """
    try:
        w, h = clip.size
        blur_dur = min(blur_duration, clip.duration / 2)

        blurred_part = (
            clip.subclip(0, blur_dur)
            .resize(0.12)
            .resize((w, h))
            .fx(vfx.fadeout, blur_dur)
        )
        composite = CompositeVideoClip([clip, blurred_part], size=(w, h))
        composite.duration = clip.duration
        return composite
    except Exception as e:
        print(f"    [OutOfFocusReveal] Notice: {e}")
        return clip

def apply_heartbeat_zoom(clip, bpm: float = 60.0, scale_min: float = 1.00, scale_max: float = 1.035):
    """
    Item 114 – Görsel Büyüme/Küçülme Nefesi (Heartbeat Zoom).
    Görsele kalp atışı gibi hafif ritmik boyut değişimi verir.
    """
    period = 60.0 / bpm  # Döngü süresi (saniye)

    def zoom_factor(t):
        sine = (math.sin(2 * math.pi * t / period) + 1.0) / 2.0
        return scale_min + (scale_max - scale_min) * sine

    def make_frame(t):
        raw = clip.get_frame(t)
        zf = zoom_factor(t)
        w, h = clip.size
        new_w = int(w * zf)
        new_h = int(h * zf)
        img = Image.fromarray(raw.astype(np.uint8))
        resized = img.resize((new_w, new_h), Image.LANCZOS)
        left = (new_w - w) // 2
        top = (new_h - h) // 2
        cropped = resized.crop((left, top, left + w, top + h))
        return np.array(cropped)

    from moviepy.editor import VideoClip
    result = VideoClip(make_frame, duration=clip.duration).set_fps(clip.fps or 30.0)
    if clip.audio:
        result = result.set_audio(clip.audio)
    print(f"    [Item 114] Heartbeat zoom: bpm={bpm}, scale={scale_min:.3f}→{scale_max:.3f}")
    return result

def apply_alternating_motion(clip, scene_index: int = 0) -> VideoFileClip:
    """
    Item 132 – Görsel Hareketi Yön Değişimi.
    Birinci sahne sola kayıyorsa (pan left), ikinci sahne sağa (pan right)
    veya yukarı (pan up) kaymalıdır.
    """
    directions = ["pan_left", "pan_right", "pan_up", "pan_down"]
    direction = directions[scene_index % len(directions)]

    try:
        w, h = clip.size
        dur = max(clip.duration, 0.1)

        crop_w, crop_h = int(w * 0.94), int(h * 0.94)
        max_dx = w - crop_w
        max_dy = h - crop_h

        def get_pos(t):
            prog = min(1.0, max(0.0, t / dur))
            if direction == "pan_left":
                x = int(max_dx * (1.0 - prog))
                y = int(max_dy / 2)
            elif direction == "pan_right":
                x = int(max_dx * prog)
                y = int(max_dy / 2)
            elif direction == "pan_up":
                x = int(max_dx / 2)
                y = int(max_dy * prog)
            else:  # pan_down
                x = int(max_dx / 2)
                y = int(max_dy * (1.0 - prog))
            return x, y

        from moviepy.editor import VideoClip
        def make_frame(t):
            frame = clip.get_frame(t)
            x, y = get_pos(t)
            cropped = frame[y:y + crop_h, x:x + crop_w]
            img = Image.fromarray(cropped.astype(np.uint8))
            return np.array(img.resize((w, h), Image.BILINEAR))

        res = VideoClip(make_frame, duration=clip.duration).set_fps(clip.fps or 30.0)
        if clip.audio:
            res = res.set_audio(clip.audio)
        print(f"    [Item 132] Alternating motion uygulandı: sahne #{scene_index+1} → {direction}")
        return res
    except Exception as e:
        print(f"    [Item 132] Notice: {e}")
        return clip
