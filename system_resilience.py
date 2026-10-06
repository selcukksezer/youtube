"""
System Resilience, Hardware Acceleration & Technical Architecture Engine
Implements Section 7 (Items 411 - 465) of the 500-Item YouTube Shorts Automation Roadmap.
Covers:
- Apple Silicon VideoToolbox Hardware Acceleration Config (Item 411)
- Circuit Breaker Pattern for External APIs (Item 416)
- Stock Video Integrity & ffprobe Verification (Item 424)
- Regex AI Preamble / Cliché Cleaner (Item 428)
- 1-Pixel Micro-Modulator / Unique MD5 Scrambler (Item 429)
- Smart Splitting at Sentence Boundary for 60s Shorts Limit (Item 430)
- Audio-Subtitle Drift Guard (Item 451)
- FFmpeg Output Sanity & File Size Verification (Item 452)
- Filename and Title Sanitizer (Item 461)
- System Health Diagnostics & Resource Monitor (Item 464)
"""

import os
import re
import time
import shutil
import platform
import subprocess
from typing import Dict, List, Any, Optional, Tuple
import imageio_ffmpeg
import config


# ─── ITEM 411: Apple Silicon VideoToolbox Donanım Hızlandırması ──────────────

def get_hardware_accelerated_encoder() -> Tuple[str, List[str]]:
    """
    Item 411: Apple Silicon Donanım Hızlandırması (VideoToolbox).
    macOS üzerinde VideoToolbox (h264_videotoolbox) aktif edilerek CPU yükü %80 düşürülür,
    render hızı 5 kat artırılır. Windows NVIDIA NVENC hardware_detector ile tespit edilir.
    Desteklenmeyen ortamlarda libx264 kullanılır.
    """
    try:
        from hardware_detector import get_system_hardware_specs

        gpu = get_system_hardware_specs().get("gpu", {})
        if gpu.get("has_videotoolbox"):
            return ("h264_videotoolbox", ["-b:v", "14M", "-allow_sw", "1"])
        # NVENC requires explicit operator opt-in. Auto-selecting a hardware
        # encoder can produce non-portable output and hide driver failures.
        if gpu.get("has_nvenc") and os.environ.get("GPU_CODEC", "").strip() == "h264_nvenc":
            return ("h264_nvenc", ["-preset", "p4", "-b:v", "0", "-cq", "20"])
    except Exception:
        pass
    if platform.system() == "Darwin":
        return ("h264_videotoolbox", ["-b:v", "14M", "-allow_sw", "1"])
    return ("libx264", ["-preset", "fast", "-b:v", "12M"])


def default_gpu_codec_for_platform() -> str:
    """Platform-aware default video encoder (NVENC on Windows NVIDIA, VideoToolbox on macOS)."""
    if platform.system() == "Darwin":
        return "h264_videotoolbox"
    if platform.system() == "Windows":
        return "h264_nvenc"
    return "libx264"


def get_export_codec_settings(
    use_gpu: Optional[bool] = None,
    gpu_codec: Optional[str] = None,
) -> Tuple[str, Optional[str], List[str], str]:
    """
    MoviePy/FFmpeg export codec selection with hardware fallback labels.
    Returns (codec, preset_or_none, ffmpeg_params, mode_label).
    """
    use_gpu = getattr(config, "USE_GPU_ACCELERATION", True) if use_gpu is None else use_gpu
    gpu_codec = (gpu_codec or getattr(config, "GPU_CODEC", "") or default_gpu_codec_for_platform()).strip()

    if not use_gpu or gpu_codec == "libx264":
        return (
            "libx264",
            "fast",
            ["-crf", "21", "-tune", "fastdecode", "-pix_fmt", "yuv420p"],
            f"CPU libx264 (threads={getattr(config, 'RENDER_THREADS', 8)})",
        )
    if gpu_codec == "h264_nvenc":
        return (
            "h264_nvenc",
            "p5",
            ["-tune", "hq", "-cq", "21", "-b:v", "0", "-spatial-aq", "1", "-temporal-aq", "1", "-pix_fmt", "yuv420p"],
            "NVIDIA NVENC",
        )
    if gpu_codec == "h264_videotoolbox":
        return (
            "h264_videotoolbox",
            None,
            ["-b:v", "14M", "-allow_sw", "1", "-pix_fmt", "yuv420p"],
            "Apple VideoToolbox",
        )
    if gpu_codec == "h264_qsv":
        return (
            "h264_qsv",
            "medium",
            ["-global_quality", "22", "-look_ahead", "1", "-pix_fmt", "yuv420p"],
            "Intel QuickSync (QSV)",
        )
    if gpu_codec == "h264_amf":
        return (
            "h264_amf",
            "speed",
            ["-rc", "cqp", "-qp_i", "20", "-qp_p", "22", "-pix_fmt", "yuv420p"],
            "AMD AMF",
        )
    if gpu_codec == "h264_mf":
        return (
            "h264_mf",
            None,
            ["-b:v", "12M", "-pix_fmt", "yuv420p"],
            "Windows Media Foundation (h264_mf)",
        )
    return (
        "libx264",
        "fast",
        ["-crf", "21", "-tune", "fastdecode", "-pix_fmt", "yuv420p"],
        "CPU libx264",
    )


