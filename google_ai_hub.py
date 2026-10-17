"""
Google AI Pro Hub — model catalog, quotas/plan, image (Nano Banana), video (Veo), text.
Uses Gemini Developer API (generativelanguage.googleapis.com) with GEMINI_API_KEY.
"""
from __future__ import annotations

import base64
import os
import time
from typing import Any, Dict, List, Optional, Tuple

import requests

import config
from services.google_ai_helpers import (
    GEMINI_BASE,
    GEMINI_TTS_VOICE_MAP,
    _api_key,
    _extract_veo_file,
    generate_gemini_tts_wav,
    generate_image_bytes,
    generate_veo_video,
    resolve_gemini_tts_voice,
    save_generated_image,
)

# Curated catalog — capabilities the user should see in Settings (Google AI Pro / paid API)
GOOGLE_AI_CATALOG: List[Dict[str, Any]] = [
    # Text / script
    {"id": "gemini-3.1-pro-preview", "name": "Gemini 3.1 Pro", "family": "text",
     "use": "Senaryo, derin araştırma, karmaşık kanca yazımı", "tier": "pro", "pro_benefit": True},
    {"id": "gemini-3.5-flash", "name": "Gemini 3.5 Flash", "family": "text",
     "use": "Hızlı senaryo + SEO (önerilen günlük üretim)", "tier": "pro", "pro_benefit": True},
    {"id": "gemini-3.5-flash-lite", "name": "Gemini 3.5 Flash-Lite", "family": "text",
     "use": "Ultra hızlı / düşük kota senaryo", "tier": "free_or_pro", "pro_benefit": False},
    {"id": "gemini-3.1-flash-lite", "name": "Gemini 3.1 Flash-Lite", "family": "text",
     "use": "Ekonomik metin üretimi", "tier": "free_or_pro", "pro_benefit": False},
    {"id": "gemini-flash-lite-latest", "name": "Gemini Flash Lite (Latest)", "family": "text",
     "use": "Alias — en güncel lite model", "tier": "free_or_pro", "pro_benefit": False},
    {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash", "family": "text",
     "use": "Stabil kısa senaryo", "tier": "free_or_pro", "pro_benefit": False},
    {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro", "family": "text",
     "use": "Yüksek kalite uzun form", "tier": "pro", "pro_benefit": True},
    # Image — Nano Banana family
    {"id": "gemini-3.1-flash-image", "name": "Nano Banana 2 (Flash Image)", "family": "image",
     "use": "Sahne B-roll / thumbnail 9:16 görsel (önerilen)", "tier": "pro", "pro_benefit": True},
    {"id": "gemini-3.1-flash-lite-image", "name": "Nano Banana 2 Lite", "family": "image",
     "use": "Hızlı ucuz görsel", "tier": "pro", "pro_benefit": True},
    {"id": "gemini-3-pro-image", "name": "Nano Banana Pro", "family": "image",
     "use": "4K stüdyo kalitesi, metin render", "tier": "pro", "pro_benefit": True},
    {"id": "gemini-2.5-flash-image", "name": "Nano Banana (2.5 Flash Image)", "family": "image",
     "use": "Legacy görsel üretimi", "tier": "pro", "pro_benefit": True},
    # Video — Veo
    {"id": "veo-3.1-fast-generate-preview", "name": "Veo 3.1 Fast", "family": "video",
     "use": "Hızlı sinematik klip + ses (Shorts B-roll)", "tier": "paid", "pro_benefit": True},
    {"id": "veo-3.1-lite-generate-preview", "name": "Veo 3.1 Lite", "family": "video",
     "use": "En ekonomik video üretimi", "tier": "paid", "pro_benefit": True},
    {"id": "veo-3.1-generate-preview", "name": "Veo 3.1 Standard", "family": "video",
     "use": "Yüksek kalite video + senkron ses", "tier": "paid", "pro_benefit": True},
    # Audio / TTS / Live (awareness — may require specific endpoints)
    {"id": "gemini-2.5-flash-preview-tts", "name": "Gemini Flash TTS", "family": "tts",
     "use": "Google native TTS (Edge-TTS alternatifi)", "tier": "pro", "pro_benefit": True},
    {"id": "gemini-2.5-flash-native-audio-latest", "name": "Gemini Native Audio", "family": "audio",
     "use": "Canlı/sesli etkileşim (ileri özellik)", "tier": "pro", "pro_benefit": True},
    # Embeddings / utility
    {"id": "text-embedding-004", "name": "Text Embedding 004", "family": "embed",
     "use": "Semantik stok eşleştirme / benzerlik", "tier": "free_or_pro", "pro_benefit": False},
    {"id": "gemini-embedding-001", "name": "Gemini Embedding", "family": "embed",
     "use": "Gelişmiş embedding", "tier": "pro", "pro_benefit": True},
]

