from __future__ import annotations

import json
import subprocess
from pathlib import Path

SKILL_DIR = Path("/Users/wu/.openclaw/workspace/skills/pg17-v1-02-26-2026")
SCRIPT = SKILL_DIR / "scripts" / "fill_page17.py"
PYTHON = SKILL_DIR / ".venv" / "bin" / "python"


def fill_page17(
    source_pdf: str,
    output_pdf: str,
    deposit_amount: str = "",
    seller_agent_name: str = "",
    escrow_number: str = "",
    acceptance_date: str = "",
    second_date: str = "",
):
    cmd = [
        str(PYTHON),
        str(SCRIPT),
        "--source",
        source_pdf,
    ]
    if deposit_amount:
        cmd += ["--deposit-amount", deposit_amount]
    if seller_agent_name:
        cmd += ["--seller-agent", seller_agent_name]
    if escrow_number:
        cmd += ["--escrow-number", escrow_number]
    if acceptance_date:
        cmd += ["--acceptance-date", acceptance_date]
    if second_date:
        cmd += ["--second-date", second_date]

    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr or p.stdout or "unknown error")

    summary = json.loads(p.stdout)
    generated = summary.get("output_pdf")
    if not generated:
        raise RuntimeError("no output_pdf in summary")

    Path(output_pdf).write_bytes(Path(generated).read_bytes())
    return {
        "missing_inputs": summary.get("missing_inputs", []),
        "filled_fields": summary.get("filled_fields", []),
        "left_blank": summary.get("left_blank", []),
    }
