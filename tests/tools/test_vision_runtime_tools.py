"""Tests for the Phase 8 vision runtime agent tools in tools/vision_tools.py."""

import asyncio
import json

import pytest

import tools.vision_tools as vt


@pytest.fixture
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("AETHEROS_HOME", str(tmp_path / ".aetheros"))
    return tmp_path / ".aetheros"


class TestRegistration:
    @pytest.mark.parametrize("name", ["screen_capture", "image_ocr", "document_extract", "screen_understand"])
    def test_tools_registered(self, name, isolated_home):
        assert name in vt.registry._tools

    def test_tools_in_vision_toolset(self, isolated_home):
        import toolsets

        tools = toolsets.TOOLSETS["vision"]["tools"]
        for name in ["image_ocr", "document_extract", "screen_capture", "screen_understand"]:
            assert name in tools


class TestDocumentExtractTool:
    def test_markdown_extraction(self, tmp_path, isolated_home):
        md = tmp_path / "doc.md"
        md.write_text("# Title\n\nBody\n", encoding="utf-8")
        result = json.loads(asyncio.run(vt.registry._tools["document_extract"].handler({"path": str(md)})))
        assert result["success"] is True
        assert result["media_type"] == "markdown"

    def test_missing_path(self, isolated_home):
        result = json.loads(asyncio.run(vt.registry._tools["document_extract"].handler({})))
        assert result["success"] is False
        assert "path" in result["error"]


class TestScreenCaptureTool:
    def test_returns_json(self, isolated_home):
        result = json.loads(asyncio.run(vt.registry._tools["screen_capture"].handler({})))
        assert "success" in result


class TestScreenUnderstandTool:
    def test_missing_path(self, isolated_home):
        result = json.loads(asyncio.run(vt.registry._tools["screen_understand"].handler({})))
        assert result["success"] is False
        assert "path" in result["error"]


class TestImageOCRTool:
    def test_missing_path(self, isolated_home):
        result = json.loads(asyncio.run(vt.registry._tools["image_ocr"].handler({})))
        assert result["success"] is False
        assert "path" in result["error"]