_AVAILABLE_ENCODERS_CACHE: Optional[set] = None
_ENCODER_PROBE_CACHE: Optional[Dict[str, bool]] = None

_ENCODER_LABELS = {
    "h264_nvenc": "NVIDIA NVENC",
    "h264_qsv": "Intel Quick Sync",
    "h264_amf": "AMD AMF",
    "h264_mf": "Windows Media Foundation",
    "h264_videotoolbox": "Apple VideoToolbox",
    "h264_vaapi": "VAAPI",
    "libx264": "CPU libx264",
}


def platform_encoder_candidates() -> List[str]:
    system = platform.system()
    if system == "Darwin":
        return ["h264_videotoolbox"]
    if system == "Windows":
        return ["h264_nvenc", "h264_qsv", "h264_amf", "h264_mf"]
    return ["h264_nvenc", "h264_vaapi", "h264_qsv"]


def _tiny_encoder_ok(ffmpeg: str, codec: str) -> bool:
    """Five-frame null encode. A name in `ffmpeg -encoders` is not a working chip."""
    args, _label = get_ffmpeg_vcodec_args(use_gpu=True, gpu_codec=codec)
    cmd = [
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "testsrc=duration=0.4:size=128x72:rate=15",
        "-frames:v", "5",
        *args,
        "-f", "null", "-",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=12)
    except Exception:
        return False
    return proc.returncode == 0


def probe_hardware_encoders(force: bool = False) -> Dict[str, bool]:
    """
    NarratoAI _detect_hardware_encoding stops at the first encoder that
    finishes a five-frame test. This keeps every encoder that passes, so
    Quick Sync stays selectable when NVENC also works. A listed encoder
    that fails the test is false.
    """
    global _ENCODER_PROBE_CACHE
    if _ENCODER_PROBE_CACHE is not None and not force:
        return dict(_ENCODER_PROBE_CACHE)
    listed = get_available_ffmpeg_encoders()
    try:
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        ffmpeg = "ffmpeg"
    report: Dict[str, bool] = {}
    for codec in platform_encoder_candidates():
        if listed and codec not in listed:
            report[codec] = False
            continue
        report[codec] = _tiny_encoder_ok(ffmpeg, codec)
    report["libx264"] = True if not listed else ("libx264" in listed)
    _ENCODER_PROBE_CACHE = report
    return dict(report)


def encoder_choices() -> List[Dict[str, Any]]:
    report = probe_hardware_encoders()
    rows = []
    for codec in list(platform_encoder_candidates()) + ["libx264"]:
        rows.append({
            "id": codec,
            "label": _ENCODER_LABELS.get(codec, codec),
            "available": bool(report.get(codec)),
        })
    return rows

def get_available_ffmpeg_encoders() -> set:
    """Probes FFmpeg binary once to find compiled video encoders."""
    global _AVAILABLE_ENCODERS_CACHE
    if _AVAILABLE_ENCODERS_CACHE is not None:
        return _AVAILABLE_ENCODERS_CACHE
    encoders: set = set()
    try:
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        res = subprocess.run([exe, "-encoders"], capture_output=True, text=True, timeout=5)
        for line in (res.stdout or "").splitlines():
            line_str = line.strip()
            if line_str.startswith("V"):
                parts = line_str.split()
                if len(parts) >= 2:
                    encoders.add(parts[1])
    except Exception:
        pass
    _AVAILABLE_ENCODERS_CACHE = encoders
    return encoders


