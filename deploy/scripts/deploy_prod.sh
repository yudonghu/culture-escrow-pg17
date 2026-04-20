#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-/opt/services/culture-escrow-pg17}"
cd "$ROOT"

echo "[1/8] Fetch latest main"
git fetch origin
git checkout main
git pull --ff-only origin main

echo "[2/8] Ensure venv"
python3 -m venv .venv || true
source .venv/bin/activate

echo "[3/8] Install API deps"
pip install -r apps/api/requirements.txt

echo "[4/8] Install engine deps"
./deploy/scripts/install_engine_deps.sh

echo "[5/8] Sync web static files"
sudo mkdir -p /var/www/pg17-web
sudo cp "$ROOT/apps/web/index.html" /var/www/pg17-web/index.html

echo "[6/8] Install cron job"
sudo cp "$ROOT/deploy/cron/pg17-cleanup" /etc/cron.d/pg17-cleanup
sudo chmod 644 /etc/cron.d/pg17-cleanup
sudo chmod +x "$ROOT/deploy/scripts/pg17_cleanup.sh"

echo "[7/8] Restart service"
sudo systemctl restart pg17

echo "[8/8] Health check (with retries)"
for i in $(seq 1 30); do
  if curl --fail --silent http://127.0.0.1:8787/health > /dev/null 2>&1; then
    echo "[OK] service is healthy"
    break
  fi
  if [ "$i" = "30" ]; then
    echo "[ERROR] service failed to become healthy after 30s"
    sudo systemctl status pg17 --no-pager || true
    exit 1
  fi
  echo "[WAIT] attempt $i/30..."
  sleep 1
done

echo "[OK] deploy complete"
