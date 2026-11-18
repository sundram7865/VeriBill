"""Health endpoint: reports whether the OCR binary is available."""

from __future__ import annotations

from fastapi import APIRouter

from extractor.parsing.ocr import tesseract_version

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    version = tesseract_version()
    return {"status": "ok", "tesseract": version or "missing"}
