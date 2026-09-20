"""
API Quota Manager & Multi-Provider Failover (Items 62, 69, 72)
Tracks API usage, real-time RPM, persistent daily RPD, live API provider quota checks,
and provides reset time forecasts and live UI badges.
"""
import os
import time
import json
import re
import urllib.request
import urllib.error
from datetime import datetime
from typing import Dict, Any, List, Optional
import config

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
USAGE_FILE = os.path.join(DATA_DIR, "quota_usage.json")

DEFAULT_LIMITS = {
    "Gemini": {
        "name": "Google Gemini Flash",
        "tier": "Google AI Studio (Ücretsiz Tier)",
        "rpm_limit": 15,
        "rpd_limit": 1500,
        "cost_per_video": "0.00 TL",
        "description": "Dakikada 15 istek, günde 1.500 istek ücretsiz."
    },
    "Edge-TTS": {
        "name": "Microsoft Edge Neural TTS",
        "tier": "Açık Kaynak & Ücretsiz",
        "rpm_limit": 9999,
        "rpd_limit": 99999,
        "cost_per_video": "0.00 TL",
        "description": "Limitsiz yüksek kaliteli doğal ses sentezi."
    },
    "ElevenLabs": {
        "name": "ElevenLabs Multilingual TTS",
        "tier": "Free Tier (~10k karakter/ay)",
        "rpm_limit": 30,
        "rpd_limit": 10000,
        "cost_per_video": "0.00 TL (free tier)",
        "description": "Pre-made çok dilli sesler — TR+EN. Kota aşımında Edge yedek."
    },
    "Pexels": {
        "name": "Pexels Video API",
        "tier": "Resmi Geliştirici Hesabı",
        "rpm_limit": 200,
        "rpd_limit": 25000,
        "cost_per_video": "0.00 TL",
        "description": "Aylık 25.000 istek, saatlik 200 istek ücretsiz."
    },
    "Pixabay": {
        "name": "Pixabay Video API",
        "tier": "Açık Medya Lisansı",
        "rpm_limit": 100,
        "rpd_limit": 5000,
        "cost_per_video": "0.00 TL",
        "description": "Dakikada 100 istek ücretsiz."
    },
    "OpenAI": {
        "name": "OpenAI GPT-4o Mini",
        "tier": "Kullanım Başına Ödeme (PayG)",
        "rpm_limit": 500,
        "rpd_limit": 10000,
        "cost_per_video": "~0.05 TL",
        "description": "Yüksek performanslı ticari model."
    },
    "Grok": {
        "name": "xAI Grok-2",
        "tier": "xAI Cloud",
        "rpm_limit": 60,
        "rpd_limit": 2000,
        "cost_per_video": "~0.08 TL",
        "description": "Alternatif AI motoru."
    },
    "DeepSeek": {
        "name": "DeepSeek V3 / R1",
        "tier": "DeepSeek API",
        "rpm_limit": 120,
        "rpd_limit": 5000,
        "cost_per_video": "~0.02 TL",
        "description": "Ultra ekonomik akıl yürütme motoru."
    }
}


