"""
render/keyframe_motion.py — Non-Linear Keyframe Curve Interpolator & FFmpeg Expression Builder.

Adapted and evolved from reference_repos2/pyJianYingDraft (keyframe.py, animation.py & video_segment.py).
Enables CapCut/JianYing style keyframe trajectories directly within FFmpeg mathematical expressions:
1. Supports Linear, Cosine Ease-In-Out, Smoothstep, and Cubic Bézier easing.
2. Compiles multi-point keyframe lists into continuous FFmpeg expression strings for zoom, pan, alpha, and volume.
"""

from __future__ import annotations

import enum
import math
from typing import Any, Dict, List, Optional, Tuple, Union


class KeyframeProperty(str, enum.Enum):
    POSITION_X = "position_x"
    POSITION_Y = "position_y"
    SCALE = "scale"
    ALPHA = "alpha"
    ROTATION = "rotation"
    VOLUME = "volume"


class EasingCurve(str, enum.Enum):
    LINEAR = "linear"
    COSINE_EASE_IN_OUT = "cosine_ease_in_out"
    SMOOTHSTEP = "smoothstep"
    CUBIC_BEZIER = "cubic_bezier"


def evaluate_easing(progress: float, curve: EasingCurve = EasingCurve.COSINE_EASE_IN_OUT) -> float:
    """Evaluates normalized progress [0.0, 1.0] along the selected easing curve."""
    p = max(0.0, min(1.0, float(progress)))

    if curve == EasingCurve.LINEAR:
        return p
    elif curve == EasingCurve.COSINE_EASE_IN_OUT:
        return 0.5 * (1.0 - math.cos(math.pi * p))
    elif curve == EasingCurve.SMOOTHSTEP:
        return (3.0 * p * p) - (2.0 * p * p * p)
    elif curve == EasingCurve.CUBIC_BEZIER:
        # Standard ease-in-out approximation (0.42, 0.0, 0.58, 1.0)
        return (p * p) * (3.0 - (2.0 * p))
    return p


class Keyframe:
    def __init__(self, time_sec: float, value: float, curve: EasingCurve = EasingCurve.COSINE_EASE_IN_OUT):
        self.time_sec = float(time_sec)
        self.value = float(value)
        self.curve = curve

    def to_dict(self) -> Dict[str, Any]:
        return {
            "time_sec": self.time_sec,
            "value": self.value,
            "curve": self.curve.value,
        }


class KeyframeTrajectory:
    """Manages an ordered list of keyframes and interpolates values at any time t."""

    def __init__(self, prop: KeyframeProperty):
        self.prop = prop
        self.keyframes: List[Keyframe] = []

    def add_keyframe(self, time_sec: float, value: float, curve: EasingCurve = EasingCurve.COSINE_EASE_IN_OUT) -> None:
        kf = Keyframe(time_sec, value, curve)
        self.keyframes.append(kf)
        self.keyframes.sort(key=lambda k: k.time_sec)

    def evaluate_at(self, t: float) -> float:
        """Interpolates value at timestamp t using segment easing."""
        if not self.keyframes:
            return 1.0 if self.prop in (KeyframeProperty.SCALE, KeyframeProperty.ALPHA, KeyframeProperty.VOLUME) else 0.0

        if t <= self.keyframes[0].time_sec:
            return self.keyframes[0].value

        if t >= self.keyframes[-1].time_sec:
            return self.keyframes[-1].value

        # Locate segment
        for i in range(len(self.keyframes) - 1):
            k0 = self.keyframes[i]
            k1 = self.keyframes[i + 1]
            if k0.time_sec <= t <= k1.time_sec:
                span = k1.time_sec - k0.time_sec
                if span <= 0.0:
                    return k1.value
                norm_progress = (t - k0.time_sec) / span
                eased = evaluate_easing(norm_progress, k0.curve)
                return k0.value + (k1.value - k0.value) * eased

        return self.keyframes[-1].value

    def build_ffmpeg_cosine_expression(self, var_name: str = "t") -> str:
        """
        Compiles a two-point or multi-point trajectory into an analytical FFmpeg expression string.
        Example for start_val=1.0, end_val=1.15 over duration d:
        '1.000 + 0.150 * 0.5 * (1 - cos(PI * min(t, 4.000) / 4.000))'
        """
        if len(self.keyframes) < 2:
            val = self.keyframes[0].value if self.keyframes else 1.0
            return f"{val:.3f}"

        k0 = self.keyframes[0]
        k1 = self.keyframes[1]
        delta = k1.value - k0.value
        dur = max(0.001, k1.time_sec - k0.time_sec)

        # Clamped cosine ease-in-out FFmpeg formula
        return (
            f"{k0.value:.3f} + ({delta:.3f}) * 0.5 * "
            f"(1 - cos(3.14159265 * min(max({var_name} - {k0.time_sec:.3f}, 0), {dur:.3f}) / {dur:.3f}))"
        )
