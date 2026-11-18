"""Node 2, parse: build the words layer and layout text, using OCR only where needed."""

from __future__ import annotations

import io
from dataclasses import dataclass
from statistics import mean

import pymupdf
from PIL import Image, ImageOps

from extractor.parsing.document import PageInfo, ParsedDocument
from extractor.parsing.layout import build_lines
from extractor.parsing.ocr import ocr_words, tesseract_version
from extractor.parsing.pdf_text import render_page, text_layer_words
from extractor.parsing.preprocess import remove_ruling_lines
from extractor.parsing.words import Word

# Tesseract reads best at roughly 200-300 dpi. A4 at 200 dpi is ~1654 px wide, so smaller
# images (phone photos, low-res scans) are upscaled to that width first.
_TARGET_OCR_WIDTH = 1654


@dataclass(frozen=True)
class ParseOptions:
    dpi: int = 200  # render resolution for PDF pages that need OCR
    min_chars: int = 40  # fewer text-layer characters than this on a page means "scanned page"
    lang: str = "eng"
    remove_lines: bool = True  # erase table rules before OCR (DECISIONS D-022)


class ParseError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _require_tesseract() -> None:
    if tesseract_version() is None:
        raise ParseError("ocr_unavailable", "This document needs OCR but Tesseract is missing")


def _ocr_page(image: Image.Image, page: int, options: ParseOptions) -> tuple[list[Word], PageInfo]:
    _require_tesseract()
    words = ocr_words(image, page, options.lang)
    confidence = mean(w.conf for w in words) if words else 0.0
    return words, PageInfo(page, "ocr", confidence)


def _clean(image: Image.Image, options: ParseOptions) -> Image.Image:
    """Erase table rules at the image's native resolution: upscaling first would stretch letter
    stems towards the rule-detection window and erase them too (found by the eval ablation)."""
    return remove_ruling_lines(image) if options.remove_lines else image


def _prepare_image(data: bytes, options: ParseOptions) -> Image.Image:
    with Image.open(io.BytesIO(data)) as raw:
        image = _clean(ImageOps.exif_transpose(raw).convert("L"), options)
    if image.width < _TARGET_OCR_WIDTH:
        scale = _TARGET_OCR_WIDTH / image.width
        image = image.resize(
            (_TARGET_OCR_WIDTH, round(image.height * scale)), Image.Resampling.LANCZOS
        )
    return image


def parse_pdf(data: bytes, options: ParseOptions) -> ParsedDocument:
    pages, lines = [], []
    with pymupdf.open(stream=data, filetype="pdf") as doc:
        for number, page in enumerate(doc, start=1):
            words = text_layer_words(page, number)
            if sum(len(w.text) for w in words) >= options.min_chars:
                info = PageInfo(number, "text")
            else:
                image = _clean(render_page(page, options.dpi), options)
                words, info = _ocr_page(image, number, options)
                del image  # free the bitmap before rendering the next page
            pages.append(info)
            lines += build_lines(words, number, from_ocr=info.source == "ocr")
    return ParsedDocument(pages=pages, lines=lines)


def parse_image(data: bytes, options: ParseOptions) -> ParsedDocument:
    words, info = _ocr_page(_prepare_image(data, options), 1, options)
    return ParsedDocument(pages=[info], lines=build_lines(words, 1, from_ocr=True))


def parse_document(data: bytes, kind: str, options: ParseOptions) -> ParsedDocument:
    if kind == "pdf":
        return parse_pdf(data, options)
    return parse_image(data, options)
