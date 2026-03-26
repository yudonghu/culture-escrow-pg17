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
