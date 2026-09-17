@echo off
setlocal
cd /d "%~dp0"
title YouTube Shorts Ultimate - Web Studio
chcp 65001 >nul 2>&1

echo ========================================================
echo   YouTube Shorts Ultimate - Web Dashboard Launcher
echo ========================================================
echo.
echo Launching web server at http://127.0.0.1:8000...
echo.

python run.py
if errorlevel 1 (
    where py >nul 2>&1
    if %errorlevel%==0 py run.py
)

pause
