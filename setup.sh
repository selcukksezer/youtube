#!/bin/bash
cd "$(dirname "$0")"

echo "============================================================"
echo "       YouTube Shorts Ultimate - macOS Kurulumu"
echo "============================================================"
echo ""

# 1) Python kontrolü
if ! command -v python3 &> /dev/null; then
    echo "[HATA] python3 bulunamadı. Lütfen Homebrew veya python.org üzerinden Python kurun."
    exit 1
fi

echo "[OK] Python bulundu: $(python3 --version)"

# 2) Sanal ortam (venv) kurulumu
echo ""
echo "[1/4] Sanal ortam hazırlanıyor (venv)..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

echo "[2/4] pip güncelleniyor ve bağımlılıklar yükleniyor..."
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# 3) FFmpeg kontrolü
echo ""
echo "[3/4] FFmpeg kontrol ediliyor..."
if command -v ffmpeg &> /dev/null; then
    echo "[OK] FFmpeg bulundu: $(which ffmpeg)"
else
    echo "[UYARI] FFmpeg sisteminizde bulunamadı."
    if command -v brew &> /dev/null; then
        echo "Homebrew üzerinden FFmpeg kuruluyor (brew install ffmpeg)..."
        brew install ffmpeg
    else
        echo "Lütfen FFmpeg'i kurun (Homebrew ile: brew install ffmpeg)"
    fi
fi

echo ""
echo "[4/4] Kurulum tamamlandı!"
echo ""
echo "Programı çalıştırmak için:"
echo "  - Web Arayüzü: ./run_ui.sh"
echo "  - CLI:         ./run.sh"
echo "============================================================"
