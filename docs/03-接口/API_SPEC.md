# API 规范（当前生产版）

## 认证
- Bearer token：请求头 `Authorization: Bearer <token>`（`PG17_API_TOKEN` 非空时启用）
- `GET /health` 为公开接口，无需认证

## 速率限制
- 20 次/分钟/IP（内存滑动窗口）
- 超限返回 `429 Too Many Requests`

## 幂等性
- 可选请求头：`x-idempotency-key`
- 同 key + 同 payload（TTL 内）：返回缓存结果，响应含 `"idempotency": {"hit": true}`
- 同 key + 不同 payload：返回 `409 PG17_409_IDEMPOTENCY_PAYLOAD_MISMATCH`
- TTL 由 `PG17_IDEMPOTENCY_TTL_SECONDS` 控制（默认 7200 秒）

---

## POST /v1/pg17/fill

### Request（multipart/form-data）
- `source_pdf` (required)：源 PDF 文件
- `deposit_amount` (optional)
- `seller_agent_name` (optional)
- `escrow_number` (optional)
- `acceptance_date` (optional)
- `second_date` (optional)

### Response（200）
```json
{
  "ok": true,
  "job_id": "...",
  "request_id": "...",
  "output_file": ".../xxx-done.pdf",
  "engine_mode": "real_fill",
  "summary": {
    "missing_inputs": [],
    "filled_fields": [],
    "left_blank": []
  },
  "timings_ms": {
    "upload": 10,
    "engine": 850,
    "export": 5
  },
  "idempotency": {
    "hit": false
  }
}
```

### Error
- 400: 参数格式错误
- 401: 认证失败
- 409: 幂等 key 冲突（payload 不匹配）
- 413: 文件过大
- 422: 模板漂移/锚点无法定位
- 429: 速率限制超限
- 500: 引擎运行失败

---

## GET /health

返回服务健康状态（公开，无需认证）：
```json
{
  "status": "ok"
}
```

---

## POST /v1/admin/cleanup

清理超出留存期的生成文件（需认证）。
- 留存期由 `PG17_RETENTION_DAYS` 控制（默认 7 天）
- 写入审计日志（event: `retention_cleanup`）
