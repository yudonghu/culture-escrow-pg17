"""Unit tests for PG17Service — no HTTP, no real engine."""
from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from pg17_service import (
    FillFields,
    FillResult,
    IdempotencyConflictError,
    PG17Service,
    PG17ServiceError,
)

MOCK_SUMMARY = {
    "output_pdf": "",          # filled in by mock
    "missing_inputs": [],
    "filled_fields": ["deposit_amount", "escrow_number"],
    "left_blank": [],
    "engine_mode": "stub_copy",
}


# ── validate_fields ───────────────────────────────────────────────────────────

class TestValidateFields:
    def test_valid_dates(self, svc):
        fields = FillFields(acceptance_date="03/20/2026", escrow_instruction_date="04/01/2026")
        assert svc.validate_fields(fields) == []

    def test_empty_dates_are_ok(self, svc):
        # second_date is auto-filled; escrow_instruction_date is optional
        fields = FillFields(acceptance_date="", second_date="", escrow_instruction_date="")
        assert svc.validate_fields(fields) == []

    def test_invalid_acceptance_date(self, svc):
        fields = FillFields(acceptance_date="2026-03-20")
        errors = svc.validate_fields(fields)
        assert len(errors) == 1
        assert "acceptance_date" in errors[0]

    def test_invalid_escrow_instruction_date(self, svc):
        # escrow_instruction_date is validated only when provided
        fields = FillFields(escrow_instruction_date="bad-date")
        errors = svc.validate_fields(fields)
        assert len(errors) == 1
        assert "escrow_instruction_date" in errors[0]

    def test_second_date_not_validated(self, svc):
        # second_date is auto-filled PST — any value (including bad) is passed through without validation
        fields = FillFields(second_date="bad-date")
        assert svc.validate_fields(fields) == []

    def test_both_dates_invalid(self, svc):
        fields = FillFields(acceptance_date="nope", escrow_instruction_date="also-nope")
        assert len(svc.validate_fields(fields)) == 2


# ── _mask_value ───────────────────────────────────────────────────────────────

class TestMaskValue:
    def test_empty_string(self, svc):
        assert svc._mask_value("") == ""

    def test_short_value_fully_masked(self, svc):
        assert svc._mask_value("abc") == "***"

    def test_normal_value_partially_masked(self, svc):
        result = svc._mask_value("024899-01")
        assert result.startswith("02")
        assert result.endswith("01")
        assert "***" in result

    def test_whitespace_stripped(self, svc):
        assert svc._mask_value("  ") == ""


# ── _valid_date ───────────────────────────────────────────────────────────────

class TestValidDate:
    @pytest.mark.parametrize("v", ["03/20/2026", "01/01/2000", "12/31/2099"])
    def test_valid(self, svc, v):
        assert svc._valid_date(v) is True

    @pytest.mark.parametrize("v", ["2026-03-20", "3/20/2026", "03/20/26", "abc", "03-20-2026"])
    def test_invalid(self, svc, v):
        assert svc._valid_date(v) is False

    def test_empty_is_valid(self, svc):
        assert svc._valid_date("") is True


# ── _build_payload_hash ───────────────────────────────────────────────────────

class TestBuildPayloadHash:
    def test_deterministic(self, svc):
        fields = FillFields(escrow_number="123")
        h1 = svc._build_payload_hash(b"bytes", fields)
        h2 = svc._build_payload_hash(b"bytes", fields)
        assert h1 == h2

    def test_different_bytes_different_hash(self, svc):
        fields = FillFields()
        assert svc._build_payload_hash(b"a", fields) != svc._build_payload_hash(b"b", fields)

    def test_different_fields_different_hash(self, svc):
        h1 = svc._build_payload_hash(b"x", FillFields(escrow_number="111"))
        h2 = svc._build_payload_hash(b"x", FillFields(escrow_number="222"))
        assert h1 != h2


# ── run_fill ──────────────────────────────────────────────────────────────────

def _mock_fill(source_pdf, output_pdf, **kwargs):
    """Simulates fill_page17: copies source to output, returns summary."""
    Path(output_pdf).write_bytes(Path(source_pdf).read_bytes())
    summary = dict(MOCK_SUMMARY)
    summary["output_pdf"] = output_pdf
    return summary


