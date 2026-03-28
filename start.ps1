# =============================================================
#  DataCenter Submittal Review Platform - Windows Startup
# =============================================================
#  Run from PowerShell:  .\start.ps1
#  Or right-click > "Run with PowerShell"
# =============================================================

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  DC Submittal Review Platform - Starting"   -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# Check Python
try { python --version | Out-Null } catch {
    Write-Host "ERROR: Python is not installed." -ForegroundColor Red
    Write-Host "Download it from: https://www.python.org/downloads/"
    Write-Host "IMPORTANT: Check 'Add Python to PATH' during install!"
    Read-Host "Press Enter to exit"
    exit 1
}

# Check Node
try { node --version | Out-Null } catch {
    Write-Host "ERROR: Node.js is not installed." -ForegroundColor Red
    Write-Host "Download it from: https://nodejs.org/"
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "[1/4] Installing Python dependencies..." -ForegroundColor Yellow
Set-Location "$root\backend"
pip install -r requirements.txt --quiet 2>&1 | Out-Null

Write-Host "[2/4] Installing frontend dependencies..." -ForegroundColor Yellow
Set-Location "$root\frontend"
npm install --silent 2>&1 | Out-Null

Write-Host "[3/4] Starting backend server..." -ForegroundColor Yellow
Set-Location "$root\backend"
$backend = Start-Process python -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000" -PassThru -WindowStyle Normal
Set-Location $root

Write-Host "     Waiting for backend..." -ForegroundColor Gray
Start-Sleep -Seconds 5

Write-Host "[4/4] Starting frontend..." -ForegroundColor Yellow
Set-Location "$root\frontend"
$frontend = Start-Process npm -ArgumentList "run", "dev" -PassThru -WindowStyle Normal
Set-Location $root

Start-Sleep -Seconds 3

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  ALL RUNNING!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Opening browser to:" -ForegroundColor White
Write-Host "    http://localhost:5173" -ForegroundColor Cyan
Write-Host ""
Write-Host "  To stop: run .\stop.ps1" -ForegroundColor Gray
Write-Host "  Or just close the windows that opened" -ForegroundColor Gray
Write-Host "============================================" -ForegroundColor Green
Write-Host ""

Start-Process "http://localhost:5173"
