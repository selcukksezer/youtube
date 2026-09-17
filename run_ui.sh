#!/bin/bash
cd "$(dirname "$0")"

echo "========================================================"
echo "  YouTube Shorts Ultimate — Web Dashboard (macOS)"
echo "========================================================"
echo ""
echo "Web arayüzü başlatılıyor: http://127.0.0.1:8000"
echo ""

# Aktif bir sanal ortam varsa onu kullan, yoksa python3
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# Tarayıcıyı aç ve sunucuyu başlat
python3 -m uvicorn server:app --host 127.0.0.1 --port 8000 --reload

