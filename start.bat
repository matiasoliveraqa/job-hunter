@echo off
REM Job Hunter Local Startup Script (Windows)
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo ==========================================
echo         Iniciando Job Hunter Local        
echo ==========================================

REM 1. Configurar entorno virtual de Python
if not exist "venv" (
    echo [*] Creando entorno virtual de Python (venv)...
    python -m venv venv
)

REM Activar venv
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM 2. Instalar dependencias de Python si faltan
python -c "import aiohttp, rich, playwright, jinja2" 2>nul
if %errorlevel% neq 0 (
    echo [*] Instalando dependencias de Python desde requirements.txt...
    pip install -r requirements.txt
    playwright install chromium
)

REM 3. Inicializar configuracion si no existe
if not exist "config\profile.json" (
    echo [*] Inicializando configuracion base...
    python -m src.cli init
)

REM 4. Configurar e inicializar frontend web
cd web
if not exist "node_modules" (
    echo [*] Instalando dependencias web (npm install)...
    call npm install
)

if not exist "dist" (
    echo [*] Compilando interfaz web (npm run build)...
    call npm run build
)

cd ..
echo [*] Arrancando servidor web local...
node web/server/index.js
pause
