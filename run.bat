@echo off
setlocal
cd /d "%~dp0"
title YouTube Shorts Ultimate
chcp 65001 >nul 2>&1

python run.py --cli %*
if errorlevel 1 (
    where py >nul 2>&1
    if %errorlevel%==0 py run.py --cli %*
)

pause
