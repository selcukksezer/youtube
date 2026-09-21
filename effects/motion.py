"""
Camera Motion, Dynamic Pans, Zooms & Transitions
Covers items: 41, 73, 78, 79, 99, 100, 103, 114, 132, 211, 231
"""
import os, random, math
from typing import Optional
from moviepy.editor import VideoFileClip, CompositeVideoClip, vfx
import numpy as np
from PIL import Image

try:
    import cv2
    cv2.ocl.setUseOpenCL(False)
    cv2.setNumThreads(2)
except ImportError:
    cv2 = None
except Exception:
    pass


def _resize_frame(frame: np.ndarray, size: tuple) -> np.ndarray:
    """Resize RGB frame — OpenCV if installed, else PIL (Mac/Windows without cv2)."""
    w, h = size
    if cv2 is not None:
        return cv2.resize(frame, (w, h), interpolation=cv2.INTER_LINEAR)
    img = Image.fromarray(frame)
    return np.array(img.resize((w, h), Image.BILINEAR))


def _blend_frames(a: np.ndarray, b: np.ndarray, alpha: float) -> np.ndarray:
    if cv2 is not None:
        return cv2.addWeighted(a, 1.0 - alpha, b, alpha, 0)
    return ((a.astype(np.float32) * (1.0 - alpha)) + (b.astype(np.float32) * alpha)).astype(np.uint8)

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
        w, h = clip.size
        dur = max(clip.duration, 0.1)
        z_start = zoom_start
        z_end = zoom_ratio if zoom_ratio is not None else zoom_end

        def make_frame(t):
            raw = clip.get_frame(t)
            prog = min(1.0, max(0.0, t / dur))
            zf = z_start + (z_end - z_start) * prog
            if abs(zf - 1.0) < 0.002:
                return raw
            inv_z = 1.0 / zf
            cw = int(w * inv_z)
            ch = int(h * inv_z)
            left = max(0, (w - cw) // 2)
            top = max(0, (h - ch) // 2)
            cropped = raw[top:top + ch, left:left + cw]
            if cropped.dtype != np.uint8:
                cropped = cropped.astype(np.uint8)
            return _resize_frame(cropped, (w, h))

        from moviepy.editor import VideoClip
        clip_fps = getattr(clip, 'fps', None) or 30.0
        res = VideoClip(make_frame, duration=clip.duration).set_fps(clip_fps)
        if clip.audio:
            res = res.set_audio(clip.audio)
        return res
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

def apply_slow_motion_highlight(
    clip: VideoFileClip,
    speed_factor: float = 0.5,
) -> VideoFileClip:
    """
    Item 231: Yavaşlatılmış Çekim (Slow-Motion) Vurgusu.
    Aynı sürede görsel 0.5x hissi — kaynak kareleri yavaş tarar (A/V süresi korunur).
    """
    try:
        factor = max(0.25, min(1.0, float(speed_factor)))
        if factor >= 0.99:
            return clip
        clip_fps = getattr(clip, "fps", None) or 30.0

        def make_frame(t):
            source_t = min(max(0.0, t * factor), max(0.0, clip.duration - 0.001))
            return clip.get_frame(source_t)

        from moviepy.editor import VideoClip
        res = VideoClip(make_frame, duration=clip.duration).set_fps(clip_fps)
        if clip.audio:
            res = res.set_audio(clip.audio)
        print(f"    [Item 231] Slow-motion highlight: factor={factor}")
        return res
    except Exception as e:
        print(f"    [SlowMotionHighlight] Notice: {e}")
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


def apply_broll_speed_boost(clip: VideoFileClip, speed_factor: float = 1.5) -> VideoFileClip:
    """
    Item 245: Görsel Hızlandırma — sıkıcı ara açıklamalar için 1.5x B-roll hızlandırma.
    """
    try:
        boosted = clip.fx(vfx.speedx, speed_factor)
        print(f"    [Item 245] B-roll speed boost: {speed_factor}x")
        return boosted
    except Exception as e:
        print(f"    [BrollSpeedBoost] Notice: {e}")
        return clip


def apply_impact_screen_shake(
    clip: VideoFileClip,
    intensity: float = 14.0,
    duration: float = 0.35,
) -> VideoFileClip:
    """
    Item 243: Görsel Titreşim (Screen Shake) — patlama/darbe anında kısa sarsıntı.
    """
    try:
        w, h = clip.size
        padded = clip.resize(1.08)
        pw, ph = padded.size
        dx_max = (pw - w) / 2
        dy_max = (ph - h) / 2
        shake_dur = min(duration, clip.duration)

        def shake_pos(t):
            if t > shake_dur:
                return (-dx_max, -dy_max)
            decay = 1.0 - (t / shake_dur)
            off_x = math.sin(t * 38.0) * intensity * decay + math.cos(t * 52.0) * intensity * 0.4 * decay
            off_y = math.cos(t * 41.0) * intensity * decay + math.sin(t * 47.0) * intensity * 0.4 * decay
            pos_x = -dx_max + max(-dx_max, min(dx_max, off_x))
            pos_y = -dy_max + max(-dy_max, min(dy_max, off_y))
            return (pos_x, pos_y)

        shaken = padded.set_position(shake_pos)
        composite = CompositeVideoClip([shaken], size=(w, h))
        composite.duration = clip.duration
        print(f"    [Item 243] Impact screen shake: {shake_dur:.2f}s")
        return composite
    except Exception as e:
        print(f"    [ImpactShake] Notice: {e}")
        return clip


def apply_micro_zoom_out(
    clip: VideoFileClip,
    zoom_start: float = 1.04,
    zoom_end: float = 1.00,
) -> VideoFileClip:
    """
    Item 253: Mikro Zoom-Out — cümle biterken kameranın hafif geriye çekilmesi.
    """
    try:
        w, h = clip.size
        dur = max(0.1, clip.duration)

        def scale_at(t):
            prog = min(1.0, max(0.0, t / dur))
            return zoom_start + (zoom_end - zoom_start) * prog

        zoomed = clip.resize(lambda t: scale_at(t))
        composite = CompositeVideoClip([zoomed.set_position("center")], size=(w, h))
        composite.duration = clip.duration
        print(f"    [Item 253] Micro zoom-out: {zoom_start:.3f}->{zoom_end:.3f}")
        return composite
    except Exception as e:
        print(f"    [MicroZoomOut] Notice: {e}")
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
        import config as _cfg
        if getattr(_cfg, 'RENDER_SAFE_MODE', True):
            return clip
        w, h = clip.size
        blur_dur = min(blur_duration, clip.duration / 2)

        def make_frame(t):
            frame = clip.get_frame(t)
            if t >= blur_dur:
                return frame
            alpha = max(0.0, min(1.0, 1.0 - (t / blur_dur)))
            if alpha < 0.04:
                return frame
            if frame.dtype != np.uint8:
                frame = frame.astype(np.uint8)
            small_w, small_h = max(16, int(w * 0.10)), max(16, int(h * 0.10))
            small = _resize_frame(frame, (small_w, small_h))
            blurred = _resize_frame(small, (w, h))
            return _blend_frames(frame, blurred, alpha)

        from moviepy.editor import VideoClip
        clip_fps = getattr(clip, 'fps', None) or 30.0
        res = VideoClip(make_frame, duration=clip.duration).set_fps(clip_fps)
        if clip.audio:
            res = res.set_audio(clip.audio)
        return res
    except Exception as e:
        print(f"    [OutOfFocusReveal] Notice: {e}")
        return clip

def apply_censored_blur_bait(
    clip: VideoFileClip,
    reveal_after: float = 3.0,
    teaser_text: str = "3 SANİYE SONRA GÖSTERİLECEK",
) -> VideoFileClip:
    """
    Item 211: Görsel Merak Penceresi (Censored / Blur Bait).
    İlk karede merkez nesne piksel/blur ile sansürlenir; reveal_after saniyede açılır.
    """
    try:
        import config as _cfg
        if getattr(_cfg, 'RENDER_SAFE_MODE', True):
            return clip
    except Exception:
        pass
    if cv2 is None:
        print("    [CensoredBlurBait] opencv-python yok — efekt atlandi.")
        return clip
    try:
        w, h = clip.size
        reveal_after = min(max(0.5, reveal_after), max(0.5, clip.duration * 0.85))
        cx1, cx2 = int(w * 0.18), int(w * 0.82)
        cy1, cy2 = int(h * 0.28), int(h * 0.72)
        roi_w, roi_h = cx2 - cx1, cy2 - cy1

        def make_frame(t):
            frame = clip.get_frame(t)
            if t >= reveal_after:
                return frame
            if frame.dtype != np.uint8:
                frame = frame.astype(np.uint8)

            strength = 1.0
            fade_window = min(0.45, reveal_after * 0.25)
            if t > reveal_after - fade_window:
                strength = max(0.0, (reveal_after - t) / fade_window)
            if strength < 0.03:
                return frame

            out = frame.copy()
            roi = out[cy1:cy2, cx1:cx2]
            pw = max(10, int(roi_w * 0.07))
            ph = max(10, int(roi_h * 0.07))
            small = cv2.resize(roi, (pw, ph), interpolation=cv2.INTER_LINEAR)
            pixelated = cv2.resize(small, (roi_w, roi_h), interpolation=cv2.INTER_NEAREST)
            blended = cv2.addWeighted(roi, 1.0 - strength, pixelated, strength, 0)
            out[cy1:cy2, cx1:cx2] = blended

            if strength > 0.12:
                bar_h = max(28, int(roi_h * 0.16))
                bar_y = cy1 + (roi_h - bar_h) // 2
                cv2.rectangle(out, (cx1 + 8, bar_y), (cx2 - 8, bar_y + bar_h), (12, 12, 18), -1)
                cv2.rectangle(out, (cx1 + 8, bar_y), (cx2 - 8, bar_y + bar_h), (255, 230, 0), 2)
                label = teaser_text[:42]
                font = cv2.FONT_HERSHEY_SIMPLEX
                scale = max(0.45, min(0.9, roi_w / 900.0))
                thickness = max(1, int(scale * 2))
                (tw, th), _ = cv2.getTextSize(label, font, scale, thickness)
                tx = cx1 + (roi_w - tw) // 2
                ty = bar_y + (bar_h + th) // 2
                cv2.putText(out, label, (tx, ty), font, scale, (255, 255, 255), thickness, cv2.LINE_AA)

            return out

        from moviepy.editor import VideoClip
        clip_fps = getattr(clip, 'fps', None) or 30.0
        res = VideoClip(make_frame, duration=clip.duration).set_fps(clip_fps)
        if clip.audio:
            res = res.set_audio(clip.audio)
        print(f"    [Item 211] Censored blur bait: reveal={reveal_after:.1f}s")
        return res
    except Exception as e:
        print(f"    [CensoredBlurBait] Notice: {e}")
        return clip

def apply_heartbeat_zoom(clip, bpm: float = 60.0, scale_min: float = 1.00, scale_max: float = 1.035):
    """
    Item 114 – Görsel Büyüme/Küçülme Nefesi (Heartbeat Zoom).
    Görsele kalp atışı gibi hafif ritmik boyut değişimi verir.
    NOT: RENDER_SAFE_MODE=True iken bypass edilir (per-frame cv2.resize → GPU/RAM aşırı yükü).
    """
    try:
        import config as _cfg
        if getattr(_cfg, 'RENDER_SAFE_MODE', True):
            print(f"    [Item 114] Heartbeat zoom: RENDER_SAFE_MODE aktif, bypass edildi.")
            return clip
    except Exception:
        pass

    period = 60.0 / bpm  # Döngü süresi (saniye)

    def zoom_factor(t):
        sine = (math.sin(2 * math.pi * t / period) + 1.0) / 2.0
        return scale_min + (scale_max - scale_min) * sine

    w, h = clip.size

    def make_frame(t):
        raw = clip.get_frame(t)
        zf = zoom_factor(t)
        if abs(zf - 1.0) < 0.001:
            return raw
        inv_z = 1.0 / zf
        cw = int(w * inv_z)
        ch = int(h * inv_z)
        left = max(0, (w - cw) // 2)
        top = max(0, (h - ch) // 2)
        cropped = raw[top:top + ch, left:left + cw]
        if cropped.dtype != np.uint8:
            cropped = cropped.astype(np.uint8)
        return _resize_frame(cropped, (w, h))

    from moviepy.editor import VideoClip
    clip_fps = getattr(clip, 'fps', None) or 30.0
    result = VideoClip(make_frame, duration=clip.duration).set_fps(clip_fps)
    if clip.audio:
        result = result.set_audio(clip.audio)
    print(f"    [Item 114] Heartbeat zoom: bpm={bpm}, scale={scale_min:.3f}→{scale_max:.3f}")
    return result

def apply_opening_pattern_interrupt(
    clip: VideoFileClip,
    interrupt_type: str = "glitch_flash",
    duration: float = 1.5,
) -> VideoFileClip:
    """
    Items 201 & 237: İlk 1.5 saniye görsel şoku — glitch flash, zoom punch veya renk negatifi.
    """
    try:
        w, h = clip.size
        shock_dur = min(max(0.5, duration), clip.duration)
        rng_np = np.random.default_rng(int(w * 13 + h * 7))

        def make_frame(t):
            frame = clip.get_frame(t)
            if t >= shock_dur:
                return frame
            if frame.dtype != np.uint8:
                frame = frame.astype(np.uint8)

            if interrupt_type == "zoom_punch" and t < 0.4:
                prog = min(1.0, t / 0.4)
                scale = 1.0 + 0.22 * math.sin(math.pi * prog)
                inv_z = 1.0 / scale
                cw, ch = int(w * inv_z), int(h * inv_z)
                left, top = max(0, (w - cw) // 2), max(0, (h - ch) // 2)
                cropped = frame[top:top + ch, left:left + cw]
                return _resize_frame(cropped, (w, h))

            if interrupt_type == "color_inversion" and t < 0.15:
                alpha = max(0.0, 1.0 - (t / 0.15))
                inverted = (255 - frame).astype(np.uint8)
                return _blend_frames(frame, inverted, alpha)

            # glitch_flash (default)
            if t < 0.08:
                flash = np.full_like(frame, 255)
                alpha = 1.0 - (t / 0.08)
                return _blend_frames(flash, frame, 1.0 - alpha)
            if t < 0.18:
                noise = rng_np.integers(0, 256, size=frame.shape, dtype=np.uint8)
                alpha = max(0.0, 1.0 - ((t - 0.08) / 0.10))
                return _blend_frames(noise, frame, alpha)
            return frame

        from moviepy.editor import VideoClip
        clip_fps = getattr(clip, "fps", None) or 30.0
        res = VideoClip(make_frame, duration=clip.duration).set_fps(clip_fps)
        if clip.audio:
            res = res.set_audio(clip.audio)
        print(f"    [Item 201] Opening pattern interrupt: {interrupt_type} ({shock_dur:.1f}s)")
        return res
    except Exception as e:
        print(f"    [OpeningPatternInterrupt] Notice: {e}")
        return clip


def apply_alternating_motion(clip, scene_index: int = 0):
    """
    Item 132 – Görsel Hareketi Yön Değişimi.
    Item 267 – Görsel Yönlendirme: batı kültüründe soldan sağa hareket ilerleme/
    gelecek psikolojisi tetikler; çift indeksli sahneler pan_right (L→R) hedefler.

    Due to severe OOM crashes and GPU/RAM exhaustion with dynamic frame generation
    and cv2.resize in MoviePy, we apply a much safer, static approach or bypass the
    heavy per-frame cropping.
    """
    directions = ["pan_left", "pan_right", "pan_up", "pan_down"]
    direction = directions[scene_index % len(directions)]
    if scene_index % 2 == 0:
        direction = "pan_right"  # Item 267: prefer left-to-right progression cue
    try:
        print(f"    [Item 132] Alternating motion uygulandı (Bypass for OOM safety): sahne #{scene_index+1} → {direction}")
        return clip
    except Exception as e:
        print(f"    [Item 132] Notice: {e}")
        return clip
