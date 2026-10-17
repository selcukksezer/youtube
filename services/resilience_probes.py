"""Hardware encoder negotiation, FFmpeg media probes, and system health diagnostics."""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

import imageio_ffmpeg
import config


def _sr_attr(name: str, default: Any) -> Any:
    mod = sys.modules.get("system_resilience")
    return getattr(mod, name, default) if mod is not None else default


def _sr_set(name: str, value: Any) -> None:
    mod = sys.modules.get("system_resilience")
    if mod is not None:
        setattr(mod, name, value)


_ENCODER_LABELS = {
    "h264_nvenc": "NVIDIA NVENC",
    "h264_qsv": "Intel Quick Sync",
    "h264_amf": "AMD AMF",
    "h264_mf": "Windows Media Foundation",
    "h264_videotoolbox": "Apple VideoToolbox",
    "h264_vaapi": "VAAPI",
    "libx264": "CPU libx264",
}


def get_hardware_accelerated_encoder() -> Tuple[str, List[str]]:
    """Item 411: Apple Silicon VideoToolbox / NVIDIA NVENC hardware encoder detection."""
    try:
        from hardware_detector import get_system_hardware_specs

        gpu = get_system_hardware_specs().get("gpu", {})
        if gpu.get("has_videotoolbox"):
            return ("h264_videotoolbox", ["-b:v", "14M", "-allow_sw", "1"])
        if gpu.get("has_nvenc") and os.environ.get("GPU_CODEC", "").strip() == "h264_nvenc":
            return ("h264_nvenc", ["-preset", "p4", "-b:v", "0", "-cq", "20"])
    except Exception:
        pass
    if _sr_attr("platform", platform).system() == "Darwin":
        return ("h264_videotoolbox", ["-b:v", "14M", "-allow_sw", "1"])
    return ("libx264", ["-preset", "fast", "-b:v", "12M"])


def default_gpu_codec_for_platform() -> str:
    """Platform-aware default video encoder (NVENC on Windows NVIDIA, VideoToolbox on macOS)."""
    sys_name = _sr_attr("platform", platform).system()
    if sys_name == "Darwin":
        return "h264_videotoolbox"
    if sys_name == "Windows":
        return "h264_nvenc"
    return "libx264"


def get_export_codec_settings(
    use_gpu: Optional[bool] = None,
    gpu_codec: Optional[str] = None,
) -> Tuple[str, Optional[str], List[str], str]:
    """MoviePy/FFmpeg export codec selection with hardware fallback labels."""
    cfg = _sr_attr("config", config)
    default_fn = _sr_attr("default_gpu_codec_for_platform", default_gpu_codec_for_platform)
    use_gpu = getattr(cfg, "USE_GPU_ACCELERATION", True) if use_gpu is None else use_gpu
    gpu_codec = (gpu_codec or getattr(cfg, "GPU_CODEC", "") or default_fn()).strip()

    if not use_gpu or gpu_codec == "libx264":
        return (
            "libx264",
            "fast",
            ["-crf", "21", "-tune", "fastdecode", "-pix_fmt", "yuv420p"],
            f"CPU libx264 (threads={getattr(cfg, 'RENDER_THREADS', 8)})",
        )
    if gpu_codec == "h264_nvenc":
        return (
            "h264_nvenc",
            "p5",
            ["-tune", "hq", "-cq", "21", "-b:v", "0", "-spatial-aq", "1", "-temporal-aq", "1", "-pix_fmt", "yuv420p"],
            "NVIDIA NVENC",
        )
    if gpu_codec == "h264_videotoolbox":
        return ("h264_videotoolbox", None, ["-b:v", "14M", "-allow_sw", "1", "-pix_fmt", "yuv420p"], "Apple VideoToolbox")
    if gpu_codec == "h264_qsv":
        return ("h264_qsv", "medium", ["-global_quality", "22", "-look_ahead", "1", "-pix_fmt", "yuv420p"], "Intel QuickSync (QSV)")
    if gpu_codec == "h264_amf":
        return ("h264_amf", "speed", ["-rc", "cqp", "-qp_i", "20", "-qp_p", "22", "-pix_fmt", "yuv420p"], "AMD AMF")
    if gpu_codec == "h264_mf":
        return ("h264_mf", None, ["-b:v", "12M", "-pix_fmt", "yuv420p"], "Windows Media Foundation (h264_mf)")
    return ("libx264", "fast", ["-crf", "21", "-tune", "fastdecode", "-pix_fmt", "yuv420p"], "CPU libx264")


