# 环境分层（PR11）

## 目标
建立最小可执行的 `staging / prod` 环境分层，避免“同一套配置跑所有环境”。

## 目录
- `.env.example`
- `deploy/environments/.env.staging.example`
- `deploy/environments/.env.prod.example`
- `deploy/scripts/run_api.sh`

## 使用方式
1. 复制环境模板：
   - staging: `cp deploy/environments/.env.staging.example .env.staging`
   - prod: `cp deploy/environments/.env.prod.example .env.prod`
2. 填入真实 token 与路径（不要提交到 git）。
3. 启动：
   - `deploy/scripts/run_api.sh .env.staging`
   - `deploy/scripts/run_api.sh .env.prod`

## 最小基线
- staging/prod 必须使用不同 `PG17_API_TOKEN`
- staging/prod 审计路径必须隔离
- staging/prod 幂等存储路径必须隔离
- prod 默认日志级别建议 `warning`
