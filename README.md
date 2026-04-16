# culture-escrow-pg17

API service that auto-fills the CAR **Page 17 – Escrow Holder Acknowledgment** PDF.

## Project layout

```
apps/
  api/         FastAPI service (main.py + pg17_service.py)
  web/         Single-page web UI (index.html)
packages/
  pg17-fill-engine/   PDF fill engine (real OCR overlay + stub copy)
deploy/
  scripts/     deploy_prod.sh, run_api.sh, install_engine_deps.sh
  environments/  .env.staging.example, .env.prod.example
docs/          Architecture, API, security, ops, roadmap docs
tests/         42 pytest integration tests
```

## Local quick start

```bash
# 1. Clone and enter repo
git clone <repo-url> && cd culture-escrow-pg17

# 2. Create virtualenv and install deps
python3 -m venv .venv && source .venv/bin/activate
pip install -r apps/api/requirements.txt

# 3. Copy example env
cp .env.example .env
# Fill in PG17_API_TOKEN (any string works locally)

# 4. Run the API
./deploy/scripts/run_api.sh
```

Web UI: open `apps/web/index.html` in a browser (or serve with any static server).

Detailed runbook: `docs/09-运维/LOCAL_DEMO_RUNBOOK.md`

## Engine dependencies (real PDF fill)

Required only when using `fill_page17_real.py` (staging / prod):

```bash
./deploy/scripts/install_engine_deps.sh
```

Installs Python packages (`pypdf`, `reportlab`, `pytesseract`, …) and `tesseract-ocr`.

## Environment variables

| Variable | Purpose |
|---|---|
| `PG17_API_TOKEN` | Bearer token for all API requests |
| `PG17_ENGINE_SCRIPT` | Path to fill engine script |
| `PG17_ENGINE_PYTHON` | Python binary to run engine |
| `PG17_ESCROW_COMPANY` / `PG17_BY_NAME` / etc. | Escrow company fixed fields |
| `PG17_CORS_ORIGINS` | Comma-separated allowed origins |
| `PG17_RATE_LIMIT_PER_MINUTE` | Per-IP rate limit (0 = off) |

See `.env.example` for local defaults and `deploy/environments/` for staging/prod examples.

## Testing

```bash
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest
```

42 tests covering service logic, API endpoints, rate limiting, idempotency, and audit logging.

## Deployment

Production runs on EC2 behind Caddy (`portal.cultureescrow.com/pg17`).

Auto-deploy on merge to `main`:
- Workflow: `.github/workflows/deploy-self-hosted.yml` (self-hosted runner on EC2)
- Script: `deploy/scripts/deploy_prod.sh`

Manual deploy: `ssh` to EC2 and run `deploy/scripts/deploy_prod.sh` directly.

Full ops guide: `docs/09-运维/EC2_DEPLOY_RUNBOOK.md`

## Docs index

| Folder | Contents |
|---|---|
| `docs/01-产品` | Product spec, field mapping |
| `docs/02-架构` | Architecture overview |
| `docs/03-接口` | API reference |
| `docs/04-数据` | Data models, audit log format |
| `docs/05-安全` | Security controls |
| `docs/06-部署` | Deployment & environment guides |
| `docs/07-路线图` | Roadmap |
| `docs/08-测试` | Test plan |
| `docs/09-运维` | Local runbook, EC2 ops |
