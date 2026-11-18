FROM python:3.12.12-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Tesseract is a system binary; pytesseract only shells out to it.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY pyproject.toml pricing.json ./
COPY extractor ./extractor
RUN pip install --no-deps .

# ---- dev / eval image: adds test tooling and the eval generator deps ----
FROM base AS dev
COPY requirements-dev.txt ./
RUN pip install -r requirements-dev.txt fpdf2==2.9.0
WORKDIR /repo

# ---- production image ----
FROM base AS prod
RUN useradd --system --uid 10001 app && mkdir -p /app/llm_cache && chown app /app/llm_cache
USER app
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
  CMD python -c "import sys,urllib.request; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health', timeout=3).status == 200 else 1)"
CMD ["uvicorn", "extractor.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log"]
