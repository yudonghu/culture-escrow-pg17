# 数据模型（当前生产版）

## 实体
- FillJob
- SourceFile
- FillInput
- FillSummary
- OutputArtifact

## 字段要求
- 每次任务必须带 `job_id` 和 `request_id`
- 输入与输出要可追溯
- 错误必须记录 error_code + message + request_id

## FillJob 关键字段
- `job_id`：任务唯一标识
- `request_id`：请求唯一标识（用于日志追踪）
- `idempotency_key`：可选，由客户端提供
- `engine_mode`：`real_fill` 或 `stub`
- `timings_ms`：`{upload, engine, export}` 三段耗时

## FillInput（输入参数）
- `deposit_amount`
- `seller_agent_name`
- `escrow_number`
- `acceptance_date`（审计日志中脱敏为 `[redacted]`）
- `second_date`（审计日志中脱敏为 `[redacted]`）

## FillSummary（引擎返回摘要）
- `missing_inputs`：缺失字段列表
- `filled_fields`：已填充字段列表
- `left_blank`：留空字段列表

## 审计日志（JSONL）
路径由 `PG17_AUDIT_LOG_PATH` 控制（生产：`/var/log/pg17/prod-audit.log.jsonl`）

事件类型：
- `auth_failed`：认证失败
- `fill_success`：填充成功
- `fill_failed`：填充失败
- `retention_cleanup`：文件清理

公共字段：`event`, `request_id`, `job_id`, `ts`（unix timestamp）, `actor`（来自 `x-actor` 请求头）

脱敏规则：`acceptance_date` / `second_date` 写入审计日志时替换为 `[redacted]`

## 幂等存储
文件级 JSON store，路径由 `PG17_IDEMPOTENCY_STORE` 控制（生产：`/var/lib/pg17/prod-idempotency.json`）
