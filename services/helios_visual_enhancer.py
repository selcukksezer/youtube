"""
Helios Visual Enhancer Service.
Applies PKU-YuanGroup/Helios cinematographic shot grammar across all script scenes.

Eliminates repetitive and static scenes by injecting varied camera motions,
micro-actions, volumetric lighting, and anti-artifact negative prompting.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from visuals.ai_video.helios_prompt_builder import (
    HELIOS_NEGATIVE_PROMPT,
    HeliosPromptBuilder,
    HeliosShotParams,
    CAMERA_MOVEMENTS,
)


class HeliosVisualEnhancer:
    """Enhances raw script scenes with cinematographic shot grammar and AI video parameters."""

    @classmethod
    def enhance_single_scene(
        cls,
        scene: Dict[str, Any],
        scene_index: int = 0,
        niche_id: str = "general",
        aspect: str = "9:16",
    ) -> Dict[str, Any]:
        """Enriches a scene dictionary with Helios cinematographic parameters."""
        narration = str(scene.get("narration") or scene.get("text") or "").strip()
        raw_desc = str(scene.get("scene_description") or scene.get("visual_intent") or "").strip()

        # Select sequenced camera motion
        motion = CAMERA_MOVEMENTS[scene_index % len(CAMERA_MOVEMENTS)]

        # Generate Helios 4-tier prompt
        helios_prompt = HeliosPromptBuilder.build_shot_prompt(
            narration=narration,
            scene_description=raw_desc,
            niche_id=niche_id,
            camera_motion=motion,
            aspect=aspect,
            index=scene_index,
        )

        helios_params: HeliosShotParams = HeliosPromptBuilder.create_helios_params(
            narration=narration,
            scene_description=raw_desc,
            niche_id=niche_id,
            aspect=aspect,
            index=scene_index,
        )

        enhanced = dict(scene)
        enhanced["helios_prompt"] = helios_prompt
        enhanced["helios_negative_prompt"] = HELIOS_NEGATIVE_PROMPT
        enhanced["helios_camera_motion"] = motion
        enhanced["helios_inference_config"] = helios_params.to_dict()

        # If scene description was empty or too brief, upgrade it
        if not raw_desc or len(raw_desc) < 15:
            enhanced["scene_description"] = helios_prompt

        return enhanced

    @classmethod
    def enhance_scenes_sequence(
        cls,
        scenes: List[Dict[str, Any]],
        niche_id: str = "general",
        aspect: str = "9:16",
    ) -> List[Dict[str, Any]]:
        """Applies alternating camera movements and progressive pacing across a scene sequence."""
        enhanced_list = []
        for idx, scene in enumerate(scenes):
            enhanced = cls.enhance_single_scene(
                scene=scene,
                scene_index=idx,
                niche_id=niche_id,
                aspect=aspect,
            )
            enhanced_list.append(enhanced)
        return enhanced_list


helios_visual_enhancer = HeliosVisualEnhancer()
