"""
MiniMax-H3 Local-First Speech & Video Generation Service.
Implements Bölüm 34.1 & 34.3: Local MiniMax-H3 inference, hardware/VRAM validation,
and safe fallback to Edge-TTS + stock/procedural video engine.

This PC serves H3 through ComfyUI on 127.0.0.1:8188
(F:\\MiniMax-H3\\start_comfy.bat). The studio starts that process only when
the user presses the button. A port that is already open is left alone.
"""
from __future__ import annotations

import logging
import os
import socket
import subprocess
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("MiniMaxH3Local")

DEFAULT_MODEL_REPO = "MiniMaxAI/MiniMax-H3"
DEFAULT_LOCAL_URL = "http://127.0.0.1:8188"
SGLANG_URL = "http://127.0.0.1:30010"
COMFY_HOST = "127.0.0.1"
COMFY_PORT = 8188
COMFY_BAT = r"F:\MiniMax-H3\start_comfy.bat"
COMFY_CWD = r"F:\MiniMax-H3\ComfyUI"
COMFY_PYTHON = r"F:\MiniMax-H3\venv\Scripts\python.exe"
MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", "minimax-h3")

_comfy_proc: Optional[subprocess.Popen] = None


@dataclass
class HardwareSuitability:
    can_run_local: bool
    vram_mb: int
    recommended_quantization: str  # "fp16", "bf16", "8bit", "4bit", "none"
    message: str
    has_nvidia: bool


def assess_minimax_h3_hardware() -> HardwareSuitability:
    """
    Checks GPU and VRAM capacity to decide whether MiniMax-H3 can run locally
    and which quantization profile is recommended.
    """
    try:
        from hardware_detector import get_gpu_info
        gpu_info = get_gpu_info()
    except Exception as exc:
        logger.warning(f"[MiniMaxH3] Failed to query hardware: {exc}")
        gpu_info = {"vram_mb": 0, "has_nvidia": False, "name": "Unknown"}

    vram_mb = gpu_info.get("vram_mb", 0)
    has_nvidia = gpu_info.get("has_nvidia", False)

    if not has_nvidia:
        return HardwareSuitability(
            can_run_local=False,
            vram_mb=0,
            recommended_quantization="none",
            message="NVIDIA GPU tespit edilemedi. MiniMax-H3 yerel çıkarımı için NVIDIA CUDA gereklidir.",
            has_nvidia=False,
        )

    if vram_mb >= 16000:
        return HardwareSuitability(
            can_run_local=True,
            vram_mb=vram_mb,
            recommended_quantization="fp16",
            message=f"VRAM yeterli ({vram_mb} MB). Tam hassasiyet (FP16/BF16) destekleniyor.",
            has_nvidia=True,
        )
    elif vram_mb >= 8000:
        return HardwareSuitability(
            can_run_local=True,
            vram_mb=vram_mb,
            recommended_quantization="4bit",
            message=f"VRAM orta seviye ({vram_mb} MB). 4-bit / 8-bit kuantizasyon (AWQ/bitsandbytes) önerilir.",
            has_nvidia=True,
        )
    else:
        return HardwareSuitability(
            can_run_local=False,
            vram_mb=vram_mb,
            recommended_quantization="none",
            message=f"VRAM yetersiz ({vram_mb} MB < 8000 MB). Sistem kilitlenmesini önlemek için Edge-TTS + FFmpeg fallback devrede.",
            has_nvidia=True,
        )


def is_model_cached_locally(model_dir: Optional[str] = None) -> bool:
    """Checks if MiniMax-H3 model weights exist in local cache directory."""
    target_dir = model_dir or MODELS_DIR
    if not os.path.isdir(target_dir):
        return False
    # Check for weights or config files
    files = os.listdir(target_dir)
    return any(f.endswith(".safetensors") or f.endswith(".bin") or f == "config.json" for f in files)


def comfy_port_open(timeout: float = 0.4) -> bool:
    """True when something is already listening on ComfyUI's port."""
    try:
        with socket.create_connection((COMFY_HOST, COMFY_PORT), timeout=timeout):
            return True
    except OSError:
        return False


