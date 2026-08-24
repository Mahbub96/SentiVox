#!/bin/bash
set -euo pipefail

# ═══════════════════════════════════════════════════════════════
# SentiVox — Production Deployment Script (Ubuntu 22.04/24.04)
# ═══════════════════════════════════════════════════════════════

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "================================================================="
echo "  🚀 SentiVox Production Deployment"
echo "================================================================="

# ─── System Dependencies ─────────────────────────────────────
echo "[+] Updating system packages..."
sudo apt-get update -y && sudo apt-get install -y \
    ffmpeg \
    libsndfile1 \
    nginx \
    nodejs \
    npm \
    python3-venv \
    python3-dev \
    build-essential

# ─── Python Environment ──────────────────────────────────────
echo "[+] Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# ─── Logs & Models Directories ───────────────────────────────
mkdir -p logs models
touch models/.gitkeep

# ─── Environment Configuration ───────────────────────────────
if [ ! -f ".env" ]; then
    echo "[!] No .env file found. Creating from template..."
    cp .env.example .env
    echo ""
    echo "  ⚠️  IMPORTANT: Edit .env before continuing!"
    echo "     Set these REQUIRED values:"
    echo "       SENTIVOX_ENV=production"
    echo "       JWT_SECRET_KEY=<generate with: python -c 'import secrets; print(secrets.token_urlsafe(64))'>"
    echo "       CORS_ORIGINS=https://yourdomain.com"
    echo "       DEFAULT_ADMIN_PASSWORD=<strong-password>"
    echo ""
    echo "  Press ENTER after editing .env to continue, or Ctrl+C to abort."
    read -r
fi

# ─── Model Check ─────────────────────────────────────────────
if [ ! -f "models/CascadeCovM1_BEST.h5" ]; then
    echo "[!] No model found. Generating development model..."
    ./venv/bin/python train_engine.py --create-dummy
fi

# ─── PM2 Process Manager ─────────────────────────────────────
echo "[+] Installing and configuring PM2..."
sudo npm install -g pm2
pm2 start ecosystem.config.js
pm2 save
pm2 startup || true

# ─── Nginx Reverse Proxy (replaces Apache) ───────────────────
echo "[+] Configuring Nginx reverse proxy..."
if [ -f "sentivox-nginx.conf" ]; then
    sudo cp sentivox-nginx.conf /etc/nginx/sites-available/sentivox
    sudo ln -sf /etc/nginx/sites-available/sentivox /etc/nginx/sites-enabled/sentivox
    sudo rm -f /etc/nginx/sites-enabled/default
    sudo nginx -t
    sudo systemctl restart nginx
    echo "[✓] Nginx configured and restarted."
else
    echo "[!] sentivox-nginx.conf not found — skipping Nginx setup."
fi

echo ""
echo "================================================================="
echo "  ✅ Deployment complete!"
echo "  Service active on port 80 (Nginx) → 8000 (Uvicorn)"
echo "  PM2 status: pm2 status"
echo "  View logs:  pm2 logs ser-api-service"
echo "================================================================="
