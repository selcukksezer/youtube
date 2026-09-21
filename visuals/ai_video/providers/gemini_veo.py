"""Optional Gemini Veo adapter (paid — wraps google_ai_hub)."""
from __future__ import annotations

from typing import Optional

from ..base import AIVideoProvider, AIVideoResult
from ..http_util import ai_generated_license, env_key, log_skip_once


class GeminiVeoProvider(AIVideoProvider):
    name = "gemini_veo"
    priority = 50  # after free tiers

    def is_available(self) -> bool:
        try:
            import config
            if not getattr(config, "USE_GEMINI_VIDEO_GEN", False):
                return False
            return bool(getattr(config, "GEMINI_API_KEY", "") or env_key("GEMINI_API_KEY"))
        except Exception:
            return bool(env_key("GEMINI_API_KEY")) and (
                (env_key("USE_GEMINI_VIDEO_GEN") or "").lower() in ("1", "true", "yes")
            )

    def generate(
        self,
        prompt: str,
        *,
        duration: float = 5.0,
        aspect: str = "9:16",
        seed: Optional[int] = None,
        output_path: str,
    ) -> Optional[AIVideoResult]:
        if not self.is_available():
            log_skip_once(self.name, "USE_GEMINI_VIDEO_GEN off or key missing")
            return None
        try:
            from google_ai_hub import generate_veo_video
            import config
            path = generate_veo_video(
                prompt,
                output_path,
                model=getattr(config, "GEMINI_VIDEO_MODEL", None),
                duration_seconds=int(max(4, min(8, duration))),
            )
            if not path:
                return None
            return AIVideoResult(
                path=path,
                provider=self.name,
                model=getattr(config, "GEMINI_VIDEO_MODEL", "veo"),
                prompt=prompt,
                seed=seed,
                duration=duration,
                aspect=aspect,
                license=ai_generated_license(self.name, "veo", commercial_ok=True),
            )
        except Exception as exc:
            print(f"    [AI-VIDEO:gemini_veo] {exc}")
            return None
