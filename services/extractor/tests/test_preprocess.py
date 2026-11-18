from PIL import Image, ImageDraw

from extractor.parsing.preprocess import remove_ruling_lines


def _ink(image: Image.Image, box: tuple[int, int, int, int]) -> int:
    return sum(1 for v in image.crop(box).getdata() if v < 128)


def test_ruling_lines_are_erased_but_text_strokes_survive():
    page = Image.new("L", (800, 400), 255)
    draw = ImageDraw.Draw(page)
    draw.line([(20, 100), (780, 100)], fill=0, width=2)  # horizontal table rule
    draw.line([(400, 40), (400, 360)], fill=0, width=2)  # vertical table rule
    # A "letter": short strokes like an 'H', ~20 px tall, as glyphs are at 200 dpi.
    draw.line([(100, 200), (100, 220)], fill=0, width=2)
    draw.line([(112, 200), (112, 220)], fill=0, width=2)
    draw.line([(100, 210), (112, 210)], fill=0, width=2)

    cleaned = remove_ruling_lines(page)

    # A stub up to one window long can survive at each end of a rule; the body must be gone.
    assert _ink(cleaned, (90, 95, 380, 105)) == 0  # horizontal rule gone
    assert _ink(cleaned, (395, 120, 405, 290)) == 0  # vertical rule gone
    assert _ink(cleaned, (95, 195, 120, 225)) == _ink(page, (95, 195, 120, 225))  # letter intact
