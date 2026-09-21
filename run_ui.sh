#!/bin/bash
cd "$(dirname "$0")"

echo "========================================================"
echo "  YouTube Shorts Ultimate — Web Dashboard (macOS)"
echo "========================================================"
echo ""
echo "Web arayüzü başlatılıyor: http://127.0.0.1:8000"
echo ""

# venv varsa doğrudan kullan; yoksa sistem python3
if [ -x "venv/bin/python" ]; then
    exec venv/bin/python run.py "$@"
fi

exec python3 run.py "$@"

