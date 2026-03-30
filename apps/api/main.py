from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
import hashlib
import logging
import os
import re
import tempfile
import time
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from pg17_engine import fill_page17

app = FastAPI(title="culture-escrow-pg17 API", version="0.2.2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8080",
        "http://localhost:8080",
        "http://127.0.0.1:8081",
        "http://localhost:8081",
        "https://app.hydenluc.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUT_DIR = Path(tempfile.gettempdir()) / "culture-escrow-pg17"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

API_TOKEN = os.getenv("PG17_API_TOKEN", "")
AUDIT_LOG_PATH = Path(os.getenv("PG17_AUDIT_LOG_PATH", str(OUTPUT_DIR / "audit.log.jsonl")))
RETENTION_DAYS = int(os.getenv("PG17_RETENTION_DAYS", "7"))
IDEMPOTENCY_TTL_SECONDS = int(os.getenv("PG17_IDEMPOTENCY_TTL_SECONDS", "3600"))
IDEMPOTENCY_STORE_PATH = Path(os.getenv("PG17_IDEMPOTENCY_STORE", str(OUTPUT_DIR / "idempotency_store.json")))

logger = logging.getLogger("pg17.api")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def _load_idempotency_store() -> dict:
    if not IDEMPOTENCY_STORE_PATH.exists():
        return {}
    try:
        return json.loads(IDEMPOTENCY_STORE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_idempotency_store(data: dict) -> None:
    IDEMPOTENCY_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    IDEMPOTENCY_STORE_PATH.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _cleanup_idempotency_store(data: dict) -> dict:
    now = time.time()
    cleaned = {}
    for k, v in data.items():
        ts = (v or {}).get("ts", 0)
        if now - ts <= IDEMPOTENCY_TTL_SECONDS:
            cleaned[k] = v
    return cleaned


def _build_payload_hash(source_bytes: bytes, fields: dict) -> str:
    h = hashlib.sha256()
    h.update(source_bytes)
    h.update(json.dumps(fields, sort_keys=True, ensure_ascii=False).encode("utf-8"))
    return h.hexdigest()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _cleanup_old_outputs(retention_days: int) -> dict:
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    deleted = 0
    scanned = 0

    for f in OUTPUT_DIR.glob("*-*.pdf"):
        try:
            scanned += 1
            mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
            if mtime < cutoff:
                f.unlink(missing_ok=True)
                deleted += 1
        except Exception:
            continue

    event = {
        "event": "retention_cleanup",
        "ts": time.time(),
        "ts_iso": _utc_now_iso(),
        "retention_days": retention_days,
        "scanned": scanned,
        "deleted": deleted,
    }
    _audit_log(event)
    return event


def _mask_value(v: str) -> str:
    v = (v or "").strip()
    if not v:
        return ""
    if len(v) <= 4:
        return "*" * len(v)
    return v[:2] + "***" + v[-2:]


def _audit_log(event: dict) -> None:
    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def _valid_date(v: str) -> bool:
    if not v:
        return True
    return bool(re.fullmatch(r"\d{2}/\d{2}/\d{4}", v))


def _new_request_id() -> str:
    return f"req_{uuid.uuid4().hex[:12]}"


def _check_auth(request_id: str, x_api_token: Optional[str]) -> None:
    if not API_TOKEN:
        return
    if not x_api_token or x_api_token != API_TOKEN:
        _audit_log({
            "event": "auth_failed",
            "request_id": request_id,
            "ts": time.time(),
            "reason": "invalid_or_missing_token",
        })
        raise HTTPException(
            status_code=401,
            detail={
                "error_code": "PG17_401_UNAUTHORIZED",
                "message": "unauthorized",
                "hint": "provide valid x-api-token header",
                "extra": {"request_id": request_id},
            },
        )


def _error_response(*, status_code: int, request_id: str, error_code: str, message: str, hint: str = "", extra: Optional[dict] = None):
    payload = {
        "ok": False,
        "request_id": request_id,
        "error_code": error_code,
        "message": message,
        "hint": hint,
    }
    if extra:
        payload.update(extra)
    return JSONResponse(status_code=status_code, content=payload)


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


@app.get("/health")
def health(request: Request):
    return {
        "ok": True,
        "request_id": request.state.request_id,
        "service": "culture-escrow-pg17-api",
        "auth_enabled": bool(API_TOKEN),
        "audit_log_path": str(AUDIT_LOG_PATH),
        "retention_days": RETENTION_DAYS,
        "idempotency_ttl_seconds": IDEMPOTENCY_TTL_SECONDS,
    }


@app.post("/v1/admin/cleanup")
def admin_cleanup(request: Request, x_api_token: Optional[str] = Header(default=None)):
    request_id = request.state.request_id
    _check_auth(request_id, x_api_token)
    event = _cleanup_old_outputs(RETENTION_DAYS)
    return {"ok": True, "request_id": request_id, "cleanup": event}


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

    if not source_pdf.filename or not source_pdf.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail={"error_code": "PG17_400_INVALID_PDF", "message": "source_pdf must be a PDF", "hint": "upload a .pdf file"})

    for k, v in {"acceptance_date": (acceptance_date or "").strip(), "second_date": (second_date or "").strip()}.items():
        if not _valid_date(v):
            raise HTTPException(status_code=400, detail={"error_code": "PG17_400_INVALID_DATE", "message": f"{k} must be MM/DD/YYYY", "hint": "example: 03/20/2026"})

    job_id = str(uuid.uuid4())
    src_path = OUTPUT_DIR / f"{job_id}-source.pdf"
    out_path = OUTPUT_DIR / f"{job_id}-done.pdf"

    t0 = time.perf_counter()
    content = await source_pdf.read()
    src_path.write_bytes(content)
    upload_ms = (time.perf_counter() - t0) * 1000

    payload_fields = {
        "deposit_amount": (deposit_amount or "").strip(),
        "seller_agent_name": (seller_agent_name or "").strip(),
        "escrow_number": (escrow_number or "").strip(),
        "acceptance_date": (acceptance_date or "").strip(),
        "second_date": (second_date or "").strip(),
    }
    payload_hash = _build_payload_hash(content, payload_fields)

    idem_key = (x_idempotency_key or "").strip()
    if idem_key:
        store = _cleanup_idempotency_store(_load_idempotency_store())
        hit = store.get(idem_key)
        if hit and hit.get("payload_hash") == payload_hash and hit.get("status") == "success":
            _audit_log({"event": "idempotency_hit", "request_id": request_id, "job_id": hit.get("job_id"), "ts": time.time(), "key": idem_key[:64]})
            return JSONResponse({"ok": True, "request_id": request_id, "job_id": hit.get("job_id"), "output_file": hit.get("output_file"), "timings_ms": hit.get("timings_ms", {}), "summary": hit.get("summary", {}), "idempotency": {"hit": True, "key": idem_key}})
        elif hit and hit.get("payload_hash") != payload_hash:
            raise HTTPException(status_code=409, detail={"error_code": "PG17_409_IDEMPOTENCY_PAYLOAD_MISMATCH", "message": "idempotency key reused with different payload", "hint": "use a new x-idempotency-key for different input"})

    t1 = time.perf_counter()
    try:
        summary = fill_page17(
            source_pdf=str(src_path),
            output_pdf=str(out_path),
            deposit_amount=(deposit_amount or "").strip(),
            seller_agent_name=(seller_agent_name or "").strip(),
            escrow_number=(escrow_number or "").strip(),
            acceptance_date=(acceptance_date or "").strip(),
            second_date=(second_date or "").strip(),
        )
    except Exception as e:
        engine_ms = (time.perf_counter() - t1) * 1000
        logger.error("pg17_fill_failed request_id=%s job_id=%s upload_ms=%.2f engine_ms=%.2f error=%s", request_id, job_id, upload_ms, engine_ms, str(e))
        _audit_log({"event": "fill_failed", "request_id": request_id, "job_id": job_id, "ts": time.time(), "actor": (x_actor or "unknown")[:64], "inputs": {"escrow_number": _mask_value(escrow_number or ""), "acceptance_date": acceptance_date or "", "second_date": second_date or ""}, "error_code": "PG17_500_ENGINE_FAILED", "error": str(e)[:500]})
        raise HTTPException(status_code=500, detail={"error_code": "PG17_500_ENGINE_FAILED", "message": "fill failed", "hint": "Check PDF layout and required anchors on page 17.", "extra": {"error": str(e)}})

    engine_ms = (time.perf_counter() - t1) * 1000
    t2 = time.perf_counter()
    export_ms = (time.perf_counter() - t2) * 1000

    logger.info("pg17_fill_ok request_id=%s job_id=%s upload_ms=%.2f engine_ms=%.2f export_ms=%.2f", request_id, job_id, upload_ms, engine_ms, export_ms)

    timings = {"upload": round(upload_ms, 2), "engine": round(engine_ms, 2), "export": round(export_ms, 2)}

    _audit_log({"event": "fill_success", "request_id": request_id, "job_id": job_id, "ts": time.time(), "actor": (x_actor or "unknown")[:64], "inputs": {"escrow_number": _mask_value(escrow_number or ""), "acceptance_date": acceptance_date or "", "second_date": second_date or ""}, "timings_ms": timings, "result": {"missing_inputs": summary.get("missing_inputs", []), "filled_count": len(summary.get("filled_fields", [])), "left_blank_count": len(summary.get("left_blank", []))}})

    if idem_key:
        store = _cleanup_idempotency_store(_load_idempotency_store())
        store[idem_key] = {"ts": time.time(), "status": "success", "payload_hash": payload_hash, "job_id": job_id, "output_file": f"/v1/pg17/output/{job_id}", "timings_ms": timings, "summary": summary}
        _save_idempotency_store(store)

    return JSONResponse({"ok": True, "request_id": request_id, "job_id": job_id, "output_file": f"/v1/pg17/output/{job_id}", "timings_ms": timings, "summary": summary, "idempotency": {"hit": False, "key": idem_key or None}})


@app.get("/v1/pg17/output/{job_id}")
def download_output(job_id: str, request: Request, x_api_token: Optional[str] = Header(default=None)):
    request_id = request.state.request_id
    _check_auth(request_id, x_api_token)
    out_path = OUTPUT_DIR / f"{job_id}-done.pdf"
    if not out_path.exists():
        raise HTTPException(status_code=404, detail={"error_code": "PG17_404_OUTPUT_NOT_FOUND", "message": "output not found", "hint": "check job_id and run fill first"})
    response = FileResponse(out_path, media_type="application/pdf", filename=f"{job_id}-done.pdf")
    response.headers["x-request-id"] = request.state.request_id
    return response
