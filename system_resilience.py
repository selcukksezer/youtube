"""
System Resilience, Hardware Acceleration & Technical Architecture Engine
Implements Section 7 (Items 411 - 465) of the 500-Item YouTube Shorts Automation Roadmap.
"""

import os
import platform
import re
import shutil
import subprocess
import time
from typing import Any, Dict, List, Optional, Tuple

import config
import imageio_ffmpeg
from services.resilience_probes import (
    _ENCODER_LABELS,
    _tiny_encoder_ok,
    default_gpu_codec_for_platform,
    encoder_choices,
    get_available_ffmpeg_encoders,
    get_encoder_fallback_chain,
    get_export_codec_settings,
    get_ffmpeg_loglevel,
    get_ffmpeg_vcodec_args,
    get_hardware_accelerated_encoder,
    get_system_health_status,
    is_material_resolution_acceptable,
    platform_encoder_candidates,
    probe_hardware_encoders,
    verify_render_output_sanity,
    verify_stock_video_integrity,
)

_AVAILABLE_ENCODERS_CACHE: Optional[set] = None
_ENCODER_PROBE_CACHE: Optional[Dict[str, bool]] = None


# ─── ITEM 416: Circuit Breaker Deseni ────────────────────────────────────────

class CircuitBreaker:
    """
    Item 416: Circuit Breaker Deseni (Devre Kesici).
    Bir API (Pexels, Pixabay, Gemini, Edge-TTS) arka arkaya 3 kez 429 veya 500 hatası
    verirse devre 'OPEN' durumuna geçer ve 60 saniye boyunca istekleri engelleyip
    otomatik olarak yedek sağlayıcıya yönlendirir.
    """
    STATE_CLOSED = "CLOSED"
    STATE_OPEN = "OPEN"
    STATE_HALF_OPEN = "HALF_OPEN"

    def __init__(self, failure_threshold: int = 3, recovery_timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.service_states: Dict[str, Dict[str, Any]] = {}

    def _get_service(self, name: str) -> Dict[str, Any]:
        if name not in self.service_states:
            self.service_states[name] = {
                "state": self.STATE_CLOSED,
                "failure_count": 0,
                "last_failure_time": 0.0,
                "total_calls": 0,
                "recovery_timeout": self.recovery_timeout,
            }
        return self.service_states[name]

    def can_execute(self, service_name: str) -> bool:
        """Checks whether the service circuit allows calls."""
        s = self._get_service(service_name)
        now = time.time()
        timeout = s.get("recovery_timeout") or self.recovery_timeout

        if s["state"] == self.STATE_OPEN:
            if now - s["last_failure_time"] >= timeout:
                s["state"] = self.STATE_HALF_OPEN
                return True
            return False
        return True

    def record_success(self, service_name: str):
        """Records a successful API call and resets failures."""
        s = self._get_service(service_name)
        s["total_calls"] += 1
        s["failure_count"] = 0
        s["state"] = self.STATE_CLOSED

    def record_failure(
        self, service_name: str, error_msg: str = "", custom_timeout: Optional[float] = None
    ):
        """Records failure and triggers tripwire if threshold reached."""
        s = self._get_service(service_name)
        s["total_calls"] += 1
        s["failure_count"] += 1
        s["last_failure_time"] = time.time()
        if custom_timeout is not None:
            s["recovery_timeout"] = float(custom_timeout)

        if s["state"] == self.STATE_HALF_OPEN or s["failure_count"] >= self.failure_threshold:
            s["state"] = self.STATE_OPEN
            timeout = s.get("recovery_timeout") or self.recovery_timeout
            print(
                f"  [CircuitBreaker] ⚠️ '{service_name}' devresi AÇILDI ({s['failure_count']} hata). {int(timeout)}s yedek servise geçildi."
            )

    def export_status(self) -> Dict[str, Dict[str, Any]]:
        """Returns snapshot of all tracked services and circuit states."""
        now = time.time()
        res = {}
        for name, s in self.service_states.items():
            timeout = s.get("recovery_timeout") or self.recovery_timeout
            remaining_cooldown = (
                max(0.0, round(timeout - (now - s["last_failure_time"]), 1))
                if s["state"] == self.STATE_OPEN
                else 0.0
            )
            res[name] = {
                "state": s["state"],
                "failure_count": s["failure_count"],
                "total_calls": s["total_calls"],
                "remaining_cooldown_sec": remaining_cooldown,
            }
        return res

    def get_public_fallback_endpoint(self, service_name: str) -> Optional[Any]:
        """
        Bölüm 34.2: Retrieve zero-cost public API fallback endpoints from services.public_apis_catalog
        when external paid/keyed APIs trip the circuit.
        """
        try:
            from services.public_apis_catalog import APICategory, PUBLIC_ENDPOINTS

            category_map = {
                "pexels": APICategory.MEDIA_ART,
                "pixabay": APICategory.MEDIA_ART,
                "coverr": APICategory.MEDIA_ART,
                "gemini": APICategory.NEWS_FACTS,
                "ddg": APICategory.NEWS_FACTS,
                "weather": APICategory.WEATHER_SCIENCE,
                "quotes": APICategory.QUOTES_WISDOM,
            }
            cat = category_map.get(service_name.lower())
            if cat:
                return [
                    ep for ep in PUBLIC_ENDPOINTS.values() if ep.category == cat and ep.is_active
                ]
        except Exception:
            pass
        return None

    def execute_with_fallback(
        self, service_name: str, primary_fn: Any, fallback_fn: Any, *args: Any, **kwargs: Any
    ) -> Any:
        """Execute primary callable or redirect to public fallback if circuit is open or call fails."""
        if not self.can_execute(service_name):
            return fallback_fn(*args, **kwargs)
        try:
            res = primary_fn(*args, **kwargs)
            self.record_success(service_name)
            return res
        except Exception as exc:
            self.record_failure(service_name, error_msg=str(exc))
            return fallback_fn(*args, **kwargs)


circuit_breaker = CircuitBreaker()


# ─── ITEM 428: Regex Tabanlı İntihal ve Sistem Lafı Temizleyici ──────────────

def clean_ai_system_preamble(raw_text: str) -> str:
    """
    Item 428: Regex Tabanlı İntihal ve Sistem Lafı Temizleyici.
    AI'nın 'İşte senaryo:', 'Elbette!', 'Here is the script:' gibi yapay zeka
    gevezeliklerini ve markdown tırnaklarını temizler.
    """
    cleaned = raw_text.strip()
    cleaned = re.sub(r'```[a-zA-Z]*\n?', '', cleaned)
    cleaned = re.sub(r'```', '', cleaned)

    preamble_patterns = [
        r'^(?:işte\s+hazırladığım\s+senaryo|işte\s+senaryo|senaryo\s+metni|işte|tabii\s+ki|elbette|merhaba)[:,\s\n-]*',
        r'^(?:sure,\s*here\'s\s+the\s+script|here\'s\s+the\s+script|here\s+is\s+the\s+script|sure|certainly|here\s+is|script)[:,\s\n-]*',
    ]

    changed = True
    while changed:
        changed = False
        cleaned = cleaned.strip()
        for pat in preamble_patterns:
            new_text = re.sub(pat, '', cleaned, count=1, flags=re.IGNORECASE).strip()
            if new_text != cleaned:
                cleaned = new_text
                changed = True
    return cleaned


# ─── ITEM 430: Akıllı Kesme (Smart Splitting for 60s Limit) ──────────────────

def smart_split_narration_for_shorts(full_text: str, max_words: int = 150) -> Tuple[str, bool]:
    """
    Item 430: Akıllı Kesme (Smart Splitting).
    60 saniyeyi aşma riski taşıyan metinler mantıklı bir cümle sonundan (. ! ?)
    kesilerek Shorts süresi limitinde tutulur.
    """
    words = full_text.split()
    if len(words) <= max_words:
        return (full_text, False)

    truncated_words = words[:max_words]
    truncated_text = " ".join(truncated_words)

    last_punc = max(
        truncated_text.rfind('.'), truncated_text.rfind('!'), truncated_text.rfind('?')
    )
    if last_punc > 50:
        return (truncated_text[: last_punc + 1], True)

    return (f"{truncated_text}...", True)


# ─── ITEM 451: Ses ve Altyazı Eşleme Sapması Kontrolü ────────────────────────

def guard_subtitle_audio_drift(
    timings: List[Dict[str, Any]], audio_duration: float
) -> List[Dict[str, Any]]:
    """
    Item 451: Ses ve Altyazı Eşleme Sapması Kontrolü (Audio-Subtitle Drift Guard).
    Eğer son altyazının süresi ses dosyasından uzunsa otomatik kırpılarak senkronizasyon korunur.
    """
    if not timings or audio_duration <= 0.0:
        return timings

    adjusted = []
    for t in timings:
        start = float(t.get("start", 0.0))
        end = float(t.get("end", 0.0))
        if start >= audio_duration:
            continue
        new_t = dict(t)
        new_t["end"] = min(end, round(audio_duration, 3))
        adjusted.append(new_t)

    return adjusted


# ─── ITEM 461: Otomatik Başlık ve Dosya Adı Temizleme ─────────────────────────

def sanitize_filename_and_title(raw_title: str) -> str:
    """
    Item 461: Otomatik Başlık Temizleme.
    Başlıktaki geçersiz dosya sistemi karakterleri (/ \\ : * ? \" < > |) ayıklanır.
    """
    tr_map = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
    clean = raw_title.translate(tr_map)
    clean = re.sub(r'[/\\:*?"<>|]', '', clean)
    clean = re.sub(r'\s+', '_', clean.strip())
    return clean[:75] if clean else f"shorts_{int(time.time())}"


# ─── ITEM 448: Otomatik Video Silme (30 gün arşiv temizliği) ─────────────────

def purge_old_videos(
    output_dir: str = None,
    max_age_days: int = 30,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Item 448: Delete rendered MP4/MOV files older than max_age_days from output tree.
    Skips hidden dirs and preserves .gitkeep markers.
    """
    target = output_dir or getattr(config, "OUTPUT_DIR", os.path.join(config.BASE_DIR, "output"))
    if not os.path.isdir(target):
        return {"purged": [], "bytes_freed": 0, "skipped": True}

    cutoff = time.time() - (max_age_days * 86400)
    purged, bytes_freed = [], 0
    for root, _dirs, files in os.walk(target):
        for name in files:
            if not name.lower().endswith((".mp4", ".mov", ".mkv", ".webm")):
                continue
            path = os.path.join(root, name)
            try:
                if os.path.getmtime(path) >= cutoff:
                    continue
                size = os.path.getsize(path)
                if dry_run:
                    purged.append(path)
                    bytes_freed += size
                else:
                    os.remove(path)
                    purged.append(path)
                    bytes_freed += size
            except OSError:
                continue
    return {
        "purged": purged,
        "purged_count": len(purged),
        "bytes_freed": bytes_freed,
        "max_age_days": max_age_days,
        "dry_run": dry_run,
    }
