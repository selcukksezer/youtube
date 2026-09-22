"""Compliance: inauthentic-content risk, originality angle, AI disclosure text."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

# Signals that YouTube's July 2025 "inauthentic content" policy targets
_TEMPLATE_MARKERS = re.compile(
    r"(scene_description|placeholder|lorem ipsum|todo:|\[insert\]|"
    r"generic template|stock slideshow)",
    re.I,
)
_SPAM_SEO = re.compile(
    r"(#\w+\s*){8,}|"  # hashtag walls
    r"(\b\w+\b[,\s]+){20,}tags?|"
    r"keyword\s*:\s*|seo\s*tags?\s*:",
    re.I,
)
_INVESTMENT_PUSH = re.compile(
    r"\b(şunu al|hemen al|garanti kazanç|100x|get rich|guaranteed returns|"
    r"yatırım tavsiyesi|buy this coin|financial advice)\b",
    re.I,
)
_AI_EXPERT_PERSONA = re.compile(
    r"(ben bir (doktor|avukat|yatırım\s*danışmanı)|"
    r"as an? (doctor|lawyer|financial advisor)|"
    r"tıbbi teşhis|legal advice|diagnose yourself|"
    r"yatırım danışmanı(yım|yim)?)",
    re.I,
)
_STOP_NICHES_HARD = {
    # patterns that should never auto-publish without human (keyed loosely)
}


def _norm_tokens(text: str) -> List[str]:
    return re.findall(r"[a-zA-ZçğıöşüÇĞİÖŞÜ0-9]{3,}", (text or "").lower())


def _jaccard(a: Sequence[str], b: Sequence[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / max(1, len(sa | sb))


def scene_template_similarity(scenes: Sequence[Dict[str, Any]]) -> float:
    """Mean pairwise Jaccard of narration tokens across scenes (high = templated)."""
    narrs = [_norm_tokens(s.get("narration") or s.get("text") or "") for s in scenes]
    narrs = [n for n in narrs if len(n) >= 4]
    if len(narrs) < 2:
        return 0.0
    pairs = 0
    total = 0.0
    for i in range(len(narrs)):
        for j in range(i + 1, len(narrs)):
            total += _jaccard(narrs[i], narrs[j])
            pairs += 1
    return total / max(1, pairs)


def commentary_angle_score(full_narration: str, keyword: str = "") -> float:
    """
    0–1: unique commentary markers (first/second person insight, contrast, numbers, questions).
    Low score = generic listicle sludge.
    """
    text = (full_narration or "").strip()
    if len(text) < 40:
        return 0.1
    score = 0.25
    if re.search(r"[?？]", text):
        score += 0.15
    if re.search(r"\b(ama|ancak|oysa|aslında|çünkü|however|but|actually|because)\b", text, re.I):
        score += 0.15
    if re.search(r"\d+", text):
        score += 0.1
    if re.search(r"\b(ben|biz|sen|siz|görüyorum|fark\s*et|I |we |you )\b", text, re.I):
        score += 0.15
    if keyword and keyword.lower()[:4] in text.lower():
        score += 0.1
    # penalty: pure enumeration
    bullets = len(re.findall(r"(^|\n)\s*[-•\d]+[.)]\s", text))
    if bullets >= 6 and len(text) < 500:
        score -= 0.2
    return max(0.0, min(1.0, score))


def inauthentic_risk_score(
    plan: Dict[str, Any],
    *,
    prior_scripts: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    """
    Returns risk 0–100 (higher = more spam-like) + hard_fail bool.
    Hard-fail when score says templated mass spam OR policy DROP patterns.
    """
    scenes = plan.get("scenes") or []
    full = plan.get("full_narration") or " ".join(
        (s.get("narration") or "") for s in scenes
    )
    keyword = plan.get("keyword") or plan.get("title") or ""
    niche = plan.get("niche_id") or ""

    reasons: List[str] = []
    risk = 10.0

    if _TEMPLATE_MARKERS.search(full):
        risk += 40
        reasons.append("placeholder_or_template_marker")

    if _INVESTMENT_PUSH.search(full):
        risk += 35
        reasons.append("investment_push_language")

    if _AI_EXPERT_PERSONA.search(full):
        risk += 50
        reasons.append("ai_expert_persona_sensitive")

    sim = scene_template_similarity(scenes)
    if sim > 0.72:
        risk += 30
        reasons.append(f"scene_near_identical:{sim:.2f}")
    elif sim > 0.55:
        risk += 15
        reasons.append(f"scene_high_overlap:{sim:.2f}")

    angle = commentary_angle_score(full, keyword=str(keyword))
    if angle < 0.35:
        risk += 25
        reasons.append(f"low_commentary_angle:{angle:.2f}")
    elif angle < 0.5:
        risk += 10
        reasons.append(f"weak_commentary_angle:{angle:.2f}")

    # Prior script near-dupe
    if prior_scripts:
        tokens = _norm_tokens(full)
        for prev in prior_scripts[:20]:
            j = _jaccard(tokens, _norm_tokens(prev))
            if j > 0.65:
                risk += 35
                reasons.append(f"prior_script_dupe:{j:.2f}")
                break

    # Query soup / stoic bleed for religious
    for s in scenes:
        for q in s.get("search_queries") or []:
            if niche.startswith("10_relig") and re.search(r"marcus|roman|stoic", str(q), re.I):
                risk += 20
                reasons.append("religious_stoic_visual_bleed")
                break

    risk = max(0.0, min(100.0, risk))
    hard_fail = risk >= 70 or "ai_expert_persona_sensitive" in reasons or "investment_push_language" in reasons
    verdict = (
        "templated_mass_spam" if hard_fail and risk >= 70
        else "policy_drop" if hard_fail
        else "elevated" if risk >= 45
        else "ok"
    )
    return {
        "risk": round(risk, 1),
        "hard_fail": hard_fail,
        "verdict": verdict,
        "reasons": reasons,
        "commentary_angle": round(angle, 3),
        "scene_similarity": round(sim, 3),
        "policy_ref": "https://support.google.com/youtube/answer/1311392",
    }


def ai_disclosure_block(
    *,
    uses_tts: bool = True,
    uses_ai_script: bool = True,
    uses_photoreal_ai: bool = False,
    uses_altered_real_event: bool = False,
    uses_real_person_synthetic: bool = False,
    uses_synthetic_persona: bool = False,
    uses_ai_visual: bool = False,
    lang: str = "tr",
) -> Dict[str, Any]:
    """
    Studio guidance + description paragraph.
    Realistic photoreal → recommend Studio AI survey = Yes.
    TTS + stock + original script → usually No, but we still disclose production assist.
    """
    reasons = []
    if uses_photoreal_ai:
        reasons.append("photorealistic_ai_visual")
    if uses_altered_real_event:
        reasons.append("altered_real_event_or_place")
    if uses_real_person_synthetic:
        reasons.append("synthetic_real_person")
    if uses_synthetic_persona:
        reasons.append("synthetic_persona")
    required = bool(reasons)
    studio_ai_survey = "yes" if required else "no"
    if lang == "tr":
        desc = (
            "🤖 Üretim notu: Bu Short'ta senaryo/kurgu yapay zekâ destekli hazırlanmış; "
            "anlatım sentez ses (TTS) kullanabilir. Şeffaflık için bakınız: "
            "YouTube GenAI disclosure politikası."
        )
        if not required:
            desc += " Gerçekçi sentetik veya değiştirilmiş gerçek olay/kişi gösterilmez."
        if required:
            desc += " Studio'da 'AI use' = Evet seçilmelidir: " + ", ".join(reasons) + "."
    else:
        desc = (
            "🤖 Production note: Script/editing may be AI-assisted; narration may use TTS. "
            "See YouTube GenAI disclosure policy."
        )
        if not required:
            desc += " No realistic depiction of a real person doing something they did not do."
        if required:
            desc += " Studio AI use = Yes: " + ", ".join(reasons) + "."
    return {
        "studio_ai_survey": studio_ai_survey,
        "disclosure_required": required,
        "required": required,
        "ai_disclosure_required": required,
        "reasons": reasons,
        "description_paragraph": desc,
        "required_if_photoreal": uses_photoreal_ai,
        "inputs": {
            "uses_tts": bool(uses_tts),
            "uses_ai_script": bool(uses_ai_script),
            "uses_photoreal_ai": bool(uses_photoreal_ai),
            "uses_altered_real_event": bool(uses_altered_real_event),
            "uses_real_person_synthetic": bool(uses_real_person_synthetic),
            "uses_synthetic_persona": bool(uses_synthetic_persona),
            "uses_ai_visual": bool(uses_ai_visual),
        },
        "policy_url": "https://support.google.com/youtube/answer/14328491",
    }


def sanitize_seo_description(description: str, max_hashtags: int = 3) -> str:
    """Strip tag stuffing / hashtag walls from descriptions (spam policy)."""
    text = description or ""
    if _SPAM_SEO.search(text):
        # drop lines that look like tag lists
        kept = []
        for line in text.splitlines():
            hashes = re.findall(r"#\w+", line)
            if len(hashes) > max_hashtags and len(line.split()) < len(hashes) + 3:
                continue
            if re.match(r"^\s*tags?\s*:", line, re.I):
                continue
            kept.append(line)
        text = "\n".join(kept)
    # Cap total hashtags
    tags = re.findall(r"#\w+", text)
    if len(tags) > max_hashtags:
        # keep first max_hashtags occurrences only
        count = 0

        def _repl(m):
            nonlocal count
            count += 1
            return m.group(0) if count <= max_hashtags else ""

        text = re.sub(r"#\w+", _repl, text)
        text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def niche_gate(niche_id: str, narration: str = "") -> Dict[str, Any]:
    """DROP / GATE / OK from research synthesis."""
    nid = (niche_id or "").lower()
    text = narration or ""
    if _AI_EXPERT_PERSONA.search(text) or _INVESTMENT_PUSH.search(text):
        return {"action": "DROP", "reason": "sensitive_advice_or_push"}
    if any(x in nid for x in ("crypto", "8_crypto")):
        return {"action": "GATE", "reason": "finance_education_disclaimer_required"}
    if any(x in nid for x in ("dark_psych", "7_dark")):
        return {"action": "GATE", "reason": "harmful_instruction_check"}
    if any(x in nid for x in ("fitness", "health", "parent")):
        return {"action": "GATE", "reason": "health_disclaimer_required"}
    if any(x in nid for x in ("kids", "36_kids", "çocuk")):
        return {"action": "GATE", "reason": "made_for_kids_coppa_limited_ads_mass_ai_risk"}
    if any(x in nid for x in ("mystery", "4_mystery", "unsolved")):
        return {"action": "GATE", "reason": "claim_vs_entertainment_framing"}
    if any(x in nid for x in ("news", "celebrity", "1_news")):
        return {"action": "GATE", "reason": "sensitive_event_exploit_check"}
    if "relig" in nid:
        return {"action": "GATE", "reason": "faith_respect_no_hate"}
    return {"action": "OK", "reason": "low_risk_niche"}


def evaluate_plan_compliance(plan: Dict[str, Any]) -> Dict[str, Any]:
    """One-shot gate for generate/render pipelines."""
    risk = inauthentic_risk_score(plan)
    gate = niche_gate(plan.get("niche_id") or "", plan.get("full_narration") or "")
    research = plan.get("research_brief") or {}
    research_gate = research_quality_gate(research)
    disclosure = ai_disclosure_block(
        uses_tts=True,
        uses_ai_script=True,
        uses_photoreal_ai=bool(plan.get("uses_photoreal_ai")),
        uses_altered_real_event=bool(plan.get("uses_altered_real_event")),
        uses_real_person_synthetic=bool(plan.get("uses_real_person_synthetic")),
        uses_synthetic_persona=bool(plan.get("uses_synthetic_persona")),
        uses_ai_visual=bool(plan.get("uses_ai_visual")),
        lang=plan.get("language") or "tr",
    )
    # Human-craft / discovery-beast (AI slop ≠ Discover)
    discovery = None
    craft_reject = False
    craft_reason = ""
    try:
        from craft import apply_human_craft, human_craft_hard_reject
        if not (plan.get("human_craft") or (plan.get("meta") or {}).get("human_craft")):
            plan = apply_human_craft(
                plan,
                title=str(plan.get("keyword") or plan.get("title") or ""),
                niche_id=str(plan.get("niche_id") or ""),
                language=str(plan.get("language") or "tr"),
            )
        craft_reject, craft_reason = human_craft_hard_reject(plan)
        discovery = (plan.get("human_craft") or {}).get("discovery_beast")
        if craft_reject:
            risk = dict(risk)
            risk["risk"] = min(100.0, float(risk.get("risk") or 0) + 20)
            reasons = list(risk.get("reasons") or [])
            reasons.append(f"discovery_beast_reject:{craft_reason}")
            risk["reasons"] = reasons
    except Exception:
        pass

    # Keep publication hard-fails separate from render blockers. A missing
    # research contract prevents auto-publish, but it does not mean the
    # rendered asset is unsafe to inspect or revise.
    hard_reasons: List[str] = []
    if risk["hard_fail"]:
        hard_reasons.extend(risk.get("reasons") or ["inauthentic_policy_risk"])
    if gate["action"] == "DROP":
        hard_reasons.append(f"niche_gate:{gate.get('reason') or 'drop'}")
    if craft_reject:
        hard_reasons.append(f"human_craft:{craft_reason or 'rejected'}")
    if research_gate["action"] in ("DROP", "GATE"):
        hard_reasons.append(f"research_gate:{research_gate.get('reason') or research_gate['action'].lower()}")
    hard = bool(hard_reasons)
    render_blocking = bool(
        risk["hard_fail"] or gate["action"] == "DROP" or craft_reject
    )
    # Render blocker and diagnostic must never disagree. Older callers used
    # the boolean only and showed the useless fallback text "policy risk".
    if render_blocking and not hard_reasons:
        if risk.get("hard_fail"):
            hard_reasons.append("inauthentic_policy_risk")
        elif gate.get("action") == "DROP":
            hard_reasons.append(f"niche_gate:{gate.get('reason') or 'drop'}")
        elif craft_reject:
            hard_reasons.append(f"human_craft:{craft_reason or 'rejected'}")
        hard = True
    # Discovery fail always marks ok=False for UI; hard_fail for spam-level risk
    if craft_reject and float(risk.get("risk") or 0) >= 55:
        hard = True

    return {
        "ok": not hard and not craft_reject,
        "hard_fail": hard,
        "hard_fail_reasons": hard_reasons,
        "render_blocking": render_blocking,
        "diagnosis": {
            "primary": hard_reasons[0] if hard_reasons else "ok",
            "message": (
                "İçerik render edildi; otomatik yayın için araştırma kanıtı gerekiyor."
                if not render_blocking and hard_reasons
                else "Politika riski yok."
                if not hard_reasons
                else "İçerik politika güvenlik kapısından geçmedi."
            ),
            "next_step": (
                "İki bağımsız kaynak ekleyip yayınlama kapısını yeniden değerlendir."
                if research_gate["action"] in ("DROP", "GATE")
                else "Metni yeniden üret ve tekrar değerlendir."
                if render_blocking else ""
            ),
        },
        "inauthentic": risk,
        "niche_gate": gate,
        "ai_disclosure": disclosure,
        "discovery_beast": discovery,
        "human_craft_reject": craft_reject,
        "human_craft_reason": craft_reason,
        "research": research_gate,
        "fingerprint": hashlib.sha1(
            (plan.get("full_narration") or "")[:2000].encode("utf-8", "ignore")
        ).hexdigest()[:16],
    }


def research_quality_gate(brief: Dict[str, Any]) -> Dict[str, Any]:
    """Block factual publishing when the evidence contract is incomplete."""
    if not brief:
        return {"action": "GATE", "reason": "research_brief_missing", "ready": False}
    from production.evidence import evaluate_evidence
    result = evaluate_evidence(brief)
    # Preserve the legacy DROP outcome for incomplete contracts. This is an
    # internal publication hold, not a claim that YouTube forbids the topic.
    if not result["ready"]:
        result["action"] = "DROP"
    return result


def publication_decision(
    plan: Dict[str, Any],
    compliance: Dict[str, Any],
    viewer_score: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Return a render/review/drop decision; automatic YouTube publishing is disabled."""
    if compliance.get("hard_fail"):
        return {"action": "DROP", "reason": "compliance_hard_fail", "auto_publish": False}
    if (compliance.get("research") or {}).get("action") != "ALLOW":
        return {"action": "HUMAN_REVIEW", "reason": "research_not_ready", "auto_publish": False}
    if (compliance.get("niche_gate") or {}).get("action") != "OK":
        return {"action": "HUMAN_REVIEW", "reason": "risk_sensitive_niche", "auto_publish": False}
    score = float((viewer_score or {}).get("score") or 0)
    if score < 70:
        return {"action": "HUMAN_REVIEW", "reason": "viewer_score_below_70", "auto_publish": False, "score": score}
    if (compliance.get("ai_disclosure") or {}).get("disclosure_required") or any(
        plan.get(key) for key in ("uses_photoreal_ai", "uses_altered_real_event", "uses_real_person_synthetic", "uses_synthetic_persona")
    ):
        return {"action": "HUMAN_REVIEW", "reason": "synthetic_media_disclosure", "auto_publish": False, "score": score}
    return {"action": "RENDER_ALLOWED", "reason": "quality_gates_passed_manual_upload_only", "auto_publish": False, "score": score}


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
    files = {
        "source_manifest": root / "source_manifest.json",
        "visual_credits": root / "visual_credits.json",
        "policy_snapshot": root / "policy_snapshot.json",
        "ai_disclosure": root / "ai_disclosure.json",
        "manual_upload_checklist": root / "manual_upload_checklist.json",
        "package_manifest": root / "package_manifest.json",
    }
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
