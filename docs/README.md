# culture-escrow-pg17 文档总览

## 文档列表

| 文件 | 内容 |
|---|---|
| [PRD.md](PRD.md) | 产品目标、MVP 范围、验收标准 |
| [ARCHITECTURE.md](ARCHITECTURE.md) | 系统分层、模块边界、引擎运行时策略 |
| [API_SPEC.md](API_SPEC.md) | 接口定义（输入输出、错误码、认证、限流、幂等） |
| [DATA_MODEL.md](DATA_MODEL.md) | 数据模型与字段追踪 |
| [SECURITY.md](SECURITY.md) | 安全基线（已实施措施 + 待实施） |
| [ENVIRONMENTS.md](ENVIRONMENTS.md) | 环境变量说明、各环境配置差异 |
| [DEPLOY.md](DEPLOY.md) | EC2 部署、GitHub Actions、self-hosted runner |
| [RUNBOOK.md](RUNBOOK.md) | 生产运维操作手册 + 本地开发运行指南 |
| [OPERATIONS.md](OPERATIONS.md) | 审计日志、幂等性、文件留存策略 |
| [ROADMAP.md](ROADMAP.md) | 已完成阶段回顾 + 待实施计划 |
| [TEST_PLAN.md](TEST_PLAN.md) | 测试计划（42 个 pytest 测试） |

## 当前阶段
生产已上线（PR #20～#33 均已合并），服务运行于 EC2，域名 portal.cultureescrow.com/pg17。
