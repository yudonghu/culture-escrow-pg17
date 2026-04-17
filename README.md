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
git clone <repo-url> && cd culture-escrow-pg17
cp .env.example .env        # fill in PG17_API_TOKEN (any string works locally)
make install                # create .venv and install all deps
make run                    # start API at http://127.0.0.1:8787
make web                    # serve web UI at http://127.0.0.1:8788 (separate terminal)
make test                   # run 42 tests
```

Detailed runbook: `docs/RUNBOOK.md`

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

Full ops guide: `docs/DEPLOY.md`

## Docs index

| File | Contents |
|---|---|
| `docs/PRD.md` | Product spec, MVP scope, acceptance criteria |
| `docs/ARCHITECTURE.md` | System layers, module boundaries, engine runtime |
| `docs/API_SPEC.md` | API reference (auth, rate limiting, endpoints) |
| `docs/DATA_MODEL.md` | Data models, audit log fields |
| `docs/SECURITY.md` | Security controls |
| `docs/ENVIRONMENTS.md` | Environment variables, staging/prod config |
| `docs/DEPLOY.md` | EC2 deploy, GitHub Actions, self-hosted runner |
| `docs/RUNBOOK.md` | Production ops + local dev guide |
| `docs/OPERATIONS.md` | Audit log, idempotency, retention policy |
| `docs/ROADMAP.md` | Completed phases + pending work |
| `docs/TEST_PLAN.md` | Test plan (42 pytest tests) |
