@echo off
setlocal
cd /d "%~dp0"
title Aeris Setup
echo.
echo ========================================
echo            AERIS SETUP
echo ========================================
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\setup_windows.ps1"
if errorlevel 1 (
    echo.
    echo Setup did not finish successfully. Keep this window open and share the error.
    pause
    exit /b 1
)
echo.
echo Aeris is ready. Double-click START_AERIS.bat to launch it.
pause
