"""Optional local MiniMax-H3. Not part of the default stock or AI chain.

The studio visual engine must be set to minimax_h3 (or mixed) before render.
This PC runs ComfyUI, not SGLang:

    F:\\MiniMax-H3\\start_comfy.bat
    http://127.0.0.1:8188

The graph loads the installed FL2VA int8 diffusion model, the NVFP4 text
encoder, and both VAEs. Text-to-video includes native audio. If ComfyUI is
down, SGLang on port 30010 is used only when that process is already up.
Otherwise the caller falls back to stock fetch.
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Callable, Optional

import requests

from ..http_util import write_bytes

_COMFY_URL = "http://127.0.0.1:8188"
_SGLANG_URL = "http://127.0.0.1:30010"
_MODEL = "MiniMaxAI/MiniMax-H3"

FL2VA_FILE = "minimax_h3_fl2va_pruned_int8_convrot.safetensors"
TEXT_ENCODER_FILE = "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors"
VIDEO_VAE_FILE = "minimax_h3_video_vae_fp16.safetensors"
AUDIO_VAE_FILE = "minimax_h3_audio_vae_fp32.safetensors"

# One RTX 3070. Parallel /prompt calls lock the GPU and never return.
_COMFY_LOCK = threading.Lock()
_COMFY_HOLDER = ""
COMFY_CONNECT_TIMEOUT = 5.0
COMFY_POLL_TIMEOUT = 900.0


def comfy_base_url() -> str:
    try:
        import config
        url = str(getattr(config, "MINIMAX_H3_COMFY_URL", "") or "").strip()
    except Exception:
        url = ""
    return (url or _COMFY_URL).rstrip("/")


def local_base_url() -> str:
    """SGLang base URL. Optional extra path only."""
    try:
        import config
        url = str(getattr(config, "MINIMAX_H3_LOCAL_URL", "") or "").strip()
    except Exception:
        url = ""
    return (url or _SGLANG_URL).rstrip("/")


def local_model_id() -> str:
    try:
        import config
        model = str(getattr(config, "MINIMAX_H3_MODEL", "") or "").strip()
    except Exception:
        model = ""
    return model or _MODEL


def _clamp_seconds(duration: float) -> float:
    return float(max(4.0, min(15.0, duration or 5.0)))


def h3_frame_length(duration: float, min_seconds: float = 3.0) -> int:
    """24 fps length snapped up onto the model's 17k+5 grid."""
    dur = float(max(min_seconds, min(15.0, duration or 5.0)))
    frames = max(5, int(round(dur * 24)))
    return frames + (5 - (frames % 17)) % 17


def canvas_9_16() -> tuple[int, int]:
    """768 short edge, 768x1344 area cap, multiple of 32."""
    return 768, 1344


