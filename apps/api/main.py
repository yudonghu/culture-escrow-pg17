from __future__ import annotations

import os
import re
import tempfile
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from pg17_engine import fill_page17

app = FastAPI(title="culture-escrow-pg17 API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OUTPUT_DIR = Path(tempfile.gettempdir()) / "culture-escrow-pg17"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _valid_date(v: str) -> bool:
    if not v:
        return True
    return bool(re.fullmatch(r"\d{2}/\d{2}/\d{4}", v))


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/v1/pg17/fill")
async def pg17_fill(
    source_pdf: UploadFile = File(...),
    deposit_amount: Optional[str] = Form(default=""),
    seller_agent_name: Optional[str] = Form(default=""),
    escrow_number: Optional[str] = Form(default=""),
    acceptance_date: Optional[str] = Form(default=""),
    second_date: Optional[str] = Form(default=""),
):
    if not source_pdf.filename or not source_pdf.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="source_pdf must be a PDF")

    for k, v in {
        "acceptance_date": (acceptance_date or "").strip(),
        "second_date": (second_date or "").strip(),
    }.items():
        if not _valid_date(v):
            raise HTTPException(status_code=400, detail=f"{k} must be MM/DD/YYYY")

    job_id = str(uuid.uuid4())
    src_path = OUTPUT_DIR / f"{job_id}-source.pdf"
    out_path = OUTPUT_DIR / f"{job_id}-done.pdf"

    content = await source_pdf.read()
    src_path.write_bytes(content)

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
        raise HTTPException(status_code=500, detail={
            "message": "fill failed",
            "error": str(e),
            "hint": "Check PDF layout and required anchors on page 17.",
        })

    return JSONResponse(
        {
            "job_id": job_id,
            "output_file": f"/v1/pg17/output/{job_id}",
            "summary": summary,
        }
    )


@app.get("/v1/pg17/output/{job_id}")
def download_output(job_id: str):
    out_path = OUTPUT_DIR / f"{job_id}-done.pdf"
    if not out_path.exists():
        raise HTTPException(status_code=404, detail="output not found")
    return FileResponse(out_path, media_type="application/pdf", filename=f"{job_id}-done.pdf")
