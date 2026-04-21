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

---

## 4. 监控告警

### 机制
每 5 分钟 cron 调用 `deploy/scripts/pg17_monitor.py`，检查：
- `/health` 端点可达性与 `ok` 状态
- 磁盘可用空间（阈值 `PG17_DISK_WARN_GB`，默认 2.0 GB）

### 告警策略
- 连续 `PG17_MONITOR_FAIL_THRESHOLD`（默认 3）次失败后发送告警邮件
- 服务恢复后发送恢复通知
- 状态持久化到 `PG17_MONITOR_STATE_FILE`，避免重复告警

### 告警目标
- 收件人：`PG17_ALERT_EMAIL`（默认 `hydenluc@gmail.com`）
- 发送方式：Gmail SMTP（需配置 `PG17_ALERT_SMTP_*` 变量）

### 所需环境变量
| 变量 | 说明 |
|---|---|
| `PG17_ALERT_EMAIL` | 告警收件人 |
| `PG17_ALERT_SMTP_USER` | Gmail 账户地址 |
| `PG17_ALERT_SMTP_PASSWORD` | Gmail App Password（非账户密码） |
| `PG17_DISK_WARN_GB` | 磁盘告警阈值（默认 `2.0`） |
| `PG17_MONITOR_FAIL_THRESHOLD` | 触发告警的连续失败次数（默认 `3`） |

### Gmail App Password 获取方式
Gmail → 账号设置 → 安全性 → 两步验证 → 应用专用密码 → 生成

### 日志
监控结果追加至 `/var/log/pg17/monitor.log`（已被 logrotate 管理）