def build_comfy_t2va_prompt(
    prompt: str,
    *,
    duration: float = 5.0,
    seed: Optional[int] = None,
    filename_prefix: str = "video/MiniMax_H3",
    width: Optional[int] = None,
    height: Optional[int] = None,
    length: Optional[int] = None,
) -> dict[str, Any]:
    def_w, def_h = canvas_9_16()
    w = int(width or def_w)
    h = int(height or def_h)
    l = int(length or h3_frame_length(duration))
    noise_seed = int(seed if seed is not None else 1)
    return {
        "1": {
            "class_type": "UNETLoader",
            "inputs": {
                "unet_name": FL2VA_FILE,
                "weight_dtype": "default",
            },
        },
        "2": {
            "class_type": "MiniMaxH3SigmaShift",
            "inputs": {
                "model": ["1", 0],
                "shift_video": 12.0,
                "shift_audio": 3.0,
            },
        },
        "3": {
            "class_type": "CLIPLoader",
            "inputs": {
                "clip_name": TEXT_ENCODER_FILE,
                "type": "minimax",
                "device": "default",
            },
        },
        "4": {
            "class_type": "VAELoader",
            "inputs": {"vae_name": VIDEO_VAE_FILE},
        },
        "5": {
            "class_type": "VAELoader",
            "inputs": {"vae_name": AUDIO_VAE_FILE},
        },
        "6": {
            "class_type": "MiniMaxH3ImageToVideo",
            "inputs": {
                "clip": ["3", 0],
                "vae": ["4", 0],
                "prompt": prompt,
                "width": w,
                "height": h,
                "length": l,
            },
        },
        "7": {
            "class_type": "KSamplerSelect",
            "inputs": {"sampler_name": "res_multistep"},
        },
        "8": {
            "class_type": "BasicScheduler",
            "inputs": {
                "model": ["2", 0],
                "scheduler": "simple",
                "steps": 20,
                "denoise": 1.0,
            },
        },
        "9": {
            "class_type": "RandomNoise",
            "inputs": {"noise_seed": noise_seed},
        },
        "10": {
            "class_type": "BasicGuider",
            "inputs": {
                "model": ["2", 0],
                "conditioning": ["6", 0],
            },
        },
        "11": {
            "class_type": "SamplerCustomAdvanced",
            "inputs": {
                "noise": ["9", 0],
                "guider": ["10", 0],
                "sampler": ["7", 0],
                "sigmas": ["8", 0],
                "latent_image": ["6", 1],
            },
        },
        "12": {
            "class_type": "VAEDecodeTiled",
            "inputs": {
                "samples": ["11", 0],
                "vae": ["4", 0],
                "tile_size": 256,
                "overlap": 64,
                "temporal_size": 64,
                "temporal_overlap": 8,
            },
        },
        "13": {
            "class_type": "VAEDecodeAudio",
            "inputs": {"samples": ["11", 0], "vae": ["5", 0]},
        },
        "14": {
            "class_type": "CreateVideo",
            "inputs": {
                "images": ["12", 0],
                "fps": 24.0,
                "audio": ["13", 0],
            },
        },
        "15": {
            "class_type": "SaveVideo",
            "inputs": {
                "video": ["14", 0],
                "filename_prefix": filename_prefix,
                "format": "mp4",
                "codec": "auto",
            },
        },
    }


def comfy_server_ready(timeout: float = 1.5) -> bool:
    base = comfy_base_url()
    try:
        response = requests.get(f"{base}/system_stats", timeout=timeout)
        return response.status_code < 500
    except Exception:
        return False


def local_server_ready(timeout: float = 1.5) -> bool:
    """True when optional SGLang on port 30010 is already answering."""
    base = local_base_url()
    for path in ("/health", "/v1/models"):
        try:
            response = requests.get(f"{base}{path}", timeout=timeout)
            if response.status_code < 500:
                return True
        except Exception:
            continue
    return False


def generate_local_h3_clip(
    prompt: str,
    output_path: str,
    *,
    duration: float = 5.0,
    aspect: str = "9:16",
    seed: Optional[int] = None,
    scene_label: str = "",
    cancel_check: Optional[Callable[[], bool]] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    length: Optional[int] = None,
) -> Optional[str]:
    """One text-to-video-with-audio clip. Returns the mp4 path, or None.

    ComfyUI jobs are serialized. A scene waits for the lock. The 5s
    connect timeout runs only after this scene holds the lock, so a busy
    queue is not a dead server. A refused connection or a dead port
    returns None and the caller can fall back to stock. One scene
    failure does not cancel the scenes still waiting.
    """
    if cancel_check and cancel_check():
        return None
    text = (prompt or "").strip()
    if not text:
        return None
    label = (scene_label or "klip").strip()
    return _run_one_h3_job(
        label,
        lambda: _generate_while_lock_held(
            text,
            output_path,
            label,
            duration=duration,
            aspect=aspect,
            seed=seed,
            cancel_check=cancel_check,
            width=width,
            height=height,
            length=length,
        ),
        cancel_check=cancel_check,
    )


