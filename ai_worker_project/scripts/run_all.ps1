# run_all.ps1 — Start all services in separate windows
# Usage: .\scripts\run_all.ps1 (from backend/)

$ErrorActionPreference = "Stop"

Write-Host "`n=== AI Task Worker — Starting all services ===" -ForegroundColor Cyan
Write-Host ""

# Check virtual environment
if (-not (Test-Path ".venv\Scripts\Activate.ps1")) {
    Write-Host "[ERROR] Virtual environment not found. Run:" -ForegroundColor Red
    Write-Host "  python -m venv .venv" -ForegroundColor Yellow
    Write-Host "  .venv\Scripts\Activate.ps1" -ForegroundColor Yellow
    Write-Host "  pip install -r requirements.txt" -ForegroundColor Yellow
    exit 1
}

# Seed data if DB doesn't exist
if (-not (Test-Path "environment\acmefinance\acmefinance.db")) {
    Write-Host "[SEED] Running seed_data.py..." -ForegroundColor Yellow
    & .venv\Scripts\python.exe scripts\seed_data.py
    Write-Host ""
}

# Start VendorHub (port 8001)
Write-Host "[1/3] Starting VendorHub on http://localhost:8001" -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
    "Set-Location '$PWD'; .venv\Scripts\Activate.ps1; python -m uvicorn environment.vendorhub.app:app --port 8001 --host 0.0.0.0"

Start-Sleep -Seconds 1

# Start AcmeFinance (port 8002)
Write-Host "[2/3] Starting AcmeFinance on http://localhost:8002" -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
    "Set-Location '$PWD'; .venv\Scripts\Activate.ps1; python -m uvicorn environment.acmefinance.app:app --port 8002 --host 0.0.0.0"

Start-Sleep -Seconds 1

# Start Worker API (port 8000) — placeholder for Phase 3+
# Write-Host "[3/3] Starting Worker API on http://localhost:8000" -ForegroundColor Green
# Start-Process powershell -ArgumentList "-NoExit", "-Command", `
#     "Set-Location '$PWD'; .venv\Scripts\Activate.ps1; python -m uvicorn app.main:app --port 8000 --host 0.0.0.0"

Write-Host ""
Write-Host "=== Services running ===" -ForegroundColor Cyan
Write-Host "  VendorHub:    http://localhost:8001" -ForegroundColor White
Write-Host "  AcmeFinance:  http://localhost:8002" -ForegroundColor White
# Write-Host "  Worker API:   http://localhost:8000" -ForegroundColor White
Write-Host ""
Write-Host "Close the PowerShell windows to stop each service." -ForegroundColor Gray