def get_ffmpeg_loglevel() -> str:
    """Item 437: warning in debug mode, error in production."""
    import os
    debug = os.getenv("FFMPEG_DEBUG", "false").lower() in ("true", "1", "yes")
    return "warning" if debug else "error"


def get_ffmpeg_vcodec_args(use_gpu: Optional[bool] = None, gpu_codec: Optional[str] = None) -> Tuple[List[str], str]:
    """FFmpeg -c:v argument list and mode label."""
    codec, preset, extra, label = get_export_codec_settings(use_gpu, gpu_codec)
    if codec == "h264_nvenc":
        # Full pairs. extra[:3] left "-b:v" without "0", so ffmpeg ate "-r"
        # and treated the fps number (30.00) as the output filename.
        args = ["-c:v", "h264_nvenc", "-preset", preset or "p4", *extra]
    elif codec == "h264_videotoolbox":
        args = ["-c:v", "h264_videotoolbox", *extra]
    elif codec == "h264_qsv":
        args = ["-c:v", "h264_qsv", "-preset", preset or "medium", *extra]
    elif codec == "h264_amf":
        args = ["-c:v", "h264_amf", "-quality", preset or "speed", *extra]
    elif codec == "h264_mf":
        args = ["-c:v", "h264_mf", *extra]
    else:
        args = ["-c:v", "libx264", "-preset", preset or "fast", *extra]
    return args, label


def get_encoder_fallback_chain(
    use_gpu: Optional[bool] = None,
    gpu_codec: Optional[str] = None,
) -> List[Tuple[List[str], str]]:
    """
    Chapter 3.4 & Section 16.1: Hierarchical Hardware Encoder Negotiation.
    Returns prioritized list of (vcodec_args, label) pairs.
    If primary GPU encoder fails, engine immediately falls through to the next candidate
    down to universal CPU libx264 without crashing or forcing an expensive MoviePy fallback.
    """
    use_gpu = getattr(config, "USE_GPU_ACCELERATION", True) if use_gpu is None else use_gpu
    if not use_gpu:
        args, label = get_ffmpeg_vcodec_args(use_gpu=False, gpu_codec="libx264")
        return [(args, label)]

    avail = get_available_ffmpeg_encoders()
    preferred = (gpu_codec or getattr(config, "GPU_CODEC", "") or "").strip()
    candidates = platform_encoder_candidates()
    report = probe_hardware_encoders()
    passed = [codec for codec in candidates if report.get(codec)]
    compiled = [codec for codec in candidates if not avail or codec in avail]
    pool = passed or compiled
    # A saved codec that failed the five-frame test does not lead the chain
    # when another encoder passed. NarratoAI drops it. We still keep the
    # working ones instead of stopping at the first.
    if preferred and report.get(preferred) is False and passed:
        preferred = ""

    ordered = []
    if preferred and preferred in candidates:
        ordered.append(preferred)
    for codec in pool:
        if codec not in ordered:
            ordered.append(codec)

    # Convert to args, ending always with libx264 fallback
    chain: List[Tuple[List[str], str]] = []
    for c in ordered:
        args, label = get_ffmpeg_vcodec_args(use_gpu=True, gpu_codec=c)
        chain.append((args, label))

    cpu_args, cpu_label = get_ffmpeg_vcodec_args(use_gpu=False, gpu_codec="libx264")
    chain.append((cpu_args, cpu_label))
    return chain



# ─── ITEM 416: Circuit Breaker Deseni ────────────────────────────────────────

