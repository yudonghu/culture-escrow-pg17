# 环境与配置

## 环境概览

| 环境 | 用途 | Engine | PII 变量 |
|---|---|---|---|
| local | 本地开发/测试 | stub | 不需要 |
| staging | 预发布验证 | real | 需要 |
| prod | 生产 | real | 需要 |

## 环境模板文件
- `.env.example`：本地开发参考模板
- `deploy/environments/.env.staging.example`：staging 环境模板
- `deploy/environments/.env.prod.example`：prod 环境模板

## 使用方式
```bash
# staging
cp deploy/environments/.env.staging.example .env.staging

# prod
cp deploy/environments/.env.prod.example .env.prod
```
填入真实 token 与路径后不要提交到 git。

---

## 完整环境变量说明

### 核心
| 变量 | 说明 | 默认值 |
|---|---|---|
| `PG17_API_TOKEN` | Bearer token，空则禁用认证 | 空 |
| `PG17_RETENTION_DAYS` | 生成文件留存天数 | 7 |
| `PG17_AUDIT_LOG_PATH` | 审计日志路径（JSONL） | `/tmp/culture-escrow-pg17/audit.log.jsonl` |
| `PG17_IDEMPOTENCY_TTL_SECONDS` | 幂等 key TTL | 3600 |
| `PG17_IDEMPOTENCY_STORE` | 幂等存储文件路径 | `/tmp/culture-escrow-pg17/idempotency_store.json` |

### 运行时
| 变量 | 说明 | 默认值 |
|---|---|---|
| `PG17_HOST` | 监听地址 | `127.0.0.1` |
| `PG17_PORT` | 监听端口 | 8787 |
| `PG17_LOG_LEVEL` | 日志级别 | `info` |

### Engine
| 变量 | 说明 | 默认值 |
|---|---|---|
| `PG17_ENGINE_PYTHON` | Python 解释器路径 | `python3` |
| `PG17_ENGINE_SCRIPT` | 引擎脚本路径 | `packages/pg17-fill-engine/fill_page17_stub.py` |

### Escrow 公司固定字段（生产必填，本地不需要）
| 变量 | 说明 |
|---|---|
| `PG17_ESCROW_COMPANY` | 托管公司名称 |
| `PG17_BY_NAME` | 签署人姓名 |
| `PG17_ADDRESS` | 地址 |
| `PG17_PHONE` | 电话 |
| `PG17_LICENSE` | 执照号 |
| `PG17_COUNTER_OFFER_NUMBERS` | Counter offer 编号（默认 `one`） |

### CORS & 限流
| 变量 | 说明 | 默认值 |
|---|---|---|
| `PG17_CORS_ORIGINS` | 允许的 origin（逗号分隔） | `http://127.0.0.1:8080,...` |
| `PG17_RATE_LIMIT_PER_MINUTE` | 每 IP 每分钟请求上限（0 = 关闭） | 20 |

### S3 永久存储（可选）
| 变量 | 说明 | 默认值 |
|---|---|---|
| `PG17_S3_BUCKET` | S3 bucket 名称，空则禁用上传 | 空 |
| `PG17_S3_REGION` | S3 bucket 所在区域 | `us-west-1` |

> **鉴权方式**：EC2 IAM role（不存储 Access Key），要求 EC2 附加的 role 拥有对该 bucket 的 `s3:PutObject` 权限。  
> **加密**：SSE-S3（AWS 托管密钥，默认开启，无需配置）。  
> **命名规则**：`{escrow_number}_{job_id_short}_{YYYYMMDD-HHMMSS}.pdf`。  
> **失败不阻断**：S3 上传失败只记录日志，不影响主流程返回。

---

## 各环境差异

### local
```
PG17_HOST=127.0.0.1
PG17_LOG_LEVEL=info
PG17_ENGINE_SCRIPT=packages/pg17-fill-engine/fill_page17_stub.py
PG17_IDEMPOTENCY_TTL_SECONDS=3600
# PII 变量不需要填
```

### staging
```
PG17_HOST=0.0.0.0
PG17_LOG_LEVEL=info
PG17_ENGINE_SCRIPT=packages/pg17-fill-engine/fill_page17_real.py
PG17_IDEMPOTENCY_TTL_SECONDS=3600
PG17_CORS_ORIGINS=https://staging.hydenluc.com,http://localhost:8080
# PII 变量需要填入
```

### prod
```
PG17_HOST=0.0.0.0
PG17_LOG_LEVEL=warning
PG17_ENGINE_SCRIPT=packages/pg17-fill-engine/fill_page17_real.py
PG17_IDEMPOTENCY_TTL_SECONDS=7200
PG17_AUDIT_LOG_PATH=/var/log/pg17/prod-audit.log.jsonl
PG17_IDEMPOTENCY_STORE=/var/lib/pg17/prod-idempotency.json
PG17_CORS_ORIGINS=https://portal.cultureescrow.com,https://app.hydenluc.com
PG17_S3_BUCKET=culture-escrow-pg17-outputs
PG17_S3_REGION=us-west-1
# PII 变量需要填入
```

## 最小基线规则
- staging/prod 必须使用不同 `PG17_API_TOKEN`
- staging/prod 审计路径必须隔离
- staging/prod 幂等存储路径必须隔离
- prod 日志级别建议 `warning`
- PII 相关变量仅在生产环境配置，本地测试不需要
