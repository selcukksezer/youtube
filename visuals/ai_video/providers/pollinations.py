"""
Pollinations Free AI Visual Provider (0 TL - No API Key Needed).
Adapts Verticals v3 broll + Ken Burns approach with Flux/SDXL image synthesis and FFmpeg zoompan.
"""
from __future__ import annotations

import os
from typing import Optional

from ..base import AIVideoProvider, AIVideoResult
from ..http_util import ai_generated_license
from services.pollinations_ai_visual import PollinationsAIVisual


class PollinationsVideoProvider(AIVideoProvider):
    name = "pollinations"
    priority = 15  # Zero-cost 0 TL fallback

    def is_available(self) -> bool:
        # 100% free, requires no API key. Can be toggled with env DISABLE_POLLINATIONS=1
        return os.getenv("DISABLE_POLLINATIONS", "").strip().lower() not in ("1", "true", "yes")

    def generate(
        self,
        prompt: str,
        *,
        duration: float = 5.0,
        aspect: str = "9:16",
        seed: Optional[int] = None,
        output_path: str,
    ) -> Optional[AIVideoResult]:
        engine = PollinationsAIVisual()
        clip_path = engine.create_ai_clip(
            prompt=prompt,
            duration=duration,
            output_path=output_path,
            seed=seed,
        )
        if not clip_path or not os.path.exists(clip_path):
            return None

        return AIVideoResult(
            path=clip_path,
            provider="pollinations",
            model="flux-sdxl-zoompan",
            prompt=prompt,
            seed=seed,
            duration=duration,
            aspect=aspect,
            license=ai_generated_license(self.name, "flux-sdxl-zoompan", commercial_ok=True),
        )
