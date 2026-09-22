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

