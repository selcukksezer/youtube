"""
Scene Intent Classification, Camera Direction Assignment, Exclusion Checks,
and Semantic / Embedding Relevance Scoring for `director/visual_intent.py`.
"""
from __future__ import annotations

import math
import re
import sys
from typing import Any, Dict, List, Optional

from .schema import VisualIntent


def _vi_attr(name: str, default: Any) -> Any:
    vi = sys.modules.get("director.visual_intent")
    return getattr(vi, name, default) if vi is not None else default


def _tokenize(text: str) -> set:
    return {t for t in re.findall(r"[a-zA-ZçğıöşüÇĞİÖŞÜ0-9]{3,}", (text or "").lower())}


# ─── INVIDEO-AI-NEXUS SHOT INTENTS MAP (Section 2.1.5 & Section 28.5) ───────
SHOT_INTENTS: Dict[str, Dict[str, Any]] = {
    "question": {
        "intent": "closeup",
        "camera_direction": "zoom_in",
        "action": "slow push in",
        "description": "Soru ve kanca anında izleyiciyi ekrana kilitleyen yakınlaşma.",
    },
    "transition": {
        "intent": "transition",
        "camera_direction": "pan_left",
        "action": "pan left",
        "description": "Sahne ve konu geçişlerinde akıcı yatay kamera kayması.",
    },
    "conclusion": {
        "intent": "establishing",
        "camera_direction": "zoom_out",
        "action": "slow pull out",
        "description": "Sonuç, kapanış ve döngü köprüsünde büyük resmi gösteren uzaklaşma.",
    },
    "action": {
        "intent": "action",
        "camera_direction": "pan_right",
        "action": "dynamic pan right",
        "description": "Yüksek tempolu olay örgüsü ve dinamik hareket.",
    },
    "closeup": {
        "intent": "closeup",
        "camera_direction": "zoom_in",
        "action": "tight focus zoom in",
        "description": "Somut nesne, yüz ifadesi ve şok detayı.",
    },
    "establishing": {
        "intent": "establishing",
        "camera_direction": "zoom_out",
        "action": "wide establishing pull out",
        "description": "Geniş çevre ve atmosfer kurulumu.",
    },
}


