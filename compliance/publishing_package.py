"""
Bölüm 8.4: Yayın Paketi (Publishing Package) JSON Standardı
(Publishing Package, Visual Credits & SEO Meta Standards)

Her render çıktısında videonun yanında arşivlenecek dosyalar:
1. publishing_package.json (Bölüm 8.4 kanonik şeması)
2. visual_credits.json (Görsel lisans ve kaynak künyesi)
3. seo_meta.json (Başlık, açıklama, etiketler, dil ve SEO meta verileri)
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union


def _extract_viewer_score(score_input: Any) -> float:
    if isinstance(score_input, (int, float)):
        return round(float(score_input), 1)
    if isinstance(score_input, dict):
        val = score_input.get("score") or score_input.get("total_score") or score_input.get("viewer_score") or 0.0
        try:
            return round(float(val), 1)
        except (ValueError, TypeError):
            return 0.0
    return 0.0


_UNSAFE_LICENSES = {"cc_nc", "cc_nd", "cc_by_sa", "mixkit", "unknown"}


def research_gate_passed(compliance: Optional[Dict[str, Any]]) -> bool:
    """PASSED only when the research gate action is ALLOW."""
    research = (compliance or {}).get("research") if isinstance(compliance, dict) else None
    if not isinstance(research, dict) or not research:
        return False
    if research.get("hard_fail") is True:
        return False
    return str(research.get("action") or "").upper() == "ALLOW"


def license_status_from_manifest(manifest_items: Optional[Sequence[Dict[str, Any]]]) -> str:
    """COMMERCIAL_SAFE only when every listed clip license is safe. Empty ledger is UNVERIFIED."""
    rows = [row for row in (manifest_items or []) if isinstance(row, dict)]
    if not rows:
        return "UNVERIFIED"
    for item in rows:
        lic = item.get("license") or {}
        if isinstance(lic, dict):
            if lic.get("safe") is False:
                return "NOT_COMMERCIAL_SAFE"
            name = str(lic.get("license") or lic.get("name") or lic.get("type") or "").lower()
        else:
            name = str(lic or "").lower()
        if name in _UNSAFE_LICENSES or "non-commercial" in name or "noncommercial" in name:
            return "NOT_COMMERCIAL_SAFE"
    return "COMMERCIAL_SAFE"


def build_publishing_package(
    *,
    title: str,
    niche_id: str,
    viewer_score: Optional[Union[float, Dict[str, Any]]] = None,
    manifest_items: Optional[Sequence[Dict[str, Any]]] = None,
    research_gate_passed: bool = True,
    license_status: str = "COMMERCIAL_SAFE",
    originality_score: float = 100.0,
    ai_disclosure: Optional[Dict[str, Any]] = None,
    extra_compliance: Optional[Dict[str, Any]] = None,
    generated_at: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Bölüm 8.4 kanonik yayın paketi şemasını derler:
    {
      "version": 1,
      "generated_at": "2026-09-26T22:00:00Z",
      "title": "Hayatınızı Kolaylaştıracak 3 Ürün",
      "niche_id": "12_amazon_affiliate",
      "viewer_score": 98.0,
      "compliance": {
        "research_gate": "PASSED",
        "license_status": "COMMERCIAL_SAFE",
        "originality_score": 100.0
      },
      "credits": {
        "manifest_count": 10,
        "unique_uids": true
      }
    }
    """
    now_iso = generated_at or datetime.now(timezone.utc).isoformat()
    manifest_list = list(manifest_items or [])
    manifest_count = len(manifest_list)

    # Check unique uids
    uids = []
    for item in manifest_list:
        uid = item.get("asset_id") or item.get("id") or item.get("uid") or item.get("source_url")
        if uid:
            uids.append(str(uid))
    unique_uids = len(uids) == len(set(uids)) if uids else True

    comp_dict: Dict[str, Any] = {
        "research_gate": "PASSED" if research_gate_passed else "FAILED",
        "license_status": str(license_status or "COMMERCIAL_SAFE"),
        "originality_score": round(float(originality_score), 1),
    }
    if extra_compliance and isinstance(extra_compliance, dict):
        for k, v in extra_compliance.items():
            if k not in comp_dict:
                comp_dict[k] = v

    pkg: Dict[str, Any] = {
        "version": 1,
        "generated_at": now_iso,
        "title": str(title or "").strip()[:100],
        "niche_id": str(niche_id or "general").strip(),
        "viewer_score": _extract_viewer_score(viewer_score),
        "compliance": comp_dict,
        "credits": {
            "manifest_count": manifest_count,
            "unique_uids": unique_uids,
        },
    }

    if ai_disclosure and isinstance(ai_disclosure, dict):
        pkg["ai_disclosure"] = ai_disclosure

    return pkg


