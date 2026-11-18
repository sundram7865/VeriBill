"""Node 1, ingest: detect the file type from magic bytes, count pages, enforce limits."""

from __future__ import annotations

import io
from dataclasses import dataclass

import pymupdf
from PIL import Image, UnidentifiedImageError

MAGIC = {
    b"%PDF-": "pdf",
    b"\x89PNG\r\n\x1a\n": "png",
    b"\xff\xd8\xff": "jpeg",
}


class IngestError(ValueError):
    """The file cannot be processed at all (wrong type, too big, too many pages, corrupt)."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class IngestedFile:
    kind: str  # pdf | png | jpeg
    page_count: int


def detect_kind(data: bytes) -> str | None:
    for magic, kind in MAGIC.items():
        if data.startswith(magic):
            return kind
    return None


def _count_pdf_pages(data: bytes) -> int:
    try:
        with pymupdf.open(stream=data, filetype="pdf") as doc:
            if doc.needs_pass:
                raise IngestError("encrypted_pdf", "Password-protected PDFs are not supported")
            return doc.page_count
    except (pymupdf.FileDataError, RuntimeError) as exc:
        raise IngestError("unreadable_file", "The PDF is corrupt or unreadable") from exc


def _check_image(data: bytes) -> int:
    try:
        with Image.open(io.BytesIO(data)) as image:
            image.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise IngestError("unreadable_file", "The image is corrupt or unreadable") from exc
    return 1


def ingest(data: bytes, max_bytes: int, max_pages: int) -> IngestedFile:
    if len(data) == 0:
        raise IngestError("empty_file", "The file is empty")
    if len(data) > max_bytes:
        raise IngestError("file_too_large", f"File exceeds {max_bytes // (1024 * 1024)} MB")
    kind = detect_kind(data)
    if kind is None:
        raise IngestError("unsupported_type", "Only PDF, PNG and JPEG files are supported")
    pages = _count_pdf_pages(data) if kind == "pdf" else _check_image(data)
    if pages == 0:
        raise IngestError("unreadable_file", "The PDF has no pages")
    if pages > max_pages:
        raise IngestError("too_many_pages", f"Document has {pages} pages; the limit is {max_pages}")
    return IngestedFile(kind=kind, page_count=pages)