def comfy_launch_argv() -> List[str]:
    """Bat when it exists, otherwise the venv python that the bat calls."""
    if os.path.isfile(COMFY_BAT):
        return [COMFY_BAT]
    return [COMFY_PYTHON, "main.py", "--listen", COMFY_HOST, "--port", str(COMFY_PORT)]


def comfy_phase() -> str:
    """up, starting, failed, or offline. Never starts a process."""
    if comfy_port_open():
        return "up"
    proc = _comfy_proc
    if proc is not None:
        if proc.poll() is None:
            return "starting"
        return "failed"
    return "offline"


def start_comfyui_server() -> Dict[str, Any]:
    """Start ComfyUI only when port 8188 is closed. Never spawn a second copy."""
    global _comfy_proc
    url = DEFAULT_LOCAL_URL
    if comfy_port_open():
        return {
            "status": "up",
            "already_running": True,
            "spawned": False,
            "server_url": url,
            "message": "ComfyUI zaten 127.0.0.1:8188 üzerinde dinliyor.",
        }
    argv = comfy_launch_argv()
    joined = " ".join(argv).lower()
    if "sglang" in joined:
        return {
            "status": "failed",
            "already_running": False,
            "spawned": False,
            "server_url": url,
            "message": "Başlatma komutu SGLang olamaz.",
        }
    try:
        flags = 0
        if os.name == "nt":
            flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        _comfy_proc = subprocess.Popen(
            argv,
            cwd=COMFY_CWD if os.path.isdir(COMFY_CWD) else None,
            creationflags=flags,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.info("[MiniMaxH3] ComfyUI başlatılıyor: %s", argv)
        return {
            "status": "starting",
            "already_running": False,
            "spawned": True,
            "server_url": url,
            "command": argv,
            "message": "ComfyUI başlıyor (F:\\MiniMax-H3\\start_comfy.bat).",
        }
    except Exception as exc:
        _comfy_proc = None
        logger.error("[MiniMaxH3] ComfyUI başlatılamadı: %s", exc)
        return {
            "status": "failed",
            "already_running": False,
            "spawned": False,
            "server_url": url,
            "message": str(exc),
        }


def check_local_server_status() -> Dict[str, Any]:
    """ComfyUI on 8188. Does not start the server."""
    try:
        phase = comfy_phase()
        return {
            "server_url": DEFAULT_LOCAL_URL,
            "is_running": phase == "up",
            "status": "ready" if phase == "up" else phase,
            "phase": phase,
            "backend": "comfyui",
        }
    except Exception as exc:
        return {
            "server_url": DEFAULT_LOCAL_URL,
            "is_running": False,
            "status": f"error: {exc}",
            "phase": "failed",
            "backend": "comfyui",
        }


def generate_local_minimax_h3(
    prompt: str,
    output_path: str,
    *,
    duration: float = 5.0,
    aspect: str = "9:16",
    mood: str = "",
    seed: Optional[int] = None,
) -> Optional[str]:
    """
    Main invocation entry point for local MiniMax-H3 generation.
    Checks hardware safety and local server readiness.
    If server is offline or hardware insufficient, returns None gracefully.
    """
    suitability = assess_minimax_h3_hardware()
    if not suitability.can_run_local:
        logger.info(f"[MiniMaxH3] Skipping local generation: {suitability.message}")
        return None

    server_status = check_local_server_status()
    if not server_status["is_running"]:
        logger.info(
            f"[MiniMaxH3] ComfyUI ({server_status['server_url']}) çevrimdışı. "
            "Stüdyodaki düğme F:\\MiniMax-H3\\start_comfy.bat başlatır. Stok hatta düşülüyor."
        )
        return None

    try:
        from visuals.ai_video.providers.minimax_h3 import generate_local_h3_clip
        full_prompt = f"{prompt} [Mood: {mood}]" if mood else prompt
        return generate_local_h3_clip(
            prompt=full_prompt,
            output_path=output_path,
            duration=duration,
            aspect=aspect,
            seed=seed,
        )
    except Exception as exc:
        logger.error(f"[MiniMaxH3] Üretim hatası: {exc}")
        return None
