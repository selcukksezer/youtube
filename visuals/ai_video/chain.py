"""AI provider failover chain + cache + USE_AI_VIDEO gate + multi-clip stitch."""
from __future__ import annotations

import os
import shutil
from typing import List, Optional

from .base import AIVideoProvider, AIVideoResult
from .cache import cache_lookup, cache_store, prompt_hash
from .http_util import env_key
from .kids_safety import is_kids_niche
from .prompt import build_cinematic_prompt, resolve_style_preset
from .providers import ALL_PROVIDER_CLASSES
from .stitch import clip_count_for_duration, ffmpeg_concat

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
        "RUNWAYML_API_SECRET", "RUNWAY_API_KEY", "RUNWAY_API_SECRET",
        "LUMA_API_KEY", "LUMAAI_API_KEY", "LUMA_KEY",
        "MINIMAX_API_KEY", "HAILUO_API_KEY",
        "OPENAI_API_KEY",
        "HIGGSFIELD_API_KEY_ID", "HIGGSFIELD_API_KEY_SECRET", "HIGGSFIELD_CREDENTIALS",
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


def _clip_max_sec() -> float:
    try:
        return float(os.getenv("AI_VIDEO_CLIP_MAX_SEC", "5") or 5)
    except (TypeError, ValueError):
        return 5.0


def _generate_one(
    eng_prompt: str,
    *,
    duration: float,
    aspect: str,
    seed: Optional[int],
    output_path: str,
    providers: List[AIVideoProvider],
) -> Optional[AIVideoResult]:
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
            return result
    return None


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
    style_preset: Optional[str] = None,
) -> Optional[AIVideoResult]:
    """
    Try providers in priority order until one returns a clip.
    If duration > AI_VIDEO_CLIP_MAX_SEC, generate N clips and ffmpeg-concat (60s Shorts).
    Cache by prompt hash. None → caller peers to stock/procedural.
    """
    if not ai_video_enabled():
        return None
    providers = available_providers()
    if not providers:
        return None

    style = resolve_style_preset(niche_id, style_preset)
    try:
        eng_prompt = prompt or build_cinematic_prompt(
            narration=narration,
            scene_description=scene_description,
            niche_id=niche_id,
            aspect=aspect,
            style_preset=style,
        )
    except ValueError as exc:
        print(f"    [AI-VIDEO:kids_safety] blocked: {exc}")
        return None

    clip_max = _clip_max_sec()
    target = float(duration or clip_max)
    n_clips = clip_count_for_duration(target, clip_max) if target > clip_max + 0.4 else 1

    key = prompt_hash(
        eng_prompt,
        aspect=aspect,
        duration=target,
        provider=f"any:n{n_clips}:{style}",
    )
    cached = cache_lookup(key, output_path)
    if cached:
        print(f"    [AI-VIDEO:cache] hit {key}")
        return AIVideoResult(
            path=cached,
            provider="cache",
            model="disk",
            prompt=eng_prompt,
            seed=seed,
            duration=target,
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

    if n_clips == 1:
        result = _generate_one(
            eng_prompt,
            duration=min(target, clip_max),
            aspect=aspect,
            seed=seed,
            output_path=output_path,
            providers=providers,
        )
        if result:
            cache_store(
                key,
                result.path,
                meta={"provider": result.provider, "model": result.model, "prompt": eng_prompt},
            )
            print(f"    [OK] [AI-VIDEO:{result.provider}] model={result.model}")
        return result

    # Multi-clip stitch for ~60s kids Shorts / long scenes
    part_paths: List[str] = []
    base_dir = os.path.dirname(output_path) or "."
    stem = os.path.splitext(os.path.basename(output_path))[0]
    last_result: Optional[AIVideoResult] = None
    for i in range(n_clips):
        part_out = os.path.join(base_dir, f"{stem}_p{i:02d}.mp4")
        beat = f" scene beat {i + 1} of {n_clips}, continuous kids story"
        part_prompt = (eng_prompt + beat)[:1200]
        part_seed = (seed or 0) + i * 17 if seed is not None else None
        res = _generate_one(
            part_prompt,
            duration=clip_max,
            aspect=aspect,
            seed=part_seed,
            output_path=part_out,
            providers=providers,
        )
        if not res or not res.path:
            break
        part_paths.append(res.path)
        last_result = res

    if not part_paths:
        return None
    stitched = ffmpeg_concat(part_paths, output_path)
    if not stitched:
        # return first part as soft fallback
        if last_result:
            return last_result
        return None
    result = AIVideoResult(
        path=stitched,
        provider=(last_result.provider if last_result else "stitch"),
        model=f"stitchx{len(part_paths)}",
        prompt=eng_prompt,
        seed=seed,
        duration=target,
        aspect=aspect,
        license=(last_result.license if last_result else {}),
        raw={"parts": len(part_paths), "kids": is_kids_niche(niche_id)},
    )
    cache_store(
        key,
        result.path,
        meta={"provider": result.provider, "model": result.model, "prompt": eng_prompt, "parts": len(part_paths)},
    )
    print(f"    [OK] [AI-VIDEO:{result.provider}] stitched parts={len(part_paths)}")
    return result
