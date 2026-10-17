"""Compliance: inauthentic-content risk, originality angle, AI disclosure text."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .originality import (
    check_script_originality,
    check_script_originality_detailed,
    register_approved_script,
    tokenize_script,
    calculate_jaccard_overlap,
    DEFAULT_ORIGINALITY_THRESHOLD,
)
from .anti_repetition import (
    get_diversified_fps,
    get_rgb_color_jitter_filter,
    get_temporal_noise_filter,
    build_anti_repetition_filter_chain,
    audit_anti_repetition_shield,
    DIVERSIFIED_FPS_OPTIONS,
)
from .transparent_disclosure import (
    format_visual_source_item,
    extract_unique_providers,
    generate_visual_sources_block,
    build_transparent_ai_disclosure_block,
    append_ai_disclosure_to_description,
    PROVIDER_DISPLAY_NAMES,
)
from .publishing_package import (
    build_publishing_package,
    build_seo_meta_package,
    validate_publishing_package_schema,
    archive_publishing_bundle,
    research_gate_passed,
    license_status_from_manifest,
)
from .viewer_score import (
    compute_viewer_score,
    audit_script_virality,
    auto_repair_script_virality,
    calculate_hook_score,
    calculate_rhythm_pacing_score,
    calculate_emotional_contrast_score,
    calculate_loop_bridge_score,
    VIRALITY_PASS_THRESHOLD,
    VIRALITY_REPAIR_THRESHOLD,
)
from .gates_core import (
    _TEMPLATE_MARKERS,
    _SPAM_SEO,
    _INVESTMENT_PUSH,
    _AI_EXPERT_PERSONA,
    _STOP_NICHES_HARD,
    _norm_tokens,
    _jaccard,
    scene_template_similarity,
    commentary_angle_score,
    inauthentic_risk_score,
    ai_disclosure_block,
    sanitize_seo_description,
    niche_gate,
    evaluate_plan_compliance,
    research_quality_gate,
    publication_decision,
)


def _jsonable(value: Any) -> Any:
    """Convert pydantic/dataclass-like values into JSON-safe structures."""
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "dict") and callable(value.dict):
        return value.dict()
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def manual_upload_checklist(*, ai_disclosure: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Checklist for a human Studio upload; no engagement automation is included."""
    disclosure = ai_disclosure or {}
    return [
        {"id": "rights", "label": "Verify every visual/audio license and attribution", "required": True},
        {"id": "sources", "label": "Confirm source_manifest and credits are complete", "required": True},
        {"id": "research", "label": "Review claims, quotes, and policy snapshot", "required": True},
        {"id": "title_description", "label": "Review title, description, and hashtags for accuracy", "required": True},
        {"id": "ai_disclosure", "label": "Set Studio altered/synthetic content answer", "required": True,
         "answer": "YES" if disclosure.get("disclosure_required") else "NO"},
        {"id": "audience", "label": "Set audience and made-for-kids setting manually", "required": True},
        {"id": "upload", "label": "Upload in YouTube Studio and inspect the preview", "required": True},
        {"id": "engagement", "label": "Do not automate views, likes, comments, hearts, or subscriptions", "required": True},
    ]


