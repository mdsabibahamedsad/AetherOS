"""Tests for the Phase 8 vision RPC handlers in tui_gateway.server."""

import base64
import io
import json

import pytest
from PIL import Image, ImageDraw

import tui_gateway.server as s


@pytest.fixture
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("AETHEROS_HOME", str(tmp_path / ".aetheros"))
    return tmp_path / ".aetheros"


def _png_data_url(width=120, height=60, text="Hello OCR"):
    img = Image.new("RGB", (width, height), "white")
    d = ImageDraw.Draw(img)
    d.text((8, height // 3), text, fill="black")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


class TestMethodRegistration:
    @pytest.mark.parametrize(
        "name",
        [
            "ocr.perform",
            "ocr.languages",
            "screen.analyze",
            "screen.ocr",
            "screen.explain",
            "screen.capture",
            "document.extract",
            "video.analyze",
            "vision.status",
        ],
    )
    def test_registered(self, name, isolated_home):
        assert name in s._methods

    def test_long_handlers_include_slow_vision(self, isolated_home):
        for name in ["ocr.perform", "screen.analyze", "screen.explain", "screen.ocr", "video.analyze", "document.extract"]:
            assert name in s._LONG_HANDLERS


class TestOCRRPC:
    def test_ocr_perform_missing_image(self, isolated_home):
        resp = s.handle_request({"jsonrpc": "2.0", "id": 1, "method": "ocr.perform", "params": {}})
        assert "error" in resp

    def test_ocr_perform_invalid_base64(self, isolated_home):
        resp = s.handle_request({"jsonrpc": "2.0", "id": 2, "method": "ocr.perform", "params": {"imageData": "not-valid-b64!!!"}})
        assert "error" in resp

    def test_ocr_perform_shape(self, isolated_home):
        resp = s.handle_request({"jsonrpc": "2.0", "id": 3, "method": "ocr.perform", "params": {"imageData": _png_data_url()}})
        assert "result" in resp
        r = resp["result"]
        assert "success" in r
        assert "text" in r
        assert "confidence" in r
        assert "pages" in r

    def test_ocr_languages_shape(self, isolated_home):
        resp = s.handle_request({"jsonrpc": "2.0", "id": 4, "method": "ocr.languages", "params": {}})
        assert "result" in resp
        assert isinstance(resp["result"]["languages"], list)


class TestScreenRPC:
    def test_screen_analyze_missing_image(self, isolated_home):
        resp = s.handle_request({"jsonrpc": "2.0", "id": 5, "method": "screen.analyze", "params": {}})
        assert "error" in resp

    def test_screen_analyze_shape(self, isolated_home):
        resp = s.handle_request({"jsonrpc": "2.0", "id": 6, "method": "screen.analyze", "params": {"imageData": _png_data_url(text="Welcome")}})
        assert "result" in resp
        r = resp["result"]
        assert "description" in r
        assert "elements" in r
        assert "text" in r

    def test_screen_ocr_shape(self, isolated_home):
        resp = s.handle_request({"jsonrpc": "2.0", "id": 7, "method": "screen.ocr", "params": {"imageData": _png_data_url()}})
        assert "result" in resp
        assert "text" in resp["result"]

    def test_screen_explain_missing_image(self, isolated_home):
        resp = s.handle_request({"jsonrpc": "2.0", "id": 8, "method": "screen.explain", "params": {}})
        assert "error" in resp

    def test_screen_explain_shape(self, isolated_home):
        resp = s.handle_request({"jsonrpc": "2.0", "id": 9, "method": "screen.explain", "params": {"imageData": _png_data_url(), "query": "anything"}})
        assert "result" in resp
        assert "explanation" in resp["result"]

    def test_screen_capture_shape(self, isolated_home):
        resp = s.handle_request({"jsonrpc": "2.0", "id": 10, "method": "screen.capture", "params": {}})
        if "result" in resp:
            assert "success" in resp["result"]


class TestDocumentRPC:
    def test_document_extract_missing_path(self, isolated_home):
        resp = s.handle_request({"jsonrpc": "2.0", "id": 11, "method": "document.extract", "params": {}})
        assert "error" in resp

    def test_document_extract_markdown(self, tmp_path, isolated_home):
        md = tmp_path / "doc.md"
        md.write_text("# Hello\n\nBody text here.\n", encoding="utf-8")
        resp = s.handle_request({"jsonrpc": "2.0", "id": 12, "method": "document.extract", "params": {"path": str(md)}})
        assert "result" in resp
        r = resp["result"]
        assert r["success"] is True
        assert "Hello" in r["text"]


class TestVisionStatusRPC:
    def test_vision_status_shape(self, isolated_home):
        resp = s.handle_request({"jsonrpc": "2.0", "id": 13, "method": "vision.status", "params": {}})
        assert "result" in resp
        r = resp["result"]
        assert "state" in r
        assert "ocr_available" in r
        assert "checks" in r


class TestUnknownMethod:
    def test_unknown_vision_method(self, isolated_home):
        resp = s.handle_request({"jsonrpc": "2.0", "id": 14, "method": "vision.nonexistent", "params": {}})
        assert "error" in resp
