# 测试计划

## 当前状态
已有 42 个自动化测试（PR #26），位于 `tests/` 目录，使用 pytest。

## 运行方式
```bash
source .venv/bin/activate
python -m pytest tests/ -v
```

- 本地测试使用 stub engine，不需要 `PG17_ESCROW_COMPANY` 等生产 PII 变量
- CI 环境：GitHub Actions self-hosted runner 在部署前执行

## 测试类型
- 单元测试：PG17Service 各方法（幂等、审计、参数校验等）
- 集成测试：API 端点 `/v1/pg17/fill`、`/health`、`/v1/admin/cleanup`

## 用例覆盖
- 正常输入（5参数齐全）
- 缺失参数输入
- 认证失败（401）
- 速率限制（429）
- 幂等性：相同 key 返回缓存结果
- 幂等性：相同 key + 不同 payload 返回 409
- 文件留存清理
- 引擎失败（stub 模拟）
- 路径注入防护

## 验证点
- 输出文件可打开
- 填充字段位置正确
- summary 与实际一致
- 审计日志写入正确
- 敏感字段脱敏验证

## 待补充
- 速率限制边界测试（压测）
- OCR 干扰输入（边界样本，需真实 engine）
- 模板漂移检测（422 场景）
