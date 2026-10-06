"""
Bölüm 8.5: Virality Audit ve İzleyici Puanlama Motoru
(Virality Audit & Viewer Scoring Engine)

Senaryo render edilmeden önce 100 üzerinden 4 katmanlı formülle puanlanır:
1. İlk 3 saniye kanca gücü (30 puan)
2. Cümle başı kelime yoğunluğu ve hece ritmi (25 puan)
3. Duygusal zıtlık ve merak öğeleri (25 puan)
4. Loop köprüsü uyumluluğu (20 puan)

Puanı 70'in altında kalan senaryolar reddedilir veya otomatik tamir edilir.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

# Eşik değerler (Bölüm 8.5)
VIRALITY_PASS_THRESHOLD: float = 70.0
VIRALITY_REPAIR_THRESHOLD: float = 50.0

# Kanca / Duygusal Zıtlık / Merak kelimeleri
HOOK_TRIGGERS = re.compile(
    r"\b(neden|asla|kimse|şok|sakın|gizli|sır|inanılmaz|gerçek|bunu bil|dikkat|"
    r"why|never|secret|shocking|nobody|truth|warning|stop)\b",
    re.I,
)
CONTRAST_TRIGGERS = re.compile(
    r"\b(ama|fakat|oysa|aksine|aslında|farklı|yanılgı|şaşırtıcı|beklenmedik|korkunç|mucize|"
    r"but|however|actually|instead|unexpected|surprising|shocking|myth|illusion)\b",
    re.I,
)


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-zA-ZçğıöşüÇĞİÖŞÜ0-9]{3,}", (text or "").lower())


def _count_syllables_tr_en(word: str) -> int:
    """Approximate syllable count (vowels for TR, vowel groups for EN)."""
    w = word.lower()
    vowels = "aeıioöuü"
    count = sum(1 for ch in w if ch in vowels)
    if count == 0:
        count = len(re.findall(r"[aeiouy]+", w))
    return max(1, count)


def calculate_hook_score(scenes: Sequence[Dict[str, Any]]) -> float:
    """
    1. İlk 3 saniye kanca gücü (30 puan).
    - İlk sahne beat_type='hook' veya index 0: +6 puan
    - Soru işareti veya güçlü kanca kelimeleri: +12 puan
    - Kelime sayısı ideal aralıkta (6–22 kelime): +8 puan
    - Retention gate açılışı (ilk kelimede duraksama yok): +4 puan
    """
    if not scenes:
        return 0.0

    first = scenes[0]
    narr = (first.get("narration") or "").strip()
    beat = str(first.get("beat_type") or first.get("beat") or "").lower()
    words = narr.split()
    word_count = len(words)

    score = 0.0

    # 1. Beat tipi ve yapı (+6)
    if beat in ("hook", "intro") or first.get("scene_index", 0) == 0:
        score += 6.0

    # 2. Soru veya tetikleyici kanca (+12)
    has_question = bool(re.search(r"[?？]", narr))
    has_trigger = bool(HOOK_TRIGGERS.search(narr))
    if has_question and has_trigger:
        score += 12.0
    elif has_question or has_trigger:
        score += 9.0
    else:
        score += 3.0

    # 3. İdeal kelime sayısı (+8)
    if 6 <= word_count <= 22:
        score += 8.0
    elif 4 <= word_count <= 28:
        score += 5.0
    else:
        score += 2.0

    # 4. Açılış dinamizmi (+4)
    if words and not words[0].lower().startswith(("ve", "veya", "bu", "o", "and", "so")):
        score += 4.0
    else:
        score += 2.0

    return min(30.0, score)


def calculate_rhythm_pacing_score(scenes: Sequence[Dict[str, Any]], total_dur: float) -> float:
    """
    2. Cümle başı kelime yoğunluğu ve hece ritmi (25 puan).
    - Ortalama konuşma hızı (2.2 – 3.4 wps): +12 puan
    - Cümleler arası süre / hece ritmi dengesi (varyans < 1.5): +8 puan
    - Sahne başına kelime sınır uyumu (<= 18 kelime): +5 puan
    """
    if not scenes:
        return 0.0

    durations = []
    wps_list = []
    syllable_rates = []

    for s in scenes:
        narr = (s.get("narration") or "").strip()
        words = narr.split()
        d = float(s.get("duration") or s.get("target_duration") or 0)
        if d <= 0:
            d = (total_dur / len(scenes)) if (total_dur > 0 and len(scenes) > 0) else 4.0
        durations.append(d)
        wps = len(words) / max(0.5, d)
        wps_list.append(wps)
        sylls = sum(_count_syllables_tr_en(w) for w in words)
        syllable_rates.append(sylls / max(0.5, d))

    score = 0.0
    avg_wps = sum(wps_list) / max(1, len(wps_list))

    # 1. Konuşma hızı bandı (+12)
    if 2.2 <= avg_wps <= 3.4:
        score += 12.0
    elif 1.8 <= avg_wps <= 4.0:
        score += 8.0
    else:
        score += 4.0

    # 2. Hece ve kelime varyansı (+8)
    if len(wps_list) >= 2:
        variance = sum((x - avg_wps) ** 2 for x in wps_list) / len(wps_list)
        if variance < 1.2:
            score += 8.0
        elif variance < 2.5:
            score += 5.0
        else:
            score += 2.0
    else:
        score += 6.0

    # 3. Sahne kelime sınır uyumu (+5)
    within_bounds = sum(1 for s in scenes if len((s.get("narration") or "").split()) <= 18)
    bound_ratio = within_bounds / max(1, len(scenes))
    score += round(bound_ratio * 5.0, 1)

    return min(25.0, score)


def calculate_emotional_contrast_score(scenes: Sequence[Dict[str, Any]]) -> float:
    """
    3. Duygusal zıtlık ve merak öğeleri (25 puan).
    - Metin içinde zıtlık köprüleri ('ama', 'oysa', 'aslında', 'fakat'): +10 puan
    - Merak ve gizem yaratan unsurlar / beklenmedik ifadeler: +10 puan
    - Sahneler arası tempo veya duygu değişimi: +5 puan
    """
    if not scenes:
        return 0.0

    full_narr = " ".join(str(s.get("narration") or "") for s in scenes)
    score = 0.0

    # 1. Zıtlık köprüsü varlığı (+10)
    contrast_matches = len(CONTRAST_TRIGGERS.findall(full_narr))
    if contrast_matches >= 2:
        score += 10.0
    elif contrast_matches == 1:
        score += 7.0
    else:
        score += 2.0

    # 2. Merak uyandıran ifadeler (+10)
    hook_matches = len(HOOK_TRIGGERS.findall(full_narr))
    if hook_matches >= 3:
        score += 10.0
    elif hook_matches >= 1:
        score += 7.0
    else:
        score += 3.0

    # 3. Sahne çeşitliliği (+5)
    beats = {str(s.get("beat_type") or s.get("beat") or "") for s in scenes}
    if len(beats) >= 2:
        score += 5.0
    else:
        score += 3.0

    return min(25.0, score)


def calculate_loop_bridge_score(scenes: Sequence[Dict[str, Any]]) -> float:
    """
    4. Loop köprüsü uyumluluğu (20 puan).
    - Son sahne anlatımının ilk sahne kancasına anlamsal bağlanması:
    - Son sahne kelimeleri ile ilk sahne kelimeleri arasındaki ortaklık: +12 puan
    - Son sahnede döngü bağlacı ('çünkü', 'işte', 'tam da bu yüzden'): +8 puan
    """
    if len(scenes) < 2:
        return 8.0

    first_narr = str(scenes[0].get("narration") or "")
    last_narr = str(scenes[-1].get("narration") or "")

    first_tokens = set(_tokenize(first_narr))
    last_tokens = set(_tokenize(last_narr))

    score = 0.0

    # 1. Kelime örtüşmesi ve anlamsal köprü (+12)
    overlap = len(first_tokens & last_tokens)
    if overlap >= 2:
        score += 12.0
    elif overlap == 1:
        score += 9.0
    else:
        score += 3.0

    # 2. Döngü köprüsü bağlacı (+8)
    loop_connectors = re.compile(
        r"(çünkü|işte|tam da bu yüzden|bunun sebebi|her şey böyle başladı|"
        r"because|that's why|and this is why|how it all started)",
        re.I,
    )
    if loop_connectors.search(last_narr) or loop_connectors.search(first_narr):
        score += 8.0
    elif last_narr.strip().endswith(("...", "—", ":")):
        score += 6.0
    else:
        score += 3.0

    return min(20.0, score)


def audit_script_virality(
    plan_or_scenes: Union[Dict[str, Any], Sequence[Dict[str, Any]]],
    total_duration: float = 0.0,
) -> Dict[str, Any]:
    """
    Bölüm 8.5 Virality Audit Motoru:
    100 üzerinden 4 katmanlı puanlama:
    - hook (30p) + rhythm (25p) + contrast (25p) + loop (20p) = 100p
    Puanı 70'in altında kalan senaryolar reddedilir veya otomatik tamir edilir.
    """
    if isinstance(plan_or_scenes, dict):
        scenes = plan_or_scenes.get("scenes") or []
        dur = float(plan_or_scenes.get("total_duration") or 0.0) or total_duration
    else:
        scenes = list(plan_or_scenes or [])
        dur = total_duration

    if dur <= 0 and scenes:
        dur = sum(float(s.get("duration") or 4.0) for s in scenes)

    hook = calculate_hook_score(scenes)
    rhythm = calculate_rhythm_pacing_score(scenes, dur)
    contrast = calculate_emotional_contrast_score(scenes)
    loop = calculate_loop_bridge_score(scenes)

    total = round(hook + rhythm + contrast + loop, 1)
    passed = total >= VIRALITY_PASS_THRESHOLD

    status = "PASSED" if passed else ("REPAIRABLE" if total >= VIRALITY_REPAIR_THRESHOLD else "REJECTED")

    diagnostics: List[str] = []
    if hook < 20.0:
        diagnostics.append("Kanca zayıf: İlk 3 saniyede güçlü soru veya merak unsuru eklenmeli.")
    if rhythm < 17.0:
        diagnostics.append("Ritim dengesiz: Kelime/saniye oranı 2.5–3.2 aralığına yaklaştırılmalı.")
    if contrast < 17.0:
        diagnostics.append("Duygusal zıtlık eksik: Beklenmedik zıtlık köprüsü ('ama', 'oysa', 'aslında') eklenmeli.")
    if loop < 14.0:
        diagnostics.append("Loop köprüsü zayıf: Son cümle ilk cümlenin konusuna doğrudan bağlanmalı.")

    return {
        "score": total,
        "total_score": total,
        "passed": passed,
        "pass": passed,
        "status": status,
        "threshold": VIRALITY_PASS_THRESHOLD,
        "components": {
            "hook_strength": hook,
            "rhythm_pacing": rhythm,
            "emotional_contrast": contrast,
            "loop_bridge": loop,
        },
        "diagnostics": diagnostics,
    }


def auto_repair_script_virality(
    plan: Dict[str, Any],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Puanı 70'in altında kalan senaryolar için otomatik virallik tamiri (Bölüm 8.5).
    Kanca, zıtlık ve döngü köprülerini güçlendirerek puanı >= 70 yapar.
    Returns:
        (repaired_plan, updated_audit_report)
    """
    import copy
    repaired = copy.deepcopy(plan)
    scenes = repaired.get("scenes") or []
    if not scenes:
        report = audit_script_virality(repaired)
        return repaired, report

    audit = audit_script_virality(repaired)
    if audit["passed"]:
        return repaired, audit

    # 1. Kanca Tamiri (< 20 puan ise)
    if audit["components"]["hook_strength"] < 20.0:
        first = scenes[0]
        narr = (first.get("narration") or "").strip()
        first["beat_type"] = "hook"
        if not narr.endswith("?"):
            first["narration"] = f"Neden kimse bundan bahsetmiyor? {narr}"
        else:
            first["narration"] = f"Bunu sakın atlama: {narr}"

    # 2. Duygusal Zıtlık Tamiri (< 17 puan ise)
    if audit["components"]["emotional_contrast"] < 17.0 and len(scenes) >= 2:
        mid_idx = len(scenes) // 2
        mid = scenes[mid_idx]
        mid_narr = (mid.get("narration") or "").strip()
        if not any(k in mid_narr.lower() for k in ["ama", "oysa", "aslında"]):
            mid["narration"] = f"Oysa gerçek tamamen farklıydı: {mid_narr}"

    # 3. Loop Köprüsü Tamiri (< 14 puan ise)
    if audit["components"]["loop_bridge"] < 14.0 and len(scenes) >= 2:
        last = scenes[-1]
        last_narr = (last.get("narration") or "").strip()
        first_tokens = _tokenize(scenes[0].get("narration") or "")
        key_term = first_tokens[0] if first_tokens else "bunu"
        if not last_narr.endswith((".", "!", "?")):
            last_narr += "."
        last["narration"] = f"{last_narr} İşte tam da bu yüzden {key_term}..."

    # Yeniden puanla
    new_audit = audit_script_virality(repaired)
    repaired.setdefault("meta", {})["viewer_score"] = new_audit
    return repaired, new_audit


