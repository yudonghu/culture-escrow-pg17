#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ENV_FILE="${1:-$ROOT/.env}"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "[ERROR] env file not found: $ENV_FILE"
  exit 1
fi

set -a
source "$ENV_FILE"
set +a

source "$ROOT/.venv/bin/activate"
export PYTHONPATH="$ROOT/packages/pg17-fill-engine"

exec uvicorn apps.api.main:app --host "${PG17_HOST:-127.0.0.1}" --port "${PG17_PORT:-8787}" --log-level "${PG17_LOG_LEVEL:-info}"
