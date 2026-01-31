# Trading Noobs Startup Script (PowerShell)
# This script starts both backend and frontend

# Set console encoding to UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001 | Out-Null

$ErrorActionPreference = "Stop"
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendPath = Join-Path $scriptPath "backend"
$frontendPath = Join-Path $scriptPath "frontend"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Trading Noobs Startup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[OK] Python installed: $pythonVersion" -ForegroundColor Green
}
catch {
    Write-Host "[ERROR] Python not found. Please install Python 3.10+" -ForegroundColor Red
    exit 1
}

# Check Node.js
try {
    $nodeVersion = node --version 2>&1
    Write-Host "[OK] Node.js installed: $nodeVersion" -ForegroundColor Green
}
catch {
    Write-Host "[ERROR] Node.js not found. Please install Node.js 18+" -ForegroundColor Red
    exit 1
}

Write-Host ""

# ========== Backend Setup ==========
Write-Host "--- Setting up Backend ---" -ForegroundColor Yellow

$venvPath = Join-Path $backendPath "venv"
$venvActivate = Join-Path $venvPath "Scripts\Activate.ps1"

# Create virtual environment if not exists
if (-not (Test-Path $venvPath)) {
    Write-Host "Creating Python virtual environment..." -ForegroundColor Cyan
    Push-Location $backendPath
    python -m venv venv
    Pop-Location
}

# Activate venv and install dependencies
Write-Host "Installing backend dependencies..." -ForegroundColor Cyan
Push-Location $backendPath
& $venvActivate
pip install -r requirements.txt --quiet
Pop-Location

# Check .env file
$envFile = Join-Path $backendPath ".env"
$envExample = Join-Path $backendPath ".env.example"
if (-not (Test-Path $envFile)) {
    if (Test-Path $envExample) {
        Write-Host "Copying .env.example to .env..." -ForegroundColor Cyan
        Copy-Item $envExample $envFile
    }
    else {
        Write-Host "Creating default .env file..." -ForegroundColor Cyan
        @"
DATABASE_URL=sqlite:///./tradingnoobs.db
SECRET_KEY=dev-secret-key-change-in-production
CORS_ORIGINS=http://localhost:3000
"@ | Out-File -FilePath $envFile -Encoding utf8
    }
}

Write-Host "[OK] Backend setup complete" -ForegroundColor Green
Write-Host ""

# ========== Frontend Setup ==========
Write-Host "--- Setting up Frontend ---" -ForegroundColor Yellow

$nodeModulesPath = Join-Path $frontendPath "node_modules"
if (-not (Test-Path $nodeModulesPath)) {
    Write-Host "Installing frontend dependencies (npm install)..." -ForegroundColor Cyan
    Push-Location $frontendPath
    npm install
    Pop-Location
}

Write-Host "[OK] Frontend setup complete" -ForegroundColor Green
Write-Host ""

# ========== Start Services ==========
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Starting Services" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Start backend (new window)
Write-Host "Starting backend (http://localhost:8000)..." -ForegroundColor Green
$backendCmd = @"
cd '$backendPath'
& '$venvActivate'
uvicorn main:app --reload --host 0.0.0.0 --port 8000
"@
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd

# Wait for backend to start
Start-Sleep -Seconds 2

# Start frontend (new window)
Write-Host "Starting frontend (http://localhost:3000)..." -ForegroundColor Green
$frontendCmd = @"
cd '$frontendPath'
npm run dev
"@
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Services Started!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Frontend: http://localhost:3000" -ForegroundColor White
Write-Host "Backend:  http://localhost:8000" -ForegroundColor White
Write-Host "API Docs: http://localhost:8000/docs" -ForegroundColor White
Write-Host ""
Write-Host "Tip: Two new terminal windows have been opened." -ForegroundColor Yellow
Write-Host "     Close them to stop the services." -ForegroundColor Yellow

