#!/usr/bin/env bash
# Deploy pg17 to staging (pg17.staging.hydenluc.com, port 8789).
#
# Usage: deploy_staging.sh [root] [ref]
#   root  deploy root, defaults to /opt/services/culture-escrow-pg17
#   ref   branch or tag to deploy, defaults to main
#
# Example: deploy a feature branch
#   bash deploy_staging.sh /opt/services/culture-escrow-pg17 feat/my-feature

set -euo pipefail

ROOT="${1:-/opt/services/culture-escrow-pg17}"
REF="${2:-main}"
cd "$ROOT"

echo "[1/6] Fetch and checkout $REF"
git fetch origin
if [ "$REF" = "main" ]; then
    git checkout main
    git pull --ff-only origin main
else
    git checkout "$REF"
fi

echo "[2/6] Ensure venv"
python3 -m venv .venv || true
source .venv/bin/activate

echo "[3/6] Install API deps"
pip install -r apps/api/requirements.txt

echo "[4/6] Install engine deps"
./deploy/scripts/install_engine_deps.sh

echo "[5/6] Restart pg17-staging"
sudo systemctl restart pg17-staging

echo "[6/6] Health check (with retries)"
for i in $(seq 1 30); do
  if curl --fail --silent http://127.0.0.1:8789/health > /dev/null 2>&1; then
    echo "[OK] staging is healthy"
    break
  fi
  if [ "$i" = "30" ]; then
    echo "[ERROR] staging failed to become healthy after 30s"
    sudo systemctl status pg17-staging --no-pager || true
    exit 1
  fi
  echo "[WAIT] attempt $i/30..."
  sleep 1
done

echo "[OK] staging deploy complete (ref=$REF)"
