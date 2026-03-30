from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENGINE_SCRIPT = ROOT / 'tools' / 'pg17-engine' / 'fill_page17_stub.py'
DEFAULT_ENGINE_PYTHON = sys.executable


def _engine_script() -> Path:
    return Path(os.getenv('PG17_ENGINE_SCRIPT', str(DEFAULT_ENGINE_SCRIPT))).expanduser().resolve()


def _engine_python() -> str:
    return os.getenv('PG17_ENGINE_PYTHON', DEFAULT_ENGINE_PYTHON)


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

    cmd = [
        python_bin,
        str(script),
        '--source',
        source_pdf,
        '--output',
        output_pdf,
    ]
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

    return {
        'missing_inputs': summary.get('missing_inputs', []),
        'filled_fields': summary.get('filled_fields', []),
        'left_blank': summary.get('left_blank', []),
        'engine_mode': summary.get('engine_mode', 'external'),
        'engine_script': str(script),
    }
