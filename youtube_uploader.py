"""YouTube metadata helpers; automatic upload and engagement automation disabled."""
from __future__ import annotations
import os
from typing import Any, Dict, List, Optional

SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.force-ssl"]
TOKENS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tokens")

def get_channel_token_path(channel_id: str = "default") -> str:
    return os.path.join(TOKENS_DIR, f"token_{channel_id}.json")

def evaluate_synthetic_content_policy(
    has_realistic_human_clone: bool = False,
    is_news_manipulation: bool = False,
    uses_photoreal_ai: bool = False,
    uses_altered_real_event: bool = False,
    uses_synthetic_persona: bool = False,
) -> Dict[str, Any]:
    from compliance import ai_disclosure_block
    disclosure = ai_disclosure_block(
        uses_photoreal_ai=uses_photoreal_ai,
        uses_altered_real_event=is_news_manipulation or uses_altered_real_event,
        uses_real_person_synthetic=has_realistic_human_clone,
        uses_synthetic_persona=uses_synthetic_persona,
    )
    return {
        "apply_synthetic_label": disclosure["disclosure_required"],
        "self_declared_altered": disclosure["studio_ai_survey"] == "yes",
        "studio_ai_survey": disclosure["studio_ai_survey"],
        "reasons": disclosure["reasons"],
        "reason": ("Studio altered/synthetic content answer YES olmalı: " + ", ".join(disclosure["reasons"])
                   if disclosure["reasons"] else "Gerçekçi sentetik veya değiştirilmiş gerçek olay yok; etiket kapalı (NO) tutulmalı."),
    }

def upload_video_to_youtube(
    video_path: str, title: str, description: str, tags: List[str], category_id: str = "22",
    privacy_status: str = "private", channel_id: str = "default", client_secret_path: str = "client_secret.json",
    pinned_comment: Optional[str] = None, scheduled_publish_at: Optional[str] = None,
    has_realistic_human_clone: bool = False, is_news_manipulation: bool = False, niche_id: str = "",
    made_for_kids: Optional[bool] = None, publishing_package: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Return a manual-upload instruction without contacting YouTube."""
    if not os.path.isfile(video_path):
        return {"success": False, "uploaded": False, "action": "DROP", "error": f"Video dosyası bulunamadı: {video_path}"}
    decision = (publishing_package or {}).get("publication_decision") or {}
    if decision.get("action") == "DROP":
        return {"success": False, "uploaded": False, "action": "DROP", "error": decision.get("reason", "policy gate")}
    synth = evaluate_synthetic_content_policy(
        has_realistic_human_clone=has_realistic_human_clone,
        is_news_manipulation=is_news_manipulation,
        uses_photoreal_ai=bool((publishing_package or {}).get("uses_photoreal_ai")),
    )
    from compliance import manual_upload_checklist
    return {
        "success": False, "uploaded": False, "action": "MANUAL_UPLOAD_REQUIRED",
        "reason": "Automatic YouTube upload is disabled; review and upload the package in YouTube Studio.",
        "video_path": os.path.abspath(video_path), "title": title[:100], "description": description,
        "tags": [str(tag).lstrip("#") for tag in (tags or [])][:30], "privacy_status": privacy_status,
        "channel_id": channel_id, "ai_disclosure": synth,
        "manual_upload_checklist": manual_upload_checklist(ai_disclosure={"disclosure_required": synth["apply_synthetic_label"]}),
        "automatic_upload_disabled": True,
    }
