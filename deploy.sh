#!/bin/bash
set -euo pipefail

# ═══════════════════════════════════════════════════════════════
# SentiVox — Production Deployment Script
# Server: 144.24.142.3 (Oracle Cloud)
# ═══════════════════════════════════════════════════════════════

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "================================================================="
echo "  🚀 SentiVox Production Deployment"
echo "  Server: 144.24.142.3"
echo "================================================================="

# ─── System Dependencies ─────────────────────────────────────
echo "[+] Installing system dependencies..."
sudo apt-get update -y && sudo apt-get install -y \
    ffmpeg \
    libsndfile1 \
    nginx \
    python3-venv \
    python3-dev \
    build-essential \
    curl

# ─── Python Environment ──────────────────────────────────────
echo "[+] Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# ─── Logs & Models Directories ───────────────────────────────
mkdir -p logs models

# ─── Production Environment Config ───────────────────────────
if [ -f ".env.production" ] && [ ! -f ".env" ]; then
    echo "[+] Activating production environment config..."
    cp .env.production .env
    echo "[✓] Production .env activated"
elif [ ! -f ".env" ]; then
    echo "[!] No .env found. Creating from .env.example..."
    cp .env.example .env
    echo ""
    echo "  ⚠️  IMPORTANT: Edit .env with production values!"
    echo "  Press ENTER after editing, or Ctrl+C to abort."
    read -r
fi

# ─── Model Check ─────────────────────────────────────────────
if [ ! -f "models/CascadeCovM1_BEST.h5" ]; then
    echo "[!] No model found. Generating development model..."
    ./venv/bin/python train_engine.py --create-dummy
fi

# ─── PM2 Process Manager ─────────────────────────────────────
echo "[+] Setting up PM2..."
if ! command -v pm2 &> /dev/null; then
    echo "[+] Installing Node.js and PM2..."
    # Install Node.js via NodeSource if not present
    if ! command -v node &> /dev/null; then
        curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
        sudo apt-get install -y nodejs
    fi
    sudo npm install -g pm2
fi

# Stop existing service if running
pm2 delete ser-api-service 2>/dev/null || true
pm2 start ecosystem.config.js
pm2 save
pm2 startup 2>/dev/null || true

# ─── Nginx Reverse Proxy ─────────────────────────────────────
echo "[+] Configuring Nginx reverse proxy..."
sudo cp sentivox-nginx.conf /etc/nginx/sites-available/sentivox
sudo ln -sf /etc/nginx/sites-available/sentivox /etc/nginx/sites-enabled/sentivox
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl enable nginx
sudo systemctl restart nginx
echo "[✓] Nginx configured for 144.24.142.3"

# ─── Firewall (Oracle Cloud iptables) ────────────────────────
echo "[+] Opening firewall ports 80 and 8000..."
sudo iptables -I INPUT -p tcp --dport 80 -j ACCEPT 2>/dev/null || true
sudo iptables -I INPUT -p tcp --dport 8000 -j ACCEPT 2>/dev/null || true

# ─── Verify ──────────────────────────────────────────────────
echo ""
sleep 3
echo "[+] Verifying deployment..."
HEALTH=$(curl -s http://127.0.0.1:8000/health 2>/dev/null || echo "FAILED")
echo "Health check: $HEALTH"

echo ""
echo "================================================================="
echo "  ✅ Deployment complete!"
echo ""
echo "  Backend API:     http://144.24.142.3:8000"
echo "  Dashboard:       http://144.24.142.3"
echo "  Health Check:    http://144.24.142.3/health"
echo "  API Docs:        http://144.24.142.3/docs (disabled in prod)"
echo ""
echo "  PM2 status:      pm2 status"
echo "  PM2 logs:        pm2 logs ser-api-service"
echo "  Nginx logs:      tail -f /var/log/nginx/sentivox_*.log"
echo "================================================================="