def build_seo_meta_package(
    *,
    title: str,
    description: str,
    tags: Optional[Sequence[str]] = None,
    language: str = "tr",
    category_id: str = "22",
    privacy_status: str = "unlisted",
    ai_disclosure_text: str = "",
) -> Dict[str, Any]:
    """
    Render edilen videonun yanında arşivlenecek seo_meta.json yapısı.
    """
    clean_tags = [str(t).lstrip("#").strip() for t in (tags or []) if str(t).strip()][:30]
    return {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "title": str(title or "").strip()[:100],
        "description": str(description or "").strip(),
        "tags": clean_tags,
        "language": str(language or "tr").lower(),
        "category_id": str(category_id or "22"),
        "privacy_status": str(privacy_status or "unlisted"),
        "ai_disclosure_text": str(ai_disclosure_text or "").strip(),
    }


def validate_publishing_package_schema(payload: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Bölüm 8.4 standartlarına göre yayın paketi şemasını denetler.
    """
    errors: List[str] = []
    if not isinstance(payload, dict):
        return False, ["Payload must be a dictionary"]

    # 1. version
    if payload.get("version") != 1:
        errors.append(f"Expected version=1, got {payload.get('version')}")

    # 2. generated_at
    if not payload.get("generated_at"):
        errors.append("Missing 'generated_at' timestamp")

    # 3. title
    if not payload.get("title") or not str(payload["title"]).strip():
        errors.append("Missing or empty 'title'")

    # 4. niche_id
    if not payload.get("niche_id"):
        errors.append("Missing 'niche_id'")

    # 5. viewer_score
    vs = payload.get("viewer_score")
    if not isinstance(vs, (int, float)):
        errors.append(f"Expected numeric viewer_score, got {type(vs)}")

    # 6. compliance block
    comp = payload.get("compliance")
    if not isinstance(comp, dict):
        errors.append("Missing or invalid 'compliance' dictionary")
    else:
        if comp.get("research_gate") not in ("PASSED", "FAILED"):
            errors.append(f"Invalid compliance.research_gate: {comp.get('research_gate')}")
        if not comp.get("license_status"):
            errors.append("Missing compliance.license_status")
        if not isinstance(comp.get("originality_score"), (int, float)):
            errors.append("Missing or non-numeric compliance.originality_score")

    # 7. credits block
    credits = payload.get("credits")
    if not isinstance(credits, dict):
        errors.append("Missing or invalid 'credits' dictionary")
    else:
        if not isinstance(credits.get("manifest_count"), int):
            errors.append("Missing or non-integer credits.manifest_count")
        if not isinstance(credits.get("unique_uids"), bool):
            errors.append("Missing or non-boolean credits.unique_uids")

    return len(errors) == 0, errors


def archive_publishing_bundle(
    output_dir: Union[str, Path],
    *,
    publishing_package: Dict[str, Any],
    seo_meta: Optional[Dict[str, Any]] = None,
    visual_credits: Optional[Dict[str, Any]] = None,
    visual_credits_text: Optional[str] = None,
) -> Dict[str, str]:
    """
    Her render çıktısında videonun yanında:
    - publishing_package.json
    - visual_credits.json (& .txt)
    - seo_meta.json
    dosyalarını UTF-8 olarak arşivler ve yollarını döner.
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    saved_files: Dict[str, str] = {}

    # 1. publishing_package.json
    pub_file = out_path / "publishing_package.json"
    pub_file.write_text(json.dumps(publishing_package, ensure_ascii=False, indent=2), encoding="utf-8")
    saved_files["publishing_package"] = str(pub_file)

    # 2. seo_meta.json
    if seo_meta is not None:
        seo_file = out_path / "seo_meta.json"
        seo_file.write_text(json.dumps(seo_meta, ensure_ascii=False, indent=2), encoding="utf-8")
        saved_files["seo_meta"] = str(seo_file)

    # 3. visual_credits.json & .txt
    if visual_credits is not None:
        vc_file = out_path / "visual_credits.json"
        vc_file.write_text(json.dumps(visual_credits, ensure_ascii=False, indent=2), encoding="utf-8")
        saved_files["visual_credits"] = str(vc_file)

    if visual_credits_text:
        vc_txt = out_path / "visual_credits.txt"
        vc_txt.write_text(visual_credits_text, encoding="utf-8")
        saved_files["visual_credits_text"] = str(vc_txt)

    return saved_files
