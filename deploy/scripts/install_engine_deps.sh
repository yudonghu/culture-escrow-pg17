#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

source .venv/bin/activate
pip install -r tools/pg17-engine/requirements.txt

if command -v apt >/dev/null 2>&1; then
  sudo apt update
  sudo apt -y install tesseract-ocr
else
  echo "[WARN] apt not found; please install tesseract-ocr manually"
fi

echo "[OK] pg17 engine dependencies installed"
