#!/usr/bin/env bash
set -e

# Job Hunter Local Startup Script (Linux & macOS)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "        Starting Job Hunter Local         "
echo "=========================================="

# 0. Verify prerequisites before doing anything else
if ! command -v python3 >/dev/null 2>&1; then
    echo "[X] python3 was not found on PATH."
    echo "    macOS:  brew install python@3.12"
    echo "    Debian: sudo apt install python3 python3-venv"
    echo "    Arch:   sudo pacman -S python"
    exit 1
fi

if ! command -v node >/dev/null 2>&1; then
    echo "[X] Node.js was not found on PATH."
    echo "    macOS:  brew install node"
    echo "    Debian: see https://github.com/nodesource/distributions"
    echo "    Arch:   sudo pacman -S nodejs npm"
    exit 1
fi

NODE_MAJOR="$(node -p 'process.versions.node.split(".")[0]')"
if [ "$NODE_MAJOR" -lt 22 ]; then
    echo "[X] Node.js 22 or newer is required. Found major version $NODE_MAJOR."
    exit 1
fi

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