def _generate_while_lock_held(
    text: str,
    output_path: str,
    label: str,
    *,
    duration: float,
    aspect: str,
    seed: Optional[int],
    cancel_check: Optional[Callable[[], bool]] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    length: Optional[int] = None,
) -> Optional[str]:
    """Caller holds the ComfyUI lock. Do not probe the port before that."""
    if cancel_check and cancel_check():
        return None
    if comfy_server_ready(timeout=COMFY_CONNECT_TIMEOUT):
        print(f"    [MiniMax-H3] {label}: ComfyUI çalışıyor")
        return _generate_via_comfy(
            text, output_path, duration=duration, seed=seed, scene_label=label,
            cancel_check=cancel_check, width=width, height=height, length=length,
        )
    print(
        f"    [MiniMax-H3] {label}: ComfyUI http://127.0.0.1:8188 kapalı "
        f"veya {COMFY_CONNECT_TIMEOUT:.0f}s içinde açılmadı. Stok hatta düşülüyor."
    )
    if local_server_ready(timeout=1.5):
        print(f"    [MiniMax-H3] {label}: SGLang 30010 zaten açık, ek yol deneniyor")
        print(f"    [MiniMax-H3] {label} üretiliyor")
        return _generate_via_sglang(
            text, output_path, duration=duration, aspect=aspect, seed=seed,
        )
    return None


def _run_one_h3_job(label: str, job, cancel_check: Optional[Callable[[], bool]] = None) -> Optional[str]:
    """Hold the ComfyUI lock for one clip. Waiters block. They do not probe the port."""
    global _COMFY_HOLDER
    if cancel_check and cancel_check():
        return None
    last_wait_log = 0.0
    while not _COMFY_LOCK.acquire(blocking=False):
        if cancel_check and cancel_check():
            return None
        now = time.time()
        if now - last_wait_log >= 30.0:
            holder = _COMFY_HOLDER or "bilinmiyor"
            print(f"    [MiniMax-H3] {label} bekliyor. Kilit {holder} üzerinde.")
            last_wait_log = now
        time.sleep(2.0)
    _COMFY_HOLDER = label
    try:
        if cancel_check and cancel_check():
            return None
        return job()
    finally:
        _COMFY_HOLDER = ""
        _COMFY_LOCK.release()


def _generate_via_comfy(
    prompt: str,
    output_path: str,
    *,
    duration: float,
    seed: Optional[int],
    scene_label: str = "",
    cancel_check: Optional[Callable[[], bool]] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
    length: Optional[int] = None,
) -> Optional[str]:
    base = comfy_base_url()
    graph = build_comfy_t2va_prompt(prompt, duration=duration, seed=seed, width=width, height=height, length=length)
    try:
        if cancel_check and cancel_check():
            return None
        created = requests.post(
            f"{base}/prompt",
            json={"prompt": graph, "client_id": uuid.uuid4().hex},
            timeout=COMFY_CONNECT_TIMEOUT,
        )
        if created.status_code not in (200, 201):
            print(f"    [MiniMax-H3] ComfyUI HTTP {created.status_code}: {created.text[:180]}")
            return None
        body = created.json() or {}
        if body.get("node_errors"):
            print(f"    [MiniMax-H3] ComfyUI düğüm hatası: {str(body.get('node_errors'))[:180]}")
            return None
        prompt_id = str(body.get("prompt_id") or "").strip()
        if not prompt_id:
            print("    [MiniMax-H3] ComfyUI prompt kimliği vermedi")
            return None
        saved = _wait_comfy_video(
            base, prompt_id, timeout=COMFY_POLL_TIMEOUT, scene_label=scene_label,
            cancel_check=cancel_check,
        )
        if not saved:
            return None
        media = requests.get(f"{base}/view", params=saved, timeout=180)
        if media.status_code != 200 or not media.content:
            print(f"    [MiniMax-H3] ComfyUI içerik HTTP {media.status_code}")
            return None
        if write_bytes(media.content, output_path):
            return output_path
    except Exception as exc:
        print(f"    [MiniMax-H3] ComfyUI ulaşılamadı: {exc}")
    return None


