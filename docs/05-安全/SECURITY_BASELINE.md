# 安全基线（当前已实施措施）

## 已实施（PR #20 起）

### PII 与密钥管理
- 禁止明文密钥/PII 入库（PR #20 移除了所有硬编码 PII）
- 托管公司信息（`PG17_ESCROW_COMPANY`、`PG17_BY_NAME`、`PG17_ADDRESS` 等）全部通过环境变量注入

### 认证
- Bearer token 认证（`PG17_API_TOKEN` 非空时启用）
- `GET /health` 为公开接口

### CORS
- CORS 限定到白名单 origins（`PG17_CORS_ORIGINS`，生产为 `https://app.hydenluc.com`）
- 仅允许 GET / POST 方法

### 路径安全
- 路径验证防止路径注入攻击（PR #20 收紧）

### 速率限制
- 20 次/分钟/IP（内存滑动窗口，PR #21，`PG17_RATE_LIMIT_PER_MINUTE`）

### 审计日志脱敏
- 敏感字段（`acceptance_date`、`second_date`）写入审计日志时替换为 `[redacted]`

### 文件留存
- 默认 7 天留存（`PG17_RETENTION_DAYS`）
- 支持手动即时清理（`POST /v1/admin/cleanup`，需认证）

## 待实施
- 多租户权限体系（当前为单租户）
- Redis 替代文件级幂等存储（多实例场景）
- 监控告警（连续失败、响应超时、磁盘异常）
