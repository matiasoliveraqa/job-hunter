#!/usr/bin/env bash
set -e

# Job Hunter Local Startup Script (Linux & macOS)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "        Starting Job Hunter Local         "
echo "=========================================="

# 1. Configure Python virtual environment
if [ ! -d "venv" ] && [ ! -L "venv" ]; then
    echo "[*] Creating Python virtual environment (venv)..."
    python3 -m venv venv
fi

# Activate venv
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
fi

# 2. Install Python dependencies if missing
if ! python3 -c "import aiohttp, rich, playwright, jinja2" 2>/dev/null; then
    echo "[*] Installing Python dependencies from requirements.txt..."
    pip install -r requirements.txt
    playwright install chromium
fi

# 3. Initialize configuration if missing
if [ ! -f "config/profile.json" ]; then
    echo "[*] Initializing base configuration..."
    python3 -m src.cli init
fi

# 4. Configure and initialize web frontend
cd "$SCRIPT_DIR/web"
if [ ! -d "node_modules" ]; then
    echo "[*] Installing web dependencies (npm install)..."
    npm install
fi

if [ ! -d "dist" ]; then
    echo "[*] Building web interface (npm run build)..."
    npm run build
fi

echo "[*] Starting local web server..."
# Start Express server
cd "$SCRIPT_DIR"
node web/server/index.js
