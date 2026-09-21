"""
Scene narration quality — complete sentences only (P0-01 / P0-02).
Validation uses normalized text (markdown/emojis stripped) to avoid false positives.
Auto-repair fixes genuinely broken narration before hard-blocking.
"""
from __future__ import annotations

import copy
import re
from typing import Any, Dict, List, Tuple

MIN_WORDS_PER_SCENE = 10
MIN_WORDS_DRAMA_SCENE = 12
MIN_WORDS_PER_SENTENCE = 5
MIN_WORDS_AI_TARGET = 10

SHORTS_MIN_DURATION = 38.0
SHORTS_MAX_DURATION = 60.0
MIN_SCENE_COUNT = 8
MAX_SCENE_COUNT = 16

_PLACEHOLDER_DESC_RE = re.compile(
    r"^(?:\(?\s*scene[_\s-]?description\s*\)?|\.\.\.|tbd|n/a|placeholder|desc(?:ription)?)\s*$",
    re.IGNORECASE,
)

_DANGLING_END_WORDS = frozenset({
    "ve", "ama", "çünkü", "için", "ise", "ile", "bir", "bu", "o", "senin", "kendi",
    "olan", "gibi", "de", "da", "hiçbir", "asla", "derin", "burada", "tam", "olarak",
    "içindeki", "icindeki", "ateşi", "atesi", "zehri", "kaleyi", "yelkenini", "şeye", "seye",
    "dertlerle", "marcus", "hiçbir", "hicbir", "ise", "gelecek", "onlara", "değil", "degil",
    "kusuru", "bozan", "ruhunu", "imparator", "kaleni", "iç", "ic", "en", "üst", "ust",
    "yolun", "kendisidir", "fani", "boş", "bos", "her", "şey", "sey", "kural",
})

_MOOD_LABEL_RE = re.compile(
    r"\*\*(?:URGENT|DRAMATIC|EPIC|CALM|MYSTERIOUS|ENERGETIC|DARK|BRIGHT|SECRET|WARNING|HOOK|CTA)\*\*\s*",
    re.IGNORECASE,
)

_TAIL_COMPLETIONS = {
    "için": "bu kuralı uygula.",
    "icin": "bu kuralı uygula.",
    "asla": "bozamaz.",
    "çünkü": "her şey bir seçimdir.",
    "cunku": "her şey bir seçimdir.",
    "onlara": "verdiğin anlamı belirler.",
    "değil": "senin tavrını belirler.",
    "degil": "senin tavrını belirler.",
    "senin": "tavrını belirler.",
    "ve": "devam eder.",
    "ama": "gerçek budur.",
}

_FRAGMENT_ENDING_RE = re.compile(
    r"(?:çünkü|asla|ama|ve|için|senin|kendi|ise|derin|olan|hiçbir|burada|"
    r"şeye|kaleyi|ateşi|yelkenini|zehri|dertlerle|onlara|değil|degil|kusuru|"
    r"bozan|ruhunu|imparator|kaleni|Marcus)\.\s*$",
    re.IGNORECASE,
)


def normalize_narration_for_validation(text: str) -> str:
    """
    Strip markdown mood tags, emojis, and trailing symbols for gate checks only.
    Display / stored narration may keep formatting; validation must not false-fail on it.
    """
    if not text:
        return ""
    t = (text or "").strip()
    t = _MOOD_LABEL_RE.sub("", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"\1", t)
    t = re.sub(r"\*([^*]+)\*", r"\1", t)
    t = re.sub(r"[\U00010000-\U0010ffff]", "", t)
    t = re.sub(r"[\u2600-\u27bf\ufe00-\ufe0f]", "", t)
    t = re.sub(r"[\u2000-\u32ff]", "", t)
    t = re.sub(r"[#*_~^\\/|<>@=`\[\]{}]", " ", t)
    t = re.sub(r"([.!?])\s*[^\w\s\u00c0-\u024f\u1e00-\u1eff]+\s*$", r"\1", t, flags=re.UNICODE)
    if t and t[-1] not in ".!?" and re.search(r"[.!?]", t):
        m = re.search(r"^(.*[.!?])", t)
        if m:
            t = m.group(1)
    t = re.sub(r"\s+([.!?,;:])", r"\1", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _split_sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[.!?])\s+", (text or "").strip())
    return [p.strip() for p in parts if p.strip()]


