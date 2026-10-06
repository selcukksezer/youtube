"""Final file-only delivery package writer."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .quality import build_policy_snapshot


def _write(path: str, payload: Any) -> str:
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    return path


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_delivery_package(
    project_dir: str,
    *,
    plan: Optional[Dict[str, Any]] = None,
    output_path: Optional[str] = None,
    quality_report: Optional[Dict[str, Any]] = None,
    source_manifest: Optional[Dict[str, Any]] = None,
    seo: Optional[Dict[str, Any]] = None,
) -> Dict[str, str]:
    """Write policy, disclosure, checksum and manual-review artifacts."""
    os.makedirs(project_dir, exist_ok=True)
    plan = plan or {}
    compliance = ((plan.get("meta") or {}).get("compliance") or {})
    disclosure = compliance.get("ai_disclosure") or {}
    required = bool(disclosure.get("required") or disclosure.get("ai_disclosure_required") or plan.get("uses_photoreal_ai"))
    paths: Dict[str, str] = {}

    paths["policy_snapshot"] = _write(
        os.path.join(project_dir, "policy_snapshot.json"),
        build_policy_snapshot(ai_disclosure_required=required),
    )
    paths["ai_disclosure"] = _write(
        os.path.join(project_dir, "ai_disclosure.json"),
        {
            "required": required,
            "studio_answer": "YES" if required else "NO",
            "reason": disclosure.get("reason") or ("photorealistic_or_meaningfully_altered_ai" if required else "stock_or_original_edit_without_realistic_synthetic_media"),
            "description_paragraph": disclosure.get("description_paragraph", ""),
        },
    )
    paths["quality_report"] = _write(
        os.path.join(project_dir, "script_quality.json"),
        quality_report or {},
    )
    paths["manual_checklist"] = _write(
        os.path.join(project_dir, "youtube_manual_checklist.json"),
        {
            "auto_upload": False,
            "review_required": bool(required or (quality_report or {}).get("hard_fail")),
            "steps": [
                "Review factual claims and evidence links.",
                "Review every source license and attribution line.",
                "Answer YouTube altered-content question from ai_disclosure.json.",
                "Check title, thumbnail, description and advertiser-safety context.",
                "Upload manually only after human approval.",
            ],
        },
    )
    if source_manifest is not None:
        paths["source_manifest"] = _write(os.path.join(project_dir, "source_manifest.json"), source_manifest)
        # Ensure visual_credits.json exists next to source_manifest
        vc_path = os.path.join(project_dir, "visual_credits.json")
        if not os.path.isfile(vc_path):
            clips = source_manifest.get("clips") if isinstance(source_manifest, dict) else []
            paths["visual_credits"] = _write(vc_path, {"credits": clips or []})

    # Chapter 8.4 Canonical publishing package and SEO meta
    from compliance.publishing_package import (
        archive_publishing_bundle,
        build_publishing_package,
        build_seo_meta_package,
        license_status_from_manifest,
        research_gate_passed,
    )
    seo = seo or {}
    title = str(seo.get("seo_title") or plan.get("title") or "Short Video").strip()
    niche_id = str(plan.get("niche_id") or (plan.get("meta") or {}).get("niche_id") or "general").strip()
    viewer_score = (plan.get("meta") or {}).get("viewer_score")
    if viewer_score is None:
        viewer_score = 0.0
    manifest_clips = (source_manifest.get("clips") if isinstance(source_manifest, dict) else []) or []
    originality = (plan.get("meta") or {}).get("originality") or {}
    if isinstance(originality, dict) and originality.get("originality_score") is not None:
        originality_score = float(originality["originality_score"])
    elif compliance.get("originality_score") is not None:
        originality_score = float(compliance.get("originality_score") or 0.0)
    else:
        originality_score = 0.0
    description = str(
        seo.get("seo_description")
        or seo.get("description")
        or plan.get("description")
        or disclosure.get("description_paragraph")
        or ""
    )

    pub_pkg = build_publishing_package(
        title=title,
        niche_id=niche_id,
        viewer_score=viewer_score,
        manifest_items=manifest_clips,
        research_gate_passed=research_gate_passed(compliance),
        license_status=license_status_from_manifest(manifest_clips),
        originality_score=originality_score,
        ai_disclosure=disclosure,
    )
    paths["publishing_package"] = _write(os.path.join(project_dir, "publishing_package.json"), pub_pkg)

    seo_meta = build_seo_meta_package(
        title=title,
        description=description,
        tags=seo.get("tags") or plan.get("tags") or [],
        language=str(seo.get("language") or plan.get("language") or "tr"),
        ai_disclosure_text=str(
            (seo.get("ai_disclosure") or {}).get("description_paragraph")
            or disclosure.get("description_paragraph")
            or ""
        ),
    )
    paths["seo_meta"] = _write(os.path.join(project_dir, "seo_meta.json"), seo_meta)

    video_dir = os.path.dirname(os.path.abspath(output_path)) if output_path else ""
    if video_dir and os.path.abspath(video_dir) != os.path.abspath(project_dir):
        credits_payload = None
        credits_path = os.path.join(project_dir, "visual_credits.json")
        if os.path.isfile(credits_path):
            with open(credits_path, "r", encoding="utf-8") as handle:
                credits_payload = json.load(handle)
        elif manifest_clips:
            credits_payload = {"clips": manifest_clips}
        beside = archive_publishing_bundle(
            video_dir,
            publishing_package=pub_pkg,
            seo_meta=seo_meta,
            visual_credits=credits_payload,
        )
        paths.update({f"beside_{key}": value for key, value in beside.items()})

    if output_path and os.path.isfile(output_path):
        paths["checksum"] = _write(
            os.path.join(project_dir, "sha256.json"),
            {
                "file": os.path.basename(output_path),
                "sha256": sha256_file(output_path),
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
        )
    return paths

