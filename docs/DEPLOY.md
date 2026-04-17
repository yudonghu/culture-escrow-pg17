# 部署指南

## 生产环境信息
- Host: Ubuntu EC2（IP: 50.18.170.151，用户: ubuntu，key: ~/Downloads/CultureEscrow-EC2.pem）
- 部署路径: `/opt/services/culture-escrow-pg17/`
- systemd 服务: `pg17`（端口 8787）
- 反向代理: Caddy
- API URL: `api.hydenluc.com`
- 前端 URL: `portal.cultureescrow.com/pg17`
- Web 静态文件: `/var/www/pg17-web/index.html`

---

## 自动部署（日常）

push to main → GitHub Actions self-hosted runner → `deploy/scripts/deploy_prod.sh`

### 工作流文件
`.github/workflows/deploy-self-hosted.yml`

### deploy_prod.sh 执行步骤
1. `git pull`
2. `pip install -r apps/api/requirements.txt`
3. `deploy/scripts/install_engine_deps.sh`
4. 同步 Web 静态文件到 `/var/www/pg17-web/`
5. `systemctl restart pg17`
6. health check

### 为什么用 self-hosted runner（而不是 SSH 方案）
- 不依赖 GitHub runner 公网 SSH 到 EC2
- 不需要 `EC2_SSH_KEY` secret
- 不需要开放 22 端口给 GitHub Actions 公网 IP
- 部署逻辑直接在目标主机执行

> SSH 版 workflow 已在 PR #22 中删除，self-hosted runner 为唯一自动部署方式。

---

## 首次手工部署步骤

1. **安装基础环境**
   ```bash
   sudo apt update
   sudo apt install -y git python3 python3-venv python3-pip curl tesseract-ocr
   ```

2. **Clone repo**
   ```bash
   git clone <repo-url> /opt/services/culture-escrow-pg17
   cd /opt/services/culture-escrow-pg17
   ```

3. **创建 venv 并安装依赖**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r apps/api/requirements.txt
   deploy/scripts/install_engine_deps.sh
   ```

4. **配置环境变量**
   ```bash
   cp deploy/environments/.env.prod.example .env.prod
   # 填入真实 token、PII 变量等
   ```

5. **配置 systemd**（`/etc/systemd/system/pg17.service`）
   ```ini
   [Unit]
   Description=pg17 API service
   After=network.target

   [Service]
   User=ubuntu
   WorkingDirectory=/opt/services/culture-escrow-pg17
   EnvironmentFile=/opt/services/culture-escrow-pg17/.env.prod
   ExecStart=/opt/services/culture-escrow-pg17/.venv/bin/uvicorn apps.api.main:app --host 0.0.0.0 --port 8787
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

6. **配置 Caddy**（API 反代 + Web 静态服务）
   ```
   api.hydenluc.com {
     reverse_proxy 127.0.0.1:8787
   }

   portal.cultureescrow.com {
     handle /pg17* {
       root * /var/www/pg17-web
       file_server
     }
   }
   ```

7. **创建必要目录**
   ```bash
   sudo mkdir -p /var/log/pg17 /var/lib/pg17 /var/www/pg17-web
   sudo cp apps/web/index.html /var/www/pg17-web/index.html
   ```

8. **启动服务**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable pg17
   sudo systemctl start pg17
   ```

9. **安装 self-hosted runner**（见下方）

---

## Self-Hosted Runner 安装

1. 进入 GitHub repo → Settings → Actions → Runners → New self-hosted runner
2. 选择 Linux x64，按页面指引在 EC2 上执行命令
3. 配置标签时加上：`pg17-prod`
4. 安装为 service 并启动：
   ```bash
   sudo ./svc.sh install
   sudo ./svc.sh start
   sudo ./svc.sh status
   ```

Runner 标签：`self-hosted`, `linux`, `x64`, `pg17-prod`

---

## 验证

```bash
# health check
curl http://127.0.0.1:8787/health

# real fill test
curl -X POST "https://api.hydenluc.com/v1/pg17/fill" \
  -H "Authorization: Bearer $PG17_API_TOKEN" \
  -F "source_pdf=@/path/to/sample.pdf" \
  -F "deposit_amount=111.00" \
  -F "seller_agent_name=test" \
  -F "escrow_number=000000-00" \
  -F "acceptance_date=03/12/2021" \
  -F "second_date=02/12/2021"
```

预期：`ok: true`，`engine_mode: real_fill`
