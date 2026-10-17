"""Core compliance gate implementations: inauthentic risk, disclosure, niche gates, and publication decisions."""
from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, List, Optional, Sequence

from .transparent_disclosure import build_transparent_ai_disclosure_block

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
    clips_or_manifest: Optional[Sequence[Dict[str, Any]]] = None,
    include_sources: bool = False,
) -> Dict[str, Any]:
    """
    Studio guidance + description paragraph + Chapter 8.3 transparent sources block.
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

    # Chapter 8.3 Transparent AI and sources block
    transparent_res = build_transparent_ai_disclosure_block(
        clips_or_manifest=clips_or_manifest,
        uses_tts=uses_tts,
        uses_ai_script=uses_ai_script,
        uses_photoreal_ai=uses_photoreal_ai,
        uses_altered_real_event=uses_altered_real_event,
        uses_real_person_synthetic=uses_real_person_synthetic,
        uses_synthetic_persona=uses_synthetic_persona,
        uses_ai_visual=uses_ai_visual,
        lang=lang,
        include_sources=(clips_or_manifest is not None or include_sources),
    )

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

    # If clips/manifest was provided or sources explicitly requested, augment description_paragraph
    if clips_or_manifest is not None or include_sources:
        desc = transparent_res["full_disclosure_text"]

    return {
        "studio_ai_survey": studio_ai_survey,
        "disclosure_required": required,
        "required": required,
        "ai_disclosure_required": required,
        "reasons": reasons,
        "description_paragraph": desc,
        "required_if_photoreal": uses_photoreal_ai,
        "header_text": transparent_res["header_text"],
        "sources_text": transparent_res["sources_text"],
        "full_disclosure_text": transparent_res["full_disclosure_text"],
        "providers": transparent_res["providers"],
        "sources_count": transparent_res["sources_count"],
        "inputs": {
            "uses_tts": bool(uses_tts), "uses_ai_script": bool(uses_ai_script),
            "uses_photoreal_ai": bool(uses_photoreal_ai), "uses_altered_real_event": bool(uses_altered_real_event),
            "uses_real_person_synthetic": bool(uses_real_person_synthetic),
            "uses_synthetic_persona": bool(uses_synthetic_persona), "uses_ai_visual": bool(uses_ai_visual),
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
    if render_blocking and not hard_reasons:
        if risk.get("hard_fail"):
            hard_reasons.append("inauthentic_policy_risk")
        elif gate.get("action") == "DROP":
            hard_reasons.append(f"niche_gate:{gate.get('reason') or 'drop'}")
        elif craft_reject:
            hard_reasons.append(f"human_craft:{craft_reason or 'rejected'}")
        hard = True
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
