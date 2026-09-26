"""
Virality & Coherence Evaluator for Shorts Scripts.
Adapted and enhanced from Anil-matcha/AI-Youtube-Shorts-Generator (highlights.py).
Evaluates script content on the 8 high-retention viral signals and guards against nonsensical slop.
"""
import re
from typing import Any, Dict, List, Optional

VIRALITY_SIGNALS = {
    "hook_moment": {
        "weight": 25,
        "name": "Hook Moment (İlk 3 Saniye)",
        "patterns": [
            r"\b(sırrı|asla|sakın|neden|nasıl|şok|gerçek|bunu bilmeden|kimse|inanılmaz|tarihin en|tuhaf)\b",
            r"[?!]",
        ],
    },
    "emotional_peak": {
        "weight": 15,
        "name": "Emotional Peak (Duygusal Zirve)",
        "patterns": [
            r"\b(korku|şaşkınlık|dehşet|öfke|tutku|heyecan|şaşırtıcı|tüyler ürpertici|mucize|acımasız)\b",
        ],
    },
    "opinion_bomb": {
        "weight": 15,
        "name": "Opinion Bomb (Kutuplaştırıcı / Karşıt Görüş)",
        "patterns": [
            r"\b(tam tersi|yanılıyorsunuz|yanılgı|hata|çoğu insan|aslında öyle değil|gerçek şu ki)\b",
        ],
    },
    "revelation_moment": {
        "weight": 15,
        "name": "Revelation Moment (Şaşırtıcı İtiraf / Gerçek)",
        "patterns": [
            r"\b(ortaya çıktı|belgeler|kanıt|keşfedildi|saklanan|perde arkası|rakamlar|istatistik)\b",
        ],
    },
    "conflict_tension": {
        "weight": 10,
        "name": "Conflict & Tension (Çatışma ve Gerilim)",
        "patterns": [
            r"\b(savaş|mücadele|karşı karşıya|tehdit|tehlike|kriz|çöküş|baskı|meydan okuma)\b",
        ],
    },
    "quotable_line": {
        "weight": 10,
        "name": "Quotable One-Liner (Alıntılanabilir Cümle)",
        "patterns": [
            r"\b(unutmayın|hayat|insan|güç|başarı|disiplin|zihin|kural|özgürlük)\b",
        ],
    },
    "practical_value": {
        "weight": 10,
        "name": "Practical Value (Uygulanabilir Değer)",
        "patterns": [
            r"\b(adım|taktik|yöntem|strateji|kural|yapmanız gereken|çözüm|teknik)\b",
        ],
    },
}

# Red flag patterns for nonsensical / absurd slop that previously broke our videos
NONSENSICAL_SLOP_PATTERNS = [
    re.compile(r"tek bir ayrıntı yeter", re.IGNORECASE),
    re.compile(r"gözlerime inanamadım,\s*kalbim duracak gibiydi", re.IGNORECASE),
    re.compile(r"hakkında söylediği söz şok edici", re.IGNORECASE),
    re.compile(r"başa dön tek rakam", re.IGNORECASE),
    re.compile(r"cevabı gördün;\s*kaydırma", re.IGNORECASE),
    re.compile(r"bunu aklında tut\.\s*bunu aklında tut", re.IGNORECASE),
    re.compile(r"rakamlar yalan söylemez:\s*rakamlar yalan söylemez", re.IGNORECASE),
    re.compile(r"kleopatra['’]ın stoacıların", re.IGNORECASE),
    re.compile(r"elon musk['’]ın antik roma", re.IGNORECASE),
]


def detect_script_slop_issues(text: str) -> List[str]:
    """Finds phrases that make the narration nonsensical."""
    issues = []
    for pat in NONSENSICAL_SLOP_PATTERNS:
        match = pat.search(text)
        if match:
            issues.append(f"Saçma/Tekrarlı kalıp tespit edildi: '{match.group(0)}'")

    # Check for excessive duplicate clauses in text
    words = text.lower().split()
    if len(words) >= 8:
        for span_len in (3, 4, 5):
            seen_spans = {}
            for i in range(len(words) - span_len + 1):
                span = " ".join(words[i : i + span_len])
                if span in seen_spans and (i - seen_spans[span]) >= span_len:
                    if span not in ("ve tam da", "bu videonun sonunda"):
                        issues.append(f"Tekrarlanan cümle parçası: '{span}'")
                        break
                seen_spans[span] = i

    return issues


def evaluate_script_virality(narration_text: str, topic: str = "") -> Dict[str, Any]:
    """
    Evaluates a script based on Anil-matcha's 8 virality signals + coherence guard.
    Returns virality score (0-100), detected signals, and slop issues.
    """
    cleaned = (narration_text or "").strip()
    if not cleaned:
        return {
            "score": 0,
            "is_coherent": False,
            "signals_detected": [],
            "issues": ["Metin boş veya geçersiz"],
            "hook_sentence": "",
            "virality_reason": "Metin bulunamadı",
        }

    slop_issues = detect_script_slop_issues(cleaned)
    is_coherent = len(slop_issues) == 0

    first_sentence = cleaned.split(".")[0].strip()
    if len(first_sentence) > 120:
        first_sentence = first_sentence[:117] + "..."

    detected_signals = []
    raw_score = 0

    for signal_key, signal_info in VIRALITY_SIGNALS.items():
        found = False
        for pat in signal_info["patterns"]:
            if re.search(pat, cleaned, re.IGNORECASE):
                found = True
                break
        if found:
            raw_score += signal_info["weight"]
            detected_signals.append(signal_info["name"])

    # Penalty for slop or broken coherence
    if slop_issues:
        raw_score = max(10, raw_score - (len(slop_issues) * 30))

    # Bonus if hook is in first sentence
    hook_present_in_opening = any(
        re.search(pat, first_sentence, re.IGNORECASE)
        for pat in VIRALITY_SIGNALS["hook_moment"]["patterns"]
    )
    if hook_present_in_opening:
        raw_score = min(100, raw_score + 10)

    # Word count evaluation (sweet spot for Shorts: 60 - 180 words)
    word_count = len(cleaned.split())
    if word_count < 25:
        raw_score = max(15, raw_score - 25)
        slop_issues.append("Metin çok kısa (25 kelimenin altında)")
    elif word_count > 220:
        raw_score = max(20, raw_score - 20)
        slop_issues.append("Metin 60 saniyelik Shorts için çok uzun (>220 kelime)")


    final_score = max(0, min(100, raw_score))

    reason_parts = []
    if detected_signals:
        reason_parts.append(", ".join(detected_signals[:3]))
    if not is_coherent:
        reason_parts.append("Kusurlu/tekrarlı kalıplar mevcut")

    return {
        "score": final_score,
        "is_coherent": is_coherent,
        "signals_detected": detected_signals,
        "issues": slop_issues,
        "hook_sentence": first_sentence,
        "virality_reason": " | ".join(reason_parts) if reason_parts else "Standart metin",
        "word_count": word_count,
    }
