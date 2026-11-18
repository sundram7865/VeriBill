"""Tesseract OCR wrapper: page image in, words with boxes and confidences out."""

from __future__ import annotations

from functools import lru_cache

import pytesseract
from PIL import Image

from extractor.parsing.words import Word


@lru_cache(maxsize=1)
def tesseract_version() -> str | None:
    try:
        return str(pytesseract.get_tesseract_version())
    except (pytesseract.TesseractNotFoundError, OSError):
        return None


def ocr_words(image: Image.Image, page: int, lang: str = "eng") -> list[Word]:
    """Run Tesseract on one page image. Boxes are normalised to 0..1 of the page size."""
    width, height = image.size
    data = pytesseract.image_to_data(
        image,
        lang=lang,
        config="--psm 6",
        output_type=pytesseract.Output.DICT,
    )
    words: list[Word] = []
    for i, text in enumerate(data["text"]):
        text = text.strip()
        conf = float(data["conf"][i])
        if not text or conf < 0:
            continue
        left, top = data["left"][i], data["top"][i]
        w, h = data["width"][i], data["height"][i]
        words.append(
            Word(
                text=text,
                page=page,
                x0=left / width,
                y0=top / height,
                x1=(left + w) / width,
                y1=(top + h) / height,
                conf=conf / 100.0,
                block=int(data["block_num"][i]),
                line=int(data["par_num"][i]) * 1000 + int(data["line_num"][i]),
            )
        )
    return words
