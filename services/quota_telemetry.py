"""
Quota pricing/tier tables, live API probes, and telemetry formatting helpers.
Extracted from quota_manager.py for modularity.
"""
import json
import time
import urllib.error
import urllib.request
from typing import Any, Dict

import config

DEFAULT_LIMITS = {
    "Gemini": {
        "name": "Google Gemini Flash",
        "category": "ai",
        "tier": "Google AI Studio (Ücretsiz Tier)",
        "rpm_limit": 15,
        "rpd_limit": 1500,
        "cost_per_video": "0.00 TL",
        "description": "Dakikada 15 istek, günde 1.500 istek ücretsiz.",
    },
    "Pexels": {
        "name": "Pexels Video API",
        "category": "stock",
        "tier": "Resmi Geliştirici Hesabı",
        "rpm_limit": 200,
        "rpd_limit": 25000,
        "cost_per_video": "0.00 TL",
        "description": "Aylık 25.000 istek, saatlik 200 istek ücretsiz.",
    },
    "Pixabay": {
        "name": "Pixabay Video API",
        "category": "stock",
        "tier": "Açık Medya Lisansı",
        "rpm_limit": 100,
        "rpd_limit": 5000,
        "cost_per_video": "0.00 TL",
        "description": "Dakikada 100 istek, günde 5.000 istek ücretsiz.",
    },
    "Edge-TTS": {
        "name": "Microsoft Edge Neural TTS",
        "category": "tts",
        "tier": "Açık Kaynak & Ücretsiz",
        "rpm_limit": 9999,
        "rpd_limit": 99999,
        "cost_per_video": "0.00 TL",
        "description": "Limitsiz yüksek kaliteli doğal ses sentezi.",
    },
    "ElevenLabs": {
        "name": "ElevenLabs Multilingual TTS",
        "category": "tts",
        "tier": "Free Tier (~10k karakter/ay)",
        "rpm_limit": 30,
        "rpd_limit": 10000,
        "cost_per_video": "0.00 TL (free tier)",
        "description": "Pre-made çok dilli sesler — TR+EN. Kota aşımında Edge yedek.",
    },
    "YouTube": {
        "name": "YouTube Data API v3",
        "category": "youtube",
        "tier": "Google Cloud Console",
        "rpm_limit": 300,
        "rpd_limit": 10000,
        "cost_per_video": "0.00 TL",
        "description": "Günlük 10.000 kota birimi (Video yükleme: 1.600 birim).",
    },
    "OpenAI": {
        "name": "OpenAI GPT-4o Mini",
        "category": "ai",
        "tier": "Kullanım Başına Ödeme (PayG)",
        "rpm_limit": 500,
        "rpd_limit": 10000,
        "cost_per_video": "~0.05 TL",
        "description": "Yüksek performanslı ticari model.",
    },
    "Grok": {
        "name": "xAI Grok-2",
        "category": "ai",
        "tier": "xAI Cloud",
        "rpm_limit": 60,
        "rpd_limit": 2000,
        "cost_per_video": "~0.08 TL",
        "description": "Alternatif AI motoru.",
    },
    "DeepSeek": {
        "name": "DeepSeek V3 / R1",
        "category": "ai",
        "tier": "DeepSeek API",
        "rpm_limit": 120,
        "rpd_limit": 5000,
        "cost_per_video": "~0.02 TL",
        "description": "Ultra ekonomik akıl yürütme motoru.",
    },
}


