"""Integration tests for FastAPI routes using TestClient."""
from __future__ import annotations

import io
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from pg17_service import FillResult


@pytest.fixture
def client():
    from main import app
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def mock_fill_result():
    return FillResult(
        job_id="test-job-id",
        output_file="/v1/pg17/output/test-job-id",
        timings_ms={"upload": 5.0, "engine": 120.0},
        summary={"missing_inputs": [], "filled_fields": ["escrow_number"], "left_blank": []},
        idempotency_hit=False,
        idem_key=None,
    )


def _pdf_upload(filename="test.pdf"):
    return {"source_pdf": (filename, io.BytesIO(b"%PDF-1.4 test"), "application/pdf")}


# ── /health ───────────────────────────────────────────────────────────────────

class TestHealth:
    def test_health_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert "ok" in body
        assert "checks" in body
        assert "disk_free_gb" in body["checks"]

    def test_health_has_request_id(self, client):
        resp = client.get("/health")
        assert "x-request-id" in resp.headers


# ── /v1/pg17/fill — validation ────────────────────────────────────────────────

class TestFillValidation:
    def test_missing_pdf_returns_422(self, client):
        resp = client.post("/v1/pg17/fill", data={})
        assert resp.status_code == 422

    def test_non_pdf_file_returns_400(self, client):
        files = {"source_pdf": ("doc.txt", io.BytesIO(b"not a pdf"), "text/plain")}
        resp = client.post("/v1/pg17/fill", files=files)
        assert resp.status_code == 400
        assert resp.json()["error_code"] == "PG17_400_INVALID_PDF"

    def test_invalid_acceptance_date_returns_400(self, client):
        resp = client.post(
            "/v1/pg17/fill",
            files=_pdf_upload(),
            data={"acceptance_date": "2026-03-20"},
        )
        assert resp.status_code == 400
        assert resp.json()["error_code"] == "PG17_400_INVALID_DATE"

    def test_invalid_escrow_instruction_date_returns_400(self, client):
        resp = client.post(
            "/v1/pg17/fill",
            files=_pdf_upload(),
            data={"escrow_instruction_date": "bad"},
        )
        assert resp.status_code == 400
        assert resp.json()["error_code"] == "PG17_400_INVALID_DATE"

    def test_invalid_second_date_is_ignored(self, client):
        # second_date is auto-filled — bad value is passed through, not validated
        resp = client.post(
            "/v1/pg17/fill",
            files=_pdf_upload(),
            data={"second_date": "bad"},
        )
        # Should NOT return 400 for second_date
        assert resp.status_code != 400 or resp.json().get("error_code") != "PG17_400_INVALID_DATE"


# ── /v1/pg17/fill — success ───────────────────────────────────────────────────

class TestFillSuccess:
    def test_successful_fill_returns_ok(self, client, mock_fill_result):
        with patch("main.service.run_fill", return_value=mock_fill_result):
            resp = client.post(
                "/v1/pg17/fill",
                files=_pdf_upload(),
                data={"escrow_number": "024899-01", "acceptance_date": "03/20/2026"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert body["job_id"] == "test-job-id"
        assert body["output_file"] == "/v1/pg17/output/test-job-id"

    def test_response_has_request_id_header(self, client, mock_fill_result):
        with patch("main.service.run_fill", return_value=mock_fill_result):
            resp = client.post("/v1/pg17/fill", files=_pdf_upload())
        assert "x-request-id" in resp.headers

    def test_engine_error_returns_500(self, client):
        from pg17_service import PG17ServiceError
        with patch("main.service.run_fill", side_effect=PG17ServiceError("OCR failed")):
            resp = client.post("/v1/pg17/fill", files=_pdf_upload())
        assert resp.status_code == 500
        assert resp.json()["error_code"] == "PG17_500_ENGINE_FAILED"

    def test_idempotency_conflict_returns_409(self, client):
        from pg17_service import IdempotencyConflictError
        with patch("main.service.run_fill", side_effect=IdempotencyConflictError("key")):
            resp = client.post(
                "/v1/pg17/fill",
                files=_pdf_upload(),
                headers={"x-idempotency-key": "some-key"},
            )
        assert resp.status_code == 409
        assert resp.json()["error_code"] == "PG17_409_IDEMPOTENCY_PAYLOAD_MISMATCH"


# ── /v1/pg17/output/{job_id} ──────────────────────────────────────────────────

class TestDownloadOutput:
    def test_missing_job_returns_404(self, client):
        resp = client.get("/v1/pg17/output/nonexistent-job-id")
        assert resp.status_code == 404
        assert resp.json()["error_code"] == "PG17_404_OUTPUT_NOT_FOUND"
