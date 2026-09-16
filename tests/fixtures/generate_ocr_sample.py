"""Regenerates tests/fixtures/ocr_sample.png.

Section 14: fixtures are "generate[d] synthetically with a script so
they are versioned and regenerable" -- the PNG itself is committed
(tests should not depend on Pillow/fonts being present just to run),
this script is how it was made and how to remake it if it ever needs
to change.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
TEXT = "Hello DHRA OCR"
OUT = Path(__file__).parent / "ocr_sample.png"


def main() -> None:
    img = Image.new("RGB", (500, 120), "white")
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT_PATH, 32)
    draw.text((20, 35), TEXT, fill="black", font=font)
    img.save(OUT)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
