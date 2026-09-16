@echo off
setlocal
cd /d "%~dp0"
title YouTube Shorts Ultimate
chcp 65001 >nul 2>&1

where py >nul 2>&1
if %errorlevel%==0 (
    py main.py %*
) else (
    python main.py %*
)

pause
