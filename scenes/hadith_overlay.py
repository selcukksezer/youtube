"""On-screen Arabic and citation for hadith scenes. Narration stays Turkish."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

_ARABIC_RUN = re.compile(
    r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]"
    r"(?:[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF\s«»]+)"
)

# Anchor phrase in the Turkish narration, Arabic on screen, citation line.
_PAIRS: List[Tuple[str, str, str]] = [
    ("niyetlere göredir", "«إِنَّمَا الْأَعْمَالُ بِالنِّيَّاتِ»", "(Buhari, Bed'ü'l-Vahy, 1)"),
    ("kolaylaştırın", "«يَسِّرُوا وَلَا تُعَسِّرُوا، وَبَشِّرُوا وَلَا تُنَفِّرُوا»", "(Buhari, İlim, 11)"),
    ("güzel söz", "«الْكَلِمَةُ الطَّيِّبَةُ صَدَقَةٌ»", "(Buhari, Edeb, 34)"),
    ("kardeşi için", "«لَا يُؤْمِنُ أَحَدُكُمْ حَتَّى يُحِبَّ لِأَخِيهِ مَا يُحِبُّ لِنَفْسِهِ»", "(Buhari, İman, 7)"),
    ("merhamet etmeyen", "«مَنْ لَا يَرْحَمْ لَا يُرْحَمْ»", "(Buhari, Edeb, 27)"),
    ("duanın özü", "«الدُّعَاءُ مُخُّ الْعِبَادَةِ»", "(Tirmizi, Daavat, 1)"),
    ("dünyada da iyilik", "«رَبَّنَا آتِنَا فِي الدُّنْيَا حَسَنَةً وَفِي الْآخِرَةِ حَسَنَةً»", "(Bakara, 201)"),
    ("şükrederseniz", "«لَئِنْ شَكَرْتُمْ لَأَزِيدَنَّكُمْ»", "(İbrahim, 7)"),
    ("kalpler ancak", "«أَلَا بِذِكْرِ اللَّهِ تَطْمَئِنُّ الْقُلُوبُ»", "(Ra'd, 28)"),
    ("her zorlukla", "«فَإِنَّ مَعَ الْعُسْرِ يُسْرًا»", "(İnşirah, 5)"),
    ("bana dua edin", "«ادْعُونِي أَسْتَجِبْ لَكُمْ»", "(Mü'min, 60)"),
    ("sabredenlerle", "«إِنَّ اللَّهَ مَعَ الصَّابِرِينَ»", "(Bakara, 153)"),
    ("bize yeter", "«حَسْبُنَا اللَّهُ وَنِعْمَ الْوَكِيلُ»", "(Al-i İmran, 173)"),
    ("ben yakınım", "«فَإِنِّي قَرِيبٌ»", "(Bakara, 186)"),
    ("beni anın", "«فَاذْكُرُونِي أَذْكُرْكُمْ»", "(Bakara, 152)"),
    ("sağlık ve boş vakit", "«نِعْمَتَانِ مَغْبُونٌ فِيهِمَا كَثِيرٌ مِنَ النَّاسِ: الصِّحَّةُ وَالْفَرَاغُ»", "(Buhari, Rikak, 1)"),
    ("kur'an'ı öğrenen", "«خَيْرُكُمْ مَنْ تَعَلَّمَ الْقُرْآنَ وَعَلَّمَهُ»", "(Buhari, Fezailü'l-Kur'an, 21)"),
    ("birbirinize kardeş", "«لَا تَحَاسَدُوا وَلَا تَبَاغَضُوا وَكُونُوا عِبَادَ اللَّهِ إِخْوَانًا»", "(Buhari, Edeb, 57)"),
    ("affedicisin", "«اللَّهُمَّ إِنَّكَ عَفُوٌّ تُحِبُّ الْعَفْوَ فَاعْفُ عَنِّي»", "(Tirmizi, Daavat, 84)"),
]


def is_sacred_niche(niche_id: str = "", title: str = "", narration: str = "") -> bool:
    blob = f"{niche_id} {title} {narration}".lower()
    keys = (
        "relig", "hadis", "hadith", "islamic", "islami", "16_islamic",
        "10_religious", "kuran", "quran", "ayet", "buhari", "müslim", "muslim",
        "peygamber",
    )
    return any(key in blob for key in keys)


def _has_arabic(text: str) -> bool:
    return bool(re.search(r"[\u0600-\u06FF]", text or ""))


def _hoist_arabic(narration: str) -> Tuple[str, str]:
    runs = [m.group(0).strip() for m in _ARABIC_RUN.finditer(narration or "")]
    runs = [r for r in runs if _has_arabic(r)]
    if not runs:
        return narration, ""
    arabic = " ".join(runs)
    cleaned = _ARABIC_RUN.sub(" ", narration)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" -–—,;")
    return cleaned, arabic


def _match_pair(narration: str) -> Optional[Tuple[str, str]]:
    low = (narration or "").lower()
    best = None
    for anchor, arabic, citation in _PAIRS:
        if anchor in low and (best is None or len(anchor) > len(best[0])):
            best = (anchor, arabic, citation)
    if not best:
        return None
    return best[1], best[2]


def attach_hadith_screen_text(plan: Dict[str, Any]) -> Dict[str, Any]:
    """Put Arabic and the book line on sacred scenes. Leave the spoken Turkish in place."""
    if not isinstance(plan, dict):
        return plan
    scenes = plan.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        return plan
    blob = " ".join([
        str(plan.get("niche_id") or ""),
        str(plan.get("title") or ""),
        str(plan.get("keyword") or ""),
    ])
    narrations = " ".join(str((s or {}).get("narration") or "") for s in scenes if isinstance(s, dict))
    if not is_sacred_niche(blob, narration=narrations):
        return plan
    for scene in scenes:
        if not isinstance(scene, dict):
            continue
        narration = str(scene.get("narration") or "")
        cleaned, hoisted = _hoist_arabic(narration)
        if hoisted and cleaned != narration:
            scene["narration"] = cleaned
            narration = cleaned
        if not _has_arabic(str(scene.get("arabic_text") or "")) and hoisted:
            scene["arabic_text"] = hoisted
        matched = _match_pair(narration)
        if matched and not _has_arabic(str(scene.get("arabic_text") or "")):
            scene["arabic_text"] = matched[0]
        if matched and not str(scene.get("source_citation") or "").strip():
            scene["source_citation"] = matched[1]
    return plan