def _ensure_terminal(s: str) -> str:
    s = (s or "").strip()
    if not s:
        return ""
    if s[-1] not in ".!?":
        s += "."
    return s


def _strip_dangling_clause(text: str) -> Tuple[str, bool]:
    words = (text or "").strip().split()
    stripped = False
    while words:
        tail = words[-1].lower().rstrip(".,!?;:")
        candidate = " ".join(words)
        if tail in _DANGLING_END_WORDS or _FRAGMENT_ENDING_RE.search(_ensure_terminal(candidate)):
            words.pop()
            stripped = True
        else:
            break
    return " ".join(words), stripped


def _append_minimal_completion(text: str) -> str:
    text = (text or "").strip().rstrip(",;:")
    words = text.split()
    if not words:
        return "Bunu aklında tut."
    tail = words[-1].lower().rstrip(".,!?;:")
    suffix = _TAIL_COMPLETIONS.get(tail, "Bunu aklında tut.")
    base = text.rstrip(".!? ")
    return _ensure_terminal(f"{base} {suffix}")


_MOOD_ONLY_RE = re.compile(
    r"^(?:urgent|dramatic|epic|calm|mysterious|energetic|dark|bright|tense|secret|warning|hook|cta)"
    r"(?:\s+(?:urgent|dramatic|epic|calm|mysterious|energetic|dark|bright|tense|energetic))?\s*[.!?]*$",
    re.IGNORECASE,
)


def scene_narration_usable(text: str) -> bool:
    """True when narration has enough semantic content for a Shorts scene."""
    raw = (text or "").strip()
    if not raw or raw in {".", "-", "—", "..."}:
        return False
    norm = normalize_narration_for_validation(raw)
    words = norm.split()
    if len(words) < MIN_WORDS_PER_SCENE:
        return False
    if _MOOD_ONLY_RE.match(norm):
        return False
    if norm[-1] not in ".!?":
        return False
    return True


def scene_description_usable(text: str) -> bool:
    """Reject empty, template, or placeholder visual descriptions."""
    raw = (text or "").strip()
    if not raw or len(raw) < 12:
        return False
    if _PLACEHOLDER_DESC_RE.match(raw):
        return False
    lower = raw.lower()
    if "scene_description" in lower and len(raw) < 40:
        return False
    if lower in {"description", "visual", "n/a", "tbd", "..."}:
        return False
    return True


def plan_narration_usable(scenes: List[Dict[str, Any]], *, min_ratio: float = 1.0) -> bool:
    """All scenes must pass scene_narration_usable (guards AI placeholder / half-empty plans)."""
    if not scenes:
        return False
    good = sum(1 for s in scenes if scene_narration_usable(s.get("narration") or ""))
    return good >= max(1, int(len(scenes) * min_ratio))