def _wait_comfy_video(
    base: str,
    prompt_id: str,
    timeout: float = COMFY_POLL_TIMEOUT,
    scene_label: str = "",
    cancel_check: Optional[Callable[[], bool]] = None,
) -> Optional[dict]:
    deadline = time.time() + timeout
    last_note = time.time()
    while time.time() < deadline:
        if cancel_check and cancel_check():
            who = f"{scene_label}: " if scene_label else ""
            print(f"    [MiniMax-H3] {who}Render iptal isteği algılandı, ComfyUI durduruluyor...")
            try:
                requests.post(f"{base}/interrupt", timeout=2.0)
            except Exception:
                pass
            return None
        try:
            response = requests.get(f"{base}/history/{prompt_id}", timeout=COMFY_CONNECT_TIMEOUT)
            if response.status_code != 200:
                time.sleep(4.0)
                continue
            entry = (response.json() or {}).get(prompt_id) or {}
            status = str((entry.get("status") or {}).get("status_str") or "").lower()
            if status in ("error", "failed"):
                print(f"    [MiniMax-H3] ComfyUI üretim durumu: {status}")
                return None
            found = _video_from_history(entry)
            if found:
                return found
            if status == "success":
                print("    [MiniMax-H3] ComfyUI video dosyası vermedi")
                return None
        except Exception:
            pass
        now = time.time()
        if now - last_note >= 30.0:
            left = max(0, int(deadline - now))
            who = f"{scene_label}: " if scene_label else ""
            print(f"    [MiniMax-H3] {who}ComfyUI çalışıyor ({prompt_id}, kalan {left}s)")
            last_note = now
        time.sleep(4.0)
    print("    [MiniMax-H3] ComfyUI üretim zaman aşımı")
    return None


def _video_from_history(entry: dict) -> Optional[dict]:
    outputs = entry.get("outputs") or {}
    for node in outputs.values():
        if not isinstance(node, dict):
            continue
        for key in ("images", "videos", "gifs"):
            rows = node.get(key) or []
            if not isinstance(rows, list):
                continue
            for row in rows:
                if not isinstance(row, dict):
                    continue
                name = str(row.get("filename") or "")
                if name.lower().endswith(".mp4"):
                    return {
                        "filename": name,
                        "subfolder": str(row.get("subfolder") or ""),
                        "type": str(row.get("type") or "output"),
                    }
    return None


def _generate_via_sglang(
    prompt: str,
    output_path: str,
    *,
    duration: float,
    aspect: str,
    seed: Optional[int],
) -> Optional[str]:
    seconds = _clamp_seconds(duration)
    ratio = aspect if aspect in {"21:9", "16:9", "4:3", "1:1", "3:4", "9:16"} else "9:16"
    payload = {
        "model": local_model_id(),
        "prompt": prompt,
        "seconds": int(round(seconds)),
        "task": "t2va",
        "conditions": [],
        "target": {
            "short_edge": 768,
            "aspect_ratio": ratio,
            "duration_seconds": seconds,
        },
        "num_outputs_per_prompt": 1,
        "num_inference_steps": 50,
        "flow_shift": 12.0,
        "audio_flow_shift": 3.0,
    }
    if seed is not None:
        payload["seed"] = int(seed)
    base = local_base_url()
    try:
        created = requests.post(f"{base}/v1/videos", json=payload, timeout=60)
        if created.status_code not in (200, 201, 202):
            print(f"    [MiniMax-H3] HTTP {created.status_code}: {created.text[:180]}")
            return None
        body = created.json() or {}
        video_id = str(body.get("id") or body.get("video_id") or "").strip()
        if not video_id:
            print("    [MiniMax-H3] yerel sunucu video kimliği vermedi")
            return None
        if not _wait_until_complete(base, video_id):
            return None
        media = requests.get(f"{base}/v1/videos/{video_id}/content", timeout=180)
        if media.status_code != 200 or not media.content:
            print(f"    [MiniMax-H3] içerik HTTP {media.status_code}")
            return None
        if write_bytes(media.content, output_path):
            return output_path
    except Exception as exc:
        print(f"    [MiniMax-H3] yerel sunucuya ulaşılamadı: {exc}")
    return None


def _wait_until_complete(base: str, video_id: str, timeout: float = 900.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            response = requests.get(f"{base}/v1/videos/{video_id}", timeout=30)
            if response.status_code != 200:
                time.sleep(4.0)
                continue
            status = str((response.json() or {}).get("status") or "").lower()
            if status == "completed":
                return True
            if status in ("failed", "error", "cancelled", "canceled"):
                print(f"    [MiniMax-H3] üretim durumu: {status}")
                return False
        except Exception:
            pass
        time.sleep(4.0)
    print("    [MiniMax-H3] yerel üretim zaman aşımı")
    return False
