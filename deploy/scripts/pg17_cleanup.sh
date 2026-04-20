#!/usr/bin/env bash
# pg17 retention cleanup — run by cron, logs to /var/log/pg17/cleanup.log
#
# Usage: pg17_cleanup.sh [env_file]
#   env_file defaults to /opt/services/culture-escrow-pg17/.env.prod

set -euo pipefail

ENV_FILE="${1:-/opt/services/culture-escrow-pg17/.env.prod}"
TOKEN=""
if [ -f "$ENV_FILE" ]; then
    TOKEN=$(grep -E '^PG17_API_TOKEN=' "$ENV_FILE" | cut -d= -f2- | tr -d '[:space:]' || true)
fi

CURL_ARGS=(-s -X POST http://127.0.0.1:8787/v1/admin/cleanup)
if [ -n "$TOKEN" ]; then
    CURL_ARGS+=(-H "x-api-token: $TOKEN")
fi

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] pg17 cleanup started"
curl "${CURL_ARGS[@]}"
echo ""
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] pg17 cleanup done"
