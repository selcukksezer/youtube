"""
Anti-Duplicate Pipeline, 3s B-Roll Rule, Video Hash Scrambling & Metadata Injectors
Covers items: 50, 74, 76, 94, 127, 128, 411, 429
"""
import os, random, subprocess, datetime, uuid
from typing import Optional
from moviepy.editor import VideoFileClip, concatenate_videoclips, vfx
import imageio_ffmpeg

from .layout import apply_smart_crop
from .motion import apply_horizontal_flip, apply_speed_ramp, apply_ken_burns
from .filters import apply_color_grading_jitter, inject_pixel_noise
from .overlays import apply_multi_layer_overlay

def apply_anti_duplicate(clip: VideoFileClip, intensity: float = 1.0) -> VideoFileClip:
    """
    Item 50: Anti-Tekrar (Anti-Duplicate) & Hash Modifier.
    Modifies video properties invisibly to prevent YouTube's "Reused Content" flags.
    """
    import config
    if getattr(config, 'RENDER_SAFE_MODE', True):
        # Anti-duplicate is already applied on GPU in FFmpeg _merge via color_vf, grain_vf, vignette_vf
        return clip
    try:
        factor = 1.0 + random.uniform(-0.02, 0.02) * intensity
        modified = clip.fx(vfx.colorx, factor)
        return modified
    except Exception as e:
        print(f"    [AntiDuplicate] Notice: {e}")
        return clip

def apply_mirror_and_pitch(clip: VideoFileClip, horizontal_flip: bool = True) -> VideoFileClip:
    """
    Item 94: Mirror (horizontal flip) for copyright-sensitive sources.
    """
    try:
        if horizontal_flip:
            return clip.fx(vfx.mirror_x)
        return clip
    except Exception as e:
        print(f"    [Mirror] Error: {e}")
        return clip

def get_diversified_fps(base_fps: float = 30.0) -> float:
    """
    Item 74: Kare Hızı (FPS) Çeşitlendirmesi.
    Videolar standart 30.0 fps yerine 29.97 fps veya 30.02 fps gibi mikro-değişken kare oranlarıyla dışa aktarılır.
    """
    fps_pool = [29.97, 30.02, 29.98, 30.01]
    return random.choice(fps_pool)

def enforce_3s_broll_rule(clip: VideoFileClip, max_duration: float = 3.2) -> VideoFileClip:
    """
    Item 76: 3 Saniye Kuralı Kurgusu.
    Hiçbir görsel veya stok klip ekranda 3.2 saniyeden uzun süre kesintisiz durmamalıdır.
    3.2 saniyeyi aşan klipler dinamik alt parçalara bölünür ve mikro-zoom (1.03x)
    veya aynalama ile görsel yenilenme sağlanır.
    """
    if clip.duration <= max_duration:
        return clip
    import config
    if getattr(config, 'RENDER_SAFE_MODE', True):
        return clip
    try:
        subclips = []
        t = 0.0
        flip = False
        while t < clip.duration:
            sub_end = min(t + max_duration, clip.duration)
            sub = clip.subclip(t, sub_end)
            if flip:
                sub = sub.crop(x_center=sub.w / 2, y_center=sub.h / 2, width=clip.w, height=clip.h)
            subclips.append(sub)
            t = sub_end
            flip = not flip

        res = concatenate_videoclips(subclips, method="chain")
        res.duration = clip.duration
        return res
    except Exception as e:
        print(f"    [3sRule] Notice: {e}")
        return clip

