"""
PG17 business logic — independent of HTTP/FastAPI.

Responsibilities:
- Input validation
- Idempotency check / store management
- Engine invocation (fill_page17)
- Audit logging
- Output file retention cleanup
- Health checks
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from pg17_engine import _engine_script, fill_page17

logger = logging.getLogger("pg17.service")


# ── Data models ───────────────────────────────────────────────────────────────

@dataclass
class FillFields:
    deposit_amount: str = ""
    seller_agent_name: str = ""
    escrow_number: str = ""
    acceptance_date: str = ""
    second_date: str = ""              # auto-filled with today PST if blank
    escrow_instruction_date: str = ""  # manual — date on escrow instruction
    by_name: str = ""     # escrow officer 姓名（覆盖 PG17_BY_NAME）
    address: str = ""     # branch 地址（覆盖 PG17_ADDRESS）
    phone: str = ""       # branch 电话（覆盖 PG17_PHONE）

    def as_dict(self) -> dict:
        return {
            "deposit_amount": self.deposit_amount,
            "seller_agent_name": self.seller_agent_name,
            "escrow_number": self.escrow_number,
            "acceptance_date": self.acceptance_date,
            "second_date": self.second_date,
            "escrow_instruction_date": self.escrow_instruction_date,
            "by_name": self.by_name,
            "address": self.address,
            "phone": self.phone,
        }


@dataclass
class FillResult:
    job_id: str
    output_file: str
    timings_ms: dict
    summary: dict
    idempotency_hit: bool = False
    idem_key: Optional[str] = None


# ── Exceptions ────────────────────────────────────────────────────────────────

class PG17ServiceError(Exception):
    """Raised when the fill engine fails."""


class IdempotencyConflictError(Exception):
    """Raised when an idempotency key is reused with a different payload."""


# ── Service ───────────────────────────────────────────────────────────────────

class PG17Service:
    def __init__(
        self,
        output_dir: Path,
        audit_log_path: Path,
        retention_days: int,
        idempotency_ttl_seconds: int,
        idempotency_store_path: Path,
        s3_bucket: Optional[str] = None,
        s3_region: Optional[str] = None,
    ):
        self.output_dir = output_dir
        self.audit_log_path = audit_log_path
        self.retention_days = retention_days
        self.idempotency_ttl_seconds = idempotency_ttl_seconds
        self.idempotency_store_path = idempotency_store_path
        self.s3_bucket = s3_bucket or ""
        self.s3_region = s3_region or "us-east-1"

    # ── private helpers ───────────────────────────────────────────────────────

    def _s3_key(self, escrow_number: str, job_id: str, ts: float) -> str:
        """Build S3 object key: {escrow_number}_{timestamp}_{job_id_short}.pdf"""
        safe_escrow = re.sub(r"[^A-Za-z0-9\-]", "_", escrow_number) if escrow_number else "unknown"
        ts_str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y%m%d-%H%M%S")
        return f"{safe_escrow}_{ts_str}_{job_id[:8]}.pdf"

    def _upload_to_s3(self, file_path: Path, s3_key: str) -> None:
        """Upload a file to S3. Non-fatal — logs error but does not raise."""
        if not self.s3_bucket:
            return
        try:
            import boto3
            s3 = boto3.client("s3", region_name=self.s3_region)
            s3.upload_file(str(file_path), self.s3_bucket, s3_key)
            logger.info("s3_upload_ok bucket=%s key=%s", self.s3_bucket, s3_key)
        except Exception as e:
            logger.error("s3_upload_failed bucket=%s key=%s error=%s", self.s3_bucket, s3_key, e)

    def _audit_log(self, event: dict) -> None:
        self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.audit_log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

    def _load_idempotency_store(self) -> dict:
        if not self.idempotency_store_path.exists():
            return {}
        try:
            return json.loads(self.idempotency_store_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.warning("idempotency store corrupted, resetting: %s", self.idempotency_store_path)
            return {}
        except OSError as e:
            logger.error("failed to read idempotency store: %s", e)
            return {}

    def _save_idempotency_store(self, data: dict) -> None:
        self.idempotency_store_path.parent.mkdir(parents=True, exist_ok=True)
        self.idempotency_store_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    def _cleanup_idempotency_store(self, data: dict) -> dict:
        now = time.time()
        return {k: v for k, v in data.items() if now - (v or {}).get("ts", 0) <= self.idempotency_ttl_seconds}

    @staticmethod
    def _build_payload_hash(source_bytes: bytes, fields: FillFields) -> str:
        h = hashlib.sha256()
        h.update(source_bytes)
        h.update(json.dumps(fields.as_dict(), sort_keys=True, ensure_ascii=False).encode("utf-8"))
        return h.hexdigest()

    @staticmethod
    def _mask_value(v: str) -> str:
        v = (v or "").strip()
        if not v:
            return ""
        if len(v) <= 4:
            return "*" * len(v)
        return v[:2] + "***" + v[-2:]

    @staticmethod
    def _valid_date(v: str) -> bool:
        if not v:
            return True
        return bool(re.fullmatch(r"\d{2}/\d{2}/\d{4}", v))

    @staticmethod
    def _utc_now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    # ── public API ────────────────────────────────────────────────────────────

    def validate_fields(self, fields: FillFields) -> list[str]:
        """Return validation error messages. Empty list means all valid."""
        errors = []
        # second_date is auto-filled PST; only validate acceptance_date and escrow_instruction_date if provided
        for name in ("acceptance_date",):
            val = getattr(fields, name)
            if not self._valid_date(val):
                errors.append(f"{name} must be MM/DD/YYYY (got: {val!r})")
        for name in ("escrow_instruction_date",):
            val = getattr(fields, name)
            if val and not self._valid_date(val):
                errors.append(f"{name} must be MM/DD/YYYY (got: {val!r})")
        return errors

    def run_fill(
        self,
        *,
        source_bytes: bytes,
        fields: FillFields,
        idem_key: str,
        actor: str,
        request_id: str,
        upload_ms: float,
    ) -> FillResult:
        """Run the full fill pipeline: idempotency check → engine → audit log → save."""
        job_id = str(uuid.uuid4())
        src_path = self.output_dir / f"{job_id}-source.pdf"
        out_path = self.output_dir / f"{job_id}-done.pdf"
        src_path.write_bytes(source_bytes)

        payload_hash = self._build_payload_hash(source_bytes, fields)

        # Idempotency check
        idem_store: dict = {}
        if idem_key:
            idem_store = self._cleanup_idempotency_store(self._load_idempotency_store())
            hit = idem_store.get(idem_key)
            if hit and hit.get("payload_hash") == payload_hash and hit.get("status") == "success":
                self._audit_log({"event": "idempotency_hit", "request_id": request_id, "job_id": hit.get("job_id"), "ts": time.time(), "key": idem_key[:64]})
                return FillResult(
                    job_id=hit["job_id"],
                    output_file=hit["output_file"],
                    timings_ms=hit.get("timings_ms", {}),
                    summary=hit.get("summary", {}),
                    idempotency_hit=True,
                    idem_key=idem_key,
                )
            if hit and hit.get("payload_hash") != payload_hash:
                raise IdempotencyConflictError(idem_key)

        # Run engine
        t1 = time.perf_counter()
        try:
            summary = fill_page17(
                source_pdf=str(src_path),
                output_pdf=str(out_path),
                deposit_amount=fields.deposit_amount,
                seller_agent_name=fields.seller_agent_name,
                escrow_number=fields.escrow_number,
                acceptance_date=fields.acceptance_date,
                second_date=fields.second_date,
                escrow_instruction_date=fields.escrow_instruction_date,
                by_name=fields.by_name,
                address=fields.address,
                phone=fields.phone,
            )
        except Exception as e:
            engine_ms = (time.perf_counter() - t1) * 1000
            logger.error("fill_failed request_id=%s job_id=%s upload_ms=%.2f engine_ms=%.2f error=%s", request_id, job_id, upload_ms, engine_ms, e)
            self._audit_log({
                "event": "fill_failed",
                "request_id": request_id,
                "job_id": job_id,
                "ts": time.time(),
                "actor": actor[:64],
                "inputs": {
                    "escrow_number": self._mask_value(fields.escrow_number),
                    "acceptance_date": "[redacted]",
                    "escrow_instruction_date": "[redacted]",
                },
                "error_code": "PG17_500_ENGINE_FAILED",
                "error": "engine processing failed",
            })
            raise PG17ServiceError(str(e)) from e

        engine_ms = (time.perf_counter() - t1) * 1000
        logger.info("fill_ok request_id=%s job_id=%s upload_ms=%.2f engine_ms=%.2f", request_id, job_id, upload_ms, engine_ms)

        timings = {"upload": round(upload_ms, 2), "engine": round(engine_ms, 2)}
        output_file = f"/v1/pg17/output/{job_id}"

        self._audit_log({
            "event": "fill_success",
            "request_id": request_id,
            "job_id": job_id,
            "ts": time.time(),
            "actor": actor[:64],
            "inputs": {
                "escrow_number": self._mask_value(fields.escrow_number),
                "acceptance_date": "[redacted]",
                "escrow_instruction_date": "[redacted]",
            },
            "timings_ms": timings,
            "result": {
                "missing_inputs": summary.get("missing_inputs", []),
                "filled_count": len(summary.get("filled_fields", [])),
                "left_blank_count": len(summary.get("left_blank", [])),
            },
        })

        # Upload to S3 for permanent storage (non-fatal)
        now_ts = time.time()
        s3_key = self._s3_key(fields.escrow_number, job_id, now_ts)
        self._upload_to_s3(out_path, s3_key)

        if idem_key:
            idem_store[idem_key] = {
                "ts": now_ts,
                "status": "success",
                "payload_hash": payload_hash,
                "job_id": job_id,
                "output_file": output_file,
                "timings_ms": timings,
                "summary": summary,
            }
            self._save_idempotency_store(idem_store)

        return FillResult(
            job_id=job_id,
            output_file=output_file,
            timings_ms=timings,
            summary=summary,
            idempotency_hit=False,
            idem_key=idem_key or None,
        )

    def cleanup_old_outputs(self) -> dict:
        """Delete output PDFs older than retention_days."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.retention_days)
        deleted = 0
        scanned = 0
        for f in self.output_dir.glob("*-*.pdf"):
            try:
                scanned += 1
                mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
                if mtime < cutoff:
                    f.unlink(missing_ok=True)
                    deleted += 1
            except OSError as e:
                logger.warning("cleanup: failed to remove %s: %s", f, e)
        event = {
            "event": "retention_cleanup",
            "ts": time.time(),
            "ts_iso": self._utc_now_iso(),
            "retention_days": self.retention_days,
            "scanned": scanned,
            "deleted": deleted,
        }
        self._audit_log(event)
        return event

    def health_checks(self) -> dict:
        """Return real dependency checks (not a hardcoded True)."""
        engine_script = _engine_script()
        return {
            "output_dir_writable": self.output_dir.exists() and os.access(self.output_dir, os.W_OK),
            "engine_script_exists": engine_script.exists(),
            "disk_free_gb": round(shutil.disk_usage(self.output_dir).free / (1024 ** 3), 2),
        }
