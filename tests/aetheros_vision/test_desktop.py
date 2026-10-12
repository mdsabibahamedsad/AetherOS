"""Tests for aetheros_vision.desktop — desktop & browser UI understanding."""

import pytest
from PIL import Image, ImageDraw


@pytest.fixture
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("AETHEROS_HOME", str(tmp_path / ".aetheros"))
    return tmp_path / ".aetheros"


def _make_screenshot(path):
    img = Image.new("RGB", (400, 200), "white")
    d = ImageDraw.Draw(img)
    d.rectangle([20, 20, 120, 60], fill="lightgray")
    d.text((30, 35), "Submit", fill="black")
    img.save(path)


class TestBrowserVision:
    def test_accessibility_tree_walk(self, isolated_home):
        from aetheros_vision.desktop import BrowserVision

        tree = {
            "role": "dialog",
            "children": [
                {"role": "button", "name": "OK", "box": {"x": 10, "y": 10, "width": 50, "height": 20}},
                {"role": "textbox", "name": "Email"},
            ],
        }
        result = BrowserVision().analyze_snapshot(tree)
        assert result.success is True
        assert result.text == "OK\nEmail"
        elements = result.metadata["elements"]
        assert len(elements) == 2
        assert elements[0]["role"] == "button"
        assert elements[0]["box"]["x"] == 10

    def test_ignores_non_dict_nodes(self, isolated_home):
        from aetheros_vision.desktop import BrowserVision

        tree = {"role": "root", "children": [None, "text", 42]}
        result = BrowserVision().analyze_snapshot(tree)
        assert result.success is True


class TestDesktopVision:
    def test_analyze_without_ocr_fails_cleanly(self, tmp_path, isolated_home):
        from aetheros_vision.desktop import DesktopVision

        p = tmp_path / "shot.png"
        _make_screenshot(p)
        result = DesktopVision().analyze_screenshot(str(p))
        # Either OCR works (returns elements) or fails cleanly — never fabricates.
        if result.success:
            assert "elements" in result.metadata
        else:
            assert result.error

    def test_find_element_not_found(self, tmp_path, isolated_home):
        from aetheros_vision.desktop import DesktopVision

        p = tmp_path / "shot.png"
        _make_screenshot(p)
        el = DesktopVision().find_element(str(p), "nonexistent-xyz-123")
        assert el is None
