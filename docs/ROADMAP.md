# 路线图

更新时间：2026-04-16

---

## 当前状态（已完成，生产上线）

- [x] 本地 Web 上传 + API `/v1/pg17/fill` + done.pdf 下载
- [x] Bearer token 认证（`PG17_API_TOKEN`）
- [x] 速率限制（20次/分钟/IP）
- [x] 幂等性（x-idempotency-key，TTL 7200s）
- [x] 审计日志（JSONL，敏感字段脱敏）
- [x] 文件留存 7 天 + cleanup API
- [x] 安全加固（移除硬编码 PII、收紧 CORS、路径注入防护）
- [x] 业务层抽取（pg17_service.py，HTTP层/业务层分离）
- [x] 42 个自动化测试（pytest）
- [x] Engine 依赖版本锁定
- [x] EC2 生产部署（systemd + Caddy + self-hosted runner）
- [x] Web UI 改版（全宽上传、How to Use、Status 默认隐藏）
- [x] 部署脚本自动同步 Web 静态文件
- [x] 统一 error code + request_id 追踪
- [x] API 返回三段耗时（timings_ms）
- [x] `/health` 公开接口
- [x] 文档整理（docs-first，docs 扁平化）
- [x] Web UI 错误提示按状态码分类 + 60s 超时保护（PR #36）
- [x] 修复 Caddyfile 缺少 `api.hydenluc.com`（服务不可达）
- [x] 修复生产 CORS 漏掉 `portal.cultureescrow.com`
- [x] git 历史 PII 清除（`git filter-repo`）+ repo 改为 public
- [x] Caddyfile 纳入版本控制（`deploy/caddy/Caddyfile.example`）
- [x] S3 永久存储（生成的 PDF 上传至 S3，命名规则 `{escrow}_{job_id_short}_{timestamp}.pdf`，IAM role 鉴权，SSE-S3 加密，写入专用策略）

**当前定位：生产上线，服务运行于 EC2，域名 portal.cultureescrow.com/pg17。**

---

## 实施阶段回顾

### Phase 0 — 文档框架 ✅
- PRD / 架构 / API / 数据 / 安全 / 部署 / 测试 / 运维文档

### Phase 1 — MVP ✅
- API skeleton（FastAPI）
- pg17 engine package
- Web 上传页
- done.pdf 下载 + 样本验证

### Phase 2 — 生产加固 ✅（PR #20～#33）
- 认证、限流、幂等、审计、留存、安全加固
- 业务层抽取、自动化测试、Engine 依赖锁定
- EC2 部署、Web UI 改版、结构优化

### Phase 3 — 待实施

#### 近期（改动小，优先做）
- [x] `.env.prod.example` 补全 CORS 配置（`portal.cultureescrow.com` 漏掉了）
- [x] PR 时自动跑测试（GitHub Actions test workflow，merge 前验证）
- [x] Makefile（`make install` / `make run` / `make test` / `make web`）
- [x] `/health` 返回版本号（commit sha）和 uptime

#### 运维
- [ ] 审计日志自动轮转（logrotate，防止无限增长）
- [ ] 自动清理 cron job（定期触发 retention cleanup，替代手动）

#### 基础设施
- [ ] 监控告警（连续失败、响应超时、磁盘异常）
- [ ] 版本化发布（tag）+ 回滚机制
- [ ] staging 环境独立部署 + 压测

#### 较大改动
- [ ] 异步任务队列（当前同步处理在引擎慢时可能超时）
- [ ] Redis 幂等存储（多实例扩容）
- [ ] 多租户权限体系

---

## Go-Live Checklist

- [x] 认证与权限已启用
- [x] 审计日志可查询
- [x] 错误码与 request_id 可追踪
- [x] 留存与删除策略可执行
- [x] 幂等/重试机制已启用
- [ ] staging 压测通过（待执行）
- [ ] 回滚演练通过（待执行）
- [ ] 监控告警在线（待实施）

---

## 风险与应对

| 风险 | 应对 |
|---|---|
| 模板漂移导致填充偏移 | 模板版本标识 + 锚点检测 + 422 明确提示 |
| 依赖升级导致行为变化 | 锁版本 + staging 回归测试 |
| 敏感数据泄漏 | 日志脱敏 + 最小留存 + 权限隔离 |
| 并发导致性能下降 | 队列化 + 限流 + 预警阈值 |
