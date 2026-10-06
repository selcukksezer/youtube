"""
Audio Tempo Guard and Shorts Duration Normalizer.
Adapted from ShortGPT (audio_utils.py -> speedUpAudio).
Ensures speech never spills past YouTube Shorts limit (57s) or cuts off mid-sentence,
using pitch-preserving FFmpeg atempo filter.
"""
import os
import subprocess
from typing import Optional

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


def build_atempo_filter_chain(speed_factor: float) -> str:
    """
    Builds chained FFmpeg atempo filter stages.
    Solves ShortGPT's bug where tempo > 2.0 or < 0.5 crashed FFmpeg.
    """
    factor = max(0.2, min(5.0, float(speed_factor)))
    filters = []
    remaining = factor

    while remaining > 2.001:
        filters.append("atempo=2.0")
        remaining /= 2.0

    while remaining < 0.499:
        filters.append("atempo=0.5")
        remaining /= 0.5

    if abs(remaining - 1.0) > 0.002:
        filters.append(f"atempo={remaining:.4f}")

    return ",".join(filters) if filters else "atempo=1.0"


def speedup_audio(
    audio_path: str,
    output_path: str,
    speed_factor: float = 1.0,
    target_duration: Optional[float] = None,
) -> str:
    """
    Speeds up or slows down audio using chained FFmpeg atempo filters (0.2x to 5.0x).
    Preserves audio pitch and avoids chipmunk/demon distortions.
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    current_dur = get_audio_duration(audio_path)
    if target_duration and target_duration > 0 and current_dur > 0:
        factor = current_dur / float(target_duration)
    else:
        factor = float(speed_factor)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    if abs(factor - 1.0) < 0.01:
        cmd = [ffmpeg_exe, "-y", "-loglevel", "error", "-i", audio_path, "-c:a", "copy", output_path]
        subprocess.run(cmd, check=True)
        return output_path

    af_chain = build_atempo_filter_chain(factor)
    cmd = [
        ffmpeg_exe, "-y", "-loglevel", "error",
        "-i", audio_path,
        "-af", af_chain,
        output_path,
    ]
    subprocess.run(cmd, check=True)
    return output_path


def adjust_audio_pitch(
    audio_path: str,
    output_path: str,
    semitones: float,
    preserve_tempo: bool = True,
    sample_rate: int = 44100,
) -> str:
    """
    Adjusts pitch by given semitones (+/- 12) for voice personas or anti-content-ID evasion.
    When preserve_tempo=True, duration remains unchanged using inverse chained atempo.
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    clamped_semi = max(-12.0, min(12.0, float(semitones)))
    if abs(clamped_semi) < 0.01:
        # No pitch shift needed
        return speedup_audio(audio_path, output_path, speed_factor=1.0)

    pitch_factor = 2.0 ** (clamped_semi / 12.0)
    shifted_rate = int(round(sample_rate * pitch_factor))

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    if preserve_tempo:
        # Inverse tempo compensation to maintain identical speech duration
        tempo_comp = 1.0 / pitch_factor
        atempo_chain = build_atempo_filter_chain(tempo_comp)
        af_filter = f"asetrate={shifted_rate},aresample={sample_rate},{atempo_chain}"
    else:
        af_filter = f"asetrate={shifted_rate},aresample={sample_rate}"

    cmd = [
        ffmpeg_exe, "-y", "-loglevel", "error",
        "-i", audio_path,
        "-af", af_filter,
        output_path,
    ]
    subprocess.run(cmd, check=True)
    return output_path


def apply_shorts_tempo_guard(
    audio_path: str,
    output_path: str,
    max_duration: float = 57.0,
    force_speedup: bool = False,
) -> str:
    """
    If audio exceeds max_duration (default 57s), speeds up audio proportionally
    so it lands under the limit without altering pitch.
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    duration = get_audio_duration(audio_path)
    if duration > max_duration or force_speedup:
        target_dur = max_duration * 0.98
        return speedup_audio(audio_path, output_path, target_duration=target_dur)
    else:
        return speedup_audio(audio_path, output_path, speed_factor=1.0)