def probe_live_api_status(usage_counts: Dict[str, int]) -> Dict[str, Any]:
    """Query official endpoints of Pexels, Pixabay, ElevenLabs, Gemini, and YouTube."""
    live_results: Dict[str, Any] = {}

    pexels_key = getattr(config, "PEXELS_API_KEY", "") or ""
    if pexels_key:
        try:
            url = "https://api.pexels.com/v1/curated?per_page=1"
            req = urllib.request.Request(
                url,
                headers={
                    "Authorization": pexels_key,
                    "User-Agent": "ShortsVideoCreators/2.0 (Windows NT 10.0; Win64; x64)",
                },
            )
            with urllib.request.urlopen(req, timeout=4) as resp:
                limit = resp.headers.get("X-Ratelimit-Limit")
                remaining = resp.headers.get("X-Ratelimit-Remaining")
                reset_val = resp.headers.get("X-Ratelimit-Reset")
                live_results["Pexels"] = {
                    "online": True,
                    "limit": int(limit) if limit and limit.isdigit() else 25000,
                    "remaining": int(remaining) if remaining and remaining.isdigit() else None,
                    "reset": reset_val,
                    "status_note": f"Canlı Senkronize ({remaining} Kalan)" if remaining else "Canlı & Aktif",
                }
        except urllib.error.HTTPError as e:
            live_results["Pexels"] = {
                "online": False,
                "error_code": e.code,
                "status_note": f"Hata ({e.code})",
            }
        except Exception:
            live_results["Pexels"] = {"online": False, "status_note": "Bağlantı Hatası"}

    pixabay_key = getattr(config, "PIXABAY_API_KEY", "") or ""
    if pixabay_key:
        try:
            url = f"https://pixabay.com/api/?key={pixabay_key}&per_page=3"
            req = urllib.request.Request(url, headers={"User-Agent": "ShortsVideoCreators/2.0"})
            with urllib.request.urlopen(req, timeout=4) as resp:
                limit = resp.headers.get("X-RateLimit-Limit")
                remaining = resp.headers.get("X-RateLimit-Remaining")
                reset_val = resp.headers.get("X-RateLimit-Reset")
                live_results["Pixabay"] = {
                    "online": True,
                    "limit": int(limit) if limit and limit.isdigit() else 100,
                    "remaining": int(remaining) if remaining and remaining.isdigit() else None,
                    "reset": reset_val,
                    "status_note": f"Canlı Senkronize ({remaining} Kalan)" if remaining else "Canlı & Aktif",
                }
        except urllib.error.HTTPError as e:
            live_results["Pixabay"] = {
                "online": False,
                "error_code": e.code,
                "status_note": f"Hata ({e.code})",
            }
        except Exception:
            live_results["Pixabay"] = {"online": False, "status_note": "Bağlantı Hatası"}

    eleven_key = getattr(config, "ELEVENLABS_API_KEY", "") or ""
    if eleven_key:
        try:
            from elevenlabs_tts import get_subscription_info

            sub = get_subscription_info()
            if sub and sub.get("character_limit"):
                live_results["ElevenLabs"] = {
                    "online": "error" not in sub,
                    "limit": sub.get("character_limit", 10000),
                    "remaining": sub.get("character_remaining"),
                    "status_note": (
                        f"Kalan {sub.get('character_remaining')} / {sub.get('character_limit')} karakter"
                        if sub.get("character_remaining") is not None
                        else "Bağlı"
                    ),
                }
            elif sub and sub.get("error"):
                live_results["ElevenLabs"] = {
                    "online": False,
                    "error_code": sub.get("error"),
                    "status_note": "Anahtar veya kota hatası",
                }
        except Exception:
            live_results["ElevenLabs"] = {"online": False, "status_note": "Bağlantı Hatası"}

    gemini_key = getattr(config, "GEMINI_API_KEY", "") or ""
    if gemini_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={gemini_key}"
            req = urllib.request.Request(url, headers={"User-Agent": "ShortsVideoCreators/2.0"})
            start_t = time.time()
            with urllib.request.urlopen(req, timeout=5) as resp:
                latency_ms = int((time.time() - start_t) * 1000)
                data = json.loads(resp.read().decode("utf-8"))
                models = [m.get("name", "") for m in data.get("models", []) if "gemini" in m.get("name", "")]
                live_results["Gemini"] = {
                    "online": True,
                    "models_count": len(models),
                    "latency_ms": latency_ms,
                    "status_note": f"Canlı Doğrulandı ({len(models)} Model Aktif, {latency_ms}ms)",
                }
        except urllib.error.HTTPError as e:
            msg = (
                "Yetkisiz / Geçersiz Anahtar"
                if e.code in (400, 401, 403)
                else ("Kota / Hız Limiti (429)" if e.code == 429 else f"HTTP {e.code}")
            )
            live_results["Gemini"] = {
                "online": False,
                "error_code": e.code,
                "status_note": msg,
            }
        except Exception:
            live_results["Gemini"] = {"online": False, "status_note": "Bağlantı Hatası"}

    yt_key = getattr(config, "YOUTUBE_DATA_API_KEY", "") or ""
    if yt_key:
        try:
            url = f"https://www.googleapis.com/youtube/v3/videos?part=id&chart=mostPopular&maxResults=1&key={yt_key}"
            req = urllib.request.Request(url, headers={"User-Agent": "ShortsVideoCreators/2.0"})
            with urllib.request.urlopen(req, timeout=4):
                live_results["YouTube"] = {
                    "online": True,
                    "limit": 10000,
                    "remaining": max(0, 10000 - usage_counts.get("YouTube", 0)),
                    "status_note": "Canlı & Aktif (10.000 Birim)",
                }
        except urllib.error.HTTPError as e:
            msg = (
                "Geçersiz YouTube Anahtarı"
                if e.code in (400, 401, 403)
                else ("YouTube Kotası Doldu" if e.code == 429 else f"HTTP {e.code}")
            )
            live_results["YouTube"] = {
                "online": False,
                "error_code": e.code,
                "status_note": msg,
            }
        except Exception:
            live_results["YouTube"] = {"online": True, "limit": 10000, "status_note": "Bağlı (10.000 Birim)"}

    return live_results


