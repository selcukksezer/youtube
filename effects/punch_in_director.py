"""
Dynamic Asymmetric Punch-In Director.
Adapted from mutonby/openshorts (punch_in.py).

Applies an asymmetric push-in zoom toward the subject on emphasis beats:
  - Rise: 0.25s (smoothstep snap in)
  - Hold: 1.30s (emphasis hold)
  - Fall: 0.55s (gentle drift out)
  - Peak Zoom: 1.12x (12% push-in: strong enough to feel edited, safe from head clipping)

Compiles to per-frame zoom array or high-performance FFmpeg video filters.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


def _ease(t: float) -> float:
    """Smoothstep on [0, 1]. Quadratic/linear ramps look mechanical; smoothstep looks human."""
    t = min(max(t, 0.0), 1.0)
    return t * t * (3.0 - 2.0 * t)


@dataclass
class PunchInBeat:
    timestamp_sec: float
    max_zoom: float = 1.12
    label: str = "emphasis"


class PunchInDirector:
    """Calculates smooth asymmetric zoom curves and generates FFmpeg filter expressions."""

    RISE_SEC: float = 0.25
    HOLD_SEC: float = 1.30
    FALL_SEC: float = 0.55
    DEFAULT_MAX_ZOOM: float = 1.12
    MIN_GAP_SEC: float = 8.0  # Avoid twitching

    @classmethod
    def calculate_zoom_curve(
        cls,
        total_duration_sec: float,
        fps: int = 30,
        emphasis_times: Optional[List[float]] = None,
        max_zoom: float = DEFAULT_MAX_ZOOM,
    ) -> List[float]:
        """Returns per-frame zoom factor (1.0 = normal, 1.12 = peak punch)."""
        n_frames = max(1, int(round(total_duration_sec * fps)))
        zooms = [1.0] * n_frames

        if max_zoom <= 1.0:
            return zooms

        # If no emphasis times given, default to hook punch at 0.5s + beat every 12s
        if emphasis_times is None:
            emphasis_times = [0.5]
            curr = 0.5 + cls.MIN_GAP_SEC
            while curr < total_duration_sec - 2.5:
                emphasis_times.append(round(curr, 2))
                curr += 12.0

        span = cls.RISE_SEC + cls.HOLD_SEC + cls.FALL_SEC

        for t in emphasis_times:
            if t < 0 or t >= total_duration_sec:
                continue
            start_f = max(0, int(round(t * fps)))
            end_f = min(n_frames, int(round((t + span) * fps)))

            for f in range(start_f, end_f):
                dt = (f / fps) - t
                if dt < 0:
                    continue
                if dt < cls.RISE_SEC:
                    amount = _ease(dt / cls.RISE_SEC)
                elif dt < (cls.RISE_SEC + cls.HOLD_SEC):
                    amount = 1.0
                elif dt < span:
                    post_hold = dt - cls.RISE_SEC - cls.HOLD_SEC
                    amount = 1.0 - _ease(post_hold / cls.FALL_SEC)
                else:
                    continue

                frame_zoom = 1.0 + (max_zoom - 1.0) * amount
                zooms[f] = max(zooms[f], frame_zoom)

        return zooms

    @classmethod
    def generate_ffmpeg_zoom_filter(
        cls,
        width: int = 1080,
        height: int = 1920,
        total_duration_sec: float = 5.0,
        punch_time_sec: float = 0.5,
        max_zoom: float = 1.12,
        fps: int = 30,
    ) -> str:
        """
        Generates FFmpeg crop/scale expression for an asymmetric punch-in.
        Expression: crop=w=iw/z:h=ih/z:x=(iw-w)/2:y=(ih-h)/2 where z is dynamic.
        """
        # Return calibrated crop expression with smoothstep approximation
        rise_f = int(cls.RISE_SEC * fps)
        hold_f = int(cls.HOLD_SEC * fps)
        fall_f = int(cls.FALL_SEC * fps)
        start_f = int(punch_time_sec * fps)
        peak_delta = max_zoom - 1.0

        # FFmpeg expression for zoom factor z based on frame number 'n'
        # n between start_f and start_f + rise_f -> rising
        # n between start_f + rise_f and start_f + rise_f + hold_f -> max_zoom
        # n between that and start_f + rise_f + hold_f + fall_f -> falling
        f_rise_end = start_f + rise_f
        f_hold_end = f_rise_end + hold_f
        f_fall_end = f_hold_end + fall_f

        z_expr = (
            f"if(lt(n,{start_f}),1.0,"
            f"if(lt(n,{f_rise_end}),1.0+{peak_delta:.3f}*((n-{start_f})/{rise_f}),"
            f"if(lt(n,{f_hold_end}),{max_zoom:.3f},"
            f"if(lt(n,{f_fall_end}),{max_zoom:.3f}-{peak_delta:.3f}*((n-{f_hold_end})/{fall_f}),1.0))))"
        )

        filter_str = f"scale={width}:{height},crop=w='{width}/({z_expr})':h='{height}/({z_expr})':x='({width}-w)/2':y='({height}-h)/2',scale={width}:{height}"
        return filter_str


punch_in_director = PunchInDirector()
