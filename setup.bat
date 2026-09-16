@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"
title YouTube Shorts Ultimate - Setup

chcp 65001 >nul 2>&1

echo ============================================================
echo        YouTube Shorts Ultimate - İlk Kurulum
echo ============================================================
echo.

REM ------------------------------------------------------------
REM 1) Python kontrolu
REM ------------------------------------------------------------
set "PY_CMD="
where py >nul 2>&1
if %errorlevel%==0 set "PY_CMD=py"

if not defined PY_CMD (
    where python >nul 2>&1
    if %errorlevel%==0 set "PY_CMD=python"
)

if not defined PY_CMD (
    echo [HATA] Python bulunamadi.
    echo.
    echo Python 3.10 veya 3.11 kurup yeniden setup.bat dosyasini calistirin.
    echo Kurulum sirasinda "Add Python to PATH" secenegini isaretleyin.
    echo.
    pause
    exit /b 1
)

echo [OK] Python bulundu:
%PY_CMD% --version

echo.
echo [1/4] pip hazirlaniyor...
%PY_CMD% -m ensurepip --upgrade >nul 2>&1
%PY_CMD% -m pip install --upgrade pip setuptools wheel
if errorlevel 1 goto :pip_error

REM ------------------------------------------------------------
REM 2) Python kutuphaneleri
REM ------------------------------------------------------------
echo.
echo [2/4] Gerekli Python kutuphaneleri kuruluyor...
%PY_CMD% -m pip install -r requirements.txt
if errorlevel 1 goto :pip_error

echo.
echo [OK] Python kutuphaneleri hazir.

REM ------------------------------------------------------------
REM 3) FFmpeg kontrolu / kurulumu
REM ------------------------------------------------------------
echo.
echo [3/4] FFmpeg kontrol ediliyor...
where ffmpeg >nul 2>&1
if %errorlevel%==0 (
    echo [OK] FFmpeg bulundu.
    goto :ffmpeg_done
)

echo [UYARI] FFmpeg PATH icinde bulunamadi.
where winget >nul 2>&1
if %errorlevel%==0 (
    echo FFmpeg winget ile kurulmaya calisiliyor...
    winget install --id Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements
    if errorlevel 1 (
        echo [UYARI] Otomatik FFmpeg kurulumu basarisiz oldu.
        echo FFmpeg'i manuel kurup PATH'e eklemeniz gerekebilir.
    ) else (
        echo [OK] FFmpeg kurulumu tamamlandi.
        echo NOT: PATH degisikliginin etkinlesmesi icin bu pencereyi kapatip
        echo setup.bat dosyasini bir kez daha calistirmaniz gerekebilir.
    )
) else (
    echo [UYARI] winget bulunamadi. FFmpeg otomatik kurulamadi.
    echo FFmpeg'i manuel olarak kurup PATH'e ekleyin.
)

:ffmpeg_done
REM ------------------------------------------------------------
REM 4) Baslat
REM ------------------------------------------------------------
echo.
echo [4/4] Kurulum tamamlandi.
echo.
echo ONEMLI: config.py icindeki en az bir AI API anahtarini ve
echo PEXELS_API_KEY alanini doldurmayi unutmayin.
echo.
echo Yazilim baslatiliyor...
echo ============================================================
echo.
%PY_CMD% main.py
set "APP_EXIT=%errorlevel%"

echo.
echo ============================================================
if not "%APP_EXIT%"=="0" (
    echo Program %APP_EXIT% cikis kodu ile sonlandi.
    echo API anahtarlarinizi ve yukaridaki hata mesajlarini kontrol edin.
) else (
    echo Program tamamlandi.
)
echo ============================================================
pause
exit /b %APP_EXIT%

:pip_error
echo.
echo ============================================================
echo [HATA] Python kutuphaneleri kurulurken hata olustu.
echo Internet baglantinizi ve Python surumunuzu kontrol edin.
echo ============================================================
pause
exit /b 1
