"""Turn a clean PDF into a 'scan': rasterise, then rotate / add noise / blur / downsample.

All randomness comes from a seeded random.Random, never from Pillow's C-level RNG, so the
same seed always produces byte-identical images.
"""

from __future__ import annotations

import io
import random

import pymupdf
from PIL import Image, ImageChops, ImageFilter

SCAN_VARIANTS = ("scan_clean", "scan_rotate", "scan_noise", "scan_blur", "scan_lowres")


def rasterize(pdf_bytes: bytes, dpi: int) -> list[Image.Image]:
    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as doc:
        pages = []
        for page in doc:
            pix = page.get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY)
            pages.append(Image.frombytes("L", (pix.width, pix.height), pix.samples))
        return pages


def _seeded_noise(size: tuple[int, int], rng: random.Random) -> Image.Image:
    return Image.frombytes("L", size, rng.randbytes(size[0] * size[1]))


def add_noise(image: Image.Image, rng: random.Random) -> Image.Image:
    noise = _seeded_noise(image.size, rng)
    grainy = Image.blend(image, noise, alpha=0.12)
    specks = noise.point(lambda v: 0 if v < 3 else 255)  # ~1% dark specks
    return ImageChops.darker(grainy, specks)


def rotate(image: Image.Image, rng: random.Random) -> Image.Image:
    angle = rng.choice([-1, 1]) * rng.uniform(0.8, 3.0)
    return image.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True, fillcolor=255)


def blur(image: Image.Image, rng: random.Random) -> Image.Image:
    return image.filter(ImageFilter.GaussianBlur(radius=rng.uniform(0.8, 1.3)))


def apply_variant(image: Image.Image, variant: str, rng: random.Random) -> Image.Image:
    if variant == "scan_rotate":
        return rotate(image, rng)
    if variant == "scan_noise":
        return add_noise(image, rng)
    if variant == "scan_blur":
        return blur(image, rng)
    return image  # scan_clean and scan_lowres differ only in resolution


def variant_dpi(variant: str) -> int:
    return 110 if variant == "scan_lowres" else 200


def to_image_bytes(image: Image.Image, fmt: str) -> bytes:
    buffer = io.BytesIO()
    if fmt == "JPEG":
        image.save(buffer, format="JPEG", quality=75, optimize=False)
    else:
        image.save(buffer, format="PNG", optimize=False)
    return buffer.getvalue()


def images_to_pdf(images: list[Image.Image], dpi: int) -> bytes:
    """Image-only PDF (no text layer), like a scanner produces."""
    doc = pymupdf.open()
    for image in images:
        width_pt = image.width * 72 / dpi
        height_pt = image.height * 72 / dpi
        page = doc.new_page(width=width_pt, height=height_pt)
        page.insert_image(page.rect, stream=to_image_bytes(image, "JPEG"))
    data = doc.tobytes(garbage=3, deflate=True, no_new_id=True)
    doc.close()
    return data


def degrade(pdf_bytes: bytes, variant: str, rng: random.Random) -> tuple[bytes, str]:
    """Returns (file bytes, mime). Single pages become PNG/JPG; multi-page becomes image PDF."""
    dpi = variant_dpi(variant)
    pages = [apply_variant(page, variant, rng) for page in rasterize(pdf_bytes, dpi)]
    if len(pages) > 1:
        return images_to_pdf(pages, dpi), "application/pdf"
    if rng.random() < 0.5:
        return to_image_bytes(pages[0], "PNG"), "image/png"
    return to_image_bytes(pages[0], "JPEG"), "image/jpeg"
