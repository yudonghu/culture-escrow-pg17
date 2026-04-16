# Audit Log

- Production path: `/var/log/pg17/prod-audit.log.jsonl`
- Override: `PG17_AUDIT_LOG_PATH`
- Format: JSONL (one JSON object per line)

## Events
- `auth_failed`: authentication token mismatch
- `fill_success`: fill job completed successfully
- `fill_failed`: fill job failed (engine error or validation error)
- `retention_cleanup`: periodic file cleanup executed

## Fields (common)
- `event`
- `request_id`
- `job_id` (when available)
- `ts` (unix timestamp)
- `actor` (from `x-actor` header)

## Additional Fields by Event

### fill_success / fill_failed
- `escrow_number`
- `deposit_amount`
- `seller_agent_name`
- `acceptance_date` → **[redacted]** (PR #20 脱敏)
- `second_date` → **[redacted]** (PR #20 脱敏)
- `engine_mode`
- `timings_ms`

### retention_cleanup
- `retention_days`
- `scanned`
- `deleted`

## Privacy
- `acceptance_date` and `second_date` are always written as `[redacted]` in audit log (PR #20)
- Never write full PDF content or sensitive payloads to logs
- Log level in production: `warning` (`PG17_LOG_LEVEL=warning`)
