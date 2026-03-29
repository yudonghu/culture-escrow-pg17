# Idempotency & Retry Safety (Phase M3)

## Purpose
Avoid duplicate processing when client retries the same request.

## Headers
- `x-idempotency-key` (optional)

## Behavior
- Same key + same payload within TTL => returns cached success response (`idempotency.hit=true`).
- Same key + different payload => `409 PG17_409_IDEMPOTENCY_PAYLOAD_MISMATCH`.
- No key => normal processing.

## Config
- `PG17_IDEMPOTENCY_TTL_SECONDS` (default `3600`)
- `PG17_IDEMPOTENCY_STORE` (default `/tmp/culture-escrow-pg17/idempotency_store.json`)

## Notes
- Current implementation is file-based MVP for single-instance deployment.
- For production multi-instance, replace with shared store (e.g., Redis).
