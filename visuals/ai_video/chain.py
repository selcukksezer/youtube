"""AI provider failover chain + cache + USE_AI_VIDEO gate."""
from __future__ import annotations

import os
import shutil
from typing import List, Optional

from .base import AIVideoProvider, AIVideoResult
from .cache import cache_lookup, cache_store, prompt_hash
from .http_util import env_key
from .prompt import build_cinematic_prompt
from .providers import ALL_PROVIDER_CLASSES

_PROVIDERS: Optional[List[AIVideoProvider]] = None


def _truthy(val: str) -> bool:
    return (val or "").strip().lower() in ("1", "true", "yes", "on")


def _any_key_present() -> bool:
    keys = (
        "FAL_API_KEY", "FAL_KEY",
        "HF_TOKEN", "HUGGINGFACE_TOKEN", "HUGGINGFACEHUB_API_TOKEN",
        "REPLICATE_API_TOKEN", "REPLICATE_API_KEY",
        "DEEPINFRA_TOKEN", "DEEPINFRA_API_KEY",
        "PIAPI_KEY", "PIAPI_API_KEY",
        "LOCAL_AI_VIDEO_URL",
    )
    if any(env_key(k) for k in keys):
        return True
    try:
        import config
        if getattr(config, "USE_GEMINI_VIDEO_GEN", False) and getattr(config, "GEMINI_API_KEY", ""):
            return True
    except Exception:
        pass
    return False


def ai_video_enabled() -> bool:
    raw = os.getenv("USE_AI_VIDEO", "").strip()
    if raw:
        return _truthy(raw) and _any_key_present()
    return _any_key_present()


def get_providers() -> List[AIVideoProvider]:
    global _PROVIDERS
    if _PROVIDERS is None:
        _PROVIDERS = sorted(
            (cls() for cls in ALL_PROVIDER_CLASSES),
            key=lambda p: p.priority,
        )
    return _PROVIDERS


def available_providers() -> List[AIVideoProvider]:
    return [p for p in get_providers() if p.is_available()]


def generate_ai_clip(
    *,
    narration: str = "",
    scene_description: str = "",
    niche_id: str = "",
    duration: float = 5.0,
    aspect: str = "9:16",
    seed: Optional[int] = None,
    output_path: str,
    prompt: Optional[str] = None,
) -> Optional[AIVideoResult]:
    """
    Try providers in priority order until one returns a clip.
    Cache by prompt hash. None → caller peers to stock/procedural.
    """
    if not ai_video_enabled():
        return None
    providers = available_providers()
    if not providers:
        return None

    eng_prompt = prompt or build_cinematic_prompt(
        narration=narration,
        scene_description=scene_description,
        niche_id=niche_id,
        aspect=aspect,
    )
    key = prompt_hash(eng_prompt, aspect=aspect, duration=duration, provider="any")
    cached = cache_lookup(key, output_path)
    if cached:
        print(f"    [AI-VIDEO:cache] hit {key}")
        return AIVideoResult(
            path=cached,
            provider="cache",
            model="disk",
            prompt=eng_prompt,
            seed=seed,
            duration=duration,
            aspect=aspect,
            cached=True,
            license={
                "license": "ai_generated",
                "source": "cache",
                "safe": True,
                "needs_attribution": True,
                "title": "AI video (cached)",
                "author": "ai_video_cache",
                "raw": key,
            },
        )

    for prov in providers:
        out = os.path.join(
            os.path.dirname(output_path) or ".",
            f"{os.path.splitext(os.path.basename(output_path))[0]}_{prov.name}.mp4",
        )
        try:
            print(f"    [AI-VIDEO:{prov.name}] generating…")
            result = prov.generate(
                eng_prompt,
                duration=duration,
                aspect=aspect,
                seed=seed,
                output_path=out,
            )
        except Exception as exc:
            print(f"    [AI-VIDEO:{prov.name}] fail: {exc}")
            continue
        if result and result.path and os.path.isfile(result.path):
            if result.path != output_path:
                try:
                    shutil.copy2(result.path, output_path)
                    result.path = output_path
                except OSError:
                    pass
            cache_store(
                key,
                result.path,
                meta={"provider": result.provider, "model": result.model, "prompt": eng_prompt},
            )
            print(f"    [OK] [AI-VIDEO:{result.provider}] model={result.model}")
            return result
    return None