def plan_needs_procedural_inject(scenes: List[Dict[str, Any]]) -> bool:
    """Director/render inject — empty, placeholder visuals, or uniform AI stub narrations."""
    if not scenes:
        return True
    if not plan_narration_usable(scenes):
        return True
    bad_desc = 0
    word_counts: List[int] = []
    for s in scenes:
        desc = (s.get("scene_description") or "").strip()
        if not desc and s.get("search_queries"):
            desc = str((s.get("search_queries") or [""])[0])
        if not scene_description_usable(desc):
            bad_desc += 1
        word_counts.append(len(normalize_narration_for_validation(s.get("narration") or "").split()))
    if bad_desc >= max(1, len(scenes) // 2):
        return True
    avg = sum(word_counts) / max(1, len(word_counts))
    if max(word_counts) < MIN_WORDS_PER_SCENE and avg < MIN_WORDS_AI_TARGET:
        return True
    return False


def plan_quality_usable(scenes: List[Dict[str, Any]], *, min_ratio: float = 1.0) -> bool:
    """Narration + visual description quality gate — rejects AI stub plans."""
    if not scenes:
        return False
    if len(scenes) < MIN_SCENE_COUNT or len(scenes) > MAX_SCENE_COUNT:
        return False
    good = 0
    word_counts: List[int] = []
    for s in scenes:
        norm = normalize_narration_for_validation(s.get("narration") or "")
        word_counts.append(len(norm.split()))
        narr_ok = scene_narration_usable(s.get("narration") or "")
        desc = (s.get("scene_description") or "").strip()
        if not desc and s.get("search_queries"):
            desc = str((s.get("search_queries") or [""])[0])
        desc_ok = scene_description_usable(desc)
        if narr_ok and desc_ok:
            good += 1
    if good < max(1, int(len(scenes) * min_ratio)):
        return False
    # Reject AI-style stub plans: any scene under 8 words or average below target
    if any(w < 8 for w in word_counts):
        return False
    avg = sum(word_counts) / max(1, len(word_counts))
    return avg >= MIN_WORDS_AI_TARGET


def scene_narration_issues(text: str, *, normalized: bool = False) -> List[str]:
    """Return issue codes for a single scene narration (uses normalized text by default)."""
    issues: List[str] = []
    narr = (text or "").strip()
    if not narr:
        return ["empty"]
    check = narr if normalized else normalize_narration_for_validation(narr)
    if not check:
        return ["empty"]
    words = check.split()
    if len(words) < MIN_WORDS_PER_SCENE:
        issues.append("low_words")
    if check[-1] not in ".!?":
        issues.append("no_terminal")
    if _FRAGMENT_ENDING_RE.search(check):
        issues.append("fragment_ending")
    tail = words[-1].lower().rstrip(".,!?;:")
    if tail in _DANGLING_END_WORDS:
        # "... bilgi için" CTAs are complete phrases, not condense artifacts
        if tail in ("için", "icin") and len(words) >= MIN_WORDS_PER_SCENE:
            pass
        else:
            issues.append("dangling_tail")
    sentences = _split_sentences(check)
    if len(sentences) == 1:
        sw = sentences[0].split()
        if len(sw) < MIN_WORDS_PER_SENTENCE and sentences[0][-1:] in ".!?":
            issues.append("fragment_sentence")
    elif sentences:
        last = sentences[-1]
        sw = last.split()
        if len(sw) < MIN_WORDS_PER_SENTENCE and last[-1:] in ".!?":
            issues.append("fragment_sentence")
        stail = sw[-1].lower().rstrip(".,!?;:") if sw else ""
        if stail in _DANGLING_END_WORDS:
            issues.append("dangling_sentence")
    else:
        for sent in sentences:
            stail = sent.split()[-1].lower().rstrip(".,!?;:") if sent.split() else ""
            if stail in _DANGLING_END_WORDS:
                issues.append("dangling_sentence")
                break
    return issues


def auto_repair_scene_narration(narration: str) -> Tuple[str, List[str]]:
    """Rule-based repair for one scene. Returns (repaired_text, fix_descriptions)."""
    fixes: List[str] = []
    raw = (narration or "").strip()
    if not raw:
        return raw, fixes

    text = normalize_narration_for_validation(raw)
    if not scene_narration_issues(text, normalized=True):
        if text != raw:
            fixes.append("normalized_formatting")
        return text if text != raw else raw, fixes

    stripped, did_strip = _strip_dangling_clause(text)
    if did_strip and stripped:
        text = stripped
        fixes.append("stripped_dangling_clause")

    if text and text[-1] not in ".!?":
        text = _ensure_terminal(text)
        fixes.append("added_terminal")

    if scene_narration_issues(text, normalized=True):
        words = text.split()
        if len(words) < MIN_WORDS_PER_SCENE:
            completed = _append_minimal_completion(text)
            if not scene_narration_issues(completed, normalized=True):
                text = completed
                fixes.append("appended_completion")
            else:
                fixed = trim_to_valid_sentences(text)
                if fixed and not scene_narration_issues(fixed, normalized=True):
                    text = fixed
                    fixes.append("trimmed_to_valid")

    if text and not scene_narration_issues(text, normalized=True):
        return text, fixes
    return text or raw, fixes


def auto_repair_scenes(scenes: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Repair scene list in-place; merge ultra-short fragments with next scene."""
    scenes = copy.deepcopy(scenes)
    fixes: List[str] = []
    i = 0
    while i < len(scenes):
        sc = scenes[i]
        raw = (sc.get("narration") or "").strip()
        if not raw:
            i += 1
            continue

        if not scene_narration_issues(raw):
            i += 1
            continue

        repaired, scene_fixes = auto_repair_scene_narration(raw)
        if scene_fixes:
            sc["narration"] = repaired
            fixes.extend(f"scene_{i}:{f}" for f in scene_fixes)

        if scene_narration_issues(sc.get("narration") or ""):
            words = (sc.get("narration") or "").split()
            if len(words) < MIN_WORDS_PER_SCENE and i + 1 < len(scenes):
                nxt = (scenes[i + 1].get("narration") or "").strip()
                merged = f"{sc['narration'].rstrip('.!?')} {nxt.lstrip()}"
                merged, mfixes = auto_repair_scene_narration(merged)
                sc["narration"] = merged
                dur = float(sc.get("duration") or 3.0) + float(scenes[i + 1].get("duration") or 3.0)
                sc["duration"] = round(dur, 1)
                scenes.pop(i + 1)
                fixes.append(f"merged_scene_{i}_with_{i + 1}")
                fixes.extend(f"scene_{i}:{f}" for f in mfixes)
                continue

        i += 1

    return scenes, fixes


def auto_repair_plan(plan: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """Repair all scene narrations and rebuild full_narration."""
    plan = copy.deepcopy(plan or {})
    scenes, fixes = auto_repair_scenes(plan.get("scenes") or [])
    plan["scenes"] = scenes
    plan["full_narration"] = " ".join(
        (s.get("narration") or "").strip() for s in scenes if (s.get("narration") or "").strip()
    )
    return plan, fixes


def apply_auto_repair_if_needed(plan: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str], bool]:
    """
    Normalize-check then repair only when issues remain.
    Returns (plan, fixes_applied, repaired_flag).
    """
    scenes = plan.get("scenes") or []
    needs_repair = any(scene_narration_issues((s.get("narration") or "")) for s in scenes)
    if not needs_repair:
        return plan, [], False
    repaired_plan, fixes = auto_repair_plan(plan)
    still_bad = any(
        scene_narration_issues((s.get("narration") or ""))
        for s in repaired_plan.get("scenes") or []
    )
    return repaired_plan, fixes, bool(fixes) and not still_bad


def trim_to_valid_sentences(text: str, min_words: int = MIN_WORDS_PER_SCENE) -> str:
    """Keep only whole sentences that pass integrity checks."""
    text = normalize_narration_for_validation(text)
    if not text:
        return ""
    kept: List[str] = []
    for sent in _split_sentences(text):
        candidate = _ensure_terminal(sent)
        if not scene_narration_issues(candidate, normalized=True):
            kept.append(candidate)
    if kept:
        return " ".join(kept)
    parts = _split_sentences(text)
    if parts:
        words = parts[0].split()
        while len(words) > min_words and words[-1].lower().rstrip(".,!?") in _DANGLING_END_WORDS:
            words.pop()
        if len(words) >= min_words:
            return _ensure_terminal(" ".join(words))
    return ""


def validate_and_fix_scenes(scenes: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Fix scene narrations; auto-repair first, coherence pass, then trim fallback."""
    from .narration_coherence import repair_split_verbs_across_scenes

    scenes, fixes = auto_repair_scenes(scenes)
    scenes, coherence_fixes = repair_split_verbs_across_scenes(scenes)
    fixes.extend(coherence_fixes)
    all_issues: List[str] = list(fixes)
    for i, sc in enumerate(scenes):
        raw = (sc.get("narration") or "").strip()
        if not raw:
            all_issues.append(f"empty_scene_{i}")
            continue
        issues = scene_narration_issues(raw)
        if issues:
            fixed = trim_to_valid_sentences(raw)
            if fixed and not scene_narration_issues(fixed):
                sc["narration"] = fixed
            else:
                all_issues.append(f"scene_{i}:{'|'.join(issues)}")
    return scenes, all_issues


def plan_narration_ok(plan: Dict[str, Any]) -> bool:
    """Quick check: all scenes pass after normalization."""
    for s in plan.get("scenes") or []:
        if scene_narration_issues((s.get("narration") or "")):
            return False
    return bool(plan.get("scenes"))


def _scene_word_total(scenes: List[Dict[str, Any]]) -> int:
    return sum(len((s.get("narration") or "").split()) for s in scenes)


def repair_post_hook_word_budget(plan: Dict[str, Any], max_words: int = 110) -> Dict[str, Any]:
    """
    Batch D — soft pre-compile trim after retention hooks.
    Drops trailing sentences from hook/closing scenes before Director hard condense.
    """
    scenes = plan.get("scenes") or []
    if not scenes:
        return plan
    before = _scene_word_total(scenes)
    if before <= max_words:
        return plan

    out = copy.deepcopy(plan)
    scenes_out: List[Dict[str, Any]] = out["scenes"]
    hook_indices = [0]
    if len(scenes_out) > 1:
        hook_indices.append(len(scenes_out) - 1)

    while _scene_word_total(scenes_out) > max_words:
        trimmed = False
        for idx in hook_indices:
            narr = (scenes_out[idx].get("narration") or "").strip()
            parts = _split_sentences(narr)
            words = narr.split()
            if len(parts) > 1 and len(words) > MIN_WORDS_PER_SCENE:
                scenes_out[idx]["narration"] = " ".join(parts[:-1]).strip()
                trimmed = True
                break
        if not trimmed:
            break

    while _scene_word_total(scenes_out) > max_words:
        idx = max(
            range(len(scenes_out)),
            key=lambda i: len((scenes_out[i].get("narration") or "").split()),
        )
        words = (scenes_out[idx].get("narration") or "").split()
        if len(words) <= MIN_WORDS_PER_SCENE:
            break
        candidate = " ".join(words[:-1]).strip()
        if scene_narration_usable(candidate):
            scenes_out[idx]["narration"] = candidate
        else:
            break

    total_now = _scene_word_total(scenes_out)
    if total_now > max_words and scenes_out:
        share = max(MIN_WORDS_PER_SCENE, max_words // len(scenes_out))
        for sc in scenes_out:
            words = (sc.get("narration") or "").split()
            if len(words) > share + 2:
                candidate = _ensure_terminal(" ".join(words[:share]).strip())
                if scene_narration_usable(candidate):
                    sc["narration"] = candidate

    after = _scene_word_total(scenes_out)
    out["full_narration"] = " ".join(
        (s.get("narration") or "").strip()
        for s in scenes_out
        if (s.get("narration") or "").strip()
    )
    if after < before:
        out["word_budget_pretrim"] = {"from": before, "to": after, "max": max_words}
    return out