PLAN_INFO = {
    "google_ai_pro": {
        "title": "Google AI Plus / Pro — abonelik ≠ API",
        "blurb": (
            "Google AI Plus (gemini.google.com) uygulama içi görsel/senaryo kotası verir; bu stüdyo "
            "o kotayı kullanamaz. Stüdyo yalnızca GEMINI_API_KEY ile generativelanguage.googleapis.com "
            "Developer API'yi çağırır — tüketici abonelik kotası buraya aktarılmaz, OAuth ile Plus "
            "faturasına bağlama resmi olarak yok. AI Studio'da Plus plan bağlama da yok (Pro/Ultra "
            "için var; fayda sadece AI Studio web arayüzünde). Görsel API modelleri ücretsiz katmanda "
            "yok; kullanırsan pay-as-you-go faturalandırma gerekir. Varsayılan: stok video."
        ),
        "tips": [
            "Plus görsel kotası → gemini.google.com uygulaması; stüdyo API ile ayrı faturalandırma",
            "aistudio.google.com → API key (aynı hesap) → isteğe bağlı billing aç (görsel için gerekli)",
            "Pro/Ultra: AI Studio Playground'da yüksek kota — dış uygulama (bu stüdyo) hariç",
            "Senaryo (ücretsiz API): gemini-flash-lite-latest veya gemini-3.5-flash",
            "Görsel (opsiyonel, ücretli): Ayarlar → Gemini görsel üretimi kutusu + billing",
            "Stok önerilir: Pexels/Pixabay/Coverr — USE_GEMINI_IMAGE_GEN=false (varsayılan)",
        ],
        "subscription_vs_api": {
            "plus_app_quota": "gemini.google.com chat/görsel — stüdyoya aktarılmaz",
            "ai_studio_ui": "Pro/Ultra → AI Studio web kotası; Plus plan linking yok",
            "developer_api": "GEMINI_API_KEY → proje billing tier; pay-as-you-go görsel",
            "oauth": "Resmi OAuth GCP projesi içindir; Plus abonelik faturasına bağlanmaz",
        },
    }
}


def list_live_models() -> Dict[str, Any]:
    """Fetch models available to the current API key."""
    key = _api_key()
    if not key:
        return {"ok": False, "error": "GEMINI_API_KEY yok", "models": [], "catalog": GOOGLE_AI_CATALOG}

    try:
        r = requests.get(f"{GEMINI_BASE}/models?key={key}", timeout=12)
        if r.status_code != 200:
            return {
                "ok": False,
                "error": f"HTTP {r.status_code}: {r.text[:200]}",
                "models": [],
                "catalog": GOOGLE_AI_CATALOG,
            }
        raw = r.json().get("models") or []
        models = []
        for m in raw:
            name = (m.get("name") or "").replace("models/", "")
            methods = m.get("supportedGenerationMethods") or []
            models.append({
                "id": name,
                "display_name": m.get("displayName") or name,
                "description": (m.get("description") or "")[:220],
                "methods": methods,
                "input_token_limit": m.get("inputTokenLimit"),
                "output_token_limit": m.get("outputTokenLimit"),
            })
        # Merge: mark which catalog entries are live
        live_ids = {x["id"] for x in models}
        catalog = []
        for c in GOOGLE_AI_CATALOG:
            row = dict(c)
            row["available"] = c["id"] in live_ids or any(
                c["id"] in lid or lid.startswith(c["id"].split("-preview")[0]) for lid in live_ids
            )
            catalog.append(row)
        # Also expose unknown live models (user might have new ones)
        known = {c["id"] for c in GOOGLE_AI_CATALOG}
        extras = [m for m in models if m["id"] not in known]
        return {
            "ok": True,
            "models": models,
            "catalog": catalog,
            "extras": extras[:40],
            "count": len(models),
            "plan": PLAN_INFO["google_ai_pro"],
            "selected": {
                "script": getattr(config, "GEMINI_MODEL", ""),
                "image": getattr(config, "GEMINI_IMAGE_MODEL", "gemini-3.1-flash-image"),
                "video": getattr(config, "GEMINI_VIDEO_MODEL", "veo-3.1-fast-generate-preview"),
                "tts": getattr(config, "GEMINI_TTS_MODEL", "gemini-2.5-flash-preview-tts"),
            },
            "flags": {
                "use_gemini_images": getattr(config, "USE_GEMINI_IMAGE_GEN", False),
                "use_gemini_video": getattr(config, "USE_GEMINI_VIDEO_GEN", False),
                "prefer_gemini_over_stock": getattr(config, "PREFER_GEMINI_SCENE_IMAGES", False),
            },
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "models": [], "catalog": GOOGLE_AI_CATALOG}


