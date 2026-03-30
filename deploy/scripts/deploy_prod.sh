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

echo "[5/6] Restart service"
sudo systemctl restart pg17
sleep 2

echo "[6/6] Health check"
curl --fail http://127.0.0.1:8787/health

echo "[OK] deploy complete"
