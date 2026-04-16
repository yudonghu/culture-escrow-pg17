# EC2 Deploy Runbook (pg17)

## 已验证目标
- Host: Ubuntu EC2（IP: 50.18.170.151，用户: ubuntu，key: ~/Downloads/CultureEscrow-EC2.pem）
- Process manager: systemd（服务名: `pg17`，端口: 8787）
- Reverse proxy: Caddy
- API domain: `api.hydenluc.com`
- 前端 URL: `portal.cultureescrow.com/pg17`
- Engine mode: `real_fill`

## 自动部署（日常）
push to main → GitHub Actions self-hosted runner → `deploy/scripts/deploy_prod.sh`

`deploy_prod.sh` 执行步骤：
1. `git pull`
2. `pip install -r apps/api/requirements.txt`
3. `deploy/scripts/install_engine_deps.sh`
4. 同步 Web 静态文件到 `/var/www/pg17-web/`（PR #29 新增）
5. `systemctl restart pg17`
6. health check

## 首次手工部署步骤
1. 安装基础环境
   - `git`
   - `python3 python3-venv python3-pip`
   - `curl`
   - `tesseract-ocr`
2. clone repo 到 `/opt/services/culture-escrow-pg17/`
3. 创建 `.venv`
4. `pip install -r apps/api/requirements.txt`
5. `deploy/scripts/install_engine_deps.sh`
6. 配置 `.env.prod`（参见环境变量列表）
7. 配置 `pg17.service`（systemd）
8. 配置 Caddy（API 反代 + Web 静态服务 `/var/www/pg17-web/`）
9. 创建必要目录：`/var/log/pg17/`、`/var/lib/pg17/`
10. 安装 GitHub self-hosted runner（参见 `SELF_HOSTED_RUNNER_SETUP.md`）

## 关键系统依赖
- `tesseract-ocr`

## 关键 Python 依赖（版本由 PR #24 锁定）
- `pypdf`
- `pymupdf`
- `pillow`
- `pytesseract`
- `reportlab`

## 验证步骤
### health
```bash
curl http://127.0.0.1:8787/health
```

### real fill test
```bash
curl -X POST "https://api.hydenluc.com/v1/pg17/fill" \
  -H "Authorization: Bearer $PG17_API_TOKEN" \
  -F "source_pdf=@/path/to/sample.pdf" \
  -F "deposit_amount=111.00" \
  -F "seller_agent_name=test" \
  -F "escrow_number=000000-00" \
  -F "acceptance_date=03/12/2021" \
  -F "second_date=02/12/2021"
```

预期：
- `ok: true`
- `engine_mode: real_fill`

## 手工 SSH 登录
```bash
ssh -i ~/Downloads/CultureEscrow-EC2.pem ubuntu@50.18.170.151
```
