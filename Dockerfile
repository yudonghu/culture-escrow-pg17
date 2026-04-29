FROM python:3.11-slim

# ── System dependencies ────────────────────────────────────────────────────────
# tesseract-ocr: OCR engine used by fill_page17_real.py
# libgl1 / libglib2.0: required by pymupdf (fitz)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    libgl1 \
    libglib2.0-0 \
  && rm -rf /var/lib/apt/lists/*

# ── App setup ─────────────────────────────────────────────────────────────────
WORKDIR /app

# Install Python dependencies first (layer cache)
COPY apps/api/requirements.txt ./apps/api/requirements.txt
COPY packages/pg17-fill-engine/requirements.txt ./packages/pg17-fill-engine/requirements.txt
RUN pip install --no-cache-dir \
    -r apps/api/requirements.txt \
    -r packages/pg17-fill-engine/requirements.txt

# Copy source code
COPY apps/api/                   ./apps/api/
COPY packages/pg17-fill-engine/  ./packages/pg17-fill-engine/

# Install engine package in editable mode
RUN pip install --no-cache-dir -e packages/pg17-fill-engine/

# ── Runtime ───────────────────────────────────────────────────────────────────
ENV PYTHONPATH=/app/packages/pg17-fill-engine
ENV PG17_ENGINE_SCRIPT=/app/packages/pg17-fill-engine/fill_page17_real.py
ENV PG17_ENGINE_PYTHON=python3

EXPOSE 8787

CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8787"]