def classify_scene_intent(
    narration: str = "",
    beat_type: str = "conflict",
    index: int = 0,
    total_scenes: int = 1,
    title: str = "",
    scene_description: str = "",
) -> str:
    """
    Bölüm 7.6 & 28.5 (invideo-ai-nexus pattern):
    Sahne niyetini belirler:
    - 'question': Soru/merak kancası -> Kamera: zoom_in
    - 'transition': Konu/zaman geçişi -> Kamera: pan_left
    - 'conclusion': Sonuç/kapanış/döngü köprüsü -> Kamera: zoom_out
    - 'closeup': Şok edici detay, yüz ifadesi, mikro obje -> Kamera: zoom_in
    - 'action': Yüksek tempolu hareket, çatışma, dinamik olay -> Kamera: pan_right
    - 'establishing': Geniş çevre ve dünya kurulumu -> Kamera: zoom_out
    """
    combined = f"{narration} {scene_description}".lower()
    tokens = _tokenize(combined)

    def _hit(words: List[str]) -> int:
        score = 0
        for kw in words:
            piece = kw.lower()
            if " " in piece:
                if piece in combined:
                    score += 1
                continue
            if any(t == piece or (len(piece) >= 3 and t.startswith(piece)) for t in tokens):
                score += 1
        return score

    question_triggers = [
        "?", "neden", "nasıl", "kim", "hiç merak", "biliyor musun", "fark ettin mi",
        "why", "how", "what if", "did you know", "ever wonder"
    ]
    if "?" in narration or _hit(question_triggers) > 0:
        if index == 0 or "neden" in combined or "nasıl" in combined or "?" in narration:
            return "question"

    if index == 0:
        closeup_hook_triggers = [
            "bu adam", "fark ettin", "gözlerine", "yüzü", "parmak", "sır",
            "fısıld", "baktı", "küçük", "close up", "detay", "shock", "göz", "yüz"
        ]
        if _hit(closeup_hook_triggers):
            return "closeup"
        return "establishing"

    conclusion_keywords = [
        "sonuç", "aslında", "işte bu yüzden", "böylece", "artık", "sonunda",
        "finally", "in the end", "conclusion", "remember"
    ]
    if total_scenes > 1 and index == total_scenes - 1:
        if _hit(conclusion_keywords) > 0 or beat_type in ("resolution", "climax"):
            return "conclusion"
        return "transition"

    establishing_keywords = [
        "dünya", "evren", "şehir", "tarihte", "uzay", "geniş", "ufuk", "sokak",
        "orman", "deniz", "gökyüzü", "aerial", "skyline", "landscape", "overview",
        "wide", "bütün", "krallık", "imparatorluk", "tapınak", "galaksi", "alan",
        "manzara", "saray", "meydan"
    ]
    closeup_keywords = [
        "göz", "yüz", "parmak", "yazı", "belge", "kitap", "para", "telefon",
        "fısıld", "küçük", "detay", "baktı", "hisset", "macro", "micro", "face",
        "hands", "letter", "coin", "altın", "saat", "ekran", "parşömen", "heykel",
        "mektup", "imza", "gözlük"
    ]
    action_keywords = [
        "koş", "patla", "fırla", "vur", "kaç", "savaş", "hızla", "çarp",
        "hareket", "sıçra", "dövüş", "tırman", "run", "jump", "explode", "strike",
        "speed", "fight", "yangın", "hücum", "kavga", "dalga", "fırtına", "kaza"
    ]
    transition_keywords = [
        "ancak", "fakat", "ardından", "sonra", "yıllar", "dönüş", "sonunda",
        "farklı", "geçiş", "köprü", "birden", "oysa", "lakin", "derken", "bunun yerine",
        "zamanla", "artık", "tam o anda", "however", "meanwhile", "later", "then"
    ]

    scores = {
        "action": _hit(action_keywords),
        "closeup": _hit(closeup_keywords),
        "establishing": _hit(establishing_keywords),
        "transition": _hit(transition_keywords),
    }

    best_intent = max(scores, key=lambda k: scores[k])
    if scores[best_intent] > 0:
        return best_intent

    beat_lower = (beat_type or "").lower()
    if beat_lower in ("hook",):
        return "establishing"
    elif beat_lower in ("climax", "conflict", "action"):
        return "action"
    elif beat_lower in ("shock", "document", "quiz"):
        return "closeup"
    elif beat_lower in ("resolution", "bridge"):
        return "conclusion"

    cycle = ["action", "closeup", "action", "establishing"]
    return cycle[index % len(cycle)]


def assign_camera_direction(
    scene_intent: str,
    index: int = 0,
    prev_direction: Optional[str] = None,
) -> str:
    """
    Bölüm 7.6 & 28.5 (invideo-ai-nexus pattern):
    Sahne niyetine göre akıllı kamera hareketi tayin eder.
    """
    shot_intents = _vi_attr("SHOT_INTENTS", SHOT_INTENTS)
    if scene_intent in shot_intents:
        direct_cam = shot_intents[scene_intent]["camera_direction"]
        if direct_cam != prev_direction:
            return direct_cam

    intent_direction_pools = {
        "question": ["zoom_in", "tilt_up"],
        "transition": ["pan_left", "tilt_down", "zoom_out"],
        "conclusion": ["zoom_out", "pan_right", "tilt_down"],
        "establishing": ["zoom_out", "pan_right", "zoom_in"],
        "closeup": ["zoom_in", "tilt_up", "zoom_out"],
        "action": ["pan_right", "pan_left", "tilt_up"],
    }
    pool = intent_direction_pools.get(scene_intent, ["zoom_in", "pan_right", "zoom_out", "pan_left"])

    chosen = pool[index % len(pool)]
    if prev_direction and chosen == prev_direction:
        for alt in pool:
            if alt != prev_direction:
                chosen = alt
                break
        else:
            general_alts = ["zoom_in", "pan_left", "zoom_out", "pan_right", "tilt_up"]
            for alt in general_alts:
                if alt != prev_direction:
                    chosen = alt
                    break

    return chosen


