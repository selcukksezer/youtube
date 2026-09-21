"""Compliance: inauthentic-content risk, originality angle, AI disclosure text."""
from __future__ import annotations

import hashlib
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
    lang: str = "tr",
) -> Dict[str, Any]:
    """
    Studio guidance + description paragraph.
    Realistic photoreal → recommend Studio AI survey = Yes.
    TTS + stock + original script → usually No, but we still disclose production assist.
    """
    studio_ai_survey = "yes" if uses_photoreal_ai else "no"
    if lang == "tr":
        desc = (
            "🤖 Üretim notu: Bu Short'ta senaryo/kurgu yapay zekâ destekli hazırlanmış; "
            "anlatım sentez ses (TTS) kullanabilir. Gerçek bir kişinin yapmadığı bir eylemi "
            "veya gerçekçi sahte olay gösterilmez. Şeffaflık için bakınız: "
            "YouTube GenAI disclosure politikası."
        )
        if uses_photoreal_ai:
            desc += " Studio'da 'AI use' = Evet seçilmelidir (gerçekçi sentetik görüntü)."
    else:
        desc = (
            "🤖 Production note: Script/editing may be AI-assisted; narration may use TTS. "
            "No realistic depiction of a real person doing something they did not do. "
            "See YouTube GenAI disclosure policy."
        )
    return {
        "studio_ai_survey": studio_ai_survey,
        "description_paragraph": desc,
        "required_if_photoreal": uses_photoreal_ai,
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
    disclosure = ai_disclosure_block(
        uses_tts=True,
        uses_ai_script=True,
        uses_photoreal_ai=bool(plan.get("uses_photoreal_ai")),
        lang=plan.get("language") or "tr",
    )
    hard = risk["hard_fail"] or gate["action"] == "DROP"
    return {
        "ok": not hard,
        "hard_fail": hard,
        "inauthentic": risk,
        "niche_gate": gate,
        "ai_disclosure": disclosure,
        "fingerprint": hashlib.sha1(
            (plan.get("full_narration") or "")[:2000].encode("utf-8", "ignore")
        ).hexdigest()[:16],
    }
