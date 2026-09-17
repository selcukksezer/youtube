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


def launch_web():
    """Starts the FastAPI Web Dashboard."""
    url = "http://127.0.0.1:8000"
    os_name = "macOS" if platform.system() == "Darwin" else "Windows" if platform.system() == "Windows" else platform.system()
    
    print("=" * 60)
    print(f"  YouTube Shorts Ultimate — Web Studio ({os_name})")
    print("=" * 60)
    print(f"\nSunucu başlatılıyor: {url}")
    print("Tarayıcınız otomatik olarak açılacaktır...\n")

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