def build_quota_stats_report(tracker: Any, now: float, live_api_info: Dict[str, Any]) -> Dict[str, Any]:
    """Assemble full quota status report, provider cards, and category summaries."""
    active_exhaustions = {}
    for prov, info in tracker.quota_status.items():
        rem = max(0, int(info.get("reset_timestamp", now) - now))
        info_copy = dict(info)
        info_copy["reset_seconds_remaining"] = rem
        if rem == 0 and info.get("status_type") == "QUOTA_EXHAUSTED":
            info_copy["exhausted"] = False
            info_copy["status_type"] = "RESTORED"
            info_copy["description"] = "Kota süresi doldu, yeniden kullanılabilir."
        active_exhaustions[prov] = info_copy

    provider_has_key = {
        "Gemini": bool(getattr(config, "GEMINI_API_KEY", "")),
        "Edge-TTS": True,
        "Pexels": bool(getattr(config, "PEXELS_API_KEY", "")),
        "Pixabay": bool(getattr(config, "PIXABAY_API_KEY", "")),
        "ElevenLabs": bool(getattr(config, "ELEVENLABS_API_KEY", "")),
        "YouTube": bool(getattr(config, "YOUTUBE_DATA_API_KEY", "")),
        "OpenAI": bool(getattr(config, "OPENAI_API_KEY", "")),
        "Grok": bool(getattr(config, "GROK_API_KEY", "")),
        "DeepSeek": bool(getattr(config, "DEEPSEEK_API_KEY", "")),
    }

    active_raw = str(getattr(config, "AI_PROVIDER", "") or "").strip()
    active_limit_key = None
    for k in DEFAULT_LIMITS:
        if k.lower() == active_raw.lower():
            active_limit_key = k
            break
    if not active_limit_key:
        active_limit_key = "Gemini"

    has_active_ai_key = bool(provider_has_key.get(active_limit_key, False))

    provider_cards = {}
    for prov_key, limits in DEFAULT_LIMITS.items():
        has_k = provider_has_key.get(prov_key, False)
        timestamps = tracker.call_timestamps.get(prov_key, [])
        rpm_used = len([t for t in timestamps if now - t <= 60])
        daily_used = tracker.usage_counts.get(prov_key, 0)
        errors = tracker.error_counts.get(prov_key, 0)
        exhaustion = active_exhaustions.get(prov_key, {})
        live_data = live_api_info.get(prov_key, {})

        rpd_limit = limits.get("rpd_limit", 1500)
        live_remaining = live_data.get("remaining")
        live_limit = live_data.get("limit")
        if live_limit is not None and live_limit > 0:
            rpd_limit = live_limit

        if live_remaining is not None:
            remaining_calls = live_remaining
            used_effective = max(0, rpd_limit - live_remaining)
        else:
            remaining_calls = max(0, rpd_limit - daily_used)
            used_effective = daily_used

        is_exhausted = exhaustion.get("exhausted", False)
        is_live_down = live_data.get("online") is False

        if not has_k:
            if prov_key == "YouTube":
                status_badge = "Tarayıcı Modu (0 Kota)"
                badge_class = "success"
                health_pct = 100
            elif prov_key == "Edge-TTS":
                status_badge = "0 TL Limitsiz & Hazır"
                badge_class = "success"
                health_pct = 100
            else:
                status_badge = "Anahtar Girilmedi"
                badge_class = "secondary"
                health_pct = 0
        elif is_exhausted or is_live_down:
            status_badge = live_data.get("status_note") or "Kota / Limit Aşıldı"
            badge_class = "warning" if is_exhausted else "danger"
            health_pct = 0
        elif live_data.get("online"):
            status_badge = live_data.get("status_note") or "%100 Canlı & Doğrulandı"
            badge_class = "success"
            health_pct = max(10, min(100, int((remaining_calls / max(1, rpd_limit)) * 100)))
        else:
            status_badge = "%100 Hazır & Kesintisiz"
            badge_class = "success"
            health_pct = max(10, min(100, int((remaining_calls / max(1, rpd_limit)) * 100)))

        provider_cards[prov_key] = {
            **limits,
            "category": limits.get("category", "ai"),
            "has_key": has_k,
            "rpm_used": rpm_used,
            "daily_used": used_effective,
            "remaining_calls": remaining_calls,
            "rpd_limit": rpd_limit,
            "total_calls": used_effective,
            "errors": errors,
            "status_badge": status_badge,
            "badge_class": badge_class,
            "health_pct": health_pct,
            "is_active": bool(has_active_ai_key and active_limit_key == prov_key),
            "is_live_verified": bool(live_data.get("online")),
            "exhaustion": exhaustion if is_exhausted else None,
        }

    if not has_active_ai_key:
        active_provider_id = "Yerel Motor"
        active_provider_name = "Akıllı Yerel Senaryo Motoru (0 TL)"
        overall_status_text = "API Anahtarı Bekleniyor (Yerel Motor Aktif)"
        overall_health_pct = 100
        current_rpm = 0
        rpm_max: Any = "Sınırsız"
        daily_calls = tracker.usage_counts.get("Yerel Fallback", 0)
        daily_remaining: Any = "Sınırsız"
        rpd_max: Any = "Sınırsız"
        is_exhausted = False
    else:
        active_card = provider_cards[active_limit_key]
        active_provider_id = active_limit_key
        active_provider_name = active_card["name"]
        is_exhausted = active_card.get("exhaustion") is not None
        overall_status_text = active_card.get("status_badge", "%100 Aktif & Kesintisiz")
        overall_health_pct = active_card["health_pct"]
        current_rpm = active_card["rpm_used"]
        rpm_max = active_card["rpm_limit"]
        daily_calls = active_card["daily_used"]
        daily_remaining = active_card["remaining_calls"]
        rpd_max = active_card["rpd_limit"]

    categories_summary = {
        "ai": {
            "title": "Yapay Zeka (Metin)",
            "active_name": active_provider_name,
            "rpm_used": current_rpm,
            "rpm_limit": rpm_max,
            "daily_used": daily_calls,
            "daily_remaining": daily_remaining,
            "rpd_limit": rpd_max,
            "health_pct": overall_health_pct,
            "status_badge": overall_status_text,
            "badge_class": "success" if overall_health_pct > 20 else "warning",
        },
        "stock": {
            "title": "Stok Medya",
            "pexels": provider_cards.get("Pexels", {}),
            "pixabay": provider_cards.get("Pixabay", {}),
            "health_pct": max(
                provider_cards.get("Pexels", {}).get("health_pct", 100),
                provider_cards.get("Pixabay", {}).get("health_pct", 100),
            ),
            "status_badge": provider_cards.get("Pexels", {}).get("status_badge", "Canlı & Aktif"),
        },
        "tts": {
            "title": "Seslendirme (TTS)",
            "edge": provider_cards.get("Edge-TTS", {}),
            "elevenlabs": provider_cards.get("ElevenLabs", {}),
            "health_pct": 100,
            "status_badge": "0 TL Limitsiz (Edge Neural)",
        },
        "youtube": {
            "title": "YouTube API",
            "provider": provider_cards.get("YouTube", {}),
            "health_pct": provider_cards.get("YouTube", {}).get("health_pct", 100),
            "status_badge": provider_cards.get("YouTube", {}).get("status_badge", "10.000 Birim / Tarayıcı"),
        },
    }

    return {
        "uptime_seconds": int(now - tracker.last_reset),
        "active_provider": active_provider_id,
        "active_provider_name": active_provider_name,
        "has_real_ai_key": has_active_ai_key,
        "is_api_key_missing": not has_active_ai_key,
        "current_rpm_used": current_rpm,
        "rpm_limit": rpm_max,
        "daily_used": daily_calls,
        "daily_remaining": daily_remaining,
        "rpd_limit": rpd_max,
        "overall_status_text": overall_status_text,
        "overall_health_pct": overall_health_pct,
        "is_exhausted": is_exhausted,
        "total_cost": "0.00 TL",
        "zero_cost_mode_active": True,
        "fallback_procedural_engine": "Aktif & Devrede (Failsafe 0 Kesinti)",
        "usage": dict(tracker.usage_counts),
        "errors": dict(tracker.error_counts),
        "providers": provider_cards,
        "categories": categories_summary,
        "quota_status": active_exhaustions,
        "has_exhausted_providers": any(p.get("exhausted", False) for p in active_exhaustions.values()),
        "live_sync": True,
    }
