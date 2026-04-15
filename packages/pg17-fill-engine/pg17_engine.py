from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENGINE_SCRIPT = ROOT / 'tools' / 'pg17-engine' / 'fill_page17_real.py'
FALLBACK_ENGINE_SCRIPT = ROOT / 'tools' / 'pg17-engine' / 'fill_page17_stub.py'
DEFAULT_ENGINE_PYTHON = sys.executable


def _engine_script() -> Path:
    configured = os.getenv('PG17_ENGINE_SCRIPT')
    if configured:
        return Path(configured).expanduser().resolve()
    if DEFAULT_ENGINE_SCRIPT.exists():
        return DEFAULT_ENGINE_SCRIPT
    return FALLBACK_ENGINE_SCRIPT


def _engine_python() -> str:
    return os.getenv('PG17_ENGINE_PYTHON', DEFAULT_ENGINE_PYTHON)


def _validate_pdf_path(path: str, label: str) -> Path:
    """Resolve and validate a PDF path to prevent path traversal attacks.

    Only allows paths that are absolute and point to an existing file
    (or a writeable parent directory for output paths).
    """
    resolved = Path(path).resolve()
    # Disallow non-absolute or suspiciously short paths
    if not resolved.is_absolute():
        raise ValueError(f"Invalid {label}: must be an absolute path")
    # Disallow paths with null bytes or shell metacharacters
    suspicious = set('\x00;&|`$><!')
    if any(c in path for c in suspicious):
        raise ValueError(f"Invalid {label}: contains disallowed characters")
    return resolved


def fill_page17(
    source_pdf: str,
    output_pdf: str,
    deposit_amount: str = '',
    seller_agent_name: str = '',
    escrow_number: str = '',
    acceptance_date: str = '',
    second_date: str = '',
):
    script = _engine_script()
    python_bin = _engine_python()

    if not script.exists():
        raise RuntimeError(f'engine script not found: {script}')

    source_path = _validate_pdf_path(source_pdf, 'source_pdf')
    output_path = _validate_pdf_path(output_pdf, 'output_pdf')

    if not source_path.exists():
        raise ValueError(f'source_pdf does not exist: {source_path}')

    cmd = [python_bin, str(script), '--source', str(source_path)]

    # support both repo-deploy real engine and stub engine
    if script.name == 'fill_page17_stub.py':
        cmd += ['--output', str(output_path)]
    if deposit_amount:
        cmd += ['--deposit-amount', deposit_amount]
    if seller_agent_name:
        cmd += ['--seller-agent', seller_agent_name]
    if escrow_number:
        cmd += ['--escrow-number', escrow_number]
    if acceptance_date:
        cmd += ['--acceptance-date', acceptance_date]
    if second_date:
        cmd += ['--second-date', second_date]

    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr or p.stdout or 'unknown error')

    summary = json.loads(p.stdout)
    generated = summary.get('output_pdf')
    if not generated:
        raise RuntimeError('no output_pdf in summary')

    generated_path = Path(generated).resolve()
    if generated_path != output_path:
        output_path.write_bytes(generated_path.read_bytes())

    return {
        'missing_inputs': summary.get('missing_inputs', []),
        'filled_fields': summary.get('filled_fields', []),
        'left_blank': summary.get('left_blank', []),
        'engine_mode': summary.get('engine_mode', 'real_fill' if script.name == 'fill_page17_real.py' else 'stub_copy'),
        'engine_script': str(script),
    }
