"""
Helios Cinematographic Prompt Builder & Shot Synthesizer.
Adapted from PKU-YuanGroup/Helios (14B Real-Time Long Video Model).

Helios 4-Tier Shot Architecture:
  1. Camera Angle & Dynamic Movement (Orbital pan, tracking shot, push-in, low-angle)
  2. Subject & Physical Micro-Action (Eyes focusing, fabric flutter, particles, steam)
  3. Environment, Lighting & Volumetric Depth (Golden hour, rim light, bokeh, fog)
  4. Optic Texture & Film Grade (35mm film, anamorphic flares, HDR, shallow DOF)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# Official Helios Anti-Artifact Negative Prompt
HELIOS_NEGATIVE_PROMPT: str = (
    "Bright tones, overexposed, static, blurred details, subtitles, style, works, "
    "paintings, images, static, overall gray, worst quality, low quality, "
    "JPEG compression residue, ugly, incomplete, extra fingers, poorly drawn hands, "
    "poorly drawn faces, deformed, disfigured, misshapen limbs, fused fingers, "
    "still picture, messy background, three legs, many people in the background, "
    "walking backwards"
)

# Cinematographic camera movements tailored for 9:16 vertical Shorts
CAMERA_MOVEMENTS = [
    "A smooth cinematic camera push-in focusing closely",
    "A dynamic handheld tracking shot following the motion",
    "An extreme close-up shot capturing intense micro-expressions",
    "A slow orbital camera sweep revealing atmospheric depth",
    "A low-angle dynamic tilt shot emphasizing scale and gravity",
    "A steady tracking shot moving through volumetric atmosphere",
]

# Lighting & optic presets
ATMOSPHERE_PRESETS = [
    "cinematic golden hour backlight, soft volumetric sun rays, dreamy bokeh and subtle lens flares",
    "moody chiaroscuro lighting, deep cinematic shadows, subtle rim light and atmospheric haze",
    "crisp high dynamic range, volumetric lighting, photorealistic textures and shallow depth of field",
    "dramatic contrast, soft diffused key light, natural film grain, 35mm film aesthetic",
]

# Niche-specific visual styles
NICHE_TEXTURES = {
    "crypto": "futuristic cyberpunk neon reflections, holographic telemetry overlays, high contrast dark studio",
    "history": "historical cinematic film grain, warm candlelit ambiance, textured vintage fabrics, 35mm film",
    "philosophy": "introspective atmospheric lighting, deep shadows, slow particle dust drifting, contemplative depth",
    "science": "macro lens focus, luminous electron glow, photorealistic microscopic depth, 8k documentary detail",
    "horror": "desaturated eerie lighting, deep vignette, unsettling shadows, suspenseful atmospheric fog",
    "general": "photorealistic cinematic lighting, master color grading, crisp 35mm film optic clarity",
}

# Translation hints for common Turkish action / scene words
TR_TO_EN_ACTION = {
    "baktı": "looks intently with sharp focus",
    "düşündü": "deep in contemplative thought with subtle micro-expressions",
    "yürüdü": "striding forward deliberately",
    "parladı": "glowing with intense volumetric luminescence",
    "patladı": "bursting with explosive kinetic energy and flying debris",
    "yükseldi": "surging upward with dynamic momentum",
    "düştü": "plummeting downward through atmospheric motion blur",
    "şaşırdı": "eyes widening with vivid emotional realization",
    "gülümsedi": "offering a subtle, mysterious closed-mouth smile",
    "fısıldadı": "leaning forward with intense hushed intimacy",
    "kaçtı": "dashing rapidly through the misty background",
    "buldu": "unveiling a glowing artifact with wonder",
}


@dataclass
class HeliosShotParams:
    """Helios model inference parameters."""
    prompt: str
    negative_prompt: str = HELIOS_NEGATIVE_PROMPT
    height: int = 640
    width: int = 384  # 9:16 vertical default
    fps: int = 24
    num_frames: int = 99  # Standard Helios default (~4.125s at 24fps)
    guidance_scale: float = 5.0
    pyramid_steps: List[int] = field(default_factory=lambda: [2, 2, 2])
    is_amplify_first_chunk: bool = True
    aspect: str = "9:16"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prompt": self.prompt,
            "negative_prompt": self.negative_prompt,
            "height": self.height,
            "width": self.width,
            "fps": self.fps,
            "num_frames": self.num_frames,
            "guidance_scale": self.guidance_scale,
            "pyramid_num_inference_steps_list": self.pyramid_steps,
            "is_amplify_first_chunk": self.is_amplify_first_chunk,
            "aspect": self.aspect,
        }


class HeliosPromptBuilder:
    """Synthesizes high-retention cinematographic prompts using the Helios 4-stage formula."""

    @staticmethod
    def _extract_core_subject(narration: str, scene_description: str) -> str:
        combined = f"{scene_description} {narration}".strip()
        # Clean out common filler phrases
        combined = re.sub(
            r"\b(aslında|gerçek şu ki|biliyor muydunuz|dikkat edin|şok edici|inanılmaz|şunu unutma)\b",
            "",
            combined,
            flags=re.IGNORECASE,
        )
        return combined.strip()

    @classmethod
    def build_shot_prompt(
        cls,
        narration: str = "",
        scene_description: str = "",
        niche_id: str = "general",
        camera_motion: Optional[str] = None,
        lighting: Optional[str] = None,
        aspect: str = "9:16",
        index: int = 0,
    ) -> str:
        """
        Builds a full 4-tier Helios prompt.
        Format: [Camera Angle & Movement] + [Subject & Micro-Action] + [Lighting & Atmosphere] + [Film Optic & 9:16 Framing]
        """
        # Tier 1: Camera Angle & Motion
        if not camera_motion:
            camera_motion = CAMERA_MOVEMENTS[index % len(CAMERA_MOVEMENTS)]

        # Tier 2: Subject & Micro-Action
        core_raw = cls._extract_core_subject(narration, scene_description)
        # Apply action translation / enhancement if Turkish keywords found
        action_enhancement = ""
        for tr_verb, en_desc in TR_TO_EN_ACTION.items():
            if tr_verb in core_raw.lower():
                action_enhancement = f", subject {en_desc}"
                break
        
        subject_core = core_raw or "a focused dramatic subject"
        if not action_enhancement and "focus" not in subject_core.lower():
            subject_core += ", dynamic micro-motion, eyes shifting and reacting with natural breathing movement"

        # Tier 3: Environment & Lighting
        niche_key = (niche_id or "general").lower()
        matched_texture = NICHE_TEXTURES.get(niche_key, NICHE_TEXTURES["general"])
        if not lighting:
            lighting = ATMOSPHERE_PRESETS[index % len(ATMOSPHERE_PRESETS)]

        # Tier 4: Optic & Framing
        aspect_framing = "vertical 9:16 smartphone framing, centered composition with balanced headroom" if aspect == "9:16" else "cinematic framing"
        film_finish = f"{aspect_framing}, shallow depth of field, sharp foreground subject, creamy bokeh background, 35mm film aesthetic, no text overlay, no watermark, master color grade."

        prompt_full = f"{camera_motion}: {subject_core}{action_enhancement}. Setting and lighting: {lighting}, {matched_texture}. {film_finish}"
        # Clean extra spaces
        return re.sub(r"\s+", " ", prompt_full).strip()

    @classmethod
    def create_helios_params(
        cls,
        narration: str = "",
        scene_description: str = "",
        niche_id: str = "general",
        duration: float = 4.0,
        aspect: str = "9:16",
        distilled: bool = True,
        index: int = 0,
    ) -> HeliosShotParams:
        """Calculates precise Helios inference configuration for vertical video."""
        prompt = cls.build_shot_prompt(
            narration=narration,
            scene_description=scene_description,
            niche_id=niche_id,
            aspect=aspect,
            index=index,
        )

        # 9:16 resolution: 384x640 or 720x1280
        if aspect == "9:16":
            width, height = 384, 640
        elif aspect == "16:9":
            width, height = 640, 384
        else:
            width, height = 512, 512

        # FPS & frames
        fps = 24
        # Helios native chunks are ~99 frames (~4.125s) or 33 frames (~1.375s)
        num_frames = int(max(33, min(144, round(duration * fps))))
        # Make frame count odd if required by Helios latent chunking:
        if num_frames % 2 == 0:
            num_frames += 1

        pyramid_steps = [2, 2, 2] if distilled else [20, 20, 20]
        guidance_scale = 1.0 if distilled else 5.0

        return HeliosShotParams(
            prompt=prompt,
            negative_prompt=HELIOS_NEGATIVE_PROMPT,
            height=height,
            width=width,
            fps=fps,
            num_frames=num_frames,
            guidance_scale=guidance_scale,
            pyramid_steps=pyramid_steps,
            is_amplify_first_chunk=True,
            aspect=aspect,
        )


def build_helios_prompt(
    narration: str = "",
    scene_description: str = "",
    niche_id: str = "general",
    aspect: str = "9:16",
    index: int = 0,
) -> str:
    """Convenience helper for generating a Helios-optimized prompt."""
    return HeliosPromptBuilder.build_shot_prompt(
        narration=narration,
        scene_description=scene_description,
        niche_id=niche_id,
        aspect=aspect,
        index=index,
    )