def platform_encoder_candidates() -> List[str]:
    system = _sr_attr("platform", platform).system()
    if system == "Darwin":
        return ["h264_videotoolbox"]
    if system == "Windows":
        return ["h264_nvenc", "h264_qsv", "h264_amf", "h264_mf"]
    return ["h264_nvenc", "h264_vaapi", "h264_qsv"]


def _tiny_encoder_ok(ffmpeg: str, codec: str) -> bool:
    """Five-frame null encode. A name in `ffmpeg -encoders` is not a working chip."""
    vcodec_fn = _sr_attr("get_ffmpeg_vcodec_args", get_ffmpeg_vcodec_args)
    subproc = _sr_attr("subprocess", subprocess)
    args, _label = vcodec_fn(use_gpu=True, gpu_codec=codec)
    cmd = [
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "testsrc=duration=0.4:size=128x72:rate=15",
        "-frames:v", "5", *args, "-f", "null", "-",
    ]
    try:
        proc = subproc.run(cmd, capture_output=True, text=True, timeout=12)
    except Exception:
        return False
    return proc.returncode == 0


def probe_hardware_encoders(force: bool = False) -> Dict[str, bool]:
    """Probe all platform candidate encoders with a five-frame test."""
    cache = _sr_attr("_ENCODER_PROBE_CACHE", None)
    if cache is not None and not force and any(v for k, v in cache.items() if k != "libx264"):
        return dict(cache)
    avail_fn = _sr_attr("get_available_ffmpeg_encoders", get_available_ffmpeg_encoders)
    cand_fn = _sr_attr("platform_encoder_candidates", platform_encoder_candidates)
    tiny_fn = _sr_attr("_tiny_encoder_ok", _tiny_encoder_ok)
    img_ffmpeg = _sr_attr("imageio_ffmpeg", imageio_ffmpeg)
    listed = avail_fn()
    try:
        ffmpeg = img_ffmpeg.get_ffmpeg_exe()
    except Exception:
        ffmpeg = "ffmpeg"
    report: Dict[str, bool] = {}
    for codec in cand_fn():
        if listed and codec not in listed:
            report[codec] = False
            continue
        report[codec] = tiny_fn(ffmpeg, codec)
    report["libx264"] = True if not listed else ("libx264" in listed)
    if any(v for k, v in report.items() if k != "libx264"):
        _sr_set("_ENCODER_PROBE_CACHE", report)
    return dict(report)


def encoder_choices() -> List[Dict[str, Any]]:
    probe_fn = _sr_attr("probe_hardware_encoders", probe_hardware_encoders)
    cand_fn = _sr_attr("platform_encoder_candidates", platform_encoder_candidates)
    report = probe_fn()
    return [
        {"id": codec, "label": _ENCODER_LABELS.get(codec, codec), "available": bool(report.get(codec))}
        for codec in list(cand_fn()) + ["libx264"]
    ]


def get_available_ffmpeg_encoders() -> set:
    """Probes FFmpeg binary once to find compiled video encoders."""
    cache = _sr_attr("_AVAILABLE_ENCODERS_CACHE", None)
    if cache:
        return cache
    encoders: set = set()
    img_ffmpeg = _sr_attr("imageio_ffmpeg", imageio_ffmpeg)
    subproc = _sr_attr("subprocess", subprocess)
    try:
        exe = img_ffmpeg.get_ffmpeg_exe()
        res = subproc.run([exe, "-encoders"], capture_output=True, text=True, timeout=5)
        for line in (res.stdout or "").splitlines():
            line_str = line.strip()
            if line_str.startswith("V"):
                parts = line_str.split()
                if len(parts) >= 2:
                    encoders.add(parts[1])
    except Exception:
        pass
    if encoders:
        _sr_set("_AVAILABLE_ENCODERS_CACHE", encoders)
    return encoders


