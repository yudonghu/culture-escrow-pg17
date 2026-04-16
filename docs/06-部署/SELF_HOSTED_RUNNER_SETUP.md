# Self-Hosted Runner Setup

## 目标
在 EC2 上安装 GitHub self-hosted runner，实现 push to main 自动部署（当前正式方案）。

## EC2 信息
- IP: 50.18.170.151
- 用户: ubuntu
- 部署路径: `/opt/services/culture-escrow-pg17/`

## Runner 标签
- `self-hosted`
- `linux`
- `x64`
- `pg17-prod`

## 安装步骤（在 EC2 上）
1. 进入 GitHub repo
   - Settings → Actions → Runners → New self-hosted runner
2. 选择 Linux x64
3. GitHub 会给出一组命令，直接在 EC2 上执行
4. 配置标签时加上：`pg17-prod`
5. 安装为 service 并启动：
   ```bash
   sudo ./svc.sh install
   sudo ./svc.sh start
   ```
6. 验证 runner 状态：
   ```bash
   sudo ./svc.sh status
   ```

## 工作流
使用：`.github/workflows/deploy-self-hosted.yml`

## 优势
- 不依赖 GitHub runner 公网 SSH 到 EC2
- 不需要 `EC2_SSH_KEY`
- 不需要开放 22 给 GitHub Actions 公网 IP
- 部署逻辑直接在目标主机执行

## 当前状态
SSH 版 workflow 已在 PR #22 中删除，self-hosted runner 为唯一自动部署方式。