def apply_section2_anti_reused_pipeline(
    clip: VideoFileClip,
    target_w: int,
    target_h: int,
    apply_flip: bool = True,
    apply_speed: bool = True,
    apply_3s: bool = True,
    apply_kb: bool = True,
    apply_noise: bool = True,
    apply_grading: bool = True,
    apply_layer: bool = True
) -> VideoFileClip:
    """
    Applies the full Section 2 (Items 71-79) Reused Content Evasion Pipeline to a clip.
    71: pHash noise (0.5%)
    72: Color grading jitter (±1.5%)
    73: Ken Burns micro-zoom (1.00x -> 1.04x)
    75: Multi-layer overlay (10% opacity)
    76: 3s rule cutting
    77: Smart crop 9:16 with 40% blur
    78: Horizontal flip
    79: Speed ramp (0.97x or 1.03x)
    """
    res = clip

    # 1. Smart Crop (Item 77)
    res = apply_smart_crop(res, target_w, target_h, blur_intensity=0.40)

    # 2. Horizontal Flip (Item 78)
    if apply_flip:
        res = apply_horizontal_flip(res, force=True)

    # 3. Speed Ramp (Item 79)
    if apply_speed:
        res = apply_speed_ramp(res)

    # 4. 3-Second B-Roll Rule (Item 76)
    if apply_3s and res.duration > 3.2:
        res = enforce_3s_broll_rule(res, max_duration=3.2)

    # 5. Ken Burns Micro-Zoom (Item 73)
    if apply_kb:
        res = apply_ken_burns(res, zoom_start=1.00, zoom_end=1.04)

    # 6. Color Grading Jitter (Item 72)
    if apply_grading:
        res = apply_color_grading_jitter(res, jitter_range=0.015)

    # 7. Multi-layer Overlay (Item 75)
    if apply_layer:
        res = apply_multi_layer_overlay(res, opacity=0.10)

    # 8. pHash Pixel Noise (Item 71)
    if apply_noise:
        res = inject_pixel_noise(res, intensity=0.005)

    return res

def scramble_mp4_hash(video_path: str) -> bool:
    """
    Item 429: Scrambles the MD5 and SHA-256 hash of the generated MP4 file
    by appending an invisible metadata atom or zero-padded comment.
    """
    if not os.path.exists(video_path):
        return False
    try:
        with open(video_path, "ab") as f:
            f.write(os.urandom(16))
        return True
    except Exception as e:
        print(f"    [HashScramble] Notice: {e}")
        return False

def get_hardware_acceleration_flags() -> list:
    """
    Item 411: Apple Silicon VideoToolbox GPU Acceleration check.
    Uses h264_videotoolbox on macOS for 5x faster rendering.
    """
    import platform
    if platform.system() == "Darwin":
        return ["-c:v", "h264_videotoolbox", "-b:v", "14M"]
    return ["-c:v", "libx264", "-preset", "fast", "-crf", "18"]

# ─── ITEM 127: Video Metadata Temizliği ──────────────────────────────────────

def clean_video_metadata(input_path: str, output_path: str,
                          title: str = "",
                          description: str = "",
                          comment: str = "") -> str:
    """
    Item 127 – Video Metadata Temizliği.
    FFmpeg -map_metadata -1 parametresiyle tüm mevcut metadata temizlenir,
    ardından özgün metadata yazılır.
    """
    if not title:
        title = f"Video_{uuid.uuid4().hex[:12].upper()}"
    if not comment:
        comment = f"Produced {datetime.datetime.now().strftime('%Y-%m-%d')}"

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg, "-y",
        "-i", input_path,
        "-map_metadata", "-1",          # Item 127: Tüm mevcut metadata silinir
        "-c:v", "copy",                  # Yeniden encode yok — hızlı
        "-c:a", "copy",
        "-metadata", f"title={title}",
        "-metadata", f"comment={comment}",
    ]

    if description:
        cmd += ["-metadata", f"description={description}"]

    cmd.append(output_path)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"    [Item 127] Metadata temizlendi: title='{title[:40]}' → {output_path}")
            return output_path
        else:
            print(f"    [Item 127] FFmpeg hatası: {result.stderr[:200]}")
    except Exception as e:
        print(f"    [Item 127] Hata: {e}")

    return input_path

# ─── ITEM 128: Kurgu Motoru İmzası Ekleme (Fake NLE Metadata) ────────────────

_NLE_SIGNATURES = [
    {
        "encoder": "Apple FCP X 10.8.0 (23720.0.0)",
        "software": "Apple Final Cut Pro X",
        "creation_tool": "Final Cut Pro"
    },
    {
        "encoder": "DaVinci Resolve 19.1.1 (b10)",
        "software": "Blackmagic Design DaVinci Resolve",
        "creation_tool": "DaVinci Resolve"
    },
    {
        "encoder": "Adobe Premiere Pro 24.6.0",
        "software": "Adobe Premiere Pro",
        "creation_tool": "Premiere Pro"
    },
    {
        "encoder": "CapCut 5.8.0 (Windows)",
        "software": "CapCut Video Editor",
        "creation_tool": "CapCut"
    },
    {
        "encoder": "Vegas Pro 21.0 Build 108",
        "software": "Sony Vegas Pro",
        "creation_tool": "Vegas Pro"
    },
]

