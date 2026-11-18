"""Words from a digital PDF's text layer (no OCR needed)."""

from __future__ import annotations

import pymupdf
from PIL import Image

from extractor.parsing.words import Word


def text_layer_words(page: pymupdf.Page, page_number: int) -> list[Word]:
    width, height = page.rect.width, page.rect.height
    words = []
    # Tuples: (x0, y0, x1, y1, text, block_no, line_no, word_no)
    for x0, y0, x1, y1, text, block, line, _ in page.get_text("words", sort=True):
        if not text.strip():
            continue
        words.append(
            Word(
                text=text,
                page=page_number,
                x0=x0 / width,
                y0=y0 / height,
                x1=x1 / width,
                y1=y1 / height,
                conf=1.0,
                block=block,
                line=line,
            )
        )
    return words


def render_page(page: pymupdf.Page, dpi: int) -> Image.Image:
    """Render one page to a grayscale PIL image (one page at a time keeps memory low)."""
    pix = page.get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY)
    return Image.frombytes("L", (pix.width, pix.height), pix.samples)
