"""
director/prompt_chains.py — Role-based Prompt Chains & Punch-In Staging Director.
Adapted and evolved from reference_repos/ai-content-studio/server/core/director_engine.py
(Plan Section 28.2).

Provides:
- 3-step specialized role-based prompt synthesis:
  1. Investigator Role: Strict fact validation and anti-hallucination extraction.
  2. Screenwriter Role: High-retention narrative tension, cold-open hook, pacing.
  3. Visual Director Role: Staging, filmable subjects, punch-in cuts, SFX timing.
- High-impact word detection for center punch-in zoom (15%) and SFX cue timing.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

HIGH_IMPACT_KEYWORDS_EN = {
    "money", "secret", "viral", "crazy", "explosive", "hack", "truth", "insane",
    "shocking", "danger", "hidden", "warning", "never", "always", "billionaire",
    "forbidden", "deadly", "killer", "rule", "magic", "exposed",
}

HIGH_IMPACT_KEYWORDS_TR = {
    "para", "sır", "viral", "çılgın", "patlama", "taktik", "gerçek", "delilik",
    "şok", "tehlike", "gizli", "uyarı", "asla", "her zaman", "milyarder",
    "yasak", "ölümcül", "tuzak", "kural", "kanıt", "ifşa", "yalan", "hata",
    "dikkat", "önemli", "sakın", "odaklan", "fırsat", "bomba",
}

ALL_HIGH_IMPACT = HIGH_IMPACT_KEYWORDS_EN | HIGH_IMPACT_KEYWORDS_TR


class RoleBasedPromptChain:
    """
    Coordinates multi-agent role prompts to prevent generic AI monologue outputs.
    """

    INVESTIGATOR_ROLE_TR = (
        "ROL: Baş Araştırmacı ve Doğrulama Uzmanı (Fact Investigator).\n"
        "GÖREV: Konu hakkındaki en çarpıcı, doğrulanabilir 3 somut gerçeği ve sayısal veriyi süz.\n"
        "İntihal ve klişe uydurmalardan kaçın; sadece doğrulanmış web ve tarihsel kanıtlara odaklan."
    )

    SCREENWRITER_ROLE_TR = (
        "ROL: Usta YouTube Shorts Senaristi (Documentary Screenwriter).\n"
        "GÖREV: Araştırmacının sağladığı somut gerçekleri 45-60 saniyelik, ilk 3 saniyesi soğuk açılış kancalı, "
        "merak boşluğu yaratan ve organik tartışma kapanışlı nefes kesici bir monoloğa dönüştür.\n"
        "YAPAY ZEKA KLİŞELERİ KESİNLİKLE YASAK."
    )

    DIRECTOR_ROLE_TR = (
        "ROL: Sinematik Görsel Yönetmen (Visual Director & Staging Agent).\n"
        "GÖREV: Her sahne cümlesi için kameranın doğrudan vizörden görebileceği SOMUT bir özne ve 3 farklı çekim açısı belirle.\n"
        "Yüksek etkili anahtar kelimelerde (para, sır, şok, tehlike) 1.2 saniyelik merkez yakınlaşması (punch-in zoom) planla."
    )

    INVESTIGATOR_ROLE_EN = (
        "ROLE: Lead Fact Investigator & Verification Specialist.\n"
        "TASK: Extract 3 verifiable, concrete facts and empirical data points without generic assumptions."
    )

    SCREENWRITER_ROLE_EN = (
        "ROLE: Master YouTube Shorts Screenwriter.\n"
        "TASK: Turn verified facts into a high-retention 45-60s script with cold open hook and curiosity gap."
    )

    DIRECTOR_ROLE_EN = (
        "ROLE: Cinematic Visual Director.\n"
        "TASK: Stage each scene with a camera-filmable noun and identify punch-in emphasis timestamps."
    )

    @classmethod
    def get_role_instructions(cls, role: str = "director", lang: str = "tr") -> str:
        lang = lang.lower()
        role = role.lower()
        if lang == "tr":
            if role in ("investigator", "researcher"):
                return cls.INVESTIGATOR_ROLE_TR
            elif role in ("screenwriter", "writer"):
                return cls.SCREENWRITER_ROLE_TR
            else:
                return cls.DIRECTOR_ROLE_TR
        else:
            if role in ("investigator", "researcher"):
                return cls.INVESTIGATOR_ROLE_EN
            elif role in ("screenwriter", "writer"):
                return cls.SCREENWRITER_ROLE_EN
            else:
                return cls.DIRECTOR_ROLE_EN

    @classmethod
    def assemble_chained_prompt(
        cls,
        topic: str,
        niche_id: str = "",
        verified_facts: Optional[List[str]] = None,
        lang: str = "tr",
    ) -> str:
        """
        Builds a comprehensive role-guided prompt injecting verified facts and staging directives.
        """
        facts_block = ""
        if verified_facts:
            facts_block = "\nDOĞRULANMIŞ GÜNCEL KANITLAR:\n" + "\n".join(f"- {f}" for f in verified_facts)

        role_guidelines = (
            f"{cls.get_role_instructions('investigator', lang)}\n\n"
            f"{cls.get_role_instructions('screenwriter', lang)}\n\n"
            f"{cls.get_role_instructions('director', lang)}"
        )

        return (
            f"=== 3 AŞAMALI ROL BAZLI ÜRETİM PROTOKOLÜ (AI Content Studio Pattern) ===\n"
            f"KONU: {topic}\n"
            f"NİŞ: {niche_id}\n"
            f"{facts_block}\n\n"
            f"ROL YÖNERGELERİ:\n{role_guidelines}\n"
        )

    @classmethod
    def generate_chain(
        cls,
        topic: str,
        niche: str = "general",
        target_duration: float = 45.0,
        language: str = "tr",
    ) -> Dict[str, Any]:
        """
        Generates structured role prompts and word targets for multi-agent synthesis.
        """
        words_per_sec = 2.5
        target_words = int(target_duration * words_per_sec)
        lang = language.lower()
        return {
            "investigator": {
                "role": "investigator",
                "prompt": f"{cls.get_role_instructions('investigator', lang)}\nKonu: {topic}\nNiş: {niche}",
            },
            "screenwriter": {
                "role": "screenwriter",
                "prompt": f"{cls.get_role_instructions('screenwriter', lang)}\nKonu: {topic}\nHedef Süre: {target_duration}s",
                "word_target": target_words,
            },
            "visual_director": {
                "role": "visual_director",
                "prompt": f"{cls.get_role_instructions('director', lang)}\nSafe-Zone ve Punch-In kurallarına dikkat et.",
            },
        }


def detect_punch_in_cues(
    words_or_text: Any,
    max_cues: int = 4,
    min_gap_sec: float = 2.5,
    min_gap_seconds: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """
    Scans word boundary timings or raw text for high-impact keywords (money, secret, viral, şok, sır).
    Generates punch-in center zoom windows (1.2s to 1.5s) and SFX cue timestamps (ai-content-studio pattern).
    """
    if min_gap_seconds is not None:
        min_gap_sec = min_gap_seconds

    cues: List[Dict[str, Any]] = []

    # If input is a list of word timing dicts: [{'word': ..., 'start': ..., 'end': ...}]
    if isinstance(words_or_text, list) and words_or_text and isinstance(words_or_text[0], dict):
        last_cue_start = -10.0
        last_cue_end = -10.0
        for w_info in words_or_text:
            raw_word = str(w_info.get("word") or "").strip()
            norm_word = raw_word.replace("İ", "i").replace("I", "ı").lower()
            clean_word = re.sub(r"[^\w]", "", norm_word)
            if clean_word in ALL_HIGH_IMPACT:
                w_start = float(w_info.get("start", 0.0))
                # Ensure minimum separation from previous cue start and prevent overlap
                if (w_start - last_cue_start >= min_gap_sec) and (w_start >= last_cue_end):
                    p_start = max(0.0, w_start - 0.15)
                    p_end = p_start + 1.25
                    cues.append({
                        "word": w_info.get("word", clean_word),
                        "start": round(p_start, 2),
                        "end": round(p_end, 2),
                        "sfx_timestamp": round(w_start, 2),
                        "zoom_ratio": 1.15,
                        "sfx_type": "swoosh",
                    })
                    last_cue_start = w_start
                    last_cue_end = p_end
                    if len(cues) >= max_cues:
                        break
        return cues

    # If input is plain string, search for matches and estimate relative timeline
    text = str(words_or_text or "").lower()
    words = re.findall(r"\b\w+\b", text)
    if not words:
        return []

    word_dur_estimate = 0.35  # ~170 wpm average
    last_cue_end = -10.0
    for idx, w in enumerate(words):
        if w in ALL_HIGH_IMPACT:
            w_start = idx * word_dur_estimate
            if w_start - last_cue_end >= min_gap_sec:
                p_start = max(0.0, w_start - 0.1)
                p_end = p_start + 1.2
                cues.append({
                    "word": w,
                    "start": round(p_start, 2),
                    "end": round(p_end, 2),
                    "sfx_timestamp": round(w_start, 2),
                    "zoom_ratio": 1.15,
                    "sfx_type": "swoosh",
                })
                last_cue_end = p_end
                if len(cues) >= max_cues:
                    break

    return cues


class FilterComplexResult(str):
    """String object representing FFmpeg filter syntax, unpackable as (filter_str, out_label)."""
    def __new__(cls, filter_str: str, out_label: str):
        obj = super().__new__(cls, filter_str)
        obj.output_label = out_label
        return obj

    def __iter__(self):
        yield str(self)
        yield self.output_label


def build_punch_in_filter(
    punch_cues: List[Dict[str, Any]],
    input_label: str = "vlook",
    output_label: str = "vpunch",
    width: int = 1080,
    height: int = 1920,
) -> FilterComplexResult:
    """
    Constructs single-pass FFmpeg filter_complex syntax for 15% center punch-ins on high impact words.
    Uses split + crop + scale + overlay enable='between(...)' without extra sub-processes.
    """
    if not punch_cues:
        return FilterComplexResult("", input_label)

    clauses = [f"between(t,{c['start']:.2f},{c['end']:.2f})" for c in punch_cues]
    enable_expr = " + ".join(clauses)

    # 15% center crop: iw*0.87 : ih*0.87 centered, scaled back to original resolution
    filter_str = (
        f"[{input_label}]split=2[base_v][punch_v];"
        f"[punch_v]crop=iw*0.87:ih*0.87:(iw-iw*0.87)/2:(ih-ih*0.87)/2,"
        f"scale={width}:{height}[zoomed_v];"
        f"[base_v][zoomed_v]overlay=0:0:enable='{enable_expr}':eof_action=pass[{output_label}]"
    )
    return FilterComplexResult(filter_str, output_label)