class QuotaTracker:
    def __init__(self):
        self.usage_counts: Dict[str, int] = {}
        self.error_counts: Dict[str, int] = {}
        self.call_timestamps: Dict[str, List[float]] = {}
        self.last_reset = time.time()
        self.quota_status: Dict[str, Dict[str, Any]] = {}
        self.live_cache: Dict[str, Any] = {}
        self.live_cache_time: float = 0.0

        os.makedirs(DATA_DIR, exist_ok=True)
        self._load_persistent_usage()

    def _today_str(self) -> str:
        return datetime.now().strftime("%Y-%m-%d")

    def _load_persistent_usage(self):
        """Loads daily and lifetime usage from disk so counts survive restarts."""
        today = self._today_str()
        if os.path.exists(USAGE_FILE):
            try:
                with open(USAGE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    saved_date = data.get("date", "")
                    if saved_date == today:
                        self.usage_counts = data.get("daily_counts", {})
                    else:
                        self.usage_counts = {}
                    return
            except Exception as e:
                print(f"  [QuotaManager] Error loading persistent usage: {e}")
        self.usage_counts = {}

    def _save_persistent_usage(self):
        """Saves current usage counts to disk."""
        try:
            today = self._today_str()
            data = {
                "date": today,
                "daily_counts": self.usage_counts,
                "last_updated": datetime.now().isoformat()
            }
            with open(USAGE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            pass

    def record_call(self, provider: str):
        prov = str(provider or "Gemini").capitalize()
        # Edge-TTS vs için formatlama
        if prov.lower() in ("edge-tts", "edgetts", "tts"):
            prov = "Edge-TTS"
        elif prov.lower() == "openai":
            prov = "OpenAI"
        elif prov.lower() == "deepseek":
            prov = "DeepSeek"
        elif prov.lower() == "grok":
            prov = "Grok"

        self.usage_counts[prov] = self.usage_counts.get(prov, 0) + 1
        now = time.time()
        if prov not in self.call_timestamps:
            self.call_timestamps[prov] = []
        self.call_timestamps[prov].append(now)

        # 24 saatten eski damgaları temizle
        self.call_timestamps[prov] = [t for t in self.call_timestamps[prov] if now - t < 86400]
        self._save_persistent_usage()

    def record_error(self, provider: str, error_msg: str):
        prov = str(provider or "Gemini").capitalize()
        if prov.lower() in ("edge-tts", "edgetts", "tts"):
            prov = "Edge-TTS"
        self.error_counts[prov] = self.error_counts.get(prov, 0) + 1
        print(f"  [QuotaManager] Provider '{prov}' error: {error_msg[:80]}")

        lower_err = str(error_msg).lower()
        now = time.time()

        is_quota_exceeded = any(k in lower_err for k in [
            "quota", "resource_exhausted", "rate limit", "429", "exceeded", "limit reached", "billing"
        ])
        is_auth_error = any(k in lower_err for k in [
            "401", "unauthenticated", "invalid authentication", "api_key_invalid", "permission_denied", "api key not valid"
        ])

        if is_quota_exceeded or is_auth_error:
            reset_seconds = 60
            reset_type = "Hız Limiti (1 Dakika RPM)"

            if "daily" in lower_err or "resource_exhausted" in lower_err or "per day" in lower_err or "quota exceeded" in lower_err:
                reset_seconds = 86400
                reset_type = "Günlük Kota (Gece Yarısı Pasifik Saati / 24 Saat)"
            elif "retry-after" in lower_err:
                m = re.search(r'retry-after:?\s*(\d+)', lower_err)
                if m:
                    reset_seconds = int(m.group(1))
                    reset_type = f"Sunucu Bildirimi ({reset_seconds} saniye)"

            reset_timestamp = now + reset_seconds
            reset_time_str = datetime.fromtimestamp(reset_timestamp).strftime("%H:%M:%S (%d.%m.%Y)")
            clean_error = error_msg.strip()
            if len(clean_error) > 200:
                clean_error = clean_error[:200] + "..."

            status_type = "AUTH_ERROR" if is_auth_error else "QUOTA_EXHAUSTED"
            summary_desc = "API anahtarı geçersiz veya yetkisiz." if is_auth_error else (
                f"Kota / Hız Limiti Aşıldı. Tahmini yenilenme: {reset_type} ({reset_time_str})"
            )

            self.quota_status[prov] = {
                "exhausted": True,
                "status_type": status_type,
                "error_summary": clean_error,
                "description": summary_desc,
                "exhausted_at": datetime.fromtimestamp(now).strftime("%H:%M:%S"),
                "reset_timestamp": reset_timestamp,
                "reset_seconds_remaining": reset_seconds,
                "reset_time_str": reset_time_str,
                "reset_type": reset_type,
                "fallback_active": True,
                "fallback_solution": "Failsafe Akıllı Prosedürel Senaryo Motoru devrede (0 Kesinti)"
            }

    def fetch_live_api_status(self, force: bool = False) -> Dict[str, Any]:
        """Queries official endpoints of Pexels, Pixabay, Gemini etc. to fetch actual live quotas and status."""
        now = time.time()
        # Use cache if within 45 seconds unless forced
        if not force and self.live_cache and (now - self.live_cache_time < 45):
            return self.live_cache

        live_results = {}

        # 1. PEXELS LIVE QUOTA
        pexels_key = getattr(config, "PEXELS_API_KEY", "") or ""
        if pexels_key:
            try:
                url = "https://api.pexels.com/v1/curated?per_page=1"
                req = urllib.request.Request(url, headers={
                    "Authorization": pexels_key,
                    "User-Agent": "ShortsVideoCreators/2.0 (Windows NT 10.0; Win64; x64)"
                })
                with urllib.request.urlopen(req, timeout=4) as resp:
                    limit = resp.headers.get("X-Ratelimit-Limit")
                    remaining = resp.headers.get("X-Ratelimit-Remaining")
                    reset_val = resp.headers.get("X-Ratelimit-Reset")
                    live_results["Pexels"] = {
                        "online": True,
                        "limit": int(limit) if limit and limit.isdigit() else 25000,
                        "remaining": int(remaining) if remaining and remaining.isdigit() else None,
                        "reset": reset_val,
                        "status_note": f"Canlı Senkronize ({remaining} Kalan)" if remaining else "Canlı & Aktif"
                    }
            except urllib.error.HTTPError as e:
                live_results["Pexels"] = {
                    "online": False,
                    "error_code": e.code,
                    "status_note": f"Hata ({e.code})"
                }
            except Exception as e:
                live_results["Pexels"] = {"online": False, "status_note": "Bağlantı Hatası"}

        # 2. PIXABAY LIVE QUOTA
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
                        "status_note": f"Canlı Senkronize ({remaining} Kalan)" if remaining else "Canlı & Aktif"
                    }
            except urllib.error.HTTPError as e:
                live_results["Pixabay"] = {
                    "online": False,
                    "error_code": e.code,
                    "status_note": f"Hata ({e.code})"
                }
            except Exception as e:
                live_results["Pixabay"] = {"online": False, "status_note": "Bağlantı Hatası"}

        # 3. ELEVENLABS SUBSCRIPTION QUOTA
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
                            if sub.get("character_remaining") is not None else "Bağlı"
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

        # 4. GEMINI LIVE HEALTH & MODEL AVAILABILITY
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
                        "status_note": f"Canlı Doğrulandı ({len(models)} Model Aktif, {latency_ms}ms)"
                    }
            except urllib.error.HTTPError as e:
                msg = "Yetkisiz / Geçersiz Anahtar" if e.code in (400, 401, 403) else ("Kota / Hız Limiti (429)" if e.code == 429 else f"HTTP {e.code}")
                live_results["Gemini"] = {
                    "online": False,
                    "error_code": e.code,
                    "status_note": msg
                }
            except Exception as e:
                live_results["Gemini"] = {"online": False, "status_note": "Bağlantı Hatası"}

        self.live_cache = live_results
        self.live_cache_time = now
        return live_results

    def reset_provider_quota(self, provider: str):
        prov = str(provider or "Gemini").capitalize()
        if prov in self.quota_status:
            del self.quota_status[prov]

    def reset_all(self):
        self.usage_counts.clear()
        self.error_counts.clear()
        self.call_timestamps.clear()
        self.quota_status.clear()
        self.last_reset = time.time()
        self.live_cache.clear()
        self.live_cache_time = 0.0
        self._save_persistent_usage()

    def get_stats(self, force_live: bool = False) -> Dict[str, Any]:
        now = time.time()
        live_api_info = self.fetch_live_api_status(force=force_live)

        active_exhaustions = {}
        for prov, info in self.quota_status.items():
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
            timestamps = self.call_timestamps.get(prov_key, [])
            rpm_used = len([t for t in timestamps if now - t <= 60])
            daily_used = self.usage_counts.get(prov_key, 0)
            errors = self.error_counts.get(prov_key, 0)
            exhaustion = active_exhaustions.get(prov_key, {})
            live_data = live_api_info.get(prov_key, {})

            rpm_limit = limits.get("rpm_limit", 15)
            rpd_limit = limits.get("rpd_limit", 1500)

            # Override with live remaining if available from official API headers
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
            is_live_down = (live_data.get("online") is False)

            if not has_k:
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
                # Health calculated from actual daily remaining, NOT 1 RPM request
                health_pct = max(10, min(100, int((remaining_calls / max(1, rpd_limit)) * 100)))
            else:
                status_badge = "%100 Hazır & Kesintisiz"
                badge_class = "success"
                health_pct = max(10, min(100, int((remaining_calls / max(1, rpd_limit)) * 100)))

            provider_cards[prov_key] = {
                **limits,
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
                "exhaustion": exhaustion if is_exhausted else None
            }

        if not has_active_ai_key:
            active_provider_id = "Yerel Motor"
            active_provider_name = "Akıllı Yerel Senaryo Motoru (0 TL)"
            overall_status_text = "API Anahtarı Bekleniyor (Yerel Motor Aktif)"
            overall_health_pct = 100
            current_rpm = 0
            rpm_max = "Sınırsız"
            daily_calls = self.usage_counts.get("Yerel Fallback", 0)
            daily_remaining = "Sınırsız"
            rpd_max = "Sınırsız"
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

        return {
            "uptime_seconds": int(now - self.last_reset),
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
            "usage": dict(self.usage_counts),
            "errors": dict(self.error_counts),
            "providers": provider_cards,
            "quota_status": active_exhaustions,
            "has_exhausted_providers": any(p.get("exhausted", False) for p in active_exhaustions.values()),
            "live_sync": True
        }


quota_tracker = QuotaTracker()
