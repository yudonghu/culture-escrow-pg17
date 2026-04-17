# 运维机制

## 1. 审计日志

- 生产路径：`/var/log/pg17/prod-audit.log.jsonl`
- 覆盖变量：`PG17_AUDIT_LOG_PATH`
- 格式：JSONL（每行一个 JSON 对象）

### 事件类型
- `auth_failed`：认证 token 不匹配
- `fill_success`：填充任务完成
- `fill_failed`：填充任务失败（引擎错误或校验错误）
- `retention_cleanup`：文件清理执行

### 公共字段
- `event`
- `request_id`
- `job_id`（有时可用）
- `ts`（unix timestamp）
- `actor`（来自 `x-actor` 请求头）

### fill_success / fill_failed 附加字段
- `escrow_number`
- `deposit_amount`
- `seller_agent_name`
- `acceptance_date` → **[redacted]**（脱敏）
- `second_date` → **[redacted]**（脱敏）
- `engine_mode`
- `timings_ms`

### retention_cleanup 附加字段
- `retention_days`
- `scanned`
- `deleted`

### 隐私规则
- `acceptance_date` 和 `second_date` 始终写为 `[redacted]`
- 不记录 PDF 内容或完整 payload
- 生产日志级别：`warning`（`PG17_LOG_LEVEL=warning`）

---

## 2. 幂等性

### 用途
防止客户端重试时重复处理同一请求。

### 请求头
- `x-idempotency-key`（可选）

### 行为
- 相同 key + 相同 payload（TTL 内）→ 返回缓存结果（`idempotency.hit=true`）
- 相同 key + 不同 payload → `409 PG17_409_IDEMPOTENCY_PAYLOAD_MISMATCH`
- 无 key → 正常处理

### 配置
- `PG17_IDEMPOTENCY_TTL_SECONDS`（默认 `7200`）
- `PG17_IDEMPOTENCY_STORE`（生产：`/var/lib/pg17/prod-idempotency.json`）

### 备注
当前实现为文件级单实例方案。多实例扩容时需替换为共享存储（如 Redis）。

---

## 3. 文件留存策略

### 用途
控制生成文件在磁盘上的保留时长。

### 默认配置
- `PG17_RETENTION_DAYS=7`

### 清理 API
- `POST /v1/admin/cleanup`
- 需认证（`PG17_API_TOKEN` 非空时）
- 删除超出留存期的文件（best-effort）

### 审计记录
每次清理写入审计事件：
- `event=retention_cleanup`
- `retention_days`
- `scanned`
- `deleted`
- `ts`（timestamp）
