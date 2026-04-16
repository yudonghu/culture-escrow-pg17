# GitHub Actions → EC2 Deploy

## 当前方案：Self-Hosted Runner（正式长期方案）

当 `main` 分支有新 commit merge 后，通过 self-hosted runner 自动部署到 EC2。

工作流文件：`.github/workflows/deploy-self-hosted.yml`

### 优势（相比 SSH 方案）
- 不依赖 GitHub runner 公网 SSH 到 EC2
- 不需要 `EC2_SSH_KEY` secret
- 不需要开放 22 端口给 GitHub Actions 公网 IP
- 部署逻辑直接在目标主机执行

### 依赖条件
- EC2 已完成首次手工部署（参见 `EC2_DEPLOY_RUNBOOK.md`）
- Self-hosted runner 已安装并运行（参见 `SELF_HOSTED_RUNNER_SETUP.md`）
- 目标目录已存在（`/opt/services/culture-escrow-pg17`）
- `pg17.service` 已配置

### 流程
1. self-hosted runner 在 EC2 本地执行
2. `deploy/scripts/deploy_prod.sh` 步骤：
   - `git pull`
   - `pip install -r apps/api/requirements.txt`
   - `deploy/scripts/install_engine_deps.sh`
   - 同步 Web 静态文件到 `/var/www/pg17-web/`（PR #29）
   - `systemctl restart pg17`
   - health check

### 首次验证
在 GitHub Actions 页手动触发 `workflow_dispatch`，确认 deploy job 通过。

---

## 历史方案：SSH Deploy（PR16，已废弃）

SSH 版 workflow 已在 PR #22 中删除，仅保留 self-hosted runner 方案。

原因：SSH 方案需要开放 22 端口并维护 `EC2_SSH_KEY` secret，安全性和可维护性不如 self-hosted runner。
