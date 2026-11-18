"""Image clean-up before OCR: erase table ruling lines.

Tesseract's layout analysis treats a gridded table as a picture and can drop every row inside
it. Long straight runs of dark pixels are lines, not text, so they are painted white first.

How lines are found without OpenCV: shrinking the image by WINDOW pixels along one axis
averages each WINDOW-long run. A ruling line stays dark after averaging, while text (strokes
separated by gaps) turns light grey. Thresholding the shrunk image gives a line mask.
"""

from __future__ import annotations

from PIL import Image, ImageChops, ImageFilter

# px: longer than letter stems even in 2x-upscaled scans (~36 px), shorter than table rules.
WINDOW = 60
DARK_INPUT = 160  # grey level below which a pixel counts as ink
DARK_AFTER_AVERAGE = 40  # ~85% of the window is ink: a solid rule, not a letter stroke


def _axis_mask(binary: Image.Image, horizontal: bool) -> Image.Image:
    width, height = binary.size
    if horizontal:
        shrunk = binary.resize((max(1, width // WINDOW), height), Image.Resampling.BOX)
    else:
        shrunk = binary.resize((width, max(1, height // WINDOW)), Image.Resampling.BOX)
    mask = shrunk.point(lambda v: 255 if v < DARK_AFTER_AVERAGE else 0)
    return mask.resize((width, height), Image.Resampling.NEAREST)


def remove_ruling_lines(image: Image.Image) -> Image.Image:
    gray = image.convert("L")
    binary = gray.point(lambda v: 0 if v < DARK_INPUT else 255)
    mask = ImageChops.lighter(_axis_mask(binary, True), _axis_mask(binary, False))
    # Grow the mask by a pixel so anti-aliased line edges go too.
    mask = mask.filter(ImageFilter.MaxFilter(3))
    white = Image.new("L", gray.size, 255)
    return Image.composite(white, gray, mask)
