"""Shared fixtures for all tests."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make apps/api importable without installing as a package
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "api"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "packages" / "pg17-fill-engine"))

from pg17_service import PG17Service


@pytest.fixture
def svc(tmp_path):
    """A PG17Service instance backed by a temp directory."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return PG17Service(
        output_dir=output_dir,
        audit_log_path=tmp_path / "audit.log.jsonl",
        retention_days=7,
        idempotency_ttl_seconds=3600,
        idempotency_store_path=tmp_path / "idem.json",
    )


@pytest.fixture
def sample_pdf_bytes():
    """Minimal valid-ish PDF bytes for upload tests."""
    return b"%PDF-1.4 fake pdf content for testing"
