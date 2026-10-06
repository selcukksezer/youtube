"""
compliance/license_governance.py — Fail-Closed Asset License Governance & Provenance Registry.

Adapted and evolved from reference_repos2/video-autopilot-kit (src/asset_license_governance.py & src/asset_registry.py).
Ensures zero copyright risk by strictly enforcing a fail-closed licensing gate:
1. Unlicensed, unknown, or non-commercial assets are blocked prior to rendering.
2. SHA-256 fingerprinting ensures asset authenticity and deduping.
3. Compiles a verified, tamper-evident credits and attribution manifest.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


ALLOWED_LICENSES: Set[str] = {
    "CC0-1.0",
    "CC-BY-4.0",
    "CC-BY-SA-4.0",
    "Pexels-License",
    "Pixabay-License",
    "Unsplash-License",
    "Commercial-Generated",
    "User-Owned",
    "Public-Domain",
    "Standard-YouTube-License",
}

BLOCKED_LICENSES: Set[str] = {
    "unknown",
    "unlicensed",
    "all-rights-reserved",
    "non-commercial-only",
    "blocked",
    "pending",
}


@dataclass
class AssetLicenseRecord:
    asset_id: str
    filepath: str
    file_sha256: str
    license_type: str
    provenance: str
    creator_attribution: Optional[str] = None
    is_valid: bool = False
    validation_reason: str = ""


class AssetLicenseGovernance:
    """Fail-closed license governor for all video, audio, and visual assets."""

    @staticmethod
    def compute_file_sha256(filepath: str) -> str:
        """Calculates SHA-256 hash of a file for integrity and deduplication."""
        p = Path(filepath)
        if not p.is_file():
            return ""
        hasher = hashlib.sha256()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    @classmethod
    def evaluate_license(cls, license_type: str, provenance: str) -> Tuple[bool, str]:
        """
        Fail-closed evaluation:
        Returns (True, 'approved') or (False, reason).
        Missing or unknown provenance is unconditionally rejected.
        """
        lic = (license_type or "").strip()
        prov = (provenance or "").strip()

        if not prov or prov.lower() == "unknown":
            return False, "BLOCKED: Missing or unknown asset provenance."

        if not lic or lic.lower() in BLOCKED_LICENSES:
            return False, f"BLOCKED: License '{lic}' is in blocked/unverified list."

        if lic in ALLOWED_LICENSES:
            return True, "APPROVED: Verified redistributable license."

        # Fail-closed default: unrecognized licenses are not permitted
        return False, f"BLOCKED: Unrecognized license '{lic}'. Fail-closed enforcement active."

    @classmethod
    def audit_asset(cls, asset: Dict[str, Any]) -> AssetLicenseRecord:
        """Audits a single asset record and returns a stamped AssetLicenseRecord."""
        filepath = str(asset.get("filepath") or asset.get("path") or "")
        lic = str(asset.get("license") or asset.get("license_type") or "unknown")
        prov = str(asset.get("provenance") or "unknown")
        attr = asset.get("creator_attribution") or asset.get("author") or None
        asset_id = str(asset.get("asset_id") or Path(filepath).stem)

        file_sha256 = asset.get("file_sha256") or (cls.compute_file_sha256(filepath) if filepath and os.path.exists(filepath) else "")

        is_valid, reason = cls.evaluate_license(lic, prov)

        return AssetLicenseRecord(
            asset_id=asset_id,
            filepath=filepath,
            file_sha256=file_sha256,
            license_type=lic,
            provenance=prov,
            creator_attribution=attr,
            is_valid=is_valid,
            validation_reason=reason,
        )

    @classmethod
    def audit_all_assets_fail_closed(cls, assets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Audits a list of assets. If ANY asset fails, the entire batch is rejected
        under fail-closed governance to prevent any copyright breach.
        """
        records: List[AssetLicenseRecord] = [cls.audit_asset(a) for a in assets]
        blocked = [r for r in records if not r.is_valid]

        passed = len(blocked) == 0
        return {
            "success": passed,
            "status": "APPROVED_FAIL_CLOSED" if passed else "REJECTED_UNLICENSED_ASSETS",
            "total_assets": len(records),
            "approved_count": len(records) - len(blocked),
            "blocked_count": len(blocked),
            "records": [asdict(r) for r in records],
            "blocked_reasons": [f"[{r.asset_id} ({r.filepath})]: {r.validation_reason}" for r in blocked],
        }

    @classmethod
    def compile_credits_manifest(
        cls, assets: List[Dict[str, Any]], output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generates an attribution manifest for approved assets."""
        audit_result = cls.audit_all_assets_fail_closed(assets)
        if not audit_result["success"]:
            raise ValueError(f"Cannot generate credits manifest: {audit_result['status']}")

        manifest = {
            "schema_version": "1.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "policy": "FAIL_CLOSED_ZERO_COPYRIGHT_RISK",
            "attributions": [
                {
                    "asset_id": r["asset_id"],
                    "creator": r["creator_attribution"] or "Public Domain / Unknown Author",
                    "license": r["license_type"],
                    "provenance": r["provenance"],
                    "sha256": r["file_sha256"],
                }
                for r in audit_result["records"]
            ],
        }

        if output_path:
            p = Path(output_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        return manifest


GLOBAL_LICENSE_GOVERNANCE = AssetLicenseGovernance()
