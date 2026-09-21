#!/usr/bin/env python3
"""
YouTube Shorts Ultimate — Universal Cross-Platform Launcher
Runs seamlessly on both macOS and Windows without requiring code changes.
"""

import sys
import os
import time
import threading
import webbrowser
import platform
import asyncio

# Ensure UTF-8 console output on Windows and Mac
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Ensure working directory is the script root
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT_DIR)


def open_browser(url: str, delay: float = 1.2):
    """Opens the web browser after a short startup delay."""
    time.sleep(delay)
    try:
        webbrowser.open(url)
    except Exception:
        pass


def _port_in_use(port: int) -> bool:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def free_port_if_occupied(port: int = 8000):
    """If port is held by an existing process, terminate it cleanly to prevent bind errors."""
    if not _port_in_use(port):
        return

    print(f"[*] Port {port} meşgul, eski arka plan süreci temizleniyor...")
    try:
        import subprocess

        if platform.system() == "Windows":
            out = subprocess.check_output(
                f"netstat -ano | findstr :{port}", shell=True
            ).decode(errors="ignore")
            for line in out.splitlines():
                parts = line.strip().split()
                if len(parts) >= 5 and "LISTENING" in parts[3].upper():
                    pid = parts[-1]
                    if pid and pid != str(os.getpid()):
                        subprocess.run(
                            f"taskkill /F /PID {pid}",
                            shell=True,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )
        else:
            result = subprocess.run(
                ["lsof", "-ti", f":{port}"],
                capture_output=True,
                text=True,
                check=False,
            )
            my_pid = str(os.getpid())
            pids = [
                pid.strip()
                for pid in result.stdout.split()
                if pid.strip() and pid.strip() != my_pid
            ]
            if pids:
                subprocess.run(
                    ["kill", "-9", *pids],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )

        for _ in range(15):
            time.sleep(0.2)
            if not _port_in_use(port):
                return
        print(f"[!] Uyarı: Port {port} hâlâ meşgul — başka süreç olabilir.")
    except Exception as e:
        print(f"[*] Port kontrol bildirimi: {e}")


def _configure_windows_asyncio():
    """Suppress benign ConnectionResetError spam when SSE clients disconnect on Windows."""
    if platform.system() != "Windows":
        return

    def _handler(loop, context):
        exc = context.get("exception")
        if isinstance(exc, (ConnectionResetError, BrokenPipeError)):
            return
        loop.default_exception_handler(context)

    try:
        asyncio.get_event_loop_policy().get_event_loop().set_exception_handler(_handler)
    except Exception:
        pass


def launch_web():
    """Starts the FastAPI Web Dashboard."""
    _configure_windows_asyncio()
    url = "http://127.0.0.1:8000"
    os_name = "macOS" if platform.system() == "Darwin" else "Windows" if platform.system() == "Windows" else platform.system()
    
    # Ensure port 8000 is clean and free
    free_port_if_occupied(8000)

    print("=" * 60)
    print(f"  YouTube Shorts Ultimate — Web Studio ({os_name})")
    print("=" * 60)
    print(f"\nSunucu başlatılıyor: {url}")
    print("Tarayıcınız otomatik olarak açılacaktır...")
    print("[*] Plan API: POST /api/plan/validate, POST /api/plan/repair\n")

    # Launch browser in a background thread
    threading.Thread(target=open_browser, args=(url,), daemon=True).start()

    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=False)


def launch_cli():
    """Starts the CLI video generator pipeline."""
    os_name = "macOS" if platform.system() == "Darwin" else "Windows"
    print("=" * 60)
    print(f"  YouTube Shorts Ultimate — CLI Mode ({os_name})")
    print("=" * 60)
    
    import main
    if hasattr(main, "main"):
        main.main()
    else:
        # Fallback to run main.py as script
        import subprocess
        subprocess.run([sys.executable, "main.py"] + sys.argv[2:])


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("--cli", "-c", "cli"):
        launch_cli()
    else:
        launch_web()
