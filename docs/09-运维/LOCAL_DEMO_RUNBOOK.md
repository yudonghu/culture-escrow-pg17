# Local Demo Runbook (pg17)

## Prerequisites
- macOS with Homebrew
- Python 3.11.x

## 0. Verify Python
```bash
python3.11 --version
```

## 1. Setup venv
```bash
cd /Users/wu/workspace/culture-escrow-pg17
rm -rf .venv
python3.11 -m venv .venv
source .venv/bin/activate
python -V
```

## 2. Install dependencies
```bash
pip install --upgrade pip
pip install -r apps/api/requirements.txt
```

## 3. Start API (Terminal A)
```bash
cd /Users/wu/workspace/culture-escrow-pg17
source .venv/bin/activate
export PYTHONPATH="$PWD/packages/pg17-fill-engine"
uvicorn apps.api.main:app --host 127.0.0.1 --port 8787
```

## 4. Start Web (Terminal B)
```bash
cd /Users/wu/workspace/culture-escrow-pg17
python3 -m http.server 8788 --directory apps/web
```

## 5. Test
- Open: http://127.0.0.1:8788
- Upload source PDF
- Fill variables
- Click `Run Fill`
- Download done.pdf from returned link

## Troubleshooting
- If browser keeps "处理中...": verify API is running and CORS enabled.
- If `pydantic-core` build fails: make sure using Python 3.11, not 3.14.

## 6. Optional auth (Phase B-1)
If you want to enable minimal auth in local/staging:

```bash
export PG17_API_TOKEN="your-local-token"
```

Then include request header in API calls:
- `x-api-token: your-local-token`

Notes:
- If `PG17_API_TOKEN` is empty, auth is disabled (demo mode).
- `GET /health` remains public to support health checks.

## 7. Retention cleanup (Phase B-3)
Set retention window:

```bash
export PG17_RETENTION_DAYS=7
```

Trigger cleanup manually:

```bash
curl -X POST http://127.0.0.1:8787/v1/admin/cleanup \
  -H "x-api-token: $PG17_API_TOKEN"
```
