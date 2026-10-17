@echo off
setlocal
set "AERIS_PROJECT_ROOT=%~dp0"
set "AERIS_PYTHON=%~dp0.venv\Scripts\python.exe"
if not exist "%AERIS_PYTHON%" (
    echo Aeris setup is incomplete in "%AERIS_PROJECT_ROOT%".
    echo Run "%AERIS_PROJECT_ROOT%SETUP_AERIS.bat" explicitly, then retry.
    exit /b 1
)
"%AERIS_PYTHON%" -I -c "import sys; sys.exit(0 if sys.version_info[:2] in ((3,11),(3,12),(3,13)) else 1)" >nul 2>&1
if errorlevel 1 (
    echo Aeris needs Python 3.11, 3.12 or 3.13 in its own .venv. Python 3.11 is recommended on Windows.
    echo The parent folder environment is separate. Existing environments have not been changed.
    exit /b 1
)
pushd "%AERIS_PROJECT_ROOT%" || exit /b 1
if "%~1"=="--test" goto tests
if "%~1"=="--lint" goto lint
if not "%~1"=="" goto console
if not exist "%AERIS_PROJECT_ROOT%.venv\Scripts\pythonw.exe" goto missing_gui
"%AERIS_PYTHON%" -c "import PySide6.QtWidgets" >nul 2>&1
if errorlevel 1 goto missing_gui
start "Aeris" "%AERIS_PROJECT_ROOT%.venv\Scripts\pythonw.exe" -m aeris --gui
set "AERIS_EXIT_CODE=%ERRORLEVEL%"
goto finish
:console
"%AERIS_PYTHON%" -m aeris %*
set "AERIS_EXIT_CODE=%ERRORLEVEL%"
goto finish
:tests
"%AERIS_PYTHON%" -m pytest tests -ra
set "AERIS_EXIT_CODE=%ERRORLEVEL%"
goto finish
:lint
"%AERIS_PYTHON%" -m ruff check .
set "AERIS_EXIT_CODE=%ERRORLEVEL%"
goto finish
:missing_gui
echo Aeris GUI packages are unavailable. Text diagnostics: RUN_AERIS.bat --self-test
echo Review and run SETUP_AERIS.bat to install the declared optional Windows dependencies.
set "AERIS_EXIT_CODE=1"
:finish
popd
exit /b %AERIS_EXIT_CODE%
