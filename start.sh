#!/bin/bash
set -euo pipefail

# ═══════════════════════════════════════════════════════════════
# SentiVox — Production Start Script
# ═══════════════════════════════════════════════════════════════

# Change to script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Defaults (overridable via environment)
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
WORKERS="${WORKERS:-1}"
SENTIVOX_ENV="${SENTIVOX_ENV:-development}"

echo "================================================================="
echo "  🎙️ SentiVox — Speech Emotion Recognition Platform"
echo "  Environment: ${SENTIVOX_ENV}"
echo "================================================================="

# Check virtual environment
if [ ! -d "venv" ]; then
    echo "[!] Virtual environment 'venv' not found. Creating..."
    python3 -m venv venv
    ./venv/bin/pip install --upgrade pip
    ./venv/bin/pip install -r requirements.txt
fi

# Ensure .env exists
if [ ! -f ".env" ]; then
    echo "[!] No .env file found. Copying from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "[✓] Created .env from .env.example — please review and customize."
    else
        echo "[!] Warning: No .env.example found. Using defaults."
    fi
fi

# Ensure logs directory exists
mkdir -p logs

# Ensure models directory exists and has a .gitkeep
mkdir -p models
touch models/.gitkeep

# Ensure development model exists
if [ ! -f "models/CascadeCovM1_BEST.h5" ]; then
    echo "[!] Model file not found. Generating development model..."
    ./venv/bin/python train_engine.py --create-dummy
fi

echo ""
echo "[✓] Starting Uvicorn server..."
echo "    - Dashboard UI: http://${HOST}:${PORT}"
echo "    - API Docs:     http://${HOST}:${PORT}/docs"
echo "    - Health Check: http://${HOST}:${PORT}/health"
echo "    - Readiness:    http://${HOST}:${PORT}/ready"
echo "================================================================="
echo ""

if [ "$SENTIVOX_ENV" = "production" ]; then
    # Production: no reload, multiple workers (if configured)
    exec ./venv/bin/uvicorn server:app \
        --host "$HOST" \
        --port "$PORT" \
        --workers "$WORKERS" \
        --log-level warning \
        --access-log \
        --proxy-headers \
        --forwarded-allow-ips="*"
else
    # Development: auto-reload enabled
    exec ./venv/bin/uvicorn server:app \
        --host "$HOST" \
        --port "$PORT" \
        --reload \
        --log-level info
fi
