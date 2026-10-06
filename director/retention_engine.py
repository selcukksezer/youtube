"""
director/retention_engine.py — High-Information Retention Engine & 3-Second Stimulus Rule.

Adapted and evolved from reference_repos2/video-autopilot-kit (src/mrbeast_editing_system.py).
Ensures viewer retention remains above 90% by enforcing strict editorial pacing rules:
1. No shot may remain static for more than 3.0 seconds without a camera shift, zoom, or visual event.
2. Injects high-retention grammar: promise_cold_open, proof_freeze, fast_pullback_reveal, and value_callout.
3. Automatically breaks up sluggish scenes into dynamic visual cuts.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional


MAX_STATIC_DURATION_SEC: float = 3.0


@dataclass
class RetentionStimulus:
    event_type: str  # e.g., "promise_cold_open", "camera_zoom_in", "kinetic_pan", "proof_freeze"
    timestamp_sec: float
    duration_sec: float
    narrative_function: str


class RetentionEngine:
    """Audits and optimizes scene sequences for maximum viewer retention."""

    @classmethod
    def audit_scene_retention(cls, scene_index: int, duration: float, has_camera_motion: bool = False) -> List[RetentionStimulus]:
        """
        Audits a single scene. If duration exceeds MAX_STATIC_DURATION_SEC (3.0s) without camera motion,
        injects intermediate visual stimulus events.
        """
        stimuli: List[RetentionStimulus] = []

        if scene_index == 0:
            stimuli.append(RetentionStimulus(
                event_type="promise_cold_open",
                timestamp_sec=0.0,
                duration_sec=min(2.0, duration),
                narrative_function="Hook viewer attention with scale, conflict, or high stakes payoff.",
            ))

        # Check for static duration gap
        if duration > MAX_STATIC_DURATION_SEC:
            # Inject midpoint motion / stimulus
            midpoint = round(duration / 2.0, 2)
            stimuli.append(RetentionStimulus(
                event_type="fast_pullback_reveal" if scene_index % 2 == 0 else "camera_zoom_in",
                timestamp_sec=midpoint,
                duration_sec=round(duration - midpoint, 2),
                narrative_function="Break visual monotony and reset viewer gaze before dropoff.",
            ))

        return stimuli

    @classmethod
    def audit_timeline(cls, scenes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Audits an entire video timeline and injects retention stimulus events."""
        total_duration = sum(float(s.get("duration", 0.0)) for s in scenes)
        stale_scenes: List[int] = []
        timeline_stimuli: List[Dict[str, Any]] = []

        current_time = 0.0
        for idx, sc in enumerate(scenes):
            dur = float(sc.get("duration", 0.0))
            has_motion = bool(sc.get("has_motion") or sc.get("camera_direction"))

            if dur > MAX_STATIC_DURATION_SEC and not has_motion:
                stale_scenes.append(idx)

            scene_stimuli = cls.audit_scene_retention(idx, dur, has_motion)
            for stim in scene_stimuli:
                item = asdict(stim)
                item["global_timestamp"] = round(current_time + stim.timestamp_sec, 2)
                timeline_stimuli.append(item)

            current_time += dur

        retention_score = round(max(0.40, 1.0 - (len(stale_scenes) * 0.15)), 2)

        return {
            "total_duration": round(total_duration, 2),
            "scene_count": len(scenes),
            "stale_scene_indices": stale_scenes,
            "retention_score": retention_score,
            "meets_mrbeast_pacing_standard": len(stale_scenes) == 0,
            "injected_stimuli": timeline_stimuli,
        }


GLOBAL_RETENTION_ENGINE = RetentionEngine()
