"""
API Quota Manager & Multi-Provider Failover (Items 62, 69, 72)
Tracks API usage, real-time RPM, persistent daily RPD, live API provider quota checks,
and provides reset time forecasts and live UI badges.
"""
import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any, Dict, List, Optional

import config
from services.quota_telemetry import (
    DEFAULT_LIMITS,
    build_quota_stats_report,
    probe_live_api_status,
)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
USAGE_FILE = os.path.join(DATA_DIR, "quota_usage.json")


class QuotaTracker:
    def __init__(self):
        self.usage_counts: Dict[str, int] = {}
        self.token_totals: Dict[str, Dict[str, int]] = {}
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
                        self.token_totals = data.get("token_totals", {})
                        return
                    else:
                        self.usage_counts = {}
                        self.token_totals = {}
                        self._save_persistent_usage()
                        return
            except Exception as e:
                print(f"  [QuotaManager] Error loading persistent usage: {e}")
        self.usage_counts = {}
        self.token_totals = {}
        self._save_persistent_usage()

    def _check_and_rollover_day(self):
        """Checks if current date matches today; if not, resets counters for the new day."""
        today = self._today_str()
        if getattr(self, "_current_day_cached", None) != today:
            self._current_day_cached = today
            self._load_persistent_usage()

    def _save_persistent_usage(self):
        """Saves current usage counts to disk."""
        try:
            today = self._today_str()
            data = {
                "date": today,
                "daily_counts": self.usage_counts,
                "token_totals": self.token_totals,
                "last_updated": datetime.now().isoformat(),
            }
            with open(USAGE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def record_call(self, provider: str):
        self._check_and_rollover_day()
        prov = str(provider or "Gemini").capitalize()
        if prov.lower() in ("edge-tts", "edgetts", "tts"):
            prov = "Edge-TTS"
        elif prov.lower() == "openai":
            prov = "OpenAI"
        elif prov.lower() == "deepseek":
            prov = "DeepSeek"
        elif prov.lower() == "grok":
            prov = "Grok"
        elif prov.lower() in ("youtube", "youtube_api", "yt"):
            prov = "YouTube"
        elif prov.lower() == "elevenlabs":
            prov = "ElevenLabs"
        elif prov.lower() == "pexels":
            prov = "Pexels"
        elif prov.lower() == "pixabay":
            prov = "Pixabay"

        self.usage_counts[prov] = self.usage_counts.get(prov, 0) + 1
        now = time.time()
        if prov not in self.call_timestamps:
            self.call_timestamps[prov] = []
        self.call_timestamps[prov].append(now)

        self.call_timestamps[prov] = [t for t in self.call_timestamps[prov] if now - t < 86400]
        self._save_persistent_usage()

    def record_token_usage(
        self,
        provider: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
    ) -> None:
        """Item 434: log Gemini prompt/completion token counts to local JSON."""
        prov = str(provider or "Gemini").capitalize()
        if prov.lower() == "gemini":
            prov = "Gemini"
        bucket = self.token_totals.setdefault(prov, {"prompt": 0, "completion": 0, "total": 0})
        bucket["prompt"] = bucket.get("prompt", 0) + int(prompt_tokens or 0)
        bucket["completion"] = bucket.get("completion", 0) + int(completion_tokens or 0)
        bucket["total"] = bucket.get("total", 0) + int(prompt_tokens or 0) + int(completion_tokens or 0)
        self._save_persistent_usage()

    def record_error(self, provider: str, error_msg: str):
        prov = str(provider or "Gemini").capitalize()
        if prov.lower() in ("edge-tts", "edgetts", "tts"):
            prov = "Edge-TTS"
        self.error_counts[prov] = self.error_counts.get(prov, 0) + 1
        print(f"  [QuotaManager] Provider '{prov}' error: {error_msg[:80]}")

        lower_err = str(error_msg).lower()
        now = time.time()

        is_quota_exceeded = any(
            k in lower_err
            for k in ["quota", "resource_exhausted", "rate limit", "429", "exceeded", "limit reached", "billing"]
        )
        is_auth_error = any(
            k in lower_err
            for k in ["401", "unauthenticated", "invalid authentication", "api_key_invalid", "permission_denied", "api key not valid"]
        )

        if is_quota_exceeded or is_auth_error:
            reset_seconds = 60
            reset_type = "Hız Limiti (1 Dakika RPM)"

            if (
                "daily" in lower_err
                or "resource_exhausted" in lower_err
                or "per day" in lower_err
                or "quota exceeded" in lower_err
            ):
                reset_seconds = 86400
                reset_type = "Günlük Kota (Gece Yarısı Pasifik Saati / 24 Saat)"
            elif "retry-after" in lower_err:
                m = re.search(r"retry-after:?\s*(\d+)", lower_err)
                if m:
                    reset_seconds = int(m.group(1))
                    reset_type = f"Sunucu Bildirimi ({reset_seconds} saniye)"

            reset_timestamp = now + reset_seconds
            reset_time_str = datetime.fromtimestamp(reset_timestamp).strftime("%H:%M:%S (%d.%m.%Y)")
            clean_error = error_msg.strip()
            if len(clean_error) > 200:
                clean_error = clean_error[:200] + "..."

            status_type = "AUTH_ERROR" if is_auth_error else "QUOTA_EXHAUSTED"
            summary_desc = (
                "API anahtarı geçersiz veya yetkisiz."
                if is_auth_error
                else f"Kota / Hız Limiti Aşıldı. Tahmini yenilenme: {reset_type} ({reset_time_str})"
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
                "fallback_solution": "Failsafe Akıllı Prosedürel Senaryo Motoru devrede (0 Kesinti)",
            }

    def fetch_live_api_status(self, force: bool = False) -> Dict[str, Any]:
        """Queries official endpoints of Pexels, Pixabay, Gemini etc. to fetch actual live quotas and status."""
        now = time.time()
        if not force and self.live_cache and (now - self.live_cache_time < 45):
            return self.live_cache

        live_results = probe_live_api_status(self.usage_counts)
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
        self._check_and_rollover_day()
        now = time.time()
        live_api_info = self.fetch_live_api_status(force=force_live)
        return build_quota_stats_report(self, now, live_api_info)


quota_tracker = QuotaTracker()
quota_manager = quota_tracker
