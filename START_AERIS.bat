@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
    echo Aeris is not installed yet. Starting setup...
    call "%~dp0SETUP_AERIS.bat"
)
if not exist ".venv\Scripts\pythonw.exe" (
    echo Aeris could not start because setup is incomplete.
    pause
    exit /b 1
)
start "Aeris" ".venv\Scripts\pythonw.exe" -m aeris --gui
