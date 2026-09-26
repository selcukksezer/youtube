"""
Audio Tempo Guard and Shorts Duration Normalizer.
Adapted from ShortGPT (audio_utils.py -> speedUpAudio).
Ensures speech never spills past YouTube Shorts limit (57s) or cuts off mid-sentence,
using pitch-preserving FFmpeg atempo filter.
"""
import os
import subprocess
import imageio_ffmpeg


def get_audio_duration(file_path: str) -> float:
    """Gets audio duration in seconds using ffprobe/ffmpeg."""
    if not os.path.exists(file_path):
        return 0.0

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [ffmpeg_exe, "-i", file_path, "-hide_banner"]
    try:
        p = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        import re
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", p.stderr)
        if m:
            hours, mins, secs = int(m.group(1)), int(m.group(2)), float(m.group(3))
            return hours * 3600 + mins * 60 + secs
    except Exception:
        pass

    # Fallback using wave module if uncompressed wav
    try:
        import wave
        with wave.open(file_path, "r") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            return frames / float(rate)
    except Exception:
        pass

    return 0.0


def apply_shorts_tempo_guard(
    audio_path: str,
    output_path: str,
    max_duration: float = 57.0,
    force_speedup: bool = False,
) -> str:
    """
    If audio exceeds max_duration (default 57s), speeds up audio proportionally
    so it lands under the limit without altering pitch.
    If already within limit and force_speedup is False, creates a fast copy.
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    duration = get_audio_duration(audio_path)
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    if duration > max_duration or force_speedup:
        # Calculate speedup ratio: target is 98% of max_duration for safety margin
        target_dur = max_duration * 0.98
        ratio = duration / target_dur
        # FFmpeg atempo supports 0.5 to 2.0 per filter instance
        ratio = max(0.8, min(1.8, ratio))

        cmd = [
            ffmpeg_exe,
            "-y",
            "-loglevel",
            "error",
            "-i",
            audio_path,
            "-af",
            f"atempo={ratio:.4f}",
            output_path,
        ]
        subprocess.run(cmd, check=True)
        return output_path
    else:
        # Fits comfortably within limits, clean copy
        cmd = [
            ffmpeg_exe,
            "-y",
            "-loglevel",
            "error",
            "-i",
            audio_path,
            "-c:a",
            "copy",
            output_path,
        ]
        subprocess.run(cmd, check=True)
        return output_path
