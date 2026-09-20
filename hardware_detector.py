"""
Hardware Detector & Performance Optimizer Engine
Detects CPU, RAM, GPU (NVIDIA RTX/CUDA), and NVENC availability.
Provides balanced high-performance profiles tailored to user hardware.
"""
import os
import platform
import subprocess
import ctypes
from typing import Dict, Any

def get_cpu_info() -> Dict[str, Any]:
    threads = os.cpu_count() or 4
    cpu_name = platform.processor() or "Bilinmeyen CPU"
    try:
        if platform.system() == "Windows":
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            val, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            if val:
                cpu_name = str(val).strip()
    except Exception:
        pass
    return {"name": cpu_name, "threads": threads, "physical_cores": max(1, threads // 2)}

def get_ram_info() -> Dict[str, Any]:
    total_gb = 8.0
    avail_gb = 4.0
    try:
        if platform.system() == "Windows":
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ('dwLength', ctypes.c_ulong),
                    ('dwMemoryLoad', ctypes.c_ulong),
                    ('ullTotalPhys', ctypes.c_ulonglong),
                    ('ullAvailPhys', ctypes.c_ulonglong),
                    ('ullTotalPageFile', ctypes.c_ulonglong),
                    ('ullAvailPageFile', ctypes.c_ulonglong),
                    ('ullTotalVirtual', ctypes.c_ulonglong),
                    ('ullAvailVirtual', ctypes.c_ulonglong),
                    ('sullAvailExtendedVirtual', ctypes.c_ulonglong),
                ]
            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
                total_gb = round(stat.ullTotalPhys / (1024**3), 1)
                avail_gb = round(stat.ullAvailPhys / (1024**3), 1)
    except Exception:
        pass
    return {"total_gb": total_gb, "avail_gb": avail_gb}

def get_gpu_info() -> Dict[str, Any]:
    gpu_name = "Entegre / Standart Grafik Birimi"
    vram_mb = 0
    has_nvidia = False
    has_nvenc = False

    # Check nvidia-smi
    try:
        res = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=3
        )
        if res.returncode == 0 and res.stdout.strip():
            lines = res.stdout.strip().split("\n")
            parts = lines[0].split(",")
            gpu_name = parts[0].strip()
            if len(parts) > 1:
                mem_str = parts[1].strip().lower().replace("mib", "").replace("mb", "")
                try:
                    vram_mb = int(mem_str.strip())
                except ValueError:
                    pass
            has_nvidia = True
    except Exception:
        pass

    # Check FFmpeg NVENC encoder support
    try:
        import imageio_ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        res_enc = subprocess.run([ffmpeg_exe, "-encoders"], capture_output=True, text=True, timeout=4)
        if "h264_nvenc" in res_enc.stdout and has_nvidia:
            has_nvenc = True
    except Exception:
        pass

    return {
        "name": gpu_name,
        "vram_mb": vram_mb,
        "vram_gb": round(vram_mb / 1024, 1) if vram_mb else 0.0,
        "has_nvidia": has_nvidia,
        "has_nvenc": has_nvenc
    }

def get_system_hardware_specs() -> Dict[str, Any]:
    cpu = get_cpu_info()
    ram = get_ram_info()
    gpu = get_gpu_info()

    # Determine recommended profile
    if gpu["has_nvenc"]:
        recommended_profile = "ultra_gpu"
        profile_label = f"RTX Donanim Hizlandirma ({gpu['name']} NVENC + 8 Thread CPU)"
        recommended_threads = min(8, max(4, cpu["threads"] // 2))
        use_gpu = True
    elif cpu["threads"] >= 8 and ram["total_gb"] >= 16:
        recommended_profile = "fast_cpu"
        profile_label = f"Cok Cekirdekli CPU Modu ({cpu['threads'] // 2} Thread)"
        recommended_threads = min(8, cpu["threads"] - 2)
        use_gpu = False
    else:
        recommended_profile = "balanced"
        profile_label = "Dengeli / Guvenli Mod (4 Thread)"
        recommended_threads = max(2, min(4, cpu["threads"] - 1))
        use_gpu = False

    return {
        "cpu": cpu,
        "ram": ram,
        "gpu": gpu,
        "recommended_profile": recommended_profile,
        "recommended_label": profile_label,
        "recommended_threads": recommended_threads,
        "recommended_use_gpu": use_gpu,
        "fps_diversification_supported": True,
        "fps_options": [29.97, 30.00, 30.02, 29.95, 30.04]
    }

hardware_detector = get_system_hardware_specs
