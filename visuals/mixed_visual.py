"""Optional mixed visual engine. Off unless the studio dropdown is mixed.

Rotation per scene index: stock, Flux.
auto, flux, and whiteboard keep their existing single-engine behavior.
"""
from __future__ import annotations

from typing import Any, Optional

MIXED_ALIASES = frozenset({"mixed", "karisik", "karışık"})
MIXED_ROTATION = ("stock", "flux")


def is_mixed_mode(mode: Optional[str]) -> bool:
    return str(mode or "").strip().lower() in MIXED_ALIASES


def mixed_scene_mode(index: int) -> str:
    return MIXED_ROTATION[int(index) % len(MIXED_ROTATION)]


def apply_selected_visual_mode(plan: Any, selected: Optional[str]) -> None:
    """Stamp the pre-render dropdown onto the plan.

    Mixed replaces every scene mode with the rotation.
    Any other explicit mode only fills scenes that have no mode yet.
    auto leaves the plan untouched.
    """
    if not isinstance(plan, dict):
        return
    mode = str(selected or "").strip().lower()
    if not mode or mode == "auto":
        return
    plan["visual_mode"] = mode
    scenes = plan.get("scenes") or []
    if is_mixed_mode(mode):
        for index, scene in enumerate(scenes):
            if isinstance(scene, dict):
                scene["visual_mode"] = mixed_scene_mode(index)
        return
    for scene in scenes:
        if isinstance(scene, dict) and not scene.get("visual_mode"):
            scene["visual_mode"] = mode
