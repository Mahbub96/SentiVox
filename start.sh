#!/bin/bash
set -e

# Change to script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"

echo "================================================================="
echo "  🎙️ Speech Emotion Recognition (SER) System Starting..."
echo "================================================================="

# Check virtual environment
if [ ! -d "venv" ]; then
    echo "[!] Virtual environment 'venv' not found. Creating..."
    python3 -m venv venv
    ./venv/bin/pip install --upgrade pip
    ./venv/bin/pip install -r requirements.txt
fi

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
echo "================================================================="
echo ""

exec ./venv/bin/uvicorn server:app --host "$HOST" --port "$PORT" --reload