def get_ffmpeg_loglevel() -> str:
    """Item 437: warning in debug mode, error in production."""
    debug = os.getenv("FFMPEG_DEBUG", "false").lower() in ("true", "1", "yes")
    return "warning" if debug else "error"


def get_ffmpeg_vcodec_args(
    use_gpu: Optional[bool] = None, gpu_codec: Optional[str] = None
) -> Tuple[List[str], str]:
    """FFmpeg -c:v argument list and mode label."""
    settings_fn = _sr_attr("get_export_codec_settings", get_export_codec_settings)
    codec, preset, extra, label = settings_fn(use_gpu, gpu_codec)
    if codec == "h264_nvenc":
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
    """Chapter 3.4 & Section 16.1: Hierarchical Hardware Encoder Negotiation."""
    cfg = _sr_attr("config", config)
    vcodec_fn = _sr_attr("get_ffmpeg_vcodec_args", get_ffmpeg_vcodec_args)
    avail_fn = _sr_attr("get_available_ffmpeg_encoders", get_available_ffmpeg_encoders)
    cand_fn = _sr_attr("platform_encoder_candidates", platform_encoder_candidates)
    probe_fn = _sr_attr("probe_hardware_encoders", probe_hardware_encoders)

    use_gpu = getattr(cfg, "USE_GPU_ACCELERATION", True) if use_gpu is None else use_gpu
    if not use_gpu:
        args, label = vcodec_fn(use_gpu=False, gpu_codec="libx264")
        return [(args, label)]

    avail = avail_fn()
    preferred = (gpu_codec or getattr(cfg, "GPU_CODEC", "") or "").strip()
    candidates = cand_fn()
    report = probe_fn() or {}
    candidate_order = list(
        dict.fromkeys(
            list(candidates) + [c for c in report.keys() if c and c != "libx264"]
        )
    )
    passed = [codec for codec in candidate_order if report.get(codec)]
    compiled = [codec for codec in candidate_order if not avail or codec in avail]
    pool = passed if passed else (compiled or list(candidates)[:1])
    if preferred and report.get(preferred) is False:
        preferred = ""

    ordered = []
    if preferred and (preferred in candidate_order) and report.get(preferred, True) is not False:
        ordered.append(preferred)
    for codec in pool:
        if codec not in ordered:
            ordered.append(codec)

    chain: List[Tuple[List[str], str]] = [vcodec_fn(use_gpu=True, gpu_codec=c) for c in ordered]
    chain.append(vcodec_fn(use_gpu=False, gpu_codec="libx264"))
    return chain


def is_material_resolution_acceptable(width: int, height: int) -> bool:
    """Rejects clip when either side is below 470px (480 - 10 rounding tolerance)."""
    try:
        w, h = int(width), int(height)
    except (TypeError, ValueError):
        return False
    return w >= 470 and h >= 470


def verify_stock_video_integrity(video_path: str, min_duration: float = 1.0) -> Dict[str, Any]:
    """Item 424: Stok Video Çözünürlük Doğrulaması."""
    if not os.path.exists(video_path):
        return {"valid": False, "reason": "Dosya mevcut değil."}
    size = os.path.getsize(video_path)
    if size == 0:
        return {"valid": False, "reason": "0 bayt dosya."}
    if size < 1000:
        return {"valid": False, "reason": "Dosya 1KB altı."}

    img_ffmpeg = _sr_attr("imageio_ffmpeg", imageio_ffmpeg)
    subproc = _sr_attr("subprocess", subprocess)
    res_check_fn = _sr_attr("is_material_resolution_acceptable", is_material_resolution_acceptable)
    ffmpeg_exe = img_ffmpeg.get_ffmpeg_exe()
    try:
        cmd = [
            ffmpeg_exe, "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height,duration", "-of", "csv=p=0", video_path,
        ]
        res = subproc.run(cmd, stdout=subproc.PIPE, stderr=subproc.PIPE, text=True, timeout=10)
        output = res.stdout.strip().split(",")
        if len(output) >= 2:
            w, h = int(output[0]), int(output[1])
            if not res_check_fn(w, h):
                return {
                    "valid": False, "width": w, "height": h,
                    "aspect_ratio": "vertical" if h > w else "horizontal",
                    "reason": f"470px altı ({w}x{h})",
                }
            soft = min(w, h) < 710
            return {
                "valid": True, "width": w, "height": h,
                "aspect_ratio": "vertical" if h > w else "horizontal",
                "soft": soft, "reason": "yuvarlama payı" if soft else "OK",
            }
    except Exception as e:
        return {"valid": False, "reason": str(e)}
    return {"valid": True, "width": 1080, "height": 1920, "reason": "Varsayılan doğrulama"}


