$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot

function Invoke-Native {
    param([scriptblock]$Command)
    & $Command
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Command failed with exit code $LASTEXITCODE"
        exit $LASTEXITCODE
    }
}
Write-Host "Setting up Aeris with Python 3.11..." -ForegroundColor Cyan

try {
    py -3.11 --version
}
catch {
    Write-Host "Python 3.11 is required. Install it from python.org, then run this script again." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path ".venv")) {
    Invoke-Native { py -3.11 -m venv ".venv" }
}

Invoke-Native { & ".\.venv\Scripts\python.exe" -m pip install --upgrade pip setuptools wheel }
Invoke-Native { & ".\.venv\Scripts\python.exe" -m pip install -e ".[windows,voice,ai,gmail,browser,dev]" }

Write-Host "Installing Playwright Chromium browser..." -ForegroundColor Cyan
Invoke-Native { & ".\.venv\Scripts\playwright.exe" install chromium }

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env. Add your Gemini key and correct Windows username before live use." -ForegroundColor Yellow
}

Write-Host "Running the Aeris safety tests..." -ForegroundColor Cyan
Invoke-Native { & ".\.venv\Scripts\python.exe" -m pytest }

Write-Host "Setup complete." -ForegroundColor Green
Write-Host "Daily use: double-click START_AERIS.bat"
Write-Host "Terminal fallback: .\.venv\Scripts\python.exe -m aeris"
