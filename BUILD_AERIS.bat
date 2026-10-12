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
if errorlevel 1 exit /b 1

echo.
echo Running pre-build self tests...
python -m aeris --self-test
if errorlevel 1 (
    echo.
    echo Self-tests failed. Aborting build.
    pause
    exit /b 1
)

echo.
echo Building Aeris...
python -m pytest
if errorlevel 1 exit /b 1
pyinstaller --noconfirm --onedir --windowed --name "Aeris" --add-data "config;config" --hidden-import "keyring.backends.Windows" run_aeris.py

if errorlevel 1 (
    echo.
    echo Build failed. Check the errors above.
    pause
    exit /b 1
)

echo.
echo Build successful! The executable is located in the "dist\Aeris" directory.
pause