def export_output_package(
    output_dir: str,
    *,
    video_path: str,
    title: str,
    description: str = "",
    tags: Optional[Sequence[str]] = None,
    research_brief: Optional[Dict[str, Any]] = None,
    source_manifest: Any = None,
    compliance: Optional[Dict[str, Any]] = None,
    viewer_score: Optional[Dict[str, Any]] = None,
    ai_disclosure: Optional[Dict[str, Any]] = None,
    thumbnail_path: Optional[str] = None,
    language: str = "tr",
) -> Dict[str, Any]:
    """Write an auditable manual-upload package next to a rendered video."""
    video = Path(video_path)
    if not video.is_file():
        raise FileNotFoundError(f"Rendered video not found: {video_path}")
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    disclosure = ai_disclosure or (compliance or {}).get("ai_disclosure") or ai_disclosure_block(lang=language)
    manifest = _jsonable(source_manifest or {"version": 1, "clips": []})
    if not isinstance(manifest, dict):
        manifest = {"version": 1, "clips": manifest}
    manifest.setdefault("version", 1)
    manifest.setdefault("generated_at", datetime.now(timezone.utc).isoformat())
    manifest.setdefault("clips", [])

    credits = []
    for clip in manifest.get("clips") or []:
        license_data = clip.get("license") or {}
        credits.append({
            "asset_id": clip.get("asset_id") or clip.get("uid"),
            "provider": clip.get("source"),
            "title": clip.get("title", ""),
            "contributor": clip.get("contributor", "") or license_data.get("author", ""),
            "source_url": clip.get("url") or license_data.get("source_url", ""),
            "license": license_data.get("license", ""),
            "license_url": license_data.get("license_url", ""),
            "attribution_required": bool(license_data.get("needs_attribution")),
        })

    policy_snapshot = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "youtube": {
            "ypp": "https://support.google.com/youtube/answer/1311392",
            "synthetic_media": disclosure.get("policy_url", "https://support.google.com/youtube/answer/14328491"),
            "community_guidelines": "https://www.youtube.com/howyoutubeworks/policies/community-guidelines/",
        },
        "automatic_upload": False,
        "ai_disclosure": disclosure,
    }
    package = {
        "package_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "video": {
            "path": os.path.relpath(video, root),
            "filename": video.name,
            "sha256": _sha256_file(video),
        },
        "thumbnail": {"path": os.path.relpath(thumbnail_path, root) if thumbnail_path and os.path.exists(thumbnail_path) else None},
        "title": title[:100],
        "description": sanitize_seo_description(description),
        "tags": [str(tag).lstrip("#") for tag in (tags or [])][:30],
        "language": language,
        "automatic_upload": False,
        "manual_upload_required": True,
        "ai_disclosure": disclosure,
        "compliance": _jsonable(compliance or {}),
        "viewer_score": _jsonable(viewer_score or {}),
    }
    # Chapter 8.4 Canonical publishing package & SEO meta
    niche_id = (compliance or {}).get("niche_id") or "general"
    pub_pkg = build_publishing_package(
        title=title,
        niche_id=niche_id,
        viewer_score=viewer_score,
        manifest_items=manifest.get("clips") or [],
        research_gate_passed=research_gate_passed(compliance),
        license_status=license_status_from_manifest(manifest.get("clips") or []),
        originality_score=float((compliance or {}).get("originality_score")) if (compliance or {}).get("originality_score") is not None else 0.0,
        ai_disclosure=disclosure,
    )
    seo_meta = build_seo_meta_package(
        title=title,
        description=sanitize_seo_description(description),
        tags=tags or [],
        language=language,
        ai_disclosure_text=disclosure.get("description_paragraph", ""),
    )

    c2pa_manifest = build_c2pa_sidecar_manifest(
        video_path=str(video),
        title=title,
        ai_disclosure=disclosure,
        source_manifest=manifest,
    )
    review_gate = enqueue_human_review_if_gated(
        package_dir=root,
        title=title,
        viewer_score=viewer_score,
        originality_score=float((compliance or {}).get("originality_score")) if (compliance or {}).get("originality_score") is not None else 100.0,
    )
    package["human_review_gate"] = review_gate

    files = {
        "source_manifest": root / "source_manifest.json",
        "visual_credits": root / "visual_credits.json",
        "policy_snapshot": root / "policy_snapshot.json",
        "ai_disclosure": root / "ai_disclosure.json",
        "manual_upload_checklist": root / "manual_upload_checklist.json",
        "package_manifest": root / "package_manifest.json",
        "publishing_package": root / "publishing_package.json",
        "seo_meta": root / "seo_meta.json",
        "c2pa_manifest": root / "c2pa_manifest.json",
    }
    files["publishing_package"].write_text(json.dumps(pub_pkg, ensure_ascii=False, indent=2), encoding="utf-8")
    files["seo_meta"].write_text(json.dumps(seo_meta, ensure_ascii=False, indent=2), encoding="utf-8")
    files["c2pa_manifest"].write_text(json.dumps(c2pa_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    files["source_manifest"].write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    files["visual_credits"].write_text(json.dumps({"credits": credits}, ensure_ascii=False, indent=2), encoding="utf-8")
    files["policy_snapshot"].write_text(json.dumps(policy_snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    files["ai_disclosure"].write_text(json.dumps(disclosure, ensure_ascii=False, indent=2), encoding="utf-8")
    checklist = manual_upload_checklist(ai_disclosure=disclosure)
    files["manual_upload_checklist"].write_text(json.dumps({"items": checklist}, ensure_ascii=False, indent=2), encoding="utf-8")
    package["files"] = {name: str(path) for name, path in files.items()}
    files["package_manifest"].write_text(json.dumps(package, ensure_ascii=False, indent=2), encoding="utf-8")
    credit_lines = ["Visual/audio credits"] + [
        f"- {c['title'] or c['asset_id']} — {c['provider']} — {c['license']} — {c['source_url']}"
        for c in credits
    ]
    (root / "visual_credits.txt").write_text("\n".join(credit_lines) + "\n", encoding="utf-8")
    (root / "manual_upload_checklist.txt").write_text(
        "\n".join(f"[ ] {item['label']}" + (f" ({item['answer']})" if item.get("answer") else "") for item in checklist) + "\n",
        encoding="utf-8",
    )
    package["files"].update({"visual_credits_txt": str(root / "visual_credits.txt"), "manual_upload_checklist_txt": str(root / "manual_upload_checklist.txt")})
    files["package_manifest"].write_text(json.dumps(package, ensure_ascii=False, indent=2), encoding="utf-8")
    return package


def build_c2pa_sidecar_manifest(
    *,
    video_path: str,
    title: str,
    ai_disclosure: dict[str, Any] | None = None,
    source_manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    RESEARCH_YOUTUBE_SHORTS_2026.md §E4 P2:
    Generate C2PA 2.1 Content Credentials sidecar manifest JSON (`c2pa_manifest.json`).
    """
    vp = Path(video_path)
    disclosure = ai_disclosure or {}
    return {
        "c2pa_version": "2.1",
        "claim_generator": "YouTubeShortsUltimate/2026.10",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "title": (title or vp.stem)[:100],
        "asset": {
            "filename": vp.name,
            "sha256": _sha256_file(vp),
            "format": "video/mp4",
        },
        "assertions": [
            {
                "label": "c2pa.actions",
                "data": {
                    "actions": [
                        {
                            "action": "c2pa.created",
                            "digitalSourceType": (
                                "http://cv.iptc.org/newscodes/digitalsourcetype/compositeWithTrainedAlgorithmicMedia"
                                if disclosure.get("requires_altered_content_disclosure")
                                else "http://cv.iptc.org/newscodes/digitalsourcetype/digitalCreation"
                            ),
                        }
                    ]
                },
            },
            {
                "label": "stds.schema-org.CreativeWork",
                "data": {
                    "headline": (title or vp.stem)[:100],
                    "ai_disclosure_required": bool(disclosure.get("requires_altered_content_disclosure")),
                    "clip_count": len((source_manifest or {}).get("clips") or []),
                },
            },
        ],
    }


def enqueue_human_review_if_gated(
    *,
    package_dir: Path | str,
    title: str,
    viewer_score: Any = None,
    originality_score: float = 100.0,
    min_viewer_score: float = 70.0,
    min_originality_score: float = 60.0,
) -> dict[str, Any]:
    """
    RESEARCH_YOUTUBE_SHORTS_2026.md §E3 P1:
    Route package to `manual_review_queue.json` when viewer_score < 70 or originality_score < 60.
    """
    vs_dict = _jsonable(viewer_score or {})
    raw_vs = (
        vs_dict.get("overall_score")
        if isinstance(vs_dict, dict) and vs_dict.get("overall_score") is not None
        else (vs_dict.get("total_score") if isinstance(vs_dict, dict) else None)
    )
    vs_val = float(raw_vs) if raw_vs is not None else 100.0
    orig_val = float(originality_score if originality_score is not None else 100.0)

    reasons: list[str] = []
    if vs_val < min_viewer_score:
        reasons.append(f"viewer_score ({vs_val:.1f}) < {min_viewer_score:.1f}")
    if orig_val < min_originality_score:
        reasons.append(f"originality_score ({orig_val:.1f}) < {min_originality_score:.1f}")

    requires_review = bool(reasons)
    result = {
        "requires_human_review": requires_review,
        "status": "quarantined_for_human_review" if requires_review else "approved_for_manual_upload",
        "viewer_score": vs_val,
        "originality_score": orig_val,
        "reasons": reasons,
    }
    if requires_review:
        root = Path(package_dir)
        queue_file = root / "manual_review_queue.json"
        queue_file.write_text(
            json.dumps(
                {
                    "queued_at": datetime.now(timezone.utc).isoformat(),
                    "title": (title or "")[:100],
                    "package_dir": str(root),
                    **result,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    return result


def check_upload_cadence_and_diversity(
    recent_uploads: list[dict[str, Any]],
    *,
    candidate_title: str = "",
    now_ts: float | None = None,
    max_per_24h: int = 1,
    min_interval_hours: float = 8.0,
) -> dict[str, Any]:
    """
    RESEARCH_YOUTUBE_SHORTS_2026.md §E3 P1:
    Enforce upload cadence limit (max_per_24h=1, min_interval_hours=8.0) and topic diversity.
    """
    import time as _time

    now = float(now_ts if now_ts is not None else _time.time())
    uploads_24h = 0
    min_elapsed_hours: float | None = None
    duplicate_topic = False
    cand_tokens = {w.lower() for w in (candidate_title or "").split() if len(w) > 3}

    for item in recent_uploads or []:
        ts = float(item.get("uploaded_at_ts") or item.get("created_at_ts") or 0.0)
        if ts > 0:
            elapsed_h = max(0.0, (now - ts) / 3600.0)
            if elapsed_h <= 24.0:
                uploads_24h += 1
            if min_elapsed_hours is None or elapsed_h < min_elapsed_hours:
                min_elapsed_hours = elapsed_h
        prev_title = str(item.get("title") or "")
        prev_tokens = {w.lower() for w in prev_title.split() if len(w) > 3}
        if cand_tokens and prev_tokens:
            overlap = len(cand_tokens & prev_tokens) / max(1, len(cand_tokens | prev_tokens))
            if overlap >= 0.65:
                duplicate_topic = True

    violations: list[str] = []
    if uploads_24h >= max_per_24h:
        violations.append(f"24h upload limit reached ({uploads_24h}/{max_per_24h})")
    if min_elapsed_hours is not None and min_elapsed_hours < min_interval_hours:
        violations.append(f"Minimum interval not met ({min_elapsed_hours:.1f}h < {min_interval_hours:.1f}h)")
    if duplicate_topic:
        violations.append("Candidate title overlaps >=65% with a recent upload")

    return {
        "allowed": len(violations) == 0,
        "uploads_last_24h": uploads_24h,
        "min_elapsed_hours": round(min_elapsed_hours, 2) if min_elapsed_hours is not None else None,
        "duplicate_topic": duplicate_topic,
        "violations": violations,
    }


def get_or_create_channel_style_fingerprint(channel_id: str) -> dict[str, Any]:
    """
    RESEARCH_YOUTUBE_SHORTS_2026.md §E3 P1:
    Deterministic per-channel visual/audio style fingerprint so multi-channel setups
    never share identical subtitle safe-zone, LUT tint, and BGM ducking parameters.
    """
    digest = hashlib.sha256((channel_id or "default_channel").encode("utf-8")).digest()
    fonts = ["Montserrat-ExtraBold", "Poppins-Bold", "Inter-Black", "Rubik-ExtraBold"]
    luts = ["warm_amber", "teal_orange", "crisp_neutral", "cinema_cobalt"]
    return {
        "channel_id": channel_id or "default_channel",
        "subtitle_font_family": fonts[digest[0] % len(fonts)],
        "lut_preset": luts[digest[1] % len(luts)],
        "safe_zone_bottom_px": 270 + (digest[2] % 36),
        "bgm_duck_db": round(-15.5 + (digest[3] % 7) * 0.5, 1),
    }

