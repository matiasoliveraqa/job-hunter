@echo off
REM Job Hunter Local Startup Script (Windows)
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo ==========================================
echo         Starting Job Hunter Local
echo ==========================================

REM 0. Verify prerequisites before doing anything else
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [X] Python was not found on PATH.
    echo     Install it with:  winget install Python.Python.3.12
    echo     Do not use the Microsoft Store build: it breaks this launcher.
    echo     Reopen this terminal after installing.
    pause
    exit /b 1
)

where node >nul 2>nul
if %errorlevel% neq 0 (
    echo [X] Node.js was not found on PATH.
    echo     Install it with:  winget install OpenJS.NodeJS.LTS
    echo     Reopen this terminal after installing.
    pause
    exit /b 1
)

for /f "tokens=1 delims=." %%v in ('node -p "process.versions.node"') do set NODE_MAJOR=%%v
if !NODE_MAJOR! LSS 22 (
    echo [X] Node.js 22 or newer is required. Found major version !NODE_MAJOR!.
    echo     Install it with:  winget install OpenJS.NodeJS.LTS
    pause
    exit /b 1
)

REM 1. Configure Python virtual environment
if not exist "venv" (
    echo [*] Creating Python virtual environment ^(venv^)...
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
    echo [*] Installing web dependencies ^(npm install^)...
    call npm install
)

if not exist "dist" (
    echo [*] Building web interface ^(npm run build^)...
    call npm run build
)

cd ..
echo [*] Starting local web server...
node web/server/index.js
pause