def inject_nle_signature(input_path: str, output_path: str,
                          nle_name: str = "auto") -> str:
    """
    Item 128 – Kurgu Motoru İmzası Ekleme.
    Videoya sahte bir NLE (Non-Linear Editor) render metadata etiketi basar.
    """
    nle_map = {
        "final_cut": _NLE_SIGNATURES[0],
        "davinci":   _NLE_SIGNATURES[1],
        "premiere":  _NLE_SIGNATURES[2],
        "capcut":    _NLE_SIGNATURES[3],
        "vegas":     _NLE_SIGNATURES[4],
    }

    if nle_name == "auto":
        sig = random.choice(_NLE_SIGNATURES)
    else:
        sig = nle_map.get(nle_name, random.choice(_NLE_SIGNATURES))

    hours_ago = random.randint(1, 72)
    render_dt = datetime.datetime.now() - datetime.timedelta(hours=hours_ago)
    render_date = render_dt.strftime("%Y-%m-%dT%H:%M:%S")

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg, "-y",
        "-i", input_path,
        "-c:v", "copy",
        "-c:a", "copy",
        "-metadata", f"encoder={sig['encoder']}",
        "-metadata", f"encoded_by={sig['software']}",
        "-metadata", f"creation_time={render_date}",
        "-metadata", f"handler_name={sig['creation_tool']} Media Handler",
        "-metadata", f"vendor_id={sig['creation_tool'][:4].upper()}",
        output_path
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"    [Item 128] NLE imzası eklendi: {sig['software']} ({render_date})")
            return output_path
        else:
            print(f"    [Item 128] FFmpeg hatası: {result.stderr[:200]}")
    except Exception as e:
        print(f"    [Item 128] Hata: {e}")

    return input_path

def apply_full_metadata_pipeline(input_path: str, output_path: str,
                                  title: str = "",
                                  nle_name: str = "auto") -> str:
    """
    Item 127 + 128 birleşik pipeline.
    Önce metadata temizler (127), ardından NLE imzası ekler (128).
    """
    if not title:
        title = f"Video_{uuid.uuid4().hex[:12].upper()}"

    nle_map = {
        "final_cut": _NLE_SIGNATURES[0],
        "davinci": _NLE_SIGNATURES[1],
        "premiere": _NLE_SIGNATURES[2],
        "capcut": _NLE_SIGNATURES[3],
        "vegas": _NLE_SIGNATURES[4]
    }
    sig = nle_map.get(nle_name, random.choice(_NLE_SIGNATURES)) if nle_name != "auto" else random.choice(_NLE_SIGNATURES)

    hours_ago = random.randint(1, 72)
    render_dt = datetime.datetime.now() - datetime.timedelta(hours=hours_ago)
    render_date = render_dt.strftime("%Y-%m-%dT%H:%M:%S")
    comment = f"Produced {datetime.datetime.now().strftime('%Y-%m-%d')}"

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg, "-y",
        "-i", input_path,
        "-map_metadata", "-1",          # 127: Temizle
        "-c:v", "copy",
        "-c:a", "copy",
        "-metadata", f"title={title}",
        "-metadata", f"comment={comment}",
        "-metadata", f"encoder={sig['encoder']}",          # 128: NLE imzası
        "-metadata", f"encoded_by={sig['software']}",
        "-metadata", f"creation_time={render_date}",
        "-metadata", f"handler_name={sig['creation_tool']} Media Handler",
        output_path
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"    [Item 127+128] Metadata pipeline: temizlendi + {sig['software']} imzası → {output_path}")
            return output_path
        else:
            print(f"    [Item 127+128] FFmpeg hatası: {result.stderr[:200]}")
    except Exception as e:
        print(f"    [Item 127+128] Hata: {e}")

    return input_path
