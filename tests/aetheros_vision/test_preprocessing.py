"""Tests for aetheros_ocr.preprocessing — Pillow-only image transforms."""

import io

import pytest
from PIL import Image

from aetheros_ocr.preprocessing import preprocess, preprocess_bytes


def _make_image(mode="RGB", size=(64, 64), color="white"):
    img = Image.new(mode, size, color)
    return img


class TestPreprocess:
    def test_returns_pil_image(self):
        out = preprocess(_make_image())
        assert hasattr(out, "save")

    def test_preserves_dimensions(self):
        img = _make_image(size=(80, 50))
        out = preprocess(img, use_deskew=True, use_denoise=True, use_enhance=True)
        assert out.size == (80, 50)

    def test_binarize_output(self):
        img = _make_image(mode="RGB", size=(40, 40))
        out = preprocess(img, use_enhance=True, binarize_output=True)
        assert out.mode == "L"

    def test_empty_input(self):
        with pytest.raises(Exception):
            preprocess(None)

    def test_grayscale_input(self):
        img = _make_image(mode="L")
        out = preprocess(img)
        assert out is not None


class TestPreprocessBytes:
    def test_round_trip(self):
        buf = io.BytesIO()
        _make_image().save(buf, format="PNG")
        out = preprocess_bytes(buf.getvalue(), use_deskew=True, use_enhance=True)
        assert isinstance(out, bytes)
        assert out.startswith(b"\x89PNG") or out[:2] in (b"\xff\xd8", b"BM")

    def test_returns_bytes_for_passthrough(self):
        buf = io.BytesIO()
        _make_image().save(buf, format="PNG")
        out = preprocess_bytes(buf.getvalue(), use_deskew=False, use_denoise=False, use_enhance=False)
        assert out == buf.getvalue()