class TestRunFill:
    def test_successful_fill(self, svc, sample_pdf_bytes):
        with patch("pg17_service.fill_page17", side_effect=_mock_fill):
            result = svc.run_fill(
                source_bytes=sample_pdf_bytes,
                fields=FillFields(escrow_number="024899-01"),
                idem_key="",
                actor="test-actor",
                request_id="req_test01",
                upload_ms=10.0,
            )
        assert isinstance(result, FillResult)
        assert result.idempotency_hit is False
        assert result.job_id
        assert result.output_file.startswith("/v1/pg17/output/")
        assert "engine" in result.timings_ms

    def test_engine_failure_raises_service_error(self, svc, sample_pdf_bytes):
        with patch("pg17_service.fill_page17", side_effect=RuntimeError("OCR failed")):
            with pytest.raises(PG17ServiceError, match="OCR failed"):
                svc.run_fill(
                    source_bytes=sample_pdf_bytes,
                    fields=FillFields(),
                    idem_key="",
                    actor="test",
                    request_id="req_test02",
                    upload_ms=5.0,
                )

    def test_idempotency_hit_returns_cached(self, svc, sample_pdf_bytes):
        with patch("pg17_service.fill_page17", side_effect=_mock_fill):
            r1 = svc.run_fill(
                source_bytes=sample_pdf_bytes,
                fields=FillFields(escrow_number="99"),
                idem_key="key-abc",
                actor="test",
                request_id="req_1",
                upload_ms=1.0,
            )
        # Second call with same key + same payload → cache hit
        with patch("pg17_service.fill_page17", side_effect=_mock_fill) as mock_engine:
            r2 = svc.run_fill(
                source_bytes=sample_pdf_bytes,
                fields=FillFields(escrow_number="99"),
                idem_key="key-abc",
                actor="test",
                request_id="req_2",
                upload_ms=1.0,
            )
            mock_engine.assert_not_called()  # engine must NOT run on cache hit

        assert r2.idempotency_hit is True
        assert r2.job_id == r1.job_id

    def test_idempotency_conflict_raises(self, svc, sample_pdf_bytes):
        with patch("pg17_service.fill_page17", side_effect=_mock_fill):
            svc.run_fill(
                source_bytes=sample_pdf_bytes,
                fields=FillFields(escrow_number="original"),
                idem_key="conflict-key",
                actor="test",
                request_id="req_3",
                upload_ms=1.0,
            )
        # Same key, different payload → conflict
        with patch("pg17_service.fill_page17", side_effect=_mock_fill):
            with pytest.raises(IdempotencyConflictError):
                svc.run_fill(
                    source_bytes=b"completely different bytes",
                    fields=FillFields(escrow_number="changed"),
                    idem_key="conflict-key",
                    actor="test",
                    request_id="req_4",
                    upload_ms=1.0,
                )

    def test_audit_log_written_on_success(self, svc, sample_pdf_bytes):
        with patch("pg17_service.fill_page17", side_effect=_mock_fill):
            svc.run_fill(
                source_bytes=sample_pdf_bytes,
                fields=FillFields(),
                idem_key="",
                actor="auditor",
                request_id="req_audit",
                upload_ms=1.0,
            )
        lines = svc.audit_log_path.read_text().strip().splitlines()
        events = [json.loads(l) for l in lines]
        assert any(e["event"] == "fill_success" for e in events)

    def test_audit_log_written_on_failure(self, svc, sample_pdf_bytes):
        with patch("pg17_service.fill_page17", side_effect=RuntimeError("boom")):
            with pytest.raises(PG17ServiceError):
                svc.run_fill(
                    source_bytes=sample_pdf_bytes,
                    fields=FillFields(),
                    idem_key="",
                    actor="test",
                    request_id="req_fail",
                    upload_ms=1.0,
                )
        lines = svc.audit_log_path.read_text().strip().splitlines()
        events = [json.loads(l) for l in lines]
        assert any(e["event"] == "fill_failed" for e in events)


# ── cleanup_old_outputs ───────────────────────────────────────────────────────

class TestCleanupOldOutputs:
    def test_deletes_old_files(self, svc):
        old = svc.output_dir / "abc123-done.pdf"
        old.write_bytes(b"old")
        # Set mtime to 10 days ago
        old_time = time.time() - 10 * 86400
        import os
        os.utime(old, (old_time, old_time))

        result = svc.cleanup_old_outputs()
        assert result["deleted"] == 1
        assert not old.exists()

    def test_keeps_recent_files(self, svc):
        recent = svc.output_dir / "xyz-done.pdf"
        recent.write_bytes(b"new")

        result = svc.cleanup_old_outputs()
        assert result["deleted"] == 0
        assert recent.exists()


# ── health_checks ─────────────────────────────────────────────────────────────

class TestHealthChecks:
    def test_output_dir_writable(self, svc):
        checks = svc.health_checks()
        assert checks["output_dir_writable"] is True

    def test_disk_free_gb_is_positive(self, svc):
        checks = svc.health_checks()
        assert checks["disk_free_gb"] > 0
