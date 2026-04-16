# culture-escrow-pg17 Demo → Prod 迁移路线图 v1.0

更新时间：2026-04-16  
适用范围：culture-escrow-pg17 项目

---

## 1) 当前状态（As-Is）

已完成（生产上线）：
- [x] 本地 Web 上传 + API `/v1/pg17/fill` + done.pdf 下载
- [x] 基础输入校验（日期格式）
- [x] 基础错误提示与本地 Runbook
- [x] docs-first 文档骨架
- [x] EC2 生产部署（systemd + Caddy）
- [x] GitHub Actions self-hosted runner 自动部署
- [x] Bearer token 认证
- [x] 速率限制 20次/分钟/IP
- [x] 幂等性（x-idempotency-key）
- [x] 审计日志（JSONL，敏感字段脱敏）
- [x] 文件留存 7 天 + cleanup API
- [x] PII 移至环境变量（移除硬编码）
- [x] CORS 收紧到白名单
- [x] 路径注入防护
- [x] 业务逻辑抽取到 pg17_service.py（HTTP层/业务层分离）
- [x] 42 个自动化测试（pytest）
- [x] Engine 依赖版本锁定
- [x] Web UI 改版（Source PDF 全宽、自定义文件选择框、Status 默认隐藏、How to Use 步骤说明）
- [x] 部署脚本自动同步 Web 静态文件到 /var/www/pg17-web/

当前定位：**已生产上线，服务运行于 EC2，域名 portal.cultureescrow.com/pg17**。

---

## 2) 目标状态（To-Be）

达到“可生产运行”的最低标准：
1. 可控：权限、审计、风险边界清晰
2. 可稳：高峰不崩、失败可重试、错误可定位
3. 可运维：有监控、有告警、有回滚
4. 可治理：数据留存策略、版本管理、变更可追溯

---

## 3) 分阶段计划（建议 4 周）

## Phase A（Week 1）稳定性与可观测性 ✅ 已完成

### A1. 错误体系标准化 ✅
- [x] 统一 error code（400/413/422/500 子码）
- [x] 统一返回格式：`message / error_code / hint / request_id`

### A2. 日志与追踪 ✅
- [x] 每次任务生成 `request_id/job_id`
- [x] API 记录关键阶段耗时（upload/engine/export timings_ms）

### A3. 健康检查 ✅
- [x] `/health` 公开接口已实现

---

## Phase B（Week 2）安全与治理 ✅ 已完成

### B1. 认证与权限 ✅
- [x] Bearer token 认证（`PG17_API_TOKEN`）
- 多租户权限体系（待实施，非当前需求）

### B2. 审计日志 ✅
- [x] 记录 event/request_id/job_id/ts/actor
- [x] 支持按 request_id 查询（通过 JSONL 文件）
- [x] 敏感字段脱敏（acceptance_date/second_date → [redacted]）

### B3. 文件留存策略 ✅
- [x] 默认 7 天留存（`PG17_RETENTION_DAYS=7`）
- [x] 手动即时清理（`POST /v1/admin/cleanup`）

---

## Phase C（Week 3）任务可靠性 部分完成

### C1. 异步任务队列（轻量）
- [ ] 前端提交后返回 job_id（当前为同步处理）

### C2. 重试与幂等 ✅
- [x] 同一 x-idempotency-key 防重复处理（TTL 7200 秒）

### C3. 超时与取消
- [ ] 任务超时可标记失败（待实施）

---

## Phase D（Week 4）上线准备 ✅ 基本完成

### D1. 环境分层 ✅
- [x] dev / prod 两环境（staging 暂未独立部署）
- [x] 配置文件与 secrets 分离

### D2. 部署与回滚 ✅
- [x] push to main 自动部署（self-hosted runner）
- [ ] 版本化发布（tag）+ 一键回滚（待实施）

### D3. 监控与告警
- [ ] 指标面板（待实施）
- [ ] 告警：连续失败、响应超时、磁盘异常（待实施）

---

## 4) 生产最低门槛（Go-Live Checklist）

- [x] 认证与权限已启用
- [x] 审计日志可查询
- [x] 错误码与 request_id 可追踪
- [x] 留存与删除策略可执行
- [x] 幂等/重试机制已启用（文件级）
- [ ] staging 压测通过（待执行）
- [ ] 回滚演练通过（待执行）
- [ ] 监控告警在线（待实施）

---

## 5) 风险与应对

1. 模板漂移导致填充偏移
- 应对：模板版本标识 + 锚点检测 + 422 明确提示

2. 依赖升级导致行为变化
- 应对：锁版本 + staging 回归测试

3. 敏感数据泄漏风险
- 应对：日志脱敏 + 最小留存 + 权限隔离

4. 并发导致性能下降
- 应对：队列化 + 限流 + 预警阈值

---

## 6) 下一步（待实施优先级）

1. 监控告警（连续失败、响应超时、磁盘异常）
2. 版本化发布（tag）+ 回滚机制
3. staging 环境独立部署 + 压测
4. 异步任务队列（当前同步处理在引擎慢时可能超时）
5. Redis 替代文件级幂等存储（为多实例扩容做准备）
