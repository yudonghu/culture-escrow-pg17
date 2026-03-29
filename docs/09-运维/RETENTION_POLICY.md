# Retention Policy (Phase B-3 MVP)

## Purpose
Control how long generated files are kept on disk.

## Default
- `PG17_RETENTION_DAYS=7`

## Config
- `PG17_RETENTION_DAYS` (int, days)
- `PG17_AUDIT_LOG_PATH` (jsonl audit path)

## Cleanup API
- `POST /v1/admin/cleanup`
- Requires auth when `PG17_API_TOKEN` is set.
- Performs best-effort deletion for files older than retention window.

## Audit
Each cleanup writes audit event:
- `event=retention_cleanup`
- `retention_days`
- `scanned`
- `deleted`
- timestamp
