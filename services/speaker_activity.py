"""Local mouth-motion and audio analysis for dialogue-aware clip framing."""
from __future__ import annotations

import math
import os
import subprocess
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

import numpy as np

WINDOW_SECONDS = 0.4
SAMPLE_RATE = 5
ANALYSIS_WIDTH = 480
AUDIO_FLOOR = 0.18
MIN_MARGIN = 0.15
MIN_SPEAKER_SHARE = 0.2


class SpeakerActivityUnavailable(RuntimeError):
    """Raised when local active-speaker analysis cannot be completed."""


@dataclass(frozen=True)
class SpeakerActivityResult:
    speaker_shares: Tuple[float, float]
    dominant_speaker: Optional[int]
    is_conversation: bool
    windows_analyzed: int


def normalise_activity(
    activity: Sequence[Tuple[float, float]],
) -> List[Tuple[float, float]]:
    if not activity:
        return []
    columns = np.asarray(activity, dtype=float)
    if columns.ndim != 2 or columns.shape[1] != 2:
        return []
    low = np.percentile(columns, 20, axis=0)
    high = np.percentile(columns, 80, axis=0)
    spread = np.where(high - low > 1e-6, high - low, 1.0)
    normalised = np.clip((columns - low) / spread, 0.0, None)
    return [(float(row[0]), float(row[1])) for row in normalised]


def classify_activity(
    activity: Sequence[Tuple[float, float]],
    loudness: Sequence[Optional[float]] = (),
) -> SpeakerActivityResult:
    normalised = normalise_activity(activity)
    verdicts: List[Optional[int]] = []
    for index, ((raw_first, raw_second), (first, second)) in enumerate(
        zip(activity, normalised)
    ):
        if (
            index < len(loudness)
            and loudness[index] is not None
            and loudness[index] < AUDIO_FLOOR
        ):
            verdicts.append(None)
            continue
        raw_total = raw_first + raw_second
        if raw_total <= 0 or abs(raw_first - raw_second) / raw_total < MIN_MARGIN:
            verdicts.append(None)
            continue
        total = first + second
        if total <= 0:
            verdicts.append(None)
            continue
        margin = abs(first - second) / total
        verdicts.append(
            None if margin < MIN_MARGIN else (0 if first > second else 1)
        )

    attributed = [speaker for speaker in verdicts if speaker is not None]
    if not attributed:
        return SpeakerActivityResult((0.0, 0.0), None, False, len(normalised))

    first_share = attributed.count(0) / len(attributed)
    second_share = attributed.count(1) / len(attributed)
    shares = (first_share, second_share)
    dominant = 0 if first_share >= second_share else 1
    conversation = min(shares) >= MIN_SPEAKER_SHARE
    return SpeakerActivityResult(shares, dominant, conversation, len(normalised))


def _mouth_regions(
    width: int,
    height: int,
    centers: Tuple[Tuple[float, float], Tuple[float, float]],
) -> List[Tuple[int, int, int, int]]:
    half_width = max(2, int(width * 0.035))
    half_height = max(2, int(height * 0.025))
    regions = []
    for center_x, center_y in centers:
        x = int(center_x * width)
        y = int(center_y * height + height * 0.035)
        x0 = max(0, min(width - 1, x - half_width))
        x1 = max(x0 + 1, min(width, x + half_width))
        y0 = max(0, min(height - 1, y - half_height))
        y1 = max(y0 + 1, min(height, y + half_height))
        regions.append((x0, y0, x1, y1))
    return regions


def _audio_envelope(
    video_path: str,
    start: float,
    duration: float,
) -> List[float]:
    import imageio_ffmpeg

    result = subprocess.run(
        [
            imageio_ffmpeg.get_ffmpeg_exe(),
            "-v", "error",
            "-ss", f"{start:.4f}",
            "-t", f"{duration:.4f}",
            "-i", video_path,
            "-map", "0:a:0?",
            "-vn",
            "-ac", "1",
            "-ar", "8000",
            "-f", "s16le",
            "-",
        ],
        capture_output=True,
        timeout=120,
        check=False,
    )
    if result.returncode != 0:
        error = result.stderr.decode("utf-8", errors="replace")
        if "does not contain any stream" in error.lower():
            return []
        raise SpeakerActivityUnavailable(
            f"FFmpeg ses etkinliğini çözemedi: {error[-240:].strip()}"
        )
    if not result.stdout:
        return []

    samples = np.frombuffer(result.stdout, dtype=np.int16).astype(np.float32)
    window_size = int(8000 * WINDOW_SECONDS)
    rms = [
        float(np.sqrt(np.mean(samples[offset:offset + window_size] ** 2)))
        for offset in range(0, len(samples), window_size)
    ]
    peak = max(rms, default=0.0)
    return [value / peak for value in rms] if peak > 0 else [0.0] * len(rms)