def text_contains_excluded(text: str, must_exclude: List[str]) -> bool:
    low = (text or "").lower()
    return any(ex.lower() in low for ex in (must_exclude or []))


_EMBED_CACHE: Dict[str, List[float]] = {}
_MAX_EMBED_CACHE_ENTRIES = 512


def _embed_text(text: str) -> List[float]:
    key = (text or "").strip().lower()[:240]
    if not key:
        return []
    cache = _vi_attr("_EMBED_CACHE", _EMBED_CACHE)
    max_entries = _vi_attr("_MAX_EMBED_CACHE_ENTRIES", _MAX_EMBED_CACHE_ENTRIES)
    if key in cache:
        return cache[key]
    try:
        from google_ai_hub import embed_text
        ok, vec = embed_text(key)
        if ok and isinstance(vec, list) and vec:
            if len(cache) >= max_entries:
                try:
                    cache.pop(next(iter(cache)))
                except (StopIteration, KeyError):
                    cache.clear()
            cache[key] = vec
            return vec
    except Exception:
        pass
    return []


def _embedding_similarity_boost(a: str, b: str) -> float:
    """Return 0..12 boost from cosine similarity of Gemini embeddings."""
    embed_fn = _vi_attr("_embed_text", _embed_text)
    va = embed_fn(a)
    vb = embed_fn(b)
    if not va or not vb:
        return 0.0
    dot = sum(x * y for x, y in zip(va, vb))
    na = math.sqrt(sum(x * x for x in va)) or 1.0
    nb = math.sqrt(sum(x * x for x in vb)) or 1.0
    cos = max(0.0, min(1.0, dot / (na * nb)))
    return cos * 12.0


def semantic_relevance_score(
    candidate_text: str,
    narration: str,
    intent: Optional[VisualIntent] = None,
) -> float:
    """Token overlap score 0..40 for stock candidate ranking (+ cross-language TR->EN & embedding boost)."""
    excl_fn = _vi_attr("text_contains_excluded", text_contains_excluded)
    if intent and excl_fn(candidate_text, intent.must_exclude):
        return -100.0
    cand = _tokenize(candidate_text)
    narr = _tokenize(narration)
    if narration:
        try:
            from visuals.query_builder import _translate_blob
            tr_en_concepts = _translate_blob(narration)
            if tr_en_concepts:
                narr |= _tokenize(tr_en_concepts)
        except Exception:
            pass
        try:
            from visuals.subject_lock import match_shot
            locked_shot = match_shot(narration)
            if locked_shot is not None:
                narr |= _tokenize(locked_shot.primary)
        except Exception:
            pass
    if intent:
        narr |= (
            _tokenize(intent.subject)
            | _tokenize(intent.mood)
            | _tokenize(intent.action)
            | _tokenize(intent.setting)
            | set(intent.must_include)
        )
    if not cand or not narr:
        base = 0.0
    else:
        overlap = len(cand & narr)
        base = min(40.0, overlap * 8.0)

    try:
        import config as _cfg
        if getattr(_cfg, "USE_GEMINI_EMBEDDINGS", False) and getattr(_cfg, "GEMINI_API_KEY", ""):
            boost_fn = _vi_attr("_embedding_similarity_boost", _embedding_similarity_boost)
            boost = boost_fn(candidate_text, narration)
            base = min(40.0, base + boost)
    except Exception:
        pass
    return base
