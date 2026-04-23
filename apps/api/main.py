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
import subprocess
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

# ── Service start time & version ──────────────────────────────────────────────

_START_TIME = time.time()


def _git_commit_sha() -> str:
    """Return short git commit sha, or env var GIT_COMMIT, or 'unknown'."""
    sha = os.getenv("GIT_COMMIT", "").strip()
    if sha:
        return sha[:7]
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True,
            cwd=Path(__file__).resolve().parents[2],
            timeout=2,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"


_VERSION_SHA = _git_commit_sha()

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
    s3_bucket=os.getenv("PG17_S3_BUCKET", ""),
    s3_region=os.getenv("PG17_S3_REGION", "us-west-1"),
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
    uptime_seconds = int(time.time() - _START_TIME)

    data = {
        "ok": ok,
        "request_id": request.state.request_id,
        "service": "culture-escrow-pg17-api",
        "version": _VERSION_SHA,
        "uptime_seconds": uptime_seconds,
        "auth_enabled": bool(API_TOKEN),
        "audit_log_path": str(service.audit_log_path),
        "retention_days": RETENTION_DAYS,
        "idempotency_ttl_seconds": IDEMPOTENCY_TTL_SECONDS,
        "checks": checks,
    }

    # 如果是浏览器请求（Accept 含 text/html），返回可读的状态页
    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        from fastapi.responses import HTMLResponse

        def _uptime_str(s: int) -> str:
            d, s = divmod(s, 86400)
            h, s = divmod(s, 3600)
            m, s = divmod(s, 60)
            parts = []
            if d: parts.append(f"{d} 天")
            if h: parts.append(f"{h} 小时")
            if m: parts.append(f"{m} 分钟")
            parts.append(f"{s} 秒")
            return " ".join(parts)

        status_color = "#22c55e" if ok else "#ef4444"
        status_text  = "正常运行" if ok else "存在异常"
        status_icon  = "✅" if ok else "🚨"

        def check_row(key: str, val, label: str, hint: str = "") -> str:
            if isinstance(val, bool):
                icon = "✅" if val else "❌"
                display = "正常" if val else "异常"
            else:
                icon = "💾"
                display = str(val)
            hint_html = f'<span class="hint">{hint}</span>' if hint else ""
            return f"""
            <tr class="{'ok-row' if val else 'fail-row'}">
              <td>{icon}</td>
              <td><code>{key}</code></td>
              <td class="label">{label}</td>
              <td><strong>{display}</strong> {hint_html}</td>
            </tr>"""

        checks_html = (
            check_row("output_dir_writable", checks["output_dir_writable"],
                      "输出目录可写", "生成的 PDF 临时存放目录") +
            check_row("engine_script_exists", checks["engine_script_exists"],
                      "引擎脚本存在", "fill_page17 引擎文件是否就位") +
            check_row("disk_free_gb", checks["disk_free_gb"],
                      "磁盘剩余空间 (GB)", "低于 2GB 时监控会发告警邮件")
        )

        html = f"""<!DOCTYPE html>
<html lang="zh">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>pg17 服务状态</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #0f172a; color: #e2e8f0;
      min-height: 100vh; padding: 40px 24px;
    }}
    .container {{ max-width: 760px; margin: 0 auto; }}

    /* 顶部状态横幅 */
    .banner {{
      background: #1e293b; border-radius: 16px;
      padding: 32px; margin-bottom: 24px;
      border-left: 6px solid {status_color};
    }}
    .banner-top {{ display: flex; align-items: center; gap: 16px; margin-bottom: 16px; }}
    .status-dot {{
      width: 14px; height: 14px; border-radius: 50%;
      background: {status_color};
      box-shadow: 0 0 10px {status_color};
      animation: {'pulse 2s infinite' if ok else 'none'};
    }}
    @keyframes pulse {{
      0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.4; }}
    }}
    .service-name {{ font-size: 22px; font-weight: 700; color: #f8fafc; }}
    .version {{
      margin-left: auto;
      background: #334155; padding: 4px 12px;
      border-radius: 20px; font-size: 13px; color: #94a3b8;
      font-family: monospace;
    }}
    .status-text {{ font-size: 28px; font-weight: 800; color: {status_color}; margin-bottom: 8px; }}
    .meta {{ color: #64748b; font-size: 14px; line-height: 2; }}
    .meta span {{ color: #94a3b8; margin-right: 24px; }}
    .meta strong {{ color: #cbd5e1; }}

    /* 检查项表格 */
    .section {{ background: #1e293b; border-radius: 16px; padding: 24px; margin-bottom: 24px; }}
    .section-title {{
      font-size: 13px; font-weight: 600; text-transform: uppercase;
      letter-spacing: 0.1em; color: #64748b; margin-bottom: 16px;
    }}
    table {{ width: 100%; border-collapse: collapse; }}
    td {{ padding: 12px 8px; border-bottom: 1px solid #0f172a; vertical-align: middle; }}
    tr:last-child td {{ border-bottom: none; }}
    td:first-child {{ width: 28px; font-size: 18px; }}
    td:nth-child(2) {{ width: 220px; }}
    code {{ background: #0f172a; padding: 2px 8px; border-radius: 6px; font-size: 13px; color: #7dd3fc; }}
    .label {{ color: #94a3b8; font-size: 14px; }}
    .hint {{ color: #475569; font-size: 12px; margin-left: 8px; }}
    .ok-row:hover td {{ background: #162032; }}
    .fail-row td {{ background: #2d1a1a; }}

    /* 配置信息网格 */
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
    .card {{
      background: #0f172a; border-radius: 10px; padding: 16px;
      border: 1px solid #1e293b;
    }}
    .card-label {{ font-size: 12px; color: #475569; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.05em; }}
    .card-value {{ font-size: 15px; font-weight: 600; color: #e2e8f0; word-break: break-all; }}
    .card-hint {{ font-size: 11px; color: #334155; margin-top: 4px; }}
    .badge {{
      display: inline-block; padding: 2px 10px; border-radius: 12px;
      font-size: 13px; font-weight: 600;
    }}
    .badge-green {{ background: #14532d; color: #4ade80; }}
    .badge-gray  {{ background: #1e293b; color: #64748b; }}

    /* 底部 */
    .footer {{ text-align: center; color: #334155; font-size: 12px; margin-top: 16px; }}
    .req-id {{ font-family: monospace; color: #475569; }}
  </style>
</head>
<body>
  <div class="container">

    <!-- 顶部状态横幅 -->
    <div class="banner">
      <div class="banner-top">
        <div class="status-dot"></div>
        <div class="service-name">culture-escrow-pg17</div>
        <div class="version">git {data['version']}</div>
      </div>
      <div class="status-text">{status_icon} {status_text}</div>
      <div class="meta">
        <span>⏱ 已运行 <strong>{_uptime_str(uptime_seconds)}</strong></span>
        <span>🔐 认证 <strong>{'已启用' if data['auth_enabled'] else '未启用'}</strong></span>
        <span>🌐 端口 <strong>{os.getenv('PG17_PORT', '8787')}</strong></span>
      </div>
    </div>

    <!-- 依赖检查 -->
    <div class="section">
      <div class="section-title">依赖检查</div>
      <table>{checks_html}</table>
    </div>

    <!-- 配置信息 -->
    <div class="section">
      <div class="section-title">服务配置</div>
      <div class="grid">
        <div class="card">
          <div class="card-label">文件留存周期</div>
          <div class="card-value">{data['retention_days']} 天</div>
          <div class="card-hint">超期文件每日凌晨 3 点自动清理</div>
        </div>
        <div class="card">
          <div class="card-label">幂等 key TTL</div>
          <div class="card-value">{data['idempotency_ttl_seconds']} 秒
            （{data['idempotency_ttl_seconds'] // 3600} 小时）</div>
          <div class="card-hint">相同 key 在此窗口内返回缓存结果</div>
        </div>
        <div class="card">
          <div class="card-label">速率限制</div>
          <div class="card-value">{RATE_LIMIT_PER_MINUTE} 次 / 分钟 / IP</div>
          <div class="card-hint">超出限制返回 429 Too Many Requests</div>
        </div>
        <div class="card">
          <div class="card-label">S3 永久存储</div>
          <div class="card-value">
            <span class="badge {'badge-green' if service.s3_bucket else 'badge-gray'}">
              {'已启用' if service.s3_bucket else '未启用'}
            </span>
          </div>
          <div class="card-hint">{service.s3_bucket or '填写 PG17_S3_BUCKET 启用'}</div>
        </div>
        <div class="card" style="grid-column: span 2;">
          <div class="card-label">审计日志路径</div>
          <div class="card-value">{data['audit_log_path']}</div>
          <div class="card-hint">JSONL 格式，敏感字段已脱敏，由 logrotate 每日轮转</div>
        </div>
      </div>
    </div>

    <!-- 底部 -->
    <div class="footer">
      request_id: <span class="req-id">{data['request_id']}</span>
    </div>

  </div>
</body>
</html>"""
        return HTMLResponse(content=html)

    return data


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
    second_date: Optional[str] = Form(default=""),              # auto-filled PST if blank
    escrow_instruction_date: Optional[str] = Form(default=""),  # manual — date on escrow instruction
    by_name: Optional[str] = Form(default=""),       # escrow officer 姓名，覆盖 PG17_BY_NAME
    address: Optional[str] = Form(default=""),        # branch 地址，覆盖 PG17_ADDRESS
    phone: Optional[str] = Form(default=""),          # branch 电话，覆盖 PG17_PHONE
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
        escrow_instruction_date=(escrow_instruction_date or "").strip(),
        # 前端传值优先；未传则 fallback 到 env var（引擎子进程会读系统环境变量）
        by_name=(by_name or "").strip(),
        address=(address or "").strip(),
        phone=(phone or "").strip(),
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
