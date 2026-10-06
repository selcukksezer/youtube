@echo off
chcp 65001 >nul
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [!] Yonetici yetkisi isteniyor...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

echo ========================================================
echo [1/2] RTX 3070 Guc Limiti 180W'a Sabitleniyor (TDP 220W -^> 180W)...
echo ========================================================
nvidia-smi -pl 180

echo.
echo ========================================================
echo [2/2] Windows TDR (Surucu Zaman Asimi) Suresi 10 Saniyeye Cikariliyor...
echo ========================================================
reg add "HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\GraphicsDrivers" /v TdrDelay /t REG_DWORD /d 10 /f
reg add "HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\GraphicsDrivers" /v TdrDdiDelay /t REG_DWORD /d 10 /f

echo.
echo ========================================================
echo BASARILI! Ekran karti yuk korumalari uygulandi.
echo ========================================================
timeout /t 5
