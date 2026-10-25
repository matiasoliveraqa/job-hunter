#!/usr/bin/env bash
set -e

# Job Hunter Local Startup Script (Linux & macOS)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "        Iniciando Job Hunter Local        "
echo "=========================================="

# 1. Configurar entorno virtual de Python
if [ ! -d "venv" ] && [ ! -L "venv" ]; then
    echo "[*] Creando entorno virtual de Python (venv)..."
    python3 -m venv venv
fi

# Activar venv
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
fi

# 2. Instalar dependencias de Python si faltan
if ! python3 -c "import aiohttp, rich, playwright, jinja2" 2>/dev/null; then
    echo "[*] Instalando dependencias de Python desde requirements.txt..."
    pip install -r requirements.txt
    playwright install chromium
fi

# 3. Inicializar configuración si no existe
if [ ! -f "config/profile.json" ]; then
    echo "[*] Inicializando configuración base..."
    python3 -m src.cli init
fi

# 4. Configurar e inicializar frontend web
cd "$SCRIPT_DIR/web"
if [ ! -d "node_modules" ]; then
    echo "[*] Instalando dependencias web (npm install)..."
    npm install
fi

if [ ! -d "dist" ]; then
    echo "[*] Compilando interfaz web (npm run build)..."
    npm run build
fi

echo "[*] Arrancando servidor web local..."
# Iniciar servidor Express
cd "$SCRIPT_DIR"
node web/server/index.js
