#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

python3 -m venv "$ROOT/.venv"
source "$ROOT/.venv/bin/activate"
pip install -r "$ROOT/apps/api/requirements.txt" >/dev/null

export PYTHONPATH="$ROOT/packages/pg17-fill-engine"

echo "[1/2] Starting API on http://127.0.0.1:8787"
uvicorn apps.api.main:app --host 127.0.0.1 --port 8787 &
API_PID=$!

echo "[2/2] Starting web on http://127.0.0.1:8788"
python3 -m http.server 8788 --directory "$ROOT/apps/web" &
WEB_PID=$!

echo "Open: http://127.0.0.1:8788"
trap 'kill $API_PID $WEB_PID 2>/dev/null || true' EXIT
wait