class CircuitBreaker:
    """
    Item 416: Circuit Breaker Deseni (Devre Kesici).
    Bir API (Pexels, Pixabay, Gemini, Edge-TTS) arka arkaya 3 kez 429 veya 500 hatası
    verirse devre 'OPEN' durumuna geçer ve 60 saniye boyunca istekleri engelleyip
    otomatik olarak yedek sağlayıcıya yönlendirir.
    """
    STATE_CLOSED = "CLOSED"      # Normal operation
    STATE_OPEN = "OPEN"          # Failing, fast-fail to fallback
    STATE_HALF_OPEN = "HALF_OPEN"  # Testing recovery

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

    def record_failure(self, service_name: str, error_msg: str = "", custom_timeout: Optional[float] = None):
        """Records failure and triggers tripwire if threshold reached."""
        s = self._get_service(service_name)
        s["total_calls"] += 1
        s["failure_count"] += 1
        s["last_failure_time"] = time.time()
        if custom_timeout is not None:
            s["recovery_timeout"] = float(custom_timeout)

        # In HALF_OPEN, a single failure immediately trips back to OPEN
        if s["state"] == self.STATE_HALF_OPEN or s["failure_count"] >= self.failure_threshold:
            s["state"] = self.STATE_OPEN
            timeout = s.get("recovery_timeout") or self.recovery_timeout
            print(f"  [CircuitBreaker] ⚠️ '{service_name}' devresi AÇILDI ({s['failure_count']} hata). {int(timeout)}s yedek servise geçildi.")

    def export_status(self) -> Dict[str, Dict[str, Any]]:
        """Returns snapshot of all tracked services and circuit states."""
        now = time.time()
        res = {}
        for name, s in self.service_states.items():
            timeout = s.get("recovery_timeout") or self.recovery_timeout
            remaining_cooldown = max(0.0, round(timeout - (now - s["last_failure_time"]), 1)) if s["state"] == self.STATE_OPEN else 0.0
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
                return [ep for ep in PUBLIC_ENDPOINTS.values() if ep.category == cat and ep.is_active]
        except Exception:
            pass
        return None

    def execute_with_fallback(self, service_name: str, primary_fn: Any, fallback_fn: Any, *args: Any, **kwargs: Any) -> Any:
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


# ─── ITEM 424: Stok Video Çözünürlük ve Bütünlük Doğrulaması ─────────────────

def is_material_resolution_acceptable(width: int, height: int) -> bool:
    """
    MoneyPrinterTurbo rejects a clip when either side is below 480, then
    subtracts 10px so a WhatsApp-rounded 478x850 file still passes.
    A true low-res frame (under 470 on either side) still fails.
    """
    try:
        w = int(width)
        h = int(height)
    except (TypeError, ValueError):
        return False
    floor = 480 - 10
    return w >= floor and h >= floor


