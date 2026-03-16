"""Image processing utilities for spectrogram and waveplot assets."""

from __future__ import annotations

from io import BytesIO

from PIL import Image


def waveplot_to_grayscale_transparent(source_path: str) -> BytesIO:
    """
    Convert a waveplot image to grayscale with transparent background.

    Reads the image from source_path, converts it to grayscale, and makes
    near-white background pixels transparent. Returns PNG bytes in a BytesIO.
    """
    img = Image.open(source_path)
    gray = img.convert("L")
    # Treat luminance >= 200 as background (white)
    threshold = 200
    data = list(gray.getdata())
    alpha = [0 if p >= threshold else 255 for p in data]
    out = Image.new("RGBA", gray.size)
    out.putdata([(p, p, p, a) for p, a in zip(data, alpha)])
    buf = BytesIO()
    out.save(buf, format="PNG")
    buf.seek(0)
    return buf
