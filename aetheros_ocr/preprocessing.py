"""AetherOS OCR — image preprocessing.

Pure-Pillow preprocessing used before OCR to improve accuracy: deskew,
denoise (median / adaptive), contrast enhancement, and scaling. All
functions are deterministic, dependency-light (Pillow only), and return a
PIL Image so they can be chained.
"""

from __future__ import annotations

import io
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

try:
    from PIL import Image, ImageEnhance, ImageFilter, ImageOps
    _PIL_AVAILABLE = True
except ImportError:  # pragma: no cover
    Image = ImageEnhance = ImageFilter = ImageOps = None
    _PIL_AVAILABLE = False


def _require_pil():
    if not _PIL_AVAILABLE:
        raise RuntimeError("Pillow is required for OCR preprocessing")


def to_grayscale(image) -> Image.Image:
    _require_pil()
    if image.mode != "L":
        return image.convert("L")
    return image


def deskew(image, max_angle: float = 15.0) -> Image.Image:
    """Rotate a slightly-skewed page so text lines are horizontal.

    Uses the image's ``getexif()`` orientation if present, then a
    light edge-density search over candidate rotations. Falls back to the
    original image when estimation is unreliable.
    """
    _require_pil()
    img = image.copy()
    if img.mode != "L":
        img = img.convert("L")

    # Honor EXIF orientation first.
    try:
        img = ImageOps.exif_transpose(img)
    except Exception:  # noqa: BLE001
        pass

    try:
        width, height = img.size
        if min(width, height) < 64:
            return image
        best_angle, best_score = 0.0, -1.0
        import math
        from PIL import ImageDraw
        small = img.resize((max(width // 4, 64), max(height // 4, 64)))
        gray = small.point(lambda p: 255 if p > 120 else 0)
        # Candidate angles in 0.5° steps within the allowed range.
        steps = [a / 2.0 for a in range(-int(max_angle * 2), int(max_angle * 2) + 1)]
        for angle in steps:
            rot = gray.rotate(angle, fillcolor=255)
            pixels = rot.load()
            score = 0
            w, h = rot.size
            for y in range(0, h, 4):
                prev = 255
                for x in range(0, w, 4):
                    cur = pixels[x, y]
                    if cur != prev:
                        score += 1
                    prev = cur
            if score > best_score:
                best_score, best_angle = score, angle
        if best_score <= 0:
            return image
        return image.rotate(best_angle, fillcolor=255, expand=True)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Deskew skipped (%s); returning original", exc)
        return image


def denoise(image, radius: int = 1) -> Image.Image:
    """Reduce sensor/scan noise with a median filter (preserves edges)."""
    _require_pil()
    return image.filter(ImageFilter.MedianFilter(radius))


def enhance_contrast(image, factor: float = 1.8) -> Image.Image:
    _require_pil()
    if image.mode not in ("L", "RGB"):
        image = image.convert("RGB")
    return ImageEnhance.Contrast(image).enhance(factor)


def sharpen(image, factor: float = 1.2) -> Image.Image:
    _require_pil()
    return image.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))


def binarize(image, threshold: int = 140) -> Image.Image:
    """High-contrast black/white binarisation good for printed text."""
    _require_pil()
    gray = to_grayscale(image)
    return gray.point(lambda p: 255 if p > threshold else 0)


def preprocess(
    image,
    *,
    use_deskew: bool = False,
    use_denoise: bool = False,
    use_enhance: bool = False,
    binarize_output: bool = False,
) -> Image.Image:
    """Apply the configured preprocessing chain in a stable order.

    Order: deskew → denoise → enhance → optional binarise. Each step is
    skipped when its flag is off, so the function is a no-op passthrough
    when everything is disabled.
    """
    _require_pil()
    img = image.copy()
    if use_deskew:
        img = deskew(img)
    if use_denoise:
        img = denoise(img)
    if use_enhance:
        img = enhance_contrast(img)
    if binarize_output:
        img = binarize(img)
    return img


def preprocess_bytes(
    data: bytes,
    *,
    use_deskew: bool = False,
    use_denoise: bool = False,
    use_enhance: bool = False,
    binarize_output: bool = False,
    format: str = "PNG",
) -> bytes:
    """Apply preprocessing to raw encoded bytes and return encoded bytes."""
    _require_pil()
    with Image.open(io.BytesIO(data)) as img:
        img.load()
        out = preprocess(img, use_deskew=use_deskew, use_denoise=use_denoise, use_enhance=use_enhance, binarize_output=binarize_output)
        buf = io.BytesIO()
        out.save(buf, format=format)
        return buf.getvalue()
