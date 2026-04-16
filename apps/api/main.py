"""
HTTP layer — FastAPI app, routing, auth, rate limiting.

Business logic lives in pg17_service.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure apps/api/ is in sys.path so pg17_service is importable
# regardless of how uvicorn is invoked (e.g. `uvicorn apps.api.main:app`
# from repo root, where apps/api/ is not on sys.path by default).
sys.path.insert(0, str(Path(__file__).parent))

import collections
import logging
import os
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from pg17_service import FillFields, IdempotencyConflictError, PG17Service, PG17ServiceError

app = FastAPI(title="culture-escrow-pg17 API", version="0.2.2")

# ── CORS ──────────────────────────────────────────────────────────────────────

_cors_origins = [
    o.strip()
    for o in os.getenv(
        "PG17_CORS_ORIGINS",
        "http://127.0.0.1:8080,http://localhost:8080,http://127.0.0.1:8081,http://localhost:8081",
    ).split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["content-type", "x-api-token", "x-idempotency-key", "x-actor"],
)

# ── Config ────────────────────────────────────────────────────────────────────

OUTPUT_DIR = Path(tempfile.gettempdir()) / "culture-escrow-pg17"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

API_TOKEN = os.getenv("PG17_API_TOKEN", "")
RETENTION_DAYS = int(os.getenv("PG17_RETENTION_DAYS", "7"))
IDEMPOTENCY_TTL_SECONDS = int(os.getenv("PG17_IDEMPOTENCY_TTL_SECONDS", "3600"))
RATE_LIMIT_PER_MINUTE = int(os.getenv("PG17_RATE_LIMIT_PER_MINUTE", "20"))

logger = logging.getLogger("pg17.api")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ── Service (singleton) ───────────────────────────────────────────────────────

service = PG17Service(
    output_dir=OUTPUT_DIR,
    audit_log_path=Path(os.getenv("PG17_AUDIT_LOG_PATH", str(OUTPUT_DIR / "audit.log.jsonl"))),
    retention_days=RETENTION_DAYS,
    idempotency_ttl_seconds=IDEMPOTENCY_TTL_SECONDS,
    idempotency_store_path=Path(os.getenv("PG17_IDEMPOTENCY_STORE", str(OUTPUT_DIR / "idempotency_store.json"))),
)

# ── Rate limiter ──────────────────────────────────────────────────────────────

_rate_limit_lock = threading.Lock()
_rate_limit_counters: dict[str, collections.deque] = {}


def _check_rate_limit(client_ip: str) -> bool:
    if not RATE_LIMIT_PER_MINUTE:
        return True
    now = time.time()
    with _rate_limit_lock:
        dq = _rate_limit_counters.setdefault(client_ip, collections.deque())
        while dq and dq[0] < now - 60.0:
            dq.popleft()
        if len(dq) >= RATE_LIMIT_PER_MINUTE:
            return False
        dq.append(now)
        return True

# ── HTTP helpers ──────────────────────────────────────────────────────────────

def _new_request_id() -> str:
    return f"req_{uuid.uuid4().hex[:12]}"


def _check_auth(request_id: str, x_api_token: Optional[str]) -> None:
    if not API_TOKEN:
        return
    if not x_api_token or x_api_token != API_TOKEN:
        service._audit_log({"event": "auth_failed", "request_id": request_id, "ts": time.time(), "reason": "invalid_or_missing_token"})
        raise HTTPException(
            status_code=401,
            detail={"error_code": "PG17_401_UNAUTHORIZED", "message": "unauthorized", "hint": "provide valid x-api-token header", "extra": {"request_id": request_id}},
        )


def _error_response(*, status_code: int, request_id: str, error_code: str, message: str, hint: str = "", extra: Optional[dict] = None):
    payload = {"ok": False, "request_id": request_id, "error_code": error_code, "message": message, "hint": hint}
    if extra:
        payload.update(extra)
    return JSONResponse(status_code=status_code, content=payload)

# ── Middleware ────────────────────────────────────────────────────────────────

@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or _new_request_id()
    request.state.request_id = request_id
    started_at = time.perf_counter()
    response = await call_next(request)
    response.headers["x-request-id"] = request_id
    response.headers["x-elapsed-ms"] = f"{(time.perf_counter() - started_at) * 1000:.2f}"
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = getattr(request.state, "request_id", _new_request_id())
    detail = exc.detail
    if isinstance(detail, dict) and detail.get("error_code"):
        return _error_response(
            status_code=exc.status_code,
            request_id=request_id,
            error_code=detail.get("error_code", "PG17_HTTP_ERROR"),
            message=detail.get("message", "request failed"),
            hint=detail.get("hint", ""),
            extra=detail.get("extra"),
        )
    code_map = {400: "PG17_400_BAD_REQUEST", 404: "PG17_404_NOT_FOUND", 413: "PG17_413_FILE_TOO_LARGE", 422: "PG17_422_UNPROCESSABLE", 500: "PG17_500_INTERNAL_ERROR"}
    return _error_response(status_code=exc.status_code, request_id=request_id, error_code=code_map.get(exc.status_code, "PG17_HTTP_ERROR"), message=str(detail), hint="")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", _new_request_id())
    return _error_response(status_code=500, request_id=request_id, error_code="PG17_500_UNHANDLED", message="unexpected server error", hint="check server logs with request_id", extra={"error": str(exc)})

# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health(request: Request):
    checks = service.health_checks()
    ok = checks["output_dir_writable"] and checks["engine_script_exists"]
    return {
        "ok": ok,
        "request_id": request.state.request_id,
        "service": "culture-escrow-pg17-api",
        "auth_enabled": bool(API_TOKEN),
        "audit_log_path": str(service.audit_log_path),
        "retention_days": RETENTION_DAYS,
        "idempotency_ttl_seconds": IDEMPOTENCY_TTL_SECONDS,
        "checks": checks,
    }


@app.post("/v1/admin/cleanup")
def admin_cleanup(request: Request, x_api_token: Optional[str] = Header(default=None)):
    _check_auth(request.state.request_id, x_api_token)
    event = service.cleanup_old_outputs()
    return {"ok": True, "request_id": request.state.request_id, "cleanup": event}


@app.post("/v1/pg17/fill")
async def pg17_fill(
    request: Request,
    source_pdf: UploadFile = File(...),
    deposit_amount: Optional[str] = Form(default=""),
    seller_agent_name: Optional[str] = Form(default=""),
    escrow_number: Optional[str] = Form(default=""),
    acceptance_date: Optional[str] = Form(default=""),
    second_date: Optional[str] = Form(default=""),
    x_api_token: Optional[str] = Header(default=None),
    x_actor: Optional[str] = Header(default="unknown"),
    x_idempotency_key: Optional[str] = Header(default=None),
):
    request_id = request.state.request_id
    _check_auth(request_id, x_api_token)

    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail={"error_code": "PG17_429_RATE_LIMITED", "message": "too many requests", "hint": f"max {RATE_LIMIT_PER_MINUTE} requests per minute per IP"})

    if not source_pdf.filename or not source_pdf.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail={"error_code": "PG17_400_INVALID_PDF", "message": "source_pdf must be a PDF", "hint": "upload a .pdf file"})

    fields = FillFields(
        deposit_amount=(deposit_amount or "").strip(),
        seller_agent_name=(seller_agent_name or "").strip(),
        escrow_number=(escrow_number or "").strip(),
        acceptance_date=(acceptance_date or "").strip(),
        second_date=(second_date or "").strip(),
    )
    errors = service.validate_fields(fields)
    if errors:
        raise HTTPException(status_code=400, detail={"error_code": "PG17_400_INVALID_DATE", "message": errors[0], "hint": "example: 03/20/2026"})

    t0 = time.perf_counter()
    content = await source_pdf.read()
    upload_ms = (time.perf_counter() - t0) * 1000

    try:
        result = service.run_fill(
            source_bytes=content,
            fields=fields,
            idem_key=(x_idempotency_key or "").strip(),
            actor=(x_actor or "unknown"),
            request_id=request_id,
            upload_ms=upload_ms,
        )
    except IdempotencyConflictError:
        raise HTTPException(status_code=409, detail={"error_code": "PG17_409_IDEMPOTENCY_PAYLOAD_MISMATCH", "message": "idempotency key reused with different payload", "hint": "use a new x-idempotency-key for different input"})
    except PG17ServiceError as e:
        raise HTTPException(status_code=500, detail={"error_code": "PG17_500_ENGINE_FAILED", "message": "fill failed", "hint": "Check PDF layout and required anchors on page 17.", "extra": {"error": str(e)}})

    return JSONResponse({
        "ok": True,
        "request_id": request_id,
        "job_id": result.job_id,
        "output_file": result.output_file,
        "timings_ms": result.timings_ms,
        "summary": result.summary,
        "idempotency": {"hit": result.idempotency_hit, "key": result.idem_key},
    })


@app.get("/v1/pg17/output/{job_id}")
def download_output(job_id: str, request: Request, x_api_token: Optional[str] = Header(default=None)):
    _check_auth(request.state.request_id, x_api_token)
    out_path = OUTPUT_DIR / f"{job_id}-done.pdf"
    if not out_path.exists():
        raise HTTPException(status_code=404, detail={"error_code": "PG17_404_OUTPUT_NOT_FOUND", "message": "output not found", "hint": "check job_id and run fill first"})
    response = FileResponse(out_path, media_type="application/pdf", filename=f"{job_id}-done.pdf")
    response.headers["x-request-id"] = request.state.request_id
    return response
