# 环境与部署

## 本地开发
- 单机运行
- 使用 stub engine（`fill_page17_stub.py`）
- 无需配置 PII 环境变量
- 参见 `09-运维/LOCAL_DEMO_RUNBOOK.md`

## 生产（当前运行中）
- EC2（Ubuntu），IP：50.18.170.151
- 部署路径：`/opt/services/culture-escrow-pg17/`
- env 文件：`/opt/services/culture-escrow-pg17/.env.prod`
- systemd 服务：`pg17`（端口 8787）
- 反向代理：Caddy
- API URL：`api.hydenluc.com`
- 前端 URL：`portal.cultureescrow.com/pg17`
- Web 静态文件：`/var/www/pg17-web/index.html`（由 Caddy 服务）
- 自动部署：push to main → GitHub Actions self-hosted runner → `deploy_prod.sh`

## 存储策略
- 生成文件留存 7 天（`PG17_RETENTION_DAYS=7`）
- 审计日志：`/var/log/pg17/prod-audit.log.jsonl`
- 幂等存储：`/var/lib/pg17/prod-idempotency.json`

## 监控与告警
- 当前：依赖 systemd + Caddy 基础监控
- 待实施：指标面板、连续失败告警、响应超时告警
