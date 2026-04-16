#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-/opt/services/culture-escrow-pg17}"
cd "$ROOT"

echo "[1/6] Fetch latest main"
git fetch origin
git checkout main
git pull --ff-only origin main

echo "[2/6] Ensure venv"
python3 -m venv .venv || true
source .venv/bin/activate

echo "[3/6] Install API deps"
pip install -r apps/api/requirements.txt

echo "[4/6] Install engine deps"
./deploy/scripts/install_engine_deps.sh

echo "[5/6] Sync web static files"
sudo mkdir -p /var/www/pg17-web
sudo cp "$ROOT/apps/web/index.html" /var/www/pg17-web/index.html

echo "[6/7] Restart service"
sudo systemctl restart pg17

echo "[7/7] Health check (with retries)"
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
