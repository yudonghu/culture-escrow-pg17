# 实施路线图

## Phase 0（文档框架）✅ 已完成
- [x] 文档框架建立
- [x] PRD / 架构 / API / 数据 / 安全 / 部署 / 测试 / 运维文档草案

## Phase 1（MVP）✅ 已完成
- [x] API skeleton（FastAPI，`apps/api/main.py`）
- [x] pg17 engine package（`packages/pg17-fill-engine/pg17_engine.py`）
- [x] web 上传页（`apps/web/index.html`）
- [x] done.pdf 下载
- [x] 真实样本验证

## Phase 2（增强）✅ 已完成（PR #20～#29）
- [x] 认证（Bearer token）
- [x] 速率限制（20次/分钟/IP）
- [x] 幂等性（x-idempotency-key，TTL 7200s）
- [x] 审计日志（JSONL，敏感字段脱敏）
- [x] 文件留存策略（7天 + cleanup API）
- [x] 安全加固（移除硬编码 PII、收紧 CORS、路径注入防护）
- [x] 业务层抽取（pg17_service.py，PR #25）
- [x] 自动化测试（42 个 pytest 测试，PR #26）
- [x] Engine 依赖版本锁定（PR #24）
- [x] EC2 生产部署（systemd + Caddy + self-hosted runner）
- [x] Web UI 改版（PR #28：全宽上传、How to Use、Status 默认隐藏）
- [x] 部署脚本同步 Web 静态文件（PR #29）

## Phase 3（待实施）
- [ ] 监控告警面板
- [ ] 版本化发布（tag）+ 回滚机制
- [ ] staging 环境独立部署
- [ ] 异步任务队列
- [ ] Redis 幂等存储（多实例扩容）
- [ ] 多租户权限体系

## Phase A-2（可观测性）✅ 已完成
- [x] API 返回 upload/engine/export 三段耗时（timings_ms）
- [x] 日志记录 request_id + job_id + 三段耗时
- [ ] 后续接入监控面板
