"""
Dual-Visual (A/B) Split Scene Compositor.
Adapted from SaarD00/AI-Youtube-Shorts-Generator (composer.py & asset_manager.py).
Splits a scene's duration into two rapid complementary visual shots (A and B)
to double viewer retention without needing 14 separate voiceover cuts.
"""
import os
import subprocess
from typing import Optional, Tuple
import imageio_ffmpeg


def compose_dual_visual_scene(
    clip_a_path: str,
    clip_b_path: Optional[str],
    audio_path: str,
    output_path: str,
    total_duration: float,
    width: int = 1080,
    height: int = 1920,
    fps: int = 30,
) -> str:
    """
    Renders a single scene using dual visual clips:
    - Clip A: 0.0s -> (total_duration / 2)
    - Clip B: (total_duration / 2) -> total_duration
    If Clip B is missing, uses Clip A for the entire duration.
    Synchronizes audio and produces 1080x1920 portrait MP4.
    """
    if not os.path.exists(clip_a_path):
        raise FileNotFoundError(f"Clip A not found: {clip_a_path}")

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    use_dual = bool(clip_b_path and os.path.exists(clip_b_path) and total_duration >= 3.0)

    if use_dual:
        dur_a = total_duration / 2.0
        dur_b = total_duration - dur_a

        # Construct FFmpeg filter graph to scale, crop, and concat A and B
        filter_complex = (
            f"[0:v]loop=loop=-1:size=1:start=0,trim=duration={dur_a:.3f},setpts=PTS-STARTPTS,"
            f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},fps={fps}[va];"
            f"[1:v]loop=loop=-1:size=1:start=0,trim=duration={dur_b:.3f},setpts=PTS-STARTPTS,"
            f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},fps={fps}[vb];"
            f"[va][vb]concat=n=2:v=1:a=0[v]"
        )

        cmd = [
            ffmpeg_exe,
            "-y",
            "-loglevel", "error",
            "-i", clip_a_path,
            "-i", clip_b_path,
            "-i", audio_path,
            "-filter_complex", filter_complex,
            "-map", "[v]",
            "-map", "2:a:0?",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "22",
            "-c:a", "aac",
            "-b:a", "128k",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            "-t", f"{total_duration:.3f}",
            output_path,
        ]
    else:
        # Single clip fallback
        filter_complex = (
            f"[0:v]loop=loop=-1:size=1:start=0,trim=duration={total_duration:.3f},setpts=PTS-STARTPTS,"
            f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},fps={fps}[v]"
        )

        cmd = [
            ffmpeg_exe,
            "-y",
            "-loglevel", "error",
            "-i", clip_a_path,
            "-i", audio_path,
            "-filter_complex", filter_complex,
            "-map", "[v]",
            "-map", "1:a:0?",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "22",
            "-c:a", "aac",
            "-b:a", "128k",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            "-t", f"{total_duration:.3f}",
            output_path,
        ]

    subprocess.run(cmd, check=True)
    return output_path
