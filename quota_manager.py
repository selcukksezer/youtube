"""
API Quota Manager & Multi-Provider Failover (Items 62, 69, 72)
Tracks API usage, real-time RPM (Requests Per Minute), daily RPD, error rates,
and provides reset time forecasts and live UI badges.
"""
import time
import re
from datetime import datetime
from typing import Dict, Any, List, Optional
import config

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
    "Pexels": {
        "name": "Pexels Video API",
        "tier": "Resmi Geliştirici Hesabı",
        "rpm_limit": 200, # 200 / saat
        "rpd_limit": 20000,
        "cost_per_video": "0.00 TL",
        "description": "Saatlik 200 istek, aylık 20.000 istek ücretsiz."
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
        # provider -> details about last quota or rate limit exhaustion
        self.quota_status: Dict[str, Dict[str, Any]] = {}

    def record_call(self, provider: str):
        prov = str(provider or "Gemini").capitalize()
        self.usage_counts[prov] = self.usage_counts.get(prov, 0) + 1
        now = time.time()
        if prov not in self.call_timestamps:
            self.call_timestamps[prov] = []
        self.call_timestamps[prov].append(now)

        # Temizlik: 24 saatten eski çağrı damgalarını sil
        self.call_timestamps[prov] = [t for t in self.call_timestamps[prov] if now - t < 86400]

    def record_error(self, provider: str, error_msg: str):
        prov = str(provider or "Gemini").capitalize()
        self.error_counts[prov] = self.error_counts.get(prov, 0) + 1
        print(f"  [QuotaManager] Provider '{prov}' encountered error: {error_msg[:80]}")

        # Check if error is quota exhaustion or rate limit
        lower_err = str(error_msg).lower()
        now = time.time()

        is_quota_exceeded = any(k in lower_err for k in [
            "quota", "resource_exhausted", "rate limit", "429", "exceeded", "limit reached", "billing"
        ])
        is_auth_error = any(k in lower_err for k in [
            "401", "unauthenticated", "invalid authentication", "api_key_invalid", "permission_denied"
        ])

        if is_quota_exceeded or is_auth_error:
            reset_seconds = 60  # Varsayılan 1 dakika RPM hız limiti
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

    def reset_provider_quota(self, provider: str):
        """Manually or automatically mark a provider as restored."""
        prov = str(provider or "Gemini").capitalize()
        if prov in self.quota_status:
            del self.quota_status[prov]

    def reset_all(self):
        """Resets all usage counters and errors."""
        self.usage_counts.clear()
        self.error_counts.clear()
        self.call_timestamps.clear()
        self.quota_status.clear()
        self.last_reset = time.time()

    def get_stats(self) -> Dict[str, Any]:
        now = time.time()
        active_provider = getattr(config, "AI_PROVIDER", "Gemini") or "Gemini"
        active_provider_cap = str(active_provider).capitalize()

        # Update remaining seconds dynamically
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

        # Per-provider key status
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

        has_active_ai_key = bool(active_limit_key and provider_has_key.get(active_limit_key, False))

        # Per-provider live metrics
        provider_cards = {}
        for prov_key, limits in DEFAULT_LIMITS.items():
            has_k = provider_has_key.get(prov_key, False)
            timestamps = self.call_timestamps.get(prov_key, [])
            rpm_used = len([t for t in timestamps if now - t <= 60])
            daily_used = len(timestamps)
            total_lifetime = self.usage_counts.get(prov_key, 0)
            errors = self.error_counts.get(prov_key, 0)
            exhaustion = active_exhaustions.get(prov_key, {})

            rpm_limit = limits.get("rpm_limit", 15)
            rpd_limit = limits.get("rpd_limit", 1500)

            is_exhausted = exhaustion.get("exhausted", False)
            if not has_k:
                status_badge = "Anahtar Girilmedi"
                badge_class = "secondary"
                health_pct = 0
            elif is_exhausted:
                status_badge = "Kota / Hız Limiti Aşıldı"
                badge_class = "warning"
                health_pct = 20
            elif errors > 0 and total_lifetime == 0:
                status_badge = "Hata Alındı"
                badge_class = "danger"
                health_pct = 40
            else:
                status_badge = "%100 Hazır & Kesintisiz"
                badge_class = "success"
                health_pct = max(10, min(100, int(100 - (rpm_used / max(1, rpm_limit)) * 100)))

            provider_cards[prov_key] = {
                **limits,
                "has_key": has_k,
                "rpm_used": rpm_used,
                "daily_used": daily_used,
                "total_calls": total_lifetime,
                "errors": errors,
                "status_badge": status_badge,
                "badge_class": badge_class,
                "health_pct": health_pct,
                "is_active": bool(has_active_ai_key and active_limit_key == prov_key),
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
            rpd_max = "Sınırsız"
            is_exhausted = False
        else:
            active_card = provider_cards[active_limit_key]
            active_provider_id = active_limit_key
            active_provider_name = active_card["name"]
            is_exhausted = active_card.get("exhaustion") is not None
            overall_status_text = "Hız Limiti Aşıldı (Fallback Aktif)" if is_exhausted else "%100 Aktif & Kesintisiz"
            overall_health_pct = active_card["health_pct"]
            current_rpm = active_card["rpm_used"]
            rpm_max = active_card["rpm_limit"]
            daily_calls = active_card["daily_used"]
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
            "has_exhausted_providers": any(p.get("exhausted", False) for p in active_exhaustions.values())
        }


quota_tracker = QuotaTracker()

