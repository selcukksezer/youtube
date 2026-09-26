"""
Character Identity Anchor Engine.
Adapted and enhanced from lcy362/agnes-video-generator (core/screenwriter/characters.py).
Maintains character visual continuity (face, clothing, body, colors) across multi-scene shorts,
generating standardized identity anchor prompts for consistent image and video generation.
"""
from dataclasses import dataclass, field
import logging
import re
from typing import Any, Dict, List, Optional
import config

logger = logging.getLogger(__name__)


@dataclass
class CharacterAnchor:
    name: str
    gender: str
    age_group: str
    hair: str
    facial_features: str
    outfit: str
    color_palette: str
    distinctive_marks: str = "none"
    art_style: str = "cinematic photorealistic"

    def to_police_sketch(self) -> str:
        """Compact objective physical description for prompt conditioning."""
        return (
            f"{self.age_group} {self.gender}, {self.hair}, {self.facial_features}, "
            f"wearing {self.outfit}, color scheme: {self.color_palette}"
        )


class CharacterIdentityAnchor:
    """
    Extracts, maintains, and injects visual identity anchors across scene prompts.
    """

    def __init__(self):
        pass

    def extract_or_create_anchor(
        self,
        topic: str,
        character_name: Optional[str] = None,
        art_style: str = "cinematic photorealistic",
    ) -> CharacterAnchor:
        """
        Derives a consistent physical anchor from topic/persona, or constructs a grounded default.
        """
        c_name = character_name or "Ana Karakter"
        topic_lower = topic.lower()

        # Heuristic archetype detection if offline
        if any(w in topic_lower for w in ["marcus", "aurelius", "stoa", "roma", "imparator"]):
            return CharacterAnchor(
                name="Marcus Aurelius",
                gender="male",
                age_group="50s mature philosopher emperor",
                hair="short curly grey-streaked beard and hair",
                facial_features="stoic determined gaze, weathered thoughtful brow",
                outfit="imperial Roman crimson woolen cloak with bronze fibula over off-white tunic",
                color_palette="crimson red, antique marble white, bronze",
                distinctive_marks="regal philosophical posture",
                art_style="cinematic ancient Roman drama",
            )
        elif any(w in topic_lower for w in ["hacker", "kod", "siber", "yazılımcı", "bilgisayar"]):
            return CharacterAnchor(
                name="Siber Uzman",
                gender="unisex",
                age_group="late 20s",
                hair="dark messy tied back hair",
                facial_features="focused intense eyes reflected by monitor glow, thin frame glasses",
                outfit="dark charcoal minimalist hoodie with rolled up sleeves",
                color_palette="charcoal grey, neon cyan accents, matte black",
                distinctive_marks="smartwatch on left wrist",
                art_style="cyberpunk realism",
            )
        elif any(w in topic_lower for w in ["doktor", "tıp", "cerrah", "hastane"]):
            return CharacterAnchor(
                name="Cerrahi Doktor",
                gender="female",
                age_group="mid 30s",
                hair="neat dark hair in low bun",
                facial_features="calm empathetic expression, sharp alert eyes",
                outfit="teal medical scrubs with silver stethoscope around neck",
                color_palette="hospital teal, crisp white, metallic silver",
                distinctive_marks="medical ID badge on lapel",
                art_style="realistic clinical documentary",
            )
        else:
            return CharacterAnchor(
                name=c_name,
                gender="neutral adult",
                age_group="30s",
                hair="neatly styled brown hair",
                facial_features="expressive confident eyes, clear facial features",
                outfit="modern dark tailored jacket over clean crewneck t-shirt",
                color_palette="navy blue, slate grey, white",
                distinctive_marks="clean silhouette",
                art_style=art_style,
            )

    def build_reference_image_prompt(self, anchor: CharacterAnchor) -> str:
        """
        Builds the master identity anchor prompt for generating the reference keyframe.
        Requires front-facing, neutral expression, diffused lighting, zero occlusion.
        """
        return (
            f"Character reference sheet of {anchor.name}: {anchor.to_police_sketch()}. "
            f"Clear three-quarter view, neutral standing pose, front-facing face with eyes and mouth "
            f"completely visible. No occlusion, hands or objects not blocking face. "
            f"Soft even diffused volumetric lighting, 8k resolution, {anchor.art_style} aesthetic."
        )

    def inject_anchor_into_scene_prompt(
        self,
        scene_visual_prompt: str,
        anchor: CharacterAnchor,
    ) -> str:
        """
        Conditions a scene prompt with the character's locked physical identity anchor.
        """
        sketch = anchor.to_police_sketch()
        # Avoid duplicating if already present
        if anchor.name.lower() in scene_visual_prompt.lower():
            return f"{scene_visual_prompt}, maintaining consistent character identity: ({sketch})"

        return f"{scene_visual_prompt}, featuring {anchor.name} ({sketch})"


character_identity_anchor = CharacterIdentityAnchor()