def get_plan_and_quota_snapshot() -> Dict[str, Any]:
    """Combine catalog + live models + local quota_manager stats for UI."""
    live = list_live_models()
    quota = {}
    try:
        from quota_manager import quota_manager
        quota = quota_manager.get_stats(force_live=True)
    except Exception as e:
        quota = {"error": str(e)}

    gemini_card = {}
    try:
        cards = quota.get("provider_cards") or {}
        gemini_card = cards.get("Gemini") or {}
    except Exception:
        pass

    families = {"text": 0, "image": 0, "video": 0, "tts": 0, "audio": 0, "embed": 0}
    for c in live.get("catalog") or []:
        if c.get("available"):
            families[c.get("family", "text")] = families.get(c.get("family", "text"), 0) + 1

    return {
        "ok": live.get("ok", False),
        "plan": PLAN_INFO["google_ai_pro"],
        "has_api_key": bool(_api_key()),
        "live_model_count": live.get("count", 0),
        "families_available": families,
        "catalog": live.get("catalog") or GOOGLE_AI_CATALOG,
        "extras": live.get("extras") or [],
        "selected": live.get("selected") or {},
        "flags": live.get("flags") or {},
        "quota": {
            "rpm_used": gemini_card.get("rpm_used"),
            "rpm_limit": gemini_card.get("rpm_limit"),
            "rpd_used": gemini_card.get("daily_used") or gemini_card.get("rpd_used"),
            "rpd_limit": gemini_card.get("rpd_limit"),
            "remaining": gemini_card.get("remaining_calls"),
            "status": gemini_card.get("status_label") or gemini_card.get("status_note"),
            "live_note": (quota.get("live_api") or {}).get("Gemini") or gemini_card.get("live") or {},
            "raw_card": gemini_card,
        },
        "error": live.get("error"),
        "benefits_checklist": [
            {"id": "script", "label": "Senaryo (Flash / Pro)", "enabled": True},
            {"id": "image", "label": "Nano Banana görsel üretimi", "enabled": getattr(config, "USE_GEMINI_IMAGE_GEN", False)},
            {"id": "video", "label": "Veo video üretimi", "enabled": getattr(config, "USE_GEMINI_VIDEO_GEN", False)},
            {"id": "tts", "label": "Gemini TTS (deneysel)", "enabled": getattr(config, "USE_GEMINI_TTS", False)},
            {"id": "grounding", "label": "Google Search grounding", "enabled": getattr(config, "USE_GEMINI_GROUNDING", False)},
            {"id": "embed", "label": "Embedding ile stok skorlama", "enabled": getattr(config, "USE_GEMINI_EMBEDDINGS", False)},
        ],
    }


def generate_text(prompt: str, model: Optional[str] = None, system: str = "") -> Tuple[bool, str]:
    key = _api_key()
    if not key:
        return False, "GEMINI_API_KEY yok"
    model = model or getattr(config, "GEMINI_MODEL", "gemini-flash-lite-latest")
    body: Dict[str, Any] = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
    }
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    if getattr(config, "USE_GEMINI_GROUNDING", False):
        body["tools"] = [{"google_search": {}}]

    url = f"{GEMINI_BASE}/models/{model}:generateContent?key={key}"
    try:
        r = requests.post(url, json=body, timeout=90)
        if r.status_code != 200:
            return False, f"HTTP {r.status_code}: {r.text[:400]}"
        data = r.json()
        parts = (((data.get("candidates") or [{}])[0].get("content") or {}).get("parts") or [])
        text = "".join(p.get("text", "") for p in parts if "text" in p)
        try:
            from quota_manager import quota_manager
            quota_manager.record_call("Gemini")
            usage = data.get("usageMetadata") or {}
            quota_manager.record_token_usage(
                "Gemini",
                prompt_tokens=int(usage.get("promptTokenCount") or 0),
                completion_tokens=int(usage.get("candidatesTokenCount") or 0),
            )
        except Exception:
            pass
        return True, text.strip()
    except Exception as e:
        return False, str(e)


def embed_text(text: str, model: Optional[str] = None) -> Tuple[bool, Any]:
    """
    R10 #39: Gemini text embeddings for semantic stock matching.
    Returns (ok, vector_list) or (False, error_string).
    """
    key = _api_key()
    if not key:
        return False, "GEMINI_API_KEY yok"
    plain = (text or "").strip()
    if not plain:
        return False, "empty text"
    model = model or "text-embedding-004"
    url = f"{GEMINI_BASE}/models/{model}:embedContent?key={key}"
    body = {
        "model": f"models/{model}",
        "content": {"parts": [{"text": plain[:2048]}]},
    }
    try:
        r = requests.post(url, json=body, timeout=45)
        if r.status_code != 200:
            return False, f"HTTP {r.status_code}: {r.text[:300]}"
        data = r.json()
        values = ((data.get("embedding") or {}).get("values")) or []
        if not values:
            values = (((data.get("embeddings") or [{}])[0]).get("values")) or []
        if not values:
            return False, "empty embedding"
        return True, list(values)
    except Exception as e:
        return False, str(e)
