"""
Scene Pacing & Deduplication Guard.
Adapted from gyoridavid/short-video-maker (excludeVideoIds, paddingBack, and scene pacing).

Enforces:
1. Strict visual asset deduplication across all scenes (exclude_ids).
2. Dynamic tail padding (padding_back_ms) to ensure smooth loop transition without abrupt audio cutoff.
3. Scene duration limits (1.5s <= duration <= 6.0s) to maximize YouTube Shorts retention.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class PacingAuditResult:
    is_valid: bool
    total_duration_sec: float
    scene_count: int
    padding_back_sec: float
    violations: List[str] = field(default_factory=list)
    repaired_scenes: List[Dict[str, Any]] = field(default_factory=list)


class ScenePacingGuard:
    """Audits and balances scene durations, asset reuse, and loop padding."""

    def __init__(
        self,
        min_scene_sec: float = 1.5,
        max_scene_sec: float = 6.0,
        target_total_max_sec: float = 58.0,
        default_padding_back_ms: int = 750,
    ):
        self.min_scene_sec = min_scene_sec
        self.max_scene_sec = max_scene_sec
        self.target_total_max_sec = target_total_max_sec
        self.default_padding_back_ms = default_padding_back_ms

    def audit_and_repair(
        self,
        scenes: List[Dict[str, Any]],
        padding_back_ms: Optional[int] = None,
    ) -> PacingAuditResult:
        """
        Audits a scene sequence and repairs pacing issues:
        - Clamps short scenes (<1.5s) and marks long scenes (>6.0s).
        - Tracks and flags duplicate visual asset IDs.
        - Adds tail padding to the last scene for loop transition.
        """
        if not scenes:
            return PacingAuditResult(
                is_valid=False,
                total_duration_sec=0.0,
                scene_count=0,
                padding_back_sec=0.0,
                violations=["scenes list is empty"],
                repaired_scenes=[],
            )

        pad_ms = padding_back_ms if padding_back_ms is not None else self.default_padding_back_ms
        pad_sec = pad_ms / 1000.0

        used_visual_ids: Set[str] = set()
        violations: List[str] = []
        repaired: List[Dict[str, Any]] = []
        total_duration = 0.0

        for idx, sc in enumerate(scenes):
            sc_copy = dict(sc)
            dur = float(sc.get("duration") or sc.get("target_duration") or 4.0)

            # 1. Deduplication check
            v_id = str(sc.get("visual_id") or sc.get("video_id") or sc.get("asset_path") or "").strip()
            if v_id:
                if v_id in used_visual_ids:
                    violations.append(f"Scene {idx}: duplicate visual asset '{v_id}' reused")
                    # Clear duplicate visual_id to trigger fallback in fetcher
                    sc_copy["visual_id"] = None
                    sc_copy["force_new_visual"] = True
                else:
                    used_visual_ids.add(v_id)

            # 2. Duration bounds check
            if dur < self.min_scene_sec:
                violations.append(f"Scene {idx}: duration {dur:.2f}s is below minimum {self.min_scene_sec}s")
                dur = self.min_scene_sec
            elif dur > self.max_scene_sec:
                violations.append(f"Scene {idx}: duration {dur:.2f}s exceeds maximum {self.max_scene_sec}s")
                # Mark for dual B-roll split or sub-cut
                sc_copy["split_required"] = True

            sc_copy["duration"] = round(dur, 2)
            total_duration += dur
            repaired.append(sc_copy)

        # 3. Tail padding on last scene
        if repaired:
            last = repaired[-1]
            last["padding_back_sec"] = pad_sec
            total_duration += pad_sec

        # 4. Total duration check (Shorts max 60s, sweet spot 50-58s)
        if total_duration > self.target_total_max_sec:
            violations.append(
                f"Total video duration {total_duration:.1f}s exceeds recommended Shorts ceiling {self.target_total_max_sec}s"
            )

        is_valid = len(violations) == 0
        return PacingAuditResult(
            is_valid=is_valid,
            total_duration_sec=round(total_duration, 2),
            scene_count=len(repaired),
            padding_back_sec=pad_sec,
            violations=violations,
            repaired_scenes=repaired,
        )


scene_pacing_guard = ScenePacingGuard()
