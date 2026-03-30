# EC2 Deploy Runbook (pg17)

## 已验证目标
- Host: Ubuntu EC2
- Process manager: systemd
- Reverse proxy: Caddy
- API domain: `api.hydenluc.com`
- Engine mode: `real_fill`

## 首次部署步骤
1. 安装基础环境
   - `git`
   - `python3 python3-venv python3-pip`
   - `curl`
2. clone repo
3. 创建 `.venv`
4. `pip install -r apps/api/requirements.txt`
5. `deploy/scripts/install_engine_deps.sh`
6. 配置 `.env.prod`
7. 配置 `pg17.service`
8. 配置 Caddy

## 关键系统依赖
- `tesseract-ocr`

## 关键 Python 依赖
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
