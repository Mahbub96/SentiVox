#!/bin/bash
set -e

echo "[+] Updating system packages..."
sudo apt-get update -y && sudo apt-get install -y ffmpeg libsndfile1 apache2 nodejs npm

echo "[+] Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "[+] Installing and starting PM2 service..."
sudo npm install -g pm2
pm2 start ecosystem.config.js
pm2 save
pm2 startup

echo "[+] Configuring Apache reverse proxy..."
sudo a2enmod proxy proxy_http headers rewrite
if [ -f ser-api.conf ]; then
    sudo cp ser-api.conf /etc/apache2/sites-available/ser-api.conf
    sudo a2ensite ser-api.conf
fi
sudo apache2ctl configtest
sudo systemctl restart apache2

echo "[+] Deployment complete! Service active on port 80/8000."
