# culture-escrow-pg17 文档总览

本项目采用 **docs-first** 开发方式：先定义边界、接口、数据与流程，再开始编码。

## 文档目录
- `01-产品/PRD.md`：产品目标、范围、验收标准
- `02-架构/ARCHITECTURE.md`：客户端/服务端/模块分层（HTTP层 + 业务层）
- `02-架构/ENGINE_RUNTIME.md`：引擎运行时策略
- `03-接口/API_SPEC.md`：接口定义（输入输出/错误码/认证/限流）
- `04-数据/DATA_MODEL.md`：数据模型与字段追踪
- `05-安全/SECURITY_BASELINE.md`：安全基线（当前已实施措施）
- `06-部署/ENVIRONMENTS.md`：环境与发布策略
- `06-部署/EC2_DEPLOY_RUNBOOK.md`：EC2 首次部署步骤
- `06-部署/ENV_SPLIT_STAGING_PROD.md`：staging/prod 环境分层
- `06-部署/GITHUB_ACTIONS_EC2_DEPLOY.md`：GitHub Actions 自动部署
- `06-部署/SELF_HOSTED_RUNNER_SETUP.md`：Self-hosted Runner 配置
- `07-路线图/DEMO_TO_PROD_ROADMAP_v1.0.md`：Demo → Prod 迁移路线图
- `07-路线图/IMPLEMENTATION_PLAN.md`：阶段实施计划
- `08-测试/TEST_PLAN.md`：测试计划（含 42 个自动化测试）
- `09-运维/RUNBOOK.md`：运行与故障处理
- `09-运维/AUDIT_LOG.md`：审计日志规范
- `09-运维/IDEMPOTENCY.md`：幂等性与重试安全
- `09-运维/LOCAL_DEMO_RUNBOOK.md`：本地开发运行手册
- `09-运维/RETENTION_POLICY.md`：文件留存策略
- `09-运维/WEB_V1_ONLINE_ENTRY.md`：Web 前端上线说明

## 当前阶段
- 生产已上线（PR #20～#29 均已合并），服务运行于 EC2，域名 portal.cultureescrow.com/pg17
