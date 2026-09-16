@echo off
title YouTube Shorts Ultimate — Web Studio
echo ========================================================
echo   YouTube Shorts Ultimate — Web Dashboard Launcher
echo ========================================================
echo.
echo Launching web server at http://127.0.0.1:8000...
echo.

start "" "http://127.0.0.1:8000"
python -m uvicorn server:app --host 127.0.0.1 --port 8000

pause
