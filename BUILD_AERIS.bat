@echo off
setlocal
cd /d "%~dp0"
title Aeris Build

echo ========================================
echo          AERIS PACKAGE BUILDER
echo ========================================
echo.

if not exist ".venv" (
    echo Error: The virtual environment .venv does not exist.
    echo Please run SETUP_AERIS.bat first.
    pause
    exit /b 1
)

echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo.
echo Installing PyInstaller...
pip install pyinstaller

echo.
echo Building Aeris...
pyinstaller --noconfirm --onedir --windowed --name "Aeris" --icon "assets\icon.ico" --add-data "aeris\assets;aeris\assets" --hidden-import "plyer.platforms.win.notification" --hidden-import "plyer.platforms.win.storagepath" --hidden-import "googleapiclient" --hidden-import "sounddevice" --hidden-import "speech_recognition" --hidden-import "keyring.backends.Windows" aeris\__main__.py

if errorlevel 1 (
    echo.
    echo Build failed. Check the errors above.
    pause
    exit /b 1
)

echo.
echo Build successful! The executable is located in the "dist\Aeris" directory.
pause
