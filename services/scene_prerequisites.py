"""
services/scene_prerequisites.py — Scene Asset Prerequisite Gate & Preflight Validation.

Adapted and evolved from reference_repos2/dramaclaw (src/novelvideo/scene_prerequisites.py).
Prevents expensive rendering crashes by ensuring all scene audio, visual assets,
and narration metadata are fully present and non-zero byte before starting FFmpeg.
"""

from __future__ import annotations

import os
import math
from typing import Any, Dict, List, Optional, Tuple


class ScenePrerequisiteError(Exception):
    """Raised when scene prerequisites fail validation."""

    def __init__(self, message: str, errors: List[Dict[str, Any]]):
        super().__init__(message)
        self.errors = errors


class ScenePrerequisiteGate:
    """Preflight validation gate for scene assets."""

    @staticmethod
    def validate_scene(scene_index: int, scene_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        errors: List[Dict[str, Any]] = []

        # 1. Visual asset verification
        visual_path = scene_data.get("visual_path") or scene_data.get("video_path") or scene_data.get("image_path")
        if not visual_path:
            errors.append({
                "scene_index": scene_index,
                "field": "visual_path",
                "code": "MISSING_VISUAL_ASSET",
                "message": f"Scene {scene_index} has no visual asset path defined.",
            })
        elif not isinstance(visual_path, (str, os.PathLike)) or not os.path.isfile(visual_path):
            errors.append({
                "scene_index": scene_index,
                "field": "visual_path",
                "code": "VISUAL_FILE_NOT_FOUND",
                "message": f"Scene {scene_index} visual file does not exist or is not a file: {visual_path}",
            })
        elif os.path.getsize(visual_path) == 0:
            errors.append({
                "scene_index": scene_index,
                "field": "visual_path",
                "code": "EMPTY_VISUAL_FILE",
                "message": f"Scene {scene_index} visual file is 0 bytes: {visual_path}",
            })

        # 2. Audio asset verification (if audio is marked required or present)
        audio_path = scene_data.get("audio_path")
        requires_audio = scene_data.get("requires_audio", True)
        if requires_audio:
            if not audio_path:
                errors.append({
                    "scene_index": scene_index,
                    "field": "audio_path",
                    "code": "MISSING_AUDIO_ASSET",
                    "message": f"Scene {scene_index} has no audio asset path defined.",
                })
            elif not isinstance(audio_path, (str, os.PathLike)) or not os.path.isfile(audio_path):
                errors.append({
                    "scene_index": scene_index,
                    "field": "audio_path",
                    "code": "AUDIO_FILE_NOT_FOUND",
                    "message": f"Scene {scene_index} audio file does not exist or is not a file: {audio_path}",
                })
            elif os.path.getsize(audio_path) == 0:
                errors.append({
                    "scene_index": scene_index,
                    "field": "audio_path",
                    "code": "EMPTY_AUDIO_FILE",
                    "message": f"Scene {scene_index} audio file is 0 bytes: {audio_path}",
                })

        # 3. Duration validation
        raw_duration = scene_data.get("duration", 0.0)
        try:
            duration: Optional[float] = float(raw_duration)
        except (TypeError, ValueError):
            duration = None
        if duration is None or not math.isfinite(duration) or duration <= 0.0:
            errors.append({
                "scene_index": scene_index,
                "field": "duration",
                "code": "INVALID_DURATION",
                "message": f"Scene {scene_index} has invalid or zero duration: {raw_duration}s.",
            })

        return errors

    @classmethod
    def validate_all_scenes(cls, scenes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validates all scenes in a plan before rendering."""
        if not scenes:
            return {
                "valid": False,
                "total_scenes": 0,
                "passed_scenes": 0,
                "errors": [{"code": "NO_SCENES", "message": "Scene list is empty."}],
            }

        all_errors: List[Dict[str, Any]] = []
        passed_scenes = 0

        for idx, sc in enumerate(scenes):
            sc_errors = cls.validate_scene(idx, sc)
            if sc_errors:
                all_errors.extend(sc_errors)
            else:
                passed_scenes += 1

        return {
            "valid": len(all_errors) == 0,
            "total_scenes": len(scenes),
            "passed_scenes": passed_scenes,
            "errors": all_errors,
        }

    @classmethod
    def check_prerequisites_or_raise(cls, scenes: List[Dict[str, Any]]) -> None:
        """Raises ScenePrerequisiteError if any validation failures exist."""
        report = cls.validate_all_scenes(scenes)
        if not report["valid"]:
            err_count = len(report["errors"])
            raise ScenePrerequisiteError(
                f"Scene prerequisite validation failed with {err_count} errors.",
                report["errors"],
            )

    @classmethod
    def check_render_prerequisites_or_raise(
        cls,
        clips: List[Dict[str, Any]],
        narration_audio_path: Optional[str],
    ) -> None:
        """Validate scene visuals and the shared narration track before final FFmpeg composition."""
        scene_assets = [
            {
                "visual_path": clip.get("path"),
                "duration": clip.get("duration", 0.0),
                "requires_audio": False,
            }
            if isinstance(clip, dict)
            else {"visual_path": None, "duration": 0.0, "requires_audio": False}
            for clip in clips
        ]
        report = cls.validate_all_scenes(scene_assets)
        errors = list(report["errors"])

        if not narration_audio_path or not isinstance(narration_audio_path, (str, os.PathLike)):
            errors.append({
                "scene_index": -1,
                "field": "narration_audio_path",
                "code": "MISSING_AUDIO_ASSET",
                "message": "Render has no narration audio path.",
            })
        elif not os.path.isfile(narration_audio_path):
            errors.append({
                "scene_index": -1,
                "field": "narration_audio_path",
                "code": "AUDIO_FILE_NOT_FOUND",
                "message": f"Narration audio file does not exist or is not a file: {narration_audio_path}",
            })
        else:
            try:
                audio_size = os.path.getsize(narration_audio_path)
            except OSError as exc:
                errors.append({
                    "scene_index": -1,
                    "field": "narration_audio_path",
                    "code": "AUDIO_FILE_UNREADABLE",
                    "message": f"Could not inspect narration audio file: {exc}",
                })
            else:
                if audio_size == 0:
                    errors.append({
                        "scene_index": -1,
                        "field": "narration_audio_path",
                        "code": "EMPTY_AUDIO_FILE",
                        "message": f"Narration audio file is 0 bytes: {narration_audio_path}",
                    })

        if errors:
            details = "; ".join(error["message"] for error in errors)
            raise ScenePrerequisiteError(
                f"Render prerequisite validation failed: {details}",
                errors,
            )


GLOBAL_PREREQUISITE_GATE = ScenePrerequisiteGate()
