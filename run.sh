#!/bin/bash
cd "$(dirname "$0")"

echo "========================================================"
echo "  YouTube Shorts Ultimate (macOS)"
echo "========================================================"

if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

python3 main.py "$@"