def verify_render_output_sanity(output_path: str, min_size_bytes: int = 500_000) -> Dict[str, Any]:
    """Item 452: FFmpeg Çıktı Doğrulaması."""
    if not os.path.exists(output_path):
        return {"valid": False, "error": "Dosya diskte bulunamadı."}
    size = os.path.getsize(output_path)
    if size < min_size_bytes:
        return {"valid": False, "error": f"Dosya boyutu çok küçük ({size // 1024} KB < 500 KB)."}

    img_ffmpeg = _sr_attr("imageio_ffmpeg", imageio_ffmpeg)
    subproc = _sr_attr("subprocess", subprocess)
    ffmpeg_exe = img_ffmpeg.get_ffmpeg_exe()
    res = subproc.run(
        [ffmpeg_exe, "-v", "error", "-i", output_path, "-f", "null", "-"],
        stdout=subproc.DEVNULL, stderr=subproc.PIPE, timeout=20,
    )
    if res.returncode != 0:
        return {"valid": False, "error": f"FFmpeg video akışı çözümlenemedi (kod {res.returncode})."}
    return {"valid": True, "size_bytes": size, "size_mb": round(size / (1024 * 1024), 2)}


def get_system_health_status() -> Dict[str, Any]:
    """Item 464: Sistem Sağlığı İzleme Endpoint'i."""
    img_ffmpeg = _sr_attr("imageio_ffmpeg", imageio_ffmpeg)
    sh = _sr_attr("shutil", shutil)
    plat = _sr_attr("platform", platform)
    cfg = _sr_attr("config", config)
    hw_fn = _sr_attr("get_hardware_accelerated_encoder", get_hardware_accelerated_encoder)

    ffmpeg_ok = False
    try:
        ffmpeg_exe = img_ffmpeg.get_ffmpeg_exe()
        ffmpeg_ok = bool(ffmpeg_exe and os.path.exists(ffmpeg_exe))
    except Exception:
        pass

    total_gb, used_gb, free_gb = 0.0, 0.0, 0.0
    try:
        stat = sh.disk_usage(cfg.BASE_DIR)
        total_gb = round(stat.total / (1024 ** 3), 1)
        used_gb = round(stat.used / (1024 ** 3), 1)
        free_gb = round(stat.free / (1024 ** 3), 1)
    except Exception:
        pass

    encoder_name, encoder_args = hw_fn()
    is_apple_silicon = plat.system() == "Darwin" and plat.machine() == "arm64"

    return {
        "status": "healthy" if (ffmpeg_ok and free_gb > 1.0) else "warning",
        "ffmpeg_installed": ffmpeg_ok,
        "hardware_acceleration": {
            "platform": plat.system(),
            "architecture": plat.machine(),
            "is_apple_silicon": is_apple_silicon,
            "encoder": encoder_name,
            "encoder_args": encoder_args,
            "hardware_accel_active": encoder_name == "h264_videotoolbox",
        },
        "disk": {"total_gb": total_gb, "used_gb": used_gb, "free_gb": free_gb, "is_low_disk": free_gb < 2.0},
        "api_providers": {
            "gemini": bool(cfg.GEMINI_API_KEY),
            "openai": bool(cfg.OPENAI_API_KEY),
            "pexels": bool(cfg.PEXELS_API_KEY),
            "pixabay": bool(cfg.PIXABAY_API_KEY),
            "youtube_data": bool(cfg.YOUTUBE_DATA_API_KEY),
        },
        "zero_cost_pipeline_active": True,
    }