def compute_viewer_score(
    plan: Dict[str, Any],
    *,
    license_safe: bool = True,
    compliance: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Backward-compatible entry point for viewer_score + Chapter 8.5 Virality Audit.
    """
    scenes = plan.get("scenes") or []
    total = float(plan.get("total_duration") or 0.0)
    if total <= 0 and scenes:
        total = sum(float(s.get("duration") or 4.0) for s in scenes)

    audit = audit_script_virality(scenes, total_duration=total)
    lic = 1.0 if license_safe else 0.0
    if compliance and compliance.get("hard_fail"):
        lic = min(lic, 0.2)

    total_score = audit["score"]
    # If hard fail in compliance, penalize score
    if compliance and compliance.get("hard_fail"):
        total_score = min(total_score, 45.0)

    is_passed = total_score >= VIRALITY_PASS_THRESHOLD and not (compliance or {}).get("hard_fail")

    return {
        "score": round(total_score, 1),
        "total_score": round(total_score, 1),
        "components": {
            "hook_strength": audit["components"]["hook_strength"],
            "rhythm_pacing": audit["components"]["rhythm_pacing"],
            "emotional_contrast": audit["components"]["emotional_contrast"],
            "loop_bridge": audit["components"]["loop_bridge"],
            "license_safety": round(lic * 100, 1),
        },
        "pass": is_passed,
        "passed": is_passed,
        "diagnostics": audit["diagnostics"],
        "status": audit["status"] if not (compliance or {}).get("hard_fail") else "REJECTED",
    }
