"""
R10 #73 / ROADMAP #454-adjacent: Translate narration plan + prepare re-TTS dub pack.

Auto YouTube upload remains out of scope — this produces a render-ready language pack.
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

# Minimal offline glossary for TR→EN smoke paths when LLM unavailable
_TR_EN_GLOSS = {
    "merhaba": "hello",
    "gerçek": "truth",
    "gizli": "secret",
    "inanılmaz": "incredible",
    "dikkat": "warning",
    "son": "end",
    "başla": "start",
    "neden": "why",
    "nasıl": "how",
    "kimse": "nobody",
}


def _simple_glossary_translate(text: str, target_lang: str) -> str:
    if (target_lang or "").lower().startswith("en"):
        out = text
        for tr, en in _TR_EN_GLOSS.items():
            out = re.sub(rf"\b{re.escape(tr)}\b", en, out, flags=re.IGNORECASE)
        return out
    return text


def translate_text(text: str, source_lang: str = "tr", target_lang: str = "en") -> str:
    """Translate a single string via Gemini when available, else glossary fallback."""
    plain = (text or "").strip()
    if not plain:
        return ""
    src = (source_lang or "tr").lower()[:2]
    tgt = (target_lang or "en").lower()[:2]
    if src == tgt:
        return plain
    try:
        import config
        from google_ai_hub import generate_text

        if getattr(config, "GEMINI_API_KEY", ""):
            prompt = (
                f"Translate from {src} to {tgt}. Keep Shorts narration punchy. "
                f"Return ONLY the translation, no quotes.\n\n{plain}"
            )
            ok, out = generate_text(prompt)
            if ok and out and isinstance(out, str) and len(out.strip()) > 2:
                return out.strip().strip('"')
    except Exception:
        pass
    return _simple_glossary_translate(plain, tgt)


def build_dubbing_pack(
    scenes: List[Dict[str, Any]],
    source_lang: str = "tr",
    target_lang: str = "en",
    title: str = "",
) -> Dict[str, Any]:
    """
    R10 #73: Build a multi-language dub pack — translated narrations ready for re-TTS.
    """
    dubbed_scenes: List[Dict[str, Any]] = []
    for i, sc in enumerate(scenes or []):
        narr = (sc.get("narration") or sc.get("text") or "").strip()
        translated = translate_text(narr, source_lang, target_lang) if narr else ""
        dubbed_scenes.append({
            "index": i,
            "source_narration": narr,
            "dubbed_narration": translated,
            "duration": sc.get("duration"),
            "search_queries": sc.get("search_queries") or [],
        })
    titled = translate_text(title, source_lang, target_lang) if title else ""
    return {
        "rule": "r10_73_dubbing",
        "source_lang": source_lang,
        "target_lang": target_lang,
        "title_source": title,
        "title_dubbed": titled,
        "scene_count": len(dubbed_scenes),
        "scenes": dubbed_scenes,
        "tts_instruction": (
            f"Set config.LANGUAGE={target_lang} and re-run TTS on dubbed_narration fields; "
            "visuals can be reused."
        ),
        "upload_note": "Manual Studio upload — auto publish out of scope.",
    }


def apply_dubbing_to_plan(plan: Dict[str, Any], target_lang: str = "en") -> Dict[str, Any]:
    """Mutate a scene plan dict in-place-ish (returns new dict) with dubbed narrations."""
    src_lang = (plan.get("language") or plan.get("lang") or "tr")
    scenes = plan.get("scenes") or []
    pack = build_dubbing_pack(scenes, source_lang=src_lang, target_lang=target_lang, title=plan.get("title", ""))
    new_scenes = []
    for sc, dub in zip(scenes, pack["scenes"]):
        merged = dict(sc)
        merged["narration_source"] = sc.get("narration")
        merged["narration"] = dub["dubbed_narration"] or sc.get("narration")
        new_scenes.append(merged)
    out = dict(plan)
    out["scenes"] = new_scenes
    out["language"] = target_lang
    out["dubbing"] = {
        "source_lang": src_lang,
        "target_lang": target_lang,
        "title_dubbed": pack.get("title_dubbed"),
    }
    if pack.get("title_dubbed"):
        out["title"] = pack["title_dubbed"]
    return out
