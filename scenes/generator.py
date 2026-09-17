"""
Core scene generator with multi-provider AI fallback and post-processing filters.
"""

import json
import re
from openai import OpenAI
import config
from .prompts import get_rotated_system_prompt, PROMPT_TR, PROMPT_EN
from .fallback import _generate_procedural_fallback_scenes
from .enrichment import (
    enrich_cinematic_search_queries,
    enforce_visual_cadence_14
)


def _call(client, params):
    try:
        return client.chat.completions.create(**params)
    except Exception as e:
        if "response_format" in params:
            del params["response_format"]
            return client.chat.completions.create(**params)
        raise e


def _clean_json(text):
    if not text:
        return None
    text = re.sub(r'//.*?\n', '\n', text)
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
    text = re.sub(r',\s*([}\]])', r'\1', text)
    try:
        return json.loads(text)
    except Exception:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                pass
    return None


def generate_scenes(title: str, niche_type: str = None, language: str = None) -> dict:
    lang = language or getattr(config, "LANGUAGE", "tr")
    if niche_type:
        try:
            from niche_templates import get_niche_prompt
            prompt = get_niche_prompt(niche_type, title, language=lang)
        except Exception:
            prompt = get_rotated_system_prompt(base_lang=lang)
    else:
        prompt = get_rotated_system_prompt(base_lang=lang)

    if lang == "en":
        user_msg = (
            f"Create a high-retention English YouTube Shorts video script for this topic: '{title}'.\n"
            f"CRITICAL REQUIREMENT: The 'narration' field in ALL 14 scenes MUST be written 100% in fluent, natural ENGLISH. "
            f"Do NOT output Turkish narration. Translate and adapt the topic into an immersive English script."
        )
    else:
        user_msg = f"Bu başlık için Türkçe YouTube Shorts senaryosu oluştur: '{title}'"

    # Build fallback provider chain
    providers = []
    # Primary configured provider first
    if getattr(config, "AI_PROVIDER", None) and getattr(config, "AI_API_KEY", None):
        providers.append((config.AI_PROVIDER, config.AI_API_KEY, config.AI_BASE_URL, config.AI_MODEL))
        # If Gemini, add lite and flash variants as instant fallbacks
        if config.AI_PROVIDER == "Gemini":
            for alt_m in ["gemini-flash-lite-latest", "gemma-4-26b-a4b-it", "gemini-3.6-flash"]:
                if alt_m != config.AI_MODEL:
                    providers.append(("Gemini (" + alt_m + ")", config.AI_API_KEY, config.AI_BASE_URL, alt_m))

    # Other available providers in config._P
    if hasattr(config, "_P"):
        for n, k, u, m in config._P:
            if k and (n != getattr(config, "AI_PROVIDER", None)):
                providers.append((n, k, u, m))

    last_error = None
    data = None

    for provider_name, api_key, base_url, model_name in providers:
        print(f"  [{provider_name}] Senaryo üretiliyor: '{title}'")
        try:
            client = OpenAI(api_key=api_key, base_url=base_url)
            params = dict(
                model=model_name,
                messages=[{"role": "system", "content": prompt}, {"role": "user", "content": user_msg}],
                temperature=0.7, max_tokens=4000,
            )
            if "Gemini" in provider_name or "OpenAI" in provider_name:
                params["response_format"] = {"type": "json_object"}

            resp = _call(client, params)
            raw = resp.choices[0].message.content.strip()
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0].strip()

            data = _clean_json(raw)
            if not data:
                print(f"  [{provider_name}] JSON ayrıştırma başarısız, retrying...")
                params["temperature"] = 0.3
                resp2 = _call(client, params)
                raw2 = resp2.choices[0].message.content.strip()
                if "```" in raw2:
                    raw2 = raw2.split("```json")[-1].split("```")[0].strip() if "```json" in raw2 else raw2.split("```")[1].split("```")[0].strip()
                data = _clean_json(raw2)

            if data and "scenes" in data and len(data["scenes"]) > 0:
                print(f"  [{provider_name}] OK: Senaryo basariyla uretildi")
                break
        except Exception as e:
            print(f"  [UYARI] {provider_name} servisi hata verdi: {e}. Sıradaki AI modeline/sağlayıcısına geçiliyor...")
            last_error = e

    if not data or not data.get("scenes"):
        print(f"  [BİLGİ] AI servisleri yanıt vermedi ({last_error}). Akıllı Prosedürel Senaryo Motoru devreye alındı.")
        data = _generate_procedural_fallback_scenes(title, niche_type=niche_type, language=lang)

    for s in data.get("scenes", []):
        if "search_query" in s and "search_queries" not in s:
            q = s.pop("search_query")
            w = q.split()
            s["search_queries"] = [q, " ".join(w[:2]) if len(w) > 2 else q, w[0] if w else "nature"]
        if "scene_description" not in s:
            s["scene_description"] = s.get("search_queries", ["nature"])[0]

        # Enrich search queries with cinematic adjectives (Item 89)
        if "search_queries" in s:
            s["search_queries"] = enrich_cinematic_search_queries(s["search_queries"], mood=s.get("mood", "epic"))

    # Enforce optimal Shorts duration: 38-48s (Madde 494)
    target_total = 42.0
    if len(data["scenes"]) >= 14:
        for s in data["scenes"]:
            s["duration"] = 3.0
    else:
        current_total = sum(s.get("duration", 3.0) for s in data["scenes"])
        if current_total <= 0:
            current_total = len(data["scenes"]) * 3.0
        scale = target_total / current_total
        for s in data["scenes"]:
            s["duration"] = round(max(1.8, min(8.0, s.get("duration", 3.0) * scale)), 1)

    # Apply 14 visual cuts cadence if eligible (Madde 88)
    data["scenes"] = enforce_visual_cadence_14(data["scenes"], min_cadence=14)

    # Final normalization to ensure 38-48s compliance (Madde 494)
    total = sum(s["duration"] for s in data["scenes"])
    if total < 38.0 or total > 48.0:
        per_scene = round(42.0 / max(1, len(data["scenes"])), 1)
        for s in data["scenes"]:
            s["duration"] = per_scene

    total = sum(s["duration"] for s in data["scenes"])
    print(f"  [SceneGenerator] Sahne Sayısı: {len(data['scenes'])}, Toplam Süre: {total}s | Tema: {data.get('visual_theme', '-')}")
    return data
