# Audit Log (Phase B-2 Minimal)

- Default path: `/tmp/culture-escrow-pg17/audit.log.jsonl`
- Override: `PG17_AUDIT_LOG_PATH`

## Events
- `auth_failed`
- `fill_failed`
- `fill_success`

## Fields (common)
- `event`
- `request_id`
- `job_id` (when available)
- `ts` (unix timestamp)
- `actor` (from `x-actor` header)

## Privacy
- Input fields are masked where needed (e.g., escrow number)
- Avoid writing full PDF content or sensitive payloads
