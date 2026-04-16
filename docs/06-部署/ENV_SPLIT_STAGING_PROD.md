# 环境分层

## 目标
建立最小可执行的 `staging / prod` 环境分层，避免”同一套配置跑所有环境”。

## 目录
- `.env.example`：本地开发参考模板
- `deploy/environments/.env.staging.example`：staging 环境模板
- `deploy/environments/.env.prod.example`：prod 环境模板
- `deploy/scripts/run_api.sh`：本地启动脚本

## 使用方式
1. 复制环境模板：
   - staging: `cp deploy/environments/.env.staging.example .env.staging`
   - prod: `cp deploy/environments/.env.prod.example .env.prod`
2. 填入真实 token 与路径（不要提交到 git）。
3. 启动：
   - `deploy/scripts/run_api.sh .env.staging`
   - `deploy/scripts/run_api.sh .env.prod`

## 生产完整环境变量列表
```
PG17_API_TOKEN=<secret>
PG17_RETENTION_DAYS=7
PG17_AUDIT_LOG_PATH=/var/log/pg17/prod-audit.log.jsonl
PG17_IDEMPOTENCY_TTL_SECONDS=7200
PG17_IDEMPOTENCY_STORE=/var/lib/pg17/prod-idempotency.json
PG17_HOST=0.0.0.0
PG17_PORT=8787
PG17_LOG_LEVEL=warning
PG17_ENGINE_PYTHON=python3
PG17_ENGINE_SCRIPT=tools/pg17-engine/fill_page17_real.py
PG17_ESCROW_COMPANY=Culture Escrow Inc.
PG17_BY_NAME=ESCROW_AGENT_NAME
PG17_ADDRESS=...
PG17_PHONE=...
PG17_LICENSE=...
PG17_COUNTER_OFFER_NUMBERS=one
PG17_CORS_ORIGINS=https://app.hydenluc.com
PG17_RATE_LIMIT_PER_MINUTE=20
```

## 最小基线
- staging/prod 必须使用不同 `PG17_API_TOKEN`
- staging/prod 审计路径必须隔离
- staging/prod 幂等存储路径必须隔离
- prod 默认日志级别建议 `warning`
- PII 相关变量（`PG17_ESCROW_COMPANY` 等）仅在生产环境配置，本地测试不需要