def analyze_speaker_activity(
    video_path: str,
    spans: Sequence[Tuple[float, float]],
    centers: Tuple[Tuple[float, float], Tuple[float, float]],
) -> SpeakerActivityResult:
    """Measure which of two stable face regions is speaking in each clip span."""
    if not os.path.isfile(video_path):
        raise SpeakerActivityUnavailable("Kaynak video etkin konuşmacı analizi için bulunamadı.")
    usable_spans = [
        (float(start), float(end))
        for start, end in spans
        if float(end) > float(start)
    ]
    if not usable_spans:
        raise SpeakerActivityUnavailable("Etkin konuşmacı analizi için geçerli aralık yok.")

    try:
        import cv2
    except ImportError as exc:
        raise SpeakerActivityUnavailable("OpenCV etkin konuşmacı analizi için gerekli.") from exc

    capture = cv2.VideoCapture(video_path)
    if not capture.isOpened():
        capture.release()
        raise SpeakerActivityUnavailable("Kaynak video etkin konuşmacı analizi için açılamadı.")

    frame_width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    frame_height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    if frame_width < 2 or frame_height < 2:
        capture.release()
        raise SpeakerActivityUnavailable("Kaynak video kare boyutları okunamadı.")

    analysis_width = min(ANALYSIS_WIDTH, frame_width)
    analysis_width -= analysis_width % 2
    analysis_height = max(
        2,
        int(frame_height * analysis_width / frame_width),
    )
    regions = _mouth_regions(analysis_width, analysis_height, centers)
    activity: List[Tuple[float, float]] = []
    audio: List[Optional[float]] = []

    try:
        for start, end in usable_spans:
            duration = end - start
            sample_count = max(2, int(math.ceil(duration * SAMPLE_RATE)))
            previous: Optional[np.ndarray] = None
            window_sums: List[List[float]] = []
            window_counts: List[int] = []
            for sample_index in range(sample_count):
                offset = sample_index / SAMPLE_RATE
                if offset >= duration:
                    break
                capture.set(cv2.CAP_PROP_POS_MSEC, (start + offset) * 1000.0)
                ok, frame = capture.read()
                if not ok or frame is None:
                    continue
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                if gray.shape[1] != analysis_width:
                    gray = cv2.resize(
                        gray,
                        (analysis_width, analysis_height),
                        interpolation=cv2.INTER_AREA,
                    )
                if previous is not None:
                    window_index = int(offset / WINDOW_SECONDS)
                    while len(window_sums) <= window_index:
                        window_sums.append([0.0, 0.0])
                        window_counts.append(0)
                    differences = []
                    for x0, y0, x1, y1 in regions:
                        current_patch = gray[y0:y1, x0:x1].astype(np.int16)
                        previous_patch = previous[y0:y1, x0:x1].astype(np.int16)
                        differences.append(
                            float(np.mean(np.abs(current_patch - previous_patch)))
                        )
                    window_sums[window_index][0] += differences[0]
                    window_sums[window_index][1] += differences[1]
                    window_counts[window_index] += 1
                previous = gray

            span_activity = [
                (first / count, second / count)
                for (first, second), count in zip(window_sums, window_counts)
                if count
            ]
            activity.extend(span_activity)
            span_audio = _audio_envelope(video_path, start, duration)
            audio.extend(
                span_audio[index] if index < len(span_audio) else None
                for index in range(len(span_activity))
            )
    except (cv2.error, OSError, ValueError, subprocess.SubprocessError) as exc:
        raise SpeakerActivityUnavailable(
            f"Etkin konuşmacı analizi başarısız: {type(exc).__name__}"
        ) from exc
    finally:
        capture.release()

    return classify_activity(activity, audio)
