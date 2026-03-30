# GitHub Actions → EC2 Deploy (PR16)

## 目标
当 `main` 分支有新 commit merge 后，自动部署到 EC2。

## 依赖条件
- EC2 已完成首次手工部署
- 目标目录已存在（如 `/opt/services/culture-escrow-pg17`）
- `pg17.service` 已配置
- 仓库在 EC2 上可 `git pull`

## 需要配置的 GitHub Secrets
- `EC2_HOST`
- `EC2_USER`
- `EC2_SSH_KEY`
- `EC2_DEPLOY_PATH`

建议值：
- `EC2_HOST=50.18.170.151`
- `EC2_USER=ubuntu`
- `EC2_DEPLOY_PATH=/opt/services/culture-escrow-pg17`

## 流程
1. checkout repo
2. 写入 SSH key
3. SSH 到 EC2
4. 执行 `deploy/scripts/deploy_prod.sh`
5. 远端完成：
   - git pull
   - pip install
   - install engine deps
   - restart pg17
   - health check

## 首次验证
在 GitHub Actions 页手动触发 `workflow_dispatch`，确认 deploy job 通过。
