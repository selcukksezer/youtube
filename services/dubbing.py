"""
R10 #73 / ROADMAP #454-adjacent: Translate narration plan + prepare re-TTS dub pack.

Auto YouTube upload remains out of scope — this produces a render-ready language pack.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class DubbingTranslationError(RuntimeError):
    """Raised when a requested narration translation cannot be produced."""


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


_DEEPL_LANG_MAP = {
    "tr": "TR",
    "en": "EN-US",
    "de": "DE",
    "fr": "FR",
    "es": "ES",
    "it": "IT",
    "pt": "PT-BR",
    "ru": "RU",
    "ja": "JA",
    "ko": "KO",
    "zh": "ZH",
    "ar": "AR",
    "nl": "NL",
    "pl": "PL",
}


def translate_via_deepl(
    text: str,
    source_lang: str = "tr",
    target_lang: str = "en",
    api_key: Optional[str] = None,
) -> Optional[str]:
    """
    Item 454: Translate narration string via DeepL REST API v2.
    Automatically selects api-free.deepl.com when the key ends with ':fx'.
    Returns None when key is missing or request fails so caller can fall back.
    """
    plain = (text or "").strip()
    if not plain:
        return ""
    try:
        import config
        import requests

        key = (api_key if api_key is not None else getattr(config, "DEEPL_API_KEY", "")).strip()
        if not key:
            return None
        endpoint = (getattr(config, "DEEPL_API_URL", "") or "").strip()
        if not endpoint:
            host = "https://api-free.deepl.com" if key.endswith(":fx") else "https://api.deepl.com"
            endpoint = f"{host}/v2/translate"

        src_code = _DEEPL_LANG_MAP.get((source_lang or "tr").lower()[:2], (source_lang or "TR").upper()[:2])
        if src_code.startswith("EN"):
            src_code = "EN"
        elif src_code.startswith("PT"):
            src_code = "PT"
        tgt_raw = (target_lang or "en").lower()[:2]
        tgt_code = _DEEPL_LANG_MAP.get(tgt_raw, tgt_raw.upper())

        resp = requests.post(
            endpoint,
            headers={
                "Authorization": f"DeepL-Auth-Key {key}",
                "Content-Type": "application/json",
            },
            json={
                "text": [plain],
                "source_lang": src_code,
                "target_lang": tgt_code,
            },
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            translations = data.get("translations") or []
            if translations and isinstance(translations[0], dict):
                translated = str(translations[0].get("text") or "").strip()
                if translated:
                    return translated
        logger.warning("DeepL translate HTTP %s: %s", resp.status_code, resp.text[:160])
    except Exception as exc:
        logger.warning("DeepL translate failed: %s", exc)
    return None


def translate_text(
    text: str,
    source_lang: str = "tr",
    target_lang: str = "en",
    strict: bool = False,
) -> str:
    """Translate a single string via DeepL (#454) -> Gemini -> glossary fallback."""
    plain = (text or "").strip()
    if not plain:
        return ""
    src = (source_lang or "tr").lower()[:2]
    tgt = (target_lang or "en").lower()[:2]
    if src == tgt:
        return plain

    # 1. Try DeepL (#454) when DEEPL_API_KEY is configured
    deepl_out = translate_via_deepl(plain, source_lang=src, target_lang=tgt)
    if deepl_out:
        return deepl_out

    try:
        import os
        import config
        from google_ai_hub import generate_text

        is_mocked_gen = (
            hasattr(generate_text, "_mock_name")
            or "unittest.mock" in type(generate_text).__module__
        )
        if not getattr(config, "GEMINI_API_KEY", "") or (
            not strict
            and (
                os.environ.get("PYTEST_CURRENT_TEST")
                or os.environ.get("SHORTS_FORCE_PROCEDURAL_FALLBACK") == "1"
            )
            and not is_mocked_gen
        ):
            if strict:
                raise DubbingTranslationError("Gemini/DeepL API anahtarı yapılandırılmamış.")
            return _simple_glossary_translate(plain, tgt)
        prompt = (
            f"Translate from {src} to {tgt}. Keep Shorts narration punchy. "
            f"Return ONLY the translation, no quotes.\n\n{plain}"
        )
        ok, out = generate_text(prompt)
        if ok and out and isinstance(out, str) and len(out.strip()) > 2:
            return out.strip().strip('"')
        if strict:
            raise DubbingTranslationError("Gemini geçerli bir çeviri döndürmedi.")
    except DubbingTranslationError:
        raise
    except Exception as exc:
        logger.warning("dubbing translate fallback to glossary: %s", exc)
        if strict:
            raise DubbingTranslationError("Gemini çevirisi başarısız oldu.") from exc
    if strict:
        raise DubbingTranslationError("Gemini geçerli bir çeviri döndürmedi.")
    return _simple_glossary_translate(plain, tgt)


def _active_translation_provider() -> str:
    try:
        import config
        if getattr(config, "DEEPL_API_KEY", ""):
            return "deepl"
        if getattr(config, "GEMINI_API_KEY", ""):
            return "gemini"
    except Exception:
        pass
    return "glossary"


def build_dubbing_pack(
    scenes: List[Dict[str, Any]],
    source_lang: str = "tr",
    target_lang: str = "en",
    title: str = "",
    strict: bool = False,
) -> Dict[str, Any]:
    """
    R10 #73 / Item #454: Build a multi-language dub pack — translated narrations ready for re-TTS.
    """
    dubbed_scenes: List[Dict[str, Any]] = []
    for i, sc in enumerate(scenes or []):
        narr = (sc.get("narration") or sc.get("text") or "").strip()
        translated = translate_text(narr, source_lang, target_lang, strict=strict) if narr else ""
        dubbed_scenes.append({
            "index": i,
            "source_narration": narr,
            "dubbed_narration": translated,
            "duration": sc.get("duration"),
            "search_queries": sc.get("search_queries") or [],
        })
    titled = translate_text(title, source_lang, target_lang, strict=strict) if title else ""
    return {
        "rule": "r10_73_dubbing",
        "translation_provider": _active_translation_provider(),
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


def apply_dubbing_to_plan(
    plan: Dict[str, Any],
    target_lang: str = "en",
    strict: bool = False,
) -> Dict[str, Any]:
    """Mutate a scene plan dict in-place-ish (returns new dict) with dubbed narrations."""
    src_lang = (plan.get("language") or plan.get("lang") or "tr")
    scenes = plan.get("scenes") or []
    pack = build_dubbing_pack(
        scenes,
        source_lang=src_lang,
        target_lang=target_lang,
        title=plan.get("title", ""),
        strict=strict,
    )
    new_scenes = []
    for sc, dub in zip(scenes, pack["scenes"]):
        merged = dict(sc)
        merged["narration_source"] = sc.get("narration_source") or sc.get("narration") or sc.get("text")
        merged["narration_source_lang"] = sc.get("narration_source_lang") or src_lang
        merged["narration"] = dub["dubbed_narration"] or sc.get("narration")
        new_scenes.append(merged)
    out = dict(plan)
    out["scenes"] = new_scenes
    out["language"] = target_lang
    out["full_narration"] = " ".join(
        str(scene.get("narration") or "").strip()
        for scene in new_scenes
        if scene.get("narration")
    )
    out["dubbing"] = {
        "source_lang": src_lang,
        "target_lang": target_lang,
        "translation_provider": pack.get("translation_provider", "glossary"),
        "title_source": plan.get("title", ""),
        "title_dubbed": pack.get("title_dubbed"),
    }
    if pack.get("title_dubbed"):
        out["title"] = pack["title_dubbed"]
    return out