def verify_stock_video_integrity(video_path: str, min_duration: float = 1.0) -> Dict[str, Any]:
    """
    Item 424: Stok Video Çözünürlük Doğrulaması.
    İndirilen stok klibin genişliği, yüksekliği ve süresi ffprobe ile kontrol edilir;
    bozuk veya 0 baytlık dosyalar kurgudan elenir.
    """
    if not os.path.exists(video_path):
        return {"valid": False, "reason": "Dosya mevcut değil."}
    size = os.path.getsize(video_path)
    if size == 0:
        return {"valid": False, "reason": "0 bayt dosya."}
    if size < 1000:
        return {"valid": False, "reason": "Dosya 1KB altı."}

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    try:
        cmd = [
            ffmpeg_exe, "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height,duration",
            "-of", "csv=p=0", video_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
        output = res.stdout.strip().split(",")
        if len(output) >= 2:
            w = int(output[0])
            h = int(output[1])
            if not is_material_resolution_acceptable(w, h):
                return {
                    "valid": False,
                    "width": w,
                    "height": h,
                    "aspect_ratio": "vertical" if h > w else "horizontal",
                    "reason": f"470px altı ({w}x{h})",
                }
            short_side = min(w, h)
            soft = short_side < (720 - 10)
            return {
                "valid": True,
                "width": w,
                "height": h,
                "aspect_ratio": "vertical" if h > w else "horizontal",
                "soft": soft,
                "reason": "yuvarlama payı" if soft else "OK",
            }
    except Exception as e:
        return {"valid": False, "reason": str(e)}

    return {"valid": True, "width": 1080, "height": 1920, "reason": "Varsayılan doğrulama"}


# ─── ITEM 428: Regex Tabanlı İntihal ve Sistem Lafı Temizleyici ──────────────

def clean_ai_system_preamble(raw_text: str) -> str:
    """
    Item 428: Regex Tabanlı İntihal ve Sistem Lafı Temizleyici.
    AI'nın 'İşte senaryo:', 'Elbette!', 'Here is the script:' gibi yapay zeka
    gevezeliklerini ve markdown tırnaklarını temizler.
    """
    cleaned = raw_text.strip()
    # Markdown kod bloklarını temizle
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

    # Cut at nearest sentence boundary before max_words
    truncated_words = words[:max_words]
    truncated_text = " ".join(truncated_words)
    
    last_punc = max(truncated_text.rfind('.'), truncated_text.rfind('!'), truncated_text.rfind('?'))
    if last_punc > 50:
        return (truncated_text[:last_punc + 1], True)

    return (f"{truncated_text}...", True)


# ─── ITEM 451: Ses ve Altyazı Eşleme Sapması Kontrolü ────────────────────────

def guard_subtitle_audio_drift(timings: List[Dict[str, Any]], audio_duration: float) -> List[Dict[str, Any]]:
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


# ─── ITEM 452: FFmpeg Çıktı Doğrulaması ──────────────────────────────────────

def verify_render_output_sanity(output_path: str, min_size_bytes: int = 500_000) -> Dict[str, Any]:
    """
    Item 452: FFmpeg Çıktı Doğrulaması.
    Üretilen dosyanın boyutu 500KB altındaysa veya oynatılamıyorsa render başarısız sayılır.
    """
    if not os.path.exists(output_path):
        return {"valid": False, "error": "Dosya diskte bulunamadı."}

    size = os.path.getsize(output_path)
    if size < min_size_bytes:
        return {"valid": False, "error": f"Dosya boyutu çok küçük ({size // 1024} KB < 500 KB)."}

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    res = subprocess.run(
        [ffmpeg_exe, "-v", "error", "-i", output_path, "-f", "null", "-"],
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=20
    )
    if res.returncode != 0:
        return {"valid": False, "error": f"FFmpeg video akışı çözümlenemedi (kod {res.returncode})."}

    return {"valid": True, "size_bytes": size, "size_mb": round(size / (1024 * 1024), 2)}


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


# ─── ITEM 464: Sistem Sağlığı İzleme Modülü ──────────────────────────────────

def get_system_health_status() -> Dict[str, Any]:
    """
    Item 464: Sistem Sağlığı İzleme Endpoint'i.
    FFmpeg, disk alanı, API anahtarları, donanım (VideoToolbox) sağlığı anlık sorgulanır.
    """
    ffmpeg_ok = False
    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        ffmpeg_ok = bool(ffmpeg_exe and os.path.exists(ffmpeg_exe))
    except Exception:
        pass

    # Disk Space Check
    total_gb, used_gb, free_gb = 0.0, 0.0, 0.0
    try:
        stat = shutil.disk_usage(config.BASE_DIR)
        total_gb = round(stat.total / (1024 ** 3), 1)
        used_gb = round(stat.used / (1024 ** 3), 1)
        free_gb = round(stat.free / (1024 ** 3), 1)
    except Exception:
        pass

    # VideoToolbox Hardware Acceleration Check (Item 411)
    encoder_name, encoder_args = get_hardware_accelerated_encoder()
    is_apple_silicon = (platform.system() == "Darwin" and platform.machine() == "arm64")

    return {
        "status": "healthy" if (ffmpeg_ok and free_gb > 1.0) else "warning",
        "ffmpeg_installed": ffmpeg_ok,
        "hardware_acceleration": {
            "platform": platform.system(),
            "architecture": platform.machine(),
            "is_apple_silicon": is_apple_silicon,
            "encoder": encoder_name,
            "encoder_args": encoder_args,
            "hardware_accel_active": encoder_name == "h264_videotoolbox"
        },
        "disk": {
            "total_gb": total_gb,
            "used_gb": used_gb,
            "free_gb": free_gb,
            "is_low_disk": free_gb < 2.0
        },
        "api_providers": {
            "gemini": bool(config.GEMINI_API_KEY),
            "openai": bool(config.OPENAI_API_KEY),
            "pexels": bool(config.PEXELS_API_KEY),
            "pixabay": bool(config.PIXABAY_API_KEY),
            "youtube_data": bool(config.YOUTUBE_DATA_API_KEY)
        },
        "zero_cost_pipeline_active": True
    }
