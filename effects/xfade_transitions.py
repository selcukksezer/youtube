"""
FFmpeg xfade & acrossfade Scene Transition Stitcher.
Adapted from SaarD00/AI-Youtube-Shorts-Generator (composer.py).
Replaces hard cuts with smooth cinematic transitions and ensures Windows/YouTube 0x80004005 safe encoding.
"""
import os
import subprocess
import random
from typing import List, Optional
import imageio_ffmpeg

AVAILABLE_TRANSITIONS = [
    "fade",
    "wipeleft",
    "wiperight",
    "smoothleft",
    "smoothright",
    "circleopen",
    "fadeblack",
    "radial",
]


def _get_video_duration(filepath: str) -> float:
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [ffmpeg_exe, "-i", filepath, "-hide_banner"]
    try:
        p = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        import re
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", p.stderr)
        if m:
            hours, mins, secs = int(m.group(1)), int(m.group(2)), float(m.group(3))
            return hours * 3600 + mins * 60 + secs
    except Exception:
        pass
    return 4.0


def concat_with_xfade_transitions(
    video_paths: List[str],
    output_path: str,
    transition_duration: float = 0.4,
    preferred_transition: Optional[str] = None,
) -> str:
    """
    Concatenates an array of video clips using progressive FFmpeg xfade and acrossfade filters.
    Includes Windows yuv420p and faststart playback fixes.
    """
    valid_paths = [p for p in video_paths if os.path.exists(p)]
    if not valid_paths:
        raise ValueError("No valid video paths provided for concatenation.")

    if len(valid_paths) == 1:
        # Single clip, simple copy/remux
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        cmd = [
            ffmpeg_exe, "-y", "-loglevel", "error",
            "-i", valid_paths[0],
            "-c:v", "copy", "-c:a", "copy",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            output_path,
        ]
        subprocess.run(cmd, check=True)
        return output_path

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    durations = [_get_video_duration(p) for p in valid_paths]
    inputs = []
    for p in valid_paths:
        inputs.extend(["-i", p])

    filter_chains = []
    current_offset = durations[0] - transition_duration
    last_v = "0:v"
    last_a = "0:a"

    for i in range(1, len(valid_paths)):
        next_v = f"{i}:v"
        next_a = f"{i}:a"
        out_v = f"v{i}"
        out_a = f"a{i}"

        trans = preferred_transition or random.choice(AVAILABLE_TRANSITIONS)
        offset = max(0.1, current_offset)

        filter_chains.append(
            f"[{last_v}][{next_v}]xfade=transition={trans}:duration={transition_duration}:offset={offset:.3f}[{out_v}]"
        )
        filter_chains.append(
            f"[{last_a}][{next_a}]acrossfade=d={transition_duration}[{out_a}]"
        )

        last_v = out_v
        last_a = out_a
        current_offset = (current_offset + durations[i]) - transition_duration

    filter_complex = ";".join(filter_chains)

    cmd = [
        ffmpeg_exe,
        "-y",
        "-loglevel", "error",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", f"[{last_v}]",
        "-map", f"[{last_a}]",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "22",
        "-c:a", "aac",
        "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        output_path,
    ]

    subprocess.run(cmd, check=True)
    return output_path
