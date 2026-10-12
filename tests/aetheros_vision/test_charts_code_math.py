"""Tests for aetheros_vision charts, code, and math heuristics."""

import pytest
from PIL import Image, ImageDraw

from aetheros_vision.charts import estimate_chart
from aetheros_vision.code import analyze_code_screenshot
from aetheros_vision.math import analyze_math_text


@pytest.fixture
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("AETHEROS_HOME", str(tmp_path / ".aetheros"))
    return tmp_path / ".aetheros"


def _make_bar_chart(path):
    img = Image.new("RGB", (400, 300), "white")
    d = ImageDraw.Draw(img)
    d.rectangle([50, 200, 120, 290], fill="blue", outline="black", width=2)
    d.rectangle([150, 150, 220, 290], fill="red", outline="black", width=2)
    d.rectangle([250, 100, 320, 290], fill="green", outline="black", width=2)
    d.line([40, 295, 380, 295], fill="black", width=2)
    d.line([40, 295, 40, 40], fill="black", width=2)
    img.save(path)


class TestEstimateChart:
    def test_bar_chart_detected(self, tmp_path, isolated_home):
        p = tmp_path / "bar.png"
        _make_bar_chart(p)
        result = estimate_chart(str(p))
        assert result.chart_type == "bar"
        assert result.bars >= 1
        assert result.confidence > 0

    def test_blank_image_not_high_confidence_chart(self, tmp_path, isolated_home):
        p = tmp_path / "blank.png"
        Image.new("RGB", (200, 200), "white").save(p)
        result = estimate_chart(str(p))
        # A plain white image has no saturated color clusters or edges.
        assert result.series_count == 0
        assert result.bars == 0


class TestCodeScreenshotAnalyzer:
    def test_analyze_no_ocr_returns_failure(self, tmp_path, isolated_home):
        # Without an OCR provider, analysis fails cleanly — no fabricated code.
        from aetheros_vision.code import CodeScreenshotAnalyzer

        p = tmp_path / "code.png"
        Image.new("RGB", (300, 150), "white").save(p)
        result = CodeScreenshotAnalyzer().analyze(str(p))
        assert result.success is False
        assert result.error is not None

    def test_analyze_code_screenshot_text(self, isolated_home):
        insight = analyze_code_screenshot("def foo():\n    import os\n    return 1")
        assert insight.language == "python"
        assert insight.confidence > 0

    def test_error_detection(self, isolated_home):
        insight = analyze_code_screenshot("Traceback (most recent call last):\n  File \"x.py\", line 1, in <module>\n    NameError: name 'foo' is not defined")
        assert len(insight.error_messages) > 0
        assert len(insight.stack_traces) > 0


class TestMathAnalyzer:
    def test_extract_expression_from_text(self, isolated_home):
        result = analyze_math_text("solve 2+2=4")
        assert result.has_math_notation is True
        assert len(result.equations) >= 1
        assert "equation" in result.notation_types

    def test_no_math_in_plain_text(self, isolated_home):
        result = analyze_math_text("hello world this is prose")
        assert result.has_math_notation is False
