@echo off
REM Job Hunter Local Startup Script (Windows)
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo ==========================================
echo         Starting Job Hunter Local        
echo ==========================================

REM 1. Configure Python virtual environment
if not exist "venv" (
    echo [*] Creating Python virtual environment (venv)...
    python -m venv venv
)

REM Activate venv
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM 2. Install Python dependencies if missing
python -c "import aiohttp, rich, playwright, jinja2" 2>nul
if %errorlevel% neq 0 (
    echo [*] Installing Python dependencies from requirements.txt...
    pip install -r requirements.txt
    playwright install chromium
)

REM 3. Initialize configuration if missing
if not exist "config\profile.json" (
    echo [*] Initializing base configuration...
    python -m src.cli init
)

REM 4. Configure and initialize web frontend
cd web
if not exist "node_modules" (
    echo [*] Installing web dependencies (npm install)...
    call npm install
)

if not exist "dist" (
    echo [*] Building web interface (npm run build)...
    call npm run build
)

cd ..
echo [*] Starting local web server...
node web/server/index.js
pause
