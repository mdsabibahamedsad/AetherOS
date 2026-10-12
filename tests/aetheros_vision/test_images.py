"""Tests for aetheros_vision.images — decoding, MIME detection, payload prep."""

import base64
import io

import pytest

_TINY_PNG = base64.b64decode(
    b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
)


@pytest.fixture
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("AETHEROS_HOME", str(tmp_path / ".aetheros"))
    return tmp_path / ".aetheros"


class TestMimeDetection:
    def test_png(self):
        from aetheros_vision.images import _mime_from_magic

        assert _mime_from_magic(_TINY_PNG) == "image/png"

    def test_jpeg(self):
        from aetheros_vision.images import _mime_from_magic

        assert _mime_from_magic(b"\xff\xd8\xff...") == "image/jpeg"

    def test_unknown(self):
        from aetheros_vision.images import _mime_from_magic

        assert _mime_from_magic(b"not an image") == ""


class TestImageLoader:
    def test_load_bytes_png(self, isolated_home):
        from aetheros_vision.images import LoadedImage

        img = LoadedImage.from_bytes(_TINY_PNG)
        assert img.format == "PNG"
        assert img.width == 1
        assert img.height == 1
        assert img.mime_type == "image/png"

    def test_load_from_file(self, tmp_path, isolated_home):
        from aetheros_vision.images import LoadedImage

        p = tmp_path / "img.png"
        p.write_bytes(_TINY_PNG)
        img = LoadedImage.from_source(str(p))
        assert img.path == str(p)
        assert img.width == 1

    def test_missing_file_raises(self, tmp_path, isolated_home):
        from aetheros_vision.images import ImageDecodeError, LoadedImage

        with pytest.raises(ImageDecodeError):
            LoadedImage.from_source(str(tmp_path / "missing.png"))

    def test_invalid_bytes_raises(self, isolated_home):
        from aetheros_vision.images import ImageDecodeError, LoadedImage

        with pytest.raises(ImageDecodeError):
            LoadedImage.from_bytes(b"\x00\x00\x00 garbage")


class TestPreparePayload:
    def test_returns_original_when_small(self, tmp_path, isolated_home):
        from aetheros_vision.images import prepare_image_payload

        p = tmp_path / "img.png"
        p.write_bytes(_TINY_PNG)
        data, mime = prepare_image_payload(p, max_bytes=1024 * 1024)
        assert data == _TINY_PNG
        assert mime == "image/png"


class TestImageUnderstanding:
    def test_describe_local_image_no_ocr(self, tmp_path, isolated_home):
        from aetheros_vision.images import ImageUnderstanding

        p = tmp_path / "img.png"
        p.write_bytes(_TINY_PNG)
        result = ImageUnderstanding().describe(str(p), use_ocr=False)
        assert result.metadata["image"]["width"] == 1
        assert result.metadata["image"]["height"] == 1
        assert result.metadata["image"]["format"] == "PNG"
